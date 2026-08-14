"""從目前工作樹產生 workbench 發布包。

取代先前以手動複製產生、且已與原始碼脫節的 `release/` 快照。檔案清單一律
由本腳本從 git 追蹤檔推導，因此不會再出現「發布包缺模組」的情形。

先決條件：`scripts/check_no_phi.py` 必須通過——發布包不得含任何個案資料。

用法：
    python scripts/build_release.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"

# 納入發布包的路徑前綴（相對於專案根目錄）。
INCLUDE_PREFIXES = (
    "qbc_workbench/",
    "tests/",
    "scripts/",
    "config/",
    "outputs/qbc_conformance/",
    "outputs/qbc_test_pack/",
    "outputs/qbc_ig_mapping/",
    # 只含 SHA-256 與行數統計；官方文件全文與逐行 CSV 由 .gitignore 排除，
    # 因此 tracked_files() 不會選到它們。
    "outputs/source_audit/",
)
INCLUDE_FILES = (
    "README.md",
    "RELEASE_NOTES.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "run_workbench.bat",
    ".gitignore",
)


def version() -> str:
    text = (ROOT / "qbc_workbench" / "__init__.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("在 qbc_workbench/__init__.py 找不到 __version__")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    gate = subprocess.run([sys.executable, "scripts/check_no_phi.py"], cwd=ROOT)
    if gate.returncode != 0:
        print("個資閘門未通過，中止打包。", file=sys.stderr)
        return 1

    ver = version()
    name = f"qbc-review-workbench-{ver}"
    staging = RELEASE_DIR / name
    archive = RELEASE_DIR / f"{name}.zip"

    selected = [
        f for f in tracked_files()
        if f.startswith(INCLUDE_PREFIXES) or f in INCLUDE_FILES
    ]
    if not selected:
        print("沒有可打包的檔案，請確認已 git init。", file=sys.stderr)
        return 1

    if staging.exists():
        shutil.rmtree(staging)
    for rel in selected:
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)

    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in selected:
            zf.write(staging / rel, f"{name}/{rel}")

    print(f"發布包：{archive.relative_to(ROOT)}（{len(selected)} 個檔案，版本 {ver}）")
    print(f"展開目錄：{staging.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
