# TWPAS projection mappings

This directory contains community-authored design artifacts for projecting Taiwan Breast Cancer common FHIR facts into the official Taiwan NHI Prior Authorization Support IG (TWPAS) task.

- `breast-common-to-twpas-1.2.5.csv` records clinical-fact projection candidates.
- `twpas-task-only-fields-1.2.5.csv` records application data that must remain owned by the prior-authorization workflow.
- `twpas-version-policy.csv` is the machine-readable release gate: published 1.2.5 is blocking; CI 1.2.6 is advisory only.
- `twpas-ci-1.2.6-watchlist.csv` records CI changes that may affect the breast-cancer projection and the regression checks required before a future upgrade.

These files do not copy, modify, or replace official TWPAS profiles, terminology, constraints, or CQL. The authoritative specification is `tw.gov.mohw.nhi.pas#1.2.5` at <https://nhicore.nhi.gov.tw/pas/>. A generated output may claim TWPAS conformance only after validation against that official package and completion of the applicable NHIA acceptance process.

The mappings contain no patient values. Public examples must remain fully synthetic.

The continuous build at <https://build.fhir.org/ig/TWNHIFHIR/pas/> is useful as an early-warning source, but it changes over time and is not an authorized publication. It must not be added as the main IG dependency, used to claim conformance, or replace validation against the currently published package. A CI warning becomes a blocking release requirement only after the corresponding version is officially published and this policy is deliberately updated.
