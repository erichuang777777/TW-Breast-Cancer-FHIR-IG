$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    # The PHI gate runs first. Any detected patient data blocks publication.
    python scripts\check_no_phi.py
    if ($LASTEXITCODE -ne 0) { throw "PHI gate failed; inspect the findings above" }

    python scripts\build_qbc_ig_mapping.py
    if ($LASTEXITCODE -ne 0) { throw "formal FHIR mapping build failed" }

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
    Write-Host "Community Preview is publishable. Production use still requires local governance and acceptance."
}
finally {
    Pop-Location
}
