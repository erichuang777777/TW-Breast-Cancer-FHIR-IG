# TWPAS projection mappings

This directory contains community-authored design artifacts for projecting Taiwan Breast Cancer common FHIR facts into the official Taiwan NHI Prior Authorization Support IG (TWPAS) task.

- `breast-common-to-twpas-1.2.5.csv` records clinical-fact projection candidates.
- `twpas-task-only-fields-1.2.5.csv` records application data that must remain owned by the prior-authorization workflow.

These files do not copy, modify, or replace official TWPAS profiles, terminology, constraints, or CQL. The authoritative specification is `tw.gov.mohw.nhi.pas#1.2.5` at <https://nhicore.nhi.gov.tw/pas/>. A generated output may claim TWPAS conformance only after validation against that official package and completion of the applicable NHIA acceptance process.

The mappings contain no patient values. Public examples must remain fully synthetic.
