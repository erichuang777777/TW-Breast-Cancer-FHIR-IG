# Case management indicators task mappings

Design artifacts for the **case management indicators** task: everything the
breast cancer case-management team calculates from its caseload and reports on
a fixed cadence. Two report families sit in this one task:

- **品質指標（quality）** — the six multidisciplinary-team quality and core
  indicators reported quarterly to the cancer committee, three of which are
  mandatory core indicators. Measures `bc-qi-01` … `bc-qi-06`.
- **個管季報（quarterly）** — the case-management quarterly/half-yearly report
  filed with the cancer centre: caseload, new-diagnosis dynamics, demographic
  and stage distributions, and five reported rates. Measures `bc-qr-01` …
  `bc-qr-05` plus the cohort measures `bc-qr-10` … `bc-qr-18`.

## Why one task and not two

The two reports have **different auditors** — the cancer committee reviews
guideline conformance, the cancer centre reviews caseload and retention — and
they are read as two documents by two groups of people. The `indicator_family`
column keeps them separately readable.

They nevertheless run on **the same clinical facts**. Held as two mapping sets
they drifted immediately: the same stage-group observation was described twice,
with two ids and two projection rules, and nothing forced the two descriptions
to agree. One mapping table, one row per fact, is the maintainable shape. Six
of the 34 common-layer facts and two of the 18 task-only fields are used by
both families, and each carries its `legacy_ids` so the earlier split remains
traceable.

Splitting the *output* is a rendering decision. Splitting the *model* was a
maintenance liability.

## Files

- `breast-common-to-case-management.csv` — clinical facts both report families
  project from the breast cancer common layer. `used_by_indicator_family` says
  which family needs each fact; `worksheet_column_quality` and
  `worksheet_column_quarterly` say where it lives on today's worksheets.
- `case-management-measure-catalog.csv` — every `Measure`: the six quality
  indicators with their team-set thresholds, the five quarterly rates, and the
  nine cohort measures carrying the distribution tables as stratifiers.
- `case-management-population-criteria.csv` — one row per measure population or
  stratum. This is the **single source of truth** both the CQL library and the
  Python reference implementation are generated from and checked against.
- `case-management-task-only-fields.csv` — case-management and committee
  workflow data that must not be promoted into the shared clinical layer.
- `python-implementation-manifest.json` — which `criterion_id`s the Python
  reference implementation actually evaluates, generated from
  `個管品管_1_品質核心指標統計/pipeline/rules.py`'s `CRITERION_IDS` /
  `UNIMPLEMENTED_CRITERIA` (see `pipeline/export_criteria_manifest.py` there).
  Its `families_covered` is `["quality"]` only: the **`quarterly` family's**
  Python reference implementation lives in a separate project
  (`個管品管_2_季報統計/scripts/quarterly_report.py`) that has not been audited
  against this CSV, so `bc-qr-*` rows' `python_status` values are currently
  **unverified claims**, not checked facts - `tests/test_case_management_measures.py`
  only compares `python_status` against this manifest for the `quality` family.

## Not the NHI P4P programme indicators

This task is **unrelated to the NHI P4P programme indicators** documented on the
[品質監控指標](../../ig/input/pagecontent/quality-indicators.md) page. Both concern breast
cancer and some measure titles read alike, but the denominators, exclusions,
thresholds, reporting body and calculation owner all differ. Do not reuse a
definition across the two.

## Reporting unit

The two families report at different levels and this is part of the model, not
a formatting detail:

- quality indicators — the multidisciplinary team; one figure per indicator per
  quarter for the whole team.
- quarterly report — **the individual case manager**; each worksheet column is
  one caseload. `MeasureReport.reporter` carries the case manager and a facility
  figure is the sum of the reports, never a separate calculation.

## Generated from these files

- `ig/input/fsh/case-management-measures.fsh` — 20 `Measure` resources, one
  shared `Library`, one `MeasureReport` profile. Both families point at the same
  library; splitting it would re-create the drift the merge removed.
- `ig/input/cql/BreastCancerCaseManagement.cql` — the population and stratifier
  logic, each define carrying the `criterion_id` it implements.
- `tests/test_case_management_measures.py` — binds the three descriptions
  together: catalog to Measure, criteria row to population, expression to
  define, criterion id to CQL comment.

## Status

Terminology in these files is marked `candidate-unverified` wherever the LOINC
or SNOMED CT code has not yet been checked against the published release. No
code carrying that status may be used in a generated artifact.

The mappings contain no patient values. Examples must remain fully synthetic.
