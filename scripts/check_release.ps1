$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    # The PHI gate runs first. Any detected patient data blocks publication.
    python scripts\check_no_phi.py `
        --json-out ig\output\repository-phi-pattern-scan-audit.json
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

    python scripts\audit_artifact_conformance.py `
        --register mappings\publication\artifact-conformance-register.csv `
        --scope-claims mappings\publication\ig-scope-claim-register.csv `
        --resource-dir ig\fsh-generated\resources `
        --resource-dir ig\input\resources `
        --json-out ig\output\artifact-conformance-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "artifact-conformance integrity audit failed" }

    python scripts\audit_terminology_conformance.py `
        --approval-register mappings\publication\case-management-terminology-approval-register.csv `
        --cql ig\input\cql\BreastCancerCaseManagement.cql `
        --resource-dir ig\fsh-generated\resources `
        --resource-dir ig\input\resources `
        --json-out ig\output\terminology-conformance-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "terminology-conformance integrity audit failed" }

    python scripts\audit_fhir_resource_inventory.py `
        --register mappings\publication\fhir-resource-inventory.csv `
        --version-policy-register mappings\publication\canonical-version-policy-register.csv `
        --generated-resource-dir ig\fsh-generated\resources `
        --manual-resource-dir ig\input\resources `
        --cql ig\input\cql\BreastCancerCaseManagement.cql `
        --json-out ig\output\fhir-resource-inventory-audit.json `
        --target inventory
    if ($LASTEXITCODE -ne 0) { throw "FHIR resource inventory audit failed" }

    python scripts\audit_fhir_reference_graph.py `
        --generated-resource-dir ig\fsh-generated\resources `
        --manual-resource-dir ig\input\resources `
        --sushi-config ig\sushi-config.yaml `
        --json-out ig\output\fhir-reference-graph-audit.json
    if ($LASTEXITCODE -ne 0) { throw "FHIR reference graph audit failed" }

    python scripts\audit_data_correctness_evidence.py `
        --source-register mappings\publication\source-traceability-register.csv `
        --validation-register mappings\publication\measure-validation-evidence-register.csv `
        --common-mapping mappings\case-management\breast-common-to-case-management.csv `
        --task-mapping mappings\case-management\case-management-task-only-fields.csv `
        --measure-catalog mappings\case-management\case-management-measure-catalog.csv `
        --population-criteria mappings\case-management\case-management-population-criteria.csv `
        --json-out ig\output\data-correctness-evidence-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "data-correctness evidence integrity audit failed" }

    python scripts\audit_source_acquisition_priority.py `
        --register mappings\publication\source-acquisition-priority.csv `
        --common-mapping mappings\case-management\breast-common-to-case-management.csv `
        --task-mapping mappings\case-management\case-management-task-only-fields.csv `
        --population-criteria mappings\case-management\case-management-population-criteria.csv `
        --source-register mappings\publication\source-traceability-register.csv `
        --json-out ig\output\source-acquisition-priority-audit.json
    if ($LASTEXITCODE -ne 0) { throw "source-acquisition priority audit failed" }

    python scripts\audit_source_acquisition_work_packages.py `
        --register mappings\publication\source-acquisition-work-packages.csv `
        --priority-register mappings\publication\source-acquisition-priority.csv `
        --json-out ig\output\source-acquisition-work-packages-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "source-acquisition work-package audit failed" }

    python scripts\audit_criterion_implementation_crosscheck.py `
        --register mappings\publication\criterion-implementation-crosscheck.csv `
        --criteria mappings\case-management\case-management-population-criteria.csv `
        --source-register mappings\publication\source-traceability-register.csv `
        --task-mapping mappings\case-management\case-management-task-only-fields.csv `
        --cql ig\input\cql\BreastCancerCaseManagement.cql `
        --fsh-directory ig\input\fsh `
        --json-out ig\output\criterion-implementation-crosscheck-audit.json
    if ($LASTEXITCODE -ne 0) { throw "criterion implementation crosscheck failed" }

    python scripts\audit_criterion_resolution_decisions.py `
        --register mappings\publication\criterion-resolution-decision-register.csv `
        --crosscheck mappings\publication\criterion-implementation-crosscheck.csv `
        --json-out ig\output\criterion-resolution-decision-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "criterion resolution decision audit failed" }

    python scripts\audit_release_controls.py `
        --controls mappings\publication\release-control-register.csv `
        --measure-audit mappings\publication\case-management-measure-audit.csv `
        --terminology-fsh ig\input\fsh\case-management-terminology.fsh `
        --approval-register outputs\qbc_ig_mapping\qbc_mapping_approval_register.csv `
        --measure-approval-register mappings\publication\case-management-measure-approval-register.csv `
        --scope-claims mappings\publication\ig-scope-claim-register.csv `
        --scope-decisions mappings\publication\publication-scope-decision-register.csv `
        --artifact-audit ig\output\artifact-conformance-audit.json `
        --terminology-audit ig\output\terminology-conformance-audit.json `
        --resource-inventory-audit ig\output\fhir-resource-inventory-audit.json `
        --reference-graph-audit ig\output\fhir-reference-graph-audit.json `
        --data-evidence-audit ig\output\data-correctness-evidence-audit.json `
        --source-work-package-audit ig\output\source-acquisition-work-packages-audit.json `
        --criterion-resolution-audit ig\output\criterion-resolution-decision-audit.json `
        --publisher-audit ig\output\publisher-warning-audit.json `
        --phi-audit ig\output\repository-phi-pattern-scan-audit.json `
        --json-out ig\output\release-control-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "release-control integrity audit failed" }

    python scripts\audit_verification_methods.py `
        --register mappings\publication\verification-method-register.csv `
        --controls mappings\publication\release-control-register.csv `
        --release-audit ig\output\release-control-audit.json `
        --json-out ig\output\verification-method-audit.json `
        --target integrity
    if ($LASTEXITCODE -ne 0) { throw "verification-method integrity audit failed" }

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
