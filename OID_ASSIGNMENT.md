# OID assignment record

This IG uses Publisher-managed OIDs for canonical resources. The assignment is
technical identity metadata only; it does not imply HL7, government, clinical,
or submission endorsement.

- Canonical URL: `https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG`
- Derivation: UUIDv5 with the standard URL namespace and the exact canonical URL
- UUID: `1c7c518e-9bbc-5fb6-8b33-68fe36428e0d`
- OID root: `2.25.37863882866210842446634463448013114893`
- Assignment register: `ig/oids.ini`

FHIR Publisher documents that `auto-oid-root` must be globally unique, may be
self-assigned, and that the generated `oids.ini` must be committed with the IG.
The UUID-derived `2.25` arc provides a stable root without claiming an
organizational OID allocation. Changing the canonical URL does not authorize
changing this root or reassigning existing resource OIDs.

Publisher 2.3.2 also reports that this root is not yet registered in the FHIR
IG registry `oid-assignments.json`. That single governance warning replaces 133
per-resource missing-OID warnings, but remains a release blocker. Registration
of the exact root is an external governance action and must not be simulated by
an ignore-warning entry.

Release checks must prove that:

1. the configured root is derived from the exact canonical URL above;
2. every registered OID is unique and below that root;
3. the counts in the `[Key]` section equal the actual assignments; and
4. Publisher reports zero per-resource missing-OID warnings; and
5. the root is registered in the FHIR IG registry before governed release.

Official Publisher parameter documentation:
<https://build.fhir.org/ig/FHIR/fhir-tools-ig/en/CodeSystem-ig-parameters.html#ig-parameters-auto-oid-root>
