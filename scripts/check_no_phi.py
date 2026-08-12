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
import re
import subprocess
import sys
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
SKIP_SUFFIXES = {
    ".pdf", ".docx", ".doc", ".xls", ".xlsx", ".zip", ".jar", ".tgz",
    ".png", ".jpg", ".svg", ".ico", ".woff", ".ttf", ".eot", ".otf", ".pyc",
}


def _git(*args: str) -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [line for line in out.stdout.splitlines() if line.strip()]


def candidate_files(staged: bool) -> tuple[list[Path], str]:
    if staged:
        names = _git("diff", "--cached", "--name-only", "--diff-filter=ACM")
        if names is None:
            raise SystemExit("--staged 需要 git repository")
        return [ROOT / n for n in names], "git staged"

    names = _git("ls-files", "--cached", "--others", "--exclude-standard")
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


def scan(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel in SELF_REFERENTIAL or path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if match.group(0) in SYNTHETIC_ALLOWLIST:
                    continue
                findings.append(f"{rel}:{lineno}: {label} -> {match.group(0)!r}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="發布前個資洩漏閘門")
    parser.add_argument("--staged", action="store_true", help="只掃描 git staged 內容")
    args = parser.parse_args()

    files, mode = candidate_files(args.staged)
    findings: list[str] = []
    for path in files:
        if path.is_file():
            findings.extend(scan(path))

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

    print(f"個資洩漏閘門通過：已掃描 {len(files)} 個檔案（{mode}），未發現病歷號或個案識別資訊。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
