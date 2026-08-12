$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    # 個資閘門必須最先通過：其餘檢查再乾淨，只要有病歷資料外流就不得發布。
    python scripts\check_no_phi.py
    if ($LASTEXITCODE -ne 0) { throw "PHI gate failed; inspect the findings above" }

    python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

    python scripts\build_qbc_test_pack.py
    if ($LASTEXITCODE -ne 0) { throw "synthetic test pack failed" }

    Push-Location (Join-Path $root "ig")
    try {
        .\sushi.cmd .
        if ($LASTEXITCODE -ne 0) { throw "SUSHI failed" }
        $env:Path = (Get-Location).Path + ";" + $env:Path
        java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
        if ($LASTEXITCODE -ne 0) { throw "IG Publisher failed" }
        $qa = Get-Content -Raw -Encoding UTF8 output\qa.html
        if ($qa -notmatch "errors = 0, warn = 0, info = \d+, broken links = 0") {
            throw "IG QA is not clean; inspect ig/output/qa.html"
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "Release checks passed: PHI gate, pytest, synthetic test pack, SUSHI and IG Publisher QA."
    Write-Host "尚未涵蓋（需人工完成）：115 欄臨床簽核、已知歧義的健保署書面確認、院內資安核准、健保 VPN 驗收。"
}
finally {
    Pop-Location
}
