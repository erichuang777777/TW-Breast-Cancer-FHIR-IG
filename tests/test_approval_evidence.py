import hashlib
from pathlib import Path

from scripts.approval_evidence import retained_evidence_matches


def test_retained_evidence_requires_safe_existing_file_and_exact_hash(tmp_path: Path):
    register = tmp_path / "register.csv"
    register.write_text("header\n", encoding="utf-8")
    evidence = tmp_path / "review.json"
    evidence.write_text('{"decision":"approve"}\n', encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    row = {"path": "review.json", "hash": digest}
    assert retained_evidence_matches(
        row, register, path_field="path", hash_field="hash"
    )
    row["hash"] = "f" * 64
    assert not retained_evidence_matches(
        row, register, path_field="path", hash_field="hash"
    )


def test_retained_evidence_rejects_url_absolute_and_parent_escape(tmp_path: Path):
    register = tmp_path / "register.csv"
    register.write_text("header\n", encoding="utf-8")
    for value in (
        "https://example.org/review.json",
        str((tmp_path / "review.json").resolve()),
        "../review.json",
    ):
        row = {"path": value, "hash": "a" * 64}
        assert not retained_evidence_matches(
            row, register, path_field="path", hash_field="hash"
        )


def test_real_worktree_requires_the_locked_publication_evidence_directory(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "scripts").mkdir()
    evidence_root = tmp_path / "mappings" / "publication" / "evidence"
    evidence_root.mkdir(parents=True)
    register = tmp_path / "mappings" / "publication" / "register.csv"
    register.write_text("header\n", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    outside_hash = hashlib.sha256(outside.read_bytes()).hexdigest()
    assert not retained_evidence_matches(
        {"path": "outside.json", "hash": outside_hash},
        register,
        path_field="path",
        hash_field="hash",
    )
    inside = evidence_root / "review.json"
    inside.write_text("{}\n", encoding="utf-8")
    inside_hash = hashlib.sha256(inside.read_bytes()).hexdigest()
    assert retained_evidence_matches(
        {
            "path": "mappings/publication/evidence/review.json",
            "hash": inside_hash,
        },
        register,
        path_field="path",
        hash_field="hash",
    )
