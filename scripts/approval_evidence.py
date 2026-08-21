"""Shared validation for repository-retained approval evidence."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def repository_root_for(path: Path) -> Path:
    """Use the containing Git worktree, or the register directory in fixtures."""
    resolved = path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        if (
            (parent / ".git").exists()
            and (parent / "scripts").is_dir()
            and (parent / "mappings").is_dir()
        ):
            return parent
    return resolved.parent


def resolve_repository_evidence(
    raw_path: str,
    register_path: Path,
    *,
    require_retained_approval_evidence: bool = True,
) -> Path | None:
    """Resolve a safe repository-relative evidence path without accepting URLs."""
    candidate = Path(raw_path)
    if (
        not raw_path.strip()
        or "://" in raw_path
        or candidate.is_absolute()
        or ".." in candidate.parts
    ):
        return None
    root = repository_root_for(register_path)
    resolved = (root / candidate).resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError:
        return None
    if (
        require_retained_approval_evidence
        and (root / ".git").exists()
        and (root / "scripts").is_dir()
        and relative.parts[:3] != ("mappings", "publication", "evidence")
    ):
        return None
    return resolved if resolved.is_file() else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retained_evidence_matches(
    row: dict[str, str],
    register_path: Path,
    *,
    path_field: str,
    hash_field: str,
) -> bool:
    """Require the declared SHA-256 to match a retained, local evidence file."""
    declared_hash = row.get(hash_field, "").strip()
    if SHA256.fullmatch(declared_hash) is None:
        return False
    evidence_path = resolve_repository_evidence(
        row.get(path_field, "").strip(), register_path
    )
    return bool(
        evidence_path
        and file_sha256(evidence_path).lower() == declared_hash.lower()
    )
