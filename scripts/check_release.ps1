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
    }
    finally {
        Pop-Location
    }

    python scripts\audit_publisher_qa.py `
        --qa-text ig\output\qa.txt `
        --qa-html ig\output\qa.html `
        --policy mappings\publication\publisher-warning-policy.csv `
        --json-out ig\output\publisher-warning-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "Publisher warning integrity audit failed" }

    python scripts\audit_release_controls.py `
        --controls mappings\publication\release-control-register.csv `
        --measure-audit mappings\publication\case-management-measure-audit.csv `
        --terminology-fsh ig\input\fsh\case-management-terminology.fsh `
        --approval-register outputs\qbc_ig_mapping\qbc_mapping_approval_register.csv `
        --measure-approval-register mappings\publication\case-management-measure-approval-register.csv `
        --scope-claims mappings\publication\ig-scope-claim-register.csv `
        --scope-decisions mappings\publication\publication-scope-decision-register.csv `
        --publisher-audit ig\output\publisher-warning-audit.json `
        --json-out ig\output\release-control-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "release-control integrity audit failed" }

    $publisherAudit = Get-Content -Raw -Encoding UTF8 ig\output\publisher-warning-audit.json | ConvertFrom-Json
    $releaseAudit = Get-Content -Raw -Encoding UTF8 ig\output\release-control-audit.json | ConvertFrom-Json
    Write-Host "Technical checks passed: PHI, pytest, synthetic pack, SUSHI, Publisher and evidence integrity."
    Write-Host "Community Preview gate: $($publisherAudit.community_preview_gate)"
    Write-Host "Complete formal release gate: $($releaseAudit.formal_release_gate)"
    Write-Host "Maximum supported claim: $($releaseAudit.maximum_supported_claim)"
}
finally {
    Pop-Location
}
