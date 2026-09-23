# TW Breast Cancer synthetic test cohort

The repository can build a deterministic 100-patient FHIR R4 test cohort from
the two public MITRE mCODE STU2/Synthea breast-cancer archives. The cohort is
for FHIR server, SMART on FHIR, CQL, mapping and conformance tests only. It is
not representative of Taiwan's population and is not for clinical use.

## Inputs

Place these immutable source files at the repository root:

- `mcode_2_0_10yrs_breast.zip`
- `mcode_2_0_longitudinal_breast.zip`

The archives are intentionally ignored by Git. They can be downloaded from the
MITRE links documented on the HL7 mCODE Test Data page and remain subject to
their source terms:

- Ten-year breast-cancer history: <https://mitre.box.com/shared/static/c6ca6y2jfumrhw4nu20kztktxdlhhzo8.zip>
- Longitudinal breast-cancer history: <https://mitre.box.com/shared/static/59n7mcm8si0qk3p36ud0vmrcdv7pr0s7.zip>

## Build

```powershell
python scripts/build_tw_synthetic_cohort.py
```

The default artifact is
`outputs/synthetic_cohort/tw-breast-cancer-synthetic-100-v0.1.zip`.

The selection is stable: 50 patient Bundles come from the ten-year dataset and
50 from the longitudinal dataset. The seed, input member name, source hash and
output hash are recorded in `manifest.csv` inside the artifact.

## Preservation and profiling policy

- Clinical text stays in English; there is no forced `zh-TW` translation.
- Every original FHIR resource, element, value, reference and entry request is
  retained.
- Original mCODE and US Core profile declarations are retained.
- Recognized breast-cancer resources receive an additional TW Breast Cancer IG
  draft profile declaration.
- A profile declaration is a conformance claim. The generated artifact must be
  checked with the matching FHIR packages before production-like use; failed
  dual-profile validation must be reported rather than hidden by deleting data.

The source patient Bundles contain external `urn:uuid` references exclusively
in `Provenance.target`. They are retained as source lineage and counted in the
summary. Clinical graph references resolve within each patient Bundle.
