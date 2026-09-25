"""發布前的個資洩漏閘門。

掃描「真的會進入版本控制或發布物」的檔案，確認沒有病歷號、個案檔名、身分證號
或受控隔離目錄的內容外流。任何命中都會讓本腳本以非零 exit code 結束。

檔案清單優先取自 `git ls-files --cached --others --exclude-standard`，因此
`.gitignore` 排除的內容（private/、runtime/、ig/output/、ig/tools/ 等）自動
不在掃描範圍內——它們本來就不會被提交。尚未 git init 時退回手動走訪。

合成識別碼必須在 SYNTHETIC_ALLOWLIST 明確宣告；未宣告的一律視為發現。

用法：
    python scripts/check_no_phi.py            # 掃描會被提交的檔案
    python scripts/check_no_phi.py --staged   # 只掃描 git staged 內容
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 一律不得出現在可提交檔案中的樣式。
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # 台灣身分證／居留證號：1 英文字母 + 性別碼(1/2/8/9) + 8 位數字
    ("疑似身分證／居留證號", re.compile(r"\b[A-Z][1289]\d{8}\b")),
    # 病歷號樣式：1 英文字母 + 6~8 位數字（本專案既有個案檔採此格式）
    ("疑似病歷號", re.compile(r"\b[A-Z]\d{6,8}\b")),
    # 受控目錄下的實際檔名不得被引用
    ("個案／名單檔名", re.compile(r"EligibleList[\w]*\.xls|新診斷及測試名單|test_case\.xlsx")),
]

# 明確宣告的合成／官方範例識別碼。新增前請確認該值確實不對應真實個案。
SYNTHETIC_ALLOWLIST = {
    "A123456789",   # 官方 Word 主表逐字轉錄的格式範例
    "B123456789",   # 合成測試包主責醫師
    "Z000000000",   # 合成 IG 範例個案
    "Z00000000",    # 合成測試包個案
    "Z999999999",   # 負向測試個案
}

# 本身就在描述這些樣式的檔案，掃描會必然自我命中。
SELF_REFERENTIAL = {"scripts/check_no_phi.py", ".gitignore"}

# 尚未 git init 時的退回清單。
FALLBACK_SKIP_DIRS = {
    ".git", "private", "patients", "incoming", "runtime", "release",
    "__pycache__", ".pytest_cache", ".venv", ".omc", ".npm-cache",
    "output", "temp", "template", "input-cache", "fsh-generated",
    "node_modules", "tools", "source_audit",
}
OFFICE_OPEN_XML_SUFFIXES = {".docx", ".xlsx"}
OFFICE_TEXT_MEMBER_SUFFIXES = {".xml", ".rels", ".txt", ".csv"}
# These formats may carry patient data but cannot be inspected reliably without
# an additional parser/OCR step.  A committable instance is therefore a finding,
# never a silent skip.
OPAQUE_SENSITIVE_SUFFIXES = {
    ".pdf", ".doc", ".xls", ".zip", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
}
SKIP_SUFFIXES = {
    ".jar", ".tgz", ".ico", ".woff", ".ttf", ".eot", ".otf", ".pyc",
}


def _git(*args: str, nul_delimited: bool = False) -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    separator = "\0" if nul_delimited else "\n"
    return [item for item in out.stdout.split(separator) if item]


def candidate_files(staged: bool) -> tuple[list[Path], str]:
    if staged:
        names = _git(
            "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z",
            nul_delimited=True,
        )
        if names is None:
            raise SystemExit("--staged 需要 git repository")
        return [ROOT / n for n in names], "git staged"

    names = _git(
        "ls-files", "--cached", "--others", "--exclude-standard", "-z",
        nul_delimited=True,
    )
    if names is not None:
        return [ROOT / n for n in names], "git 可提交檔案"

    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in FALLBACK_SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files, "手動走訪（尚未 git init）"


def _scan_text(text: str, location: str) -> list[str]:
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if match.group(0) in SYNTHETIC_ALLOWLIST:
                    continue
                findings.append(
                    f"{location}:{lineno}: {label} -> {match.group(0)!r}"
                )
    return findings


def _decode_text_payload(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    declaration = re.search(
        br"<\?xml[^>]*\bencoding=[\"']([A-Za-z0-9._-]+)[\"']",
        data[:256],
        re.IGNORECASE,
    )
    if declaration:
        try:
            return data.decode(declaration.group(1).decode("ascii"))
        except (LookupError, UnicodeDecodeError):
            return None
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    return None


def scan(path: Path, root: Path = ROOT) -> list[str]:
    rel = path.relative_to(root).as_posix()
    if rel in SELF_REFERENTIAL or path.suffix.lower() in SKIP_SUFFIXES:
        return []
    suffix = path.suffix.lower()
    if suffix in OPAQUE_SENSITIVE_SUFFIXES:
        return [f"{rel}: 無法自動檢查的敏感二進位格式 {suffix}"]
    if suffix in OFFICE_OPEN_XML_SUFFIXES:
        try:
            findings: list[str] = []
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if Path(member.filename).suffix.lower() not in OFFICE_TEXT_MEMBER_SUFFIXES:
                        continue
                    text = _decode_text_payload(archive.read(member))
                    if text is None:
                        return [
                            f"{rel}!{member.filename}: Office 文字內容無法解碼檢查"
                        ]
                    findings.extend(_scan_text(text, f"{rel}!{member.filename}"))
            return findings
        except (OSError, zipfile.BadZipFile):
            return [f"{rel}: Office Open XML 檔無法解包檢查"]
    try:
        data = path.read_bytes()
    except OSError:
        return [f"{rel}: 檔案無法讀取，未完成個資檢查"]
    text = _decode_text_payload(data)
    if text is None:
        return [f"{rel}: 未列入安全略過清單且無法解碼檢查的二進位內容"]
    return _scan_text(text, rel)


def main() -> int:
    parser = argparse.ArgumentParser(description="發布前個資洩漏閘門")
    parser.add_argument("--staged", action="store_true", help="只掃描 git staged 內容")
    parser.add_argument("--json-out", type=Path, help="寫出不含命中值的機器可讀證據")
    args = parser.parse_args()

    files, mode = candidate_files(args.staged)
    existing_files = [path for path in files if path.is_file()]
    excluded_files = [
        path for path in existing_files
        if path.relative_to(ROOT).as_posix() in SELF_REFERENTIAL
        or path.suffix.lower() in SKIP_SUFFIXES
    ]
    findings: list[str] = []
    for path in existing_files:
        findings.extend(scan(path))

    report = {
        "gate_scope": "committable-publication-content-phi-pattern-scan",
        "scan_mode": mode,
        "candidate_file_count": len(files),
        "inspected_file_count": len(existing_files) - len(excluded_files),
        "scanner_exclusion_count": len(excluded_files),
        "pattern_count": len(PATTERNS),
        "office_open_xml_scanning": "enabled",
        "opaque_sensitive_file_policy": "block",
        "finding_count": len(findings),
        "repository_phi_pattern_scan_gate": "block" if findings else "pass",
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if findings:
        print(f"個資洩漏閘門：發現不得提交／發布的內容（來源：{mode}）", file=sys.stderr)
        for item in findings:
            print(f"  {item}", file=sys.stderr)
        print(
            "\n請將相關檔案移入 private/ 受控目錄、改以目錄層級描述，"
            "或確認為合成值後加入 SYNTHETIC_ALLOWLIST。",
            file=sys.stderr,
        )
        return 1

    print(
        f"個資洩漏閘門通過：已檢查 {report['inspected_file_count']} 個檔案"
        f"（候選 {len(files)}；{mode}），未發現病歷號或個案識別資訊。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
