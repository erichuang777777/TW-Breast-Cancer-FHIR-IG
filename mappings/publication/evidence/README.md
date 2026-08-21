# Publication approval evidence

Only de-identified, publication-safe approval evidence belongs here. RC-07 and
RC-08 approval rows must use a repository-relative path below this directory,
and the declared SHA-256 must match the committed file bytes.

Do not commit patient-level data, credentials, private keys, unredacted meeting
minutes, licensed terminology content, or other restricted material. Preserve
those items in the controlled governance system and commit only an approved,
redacted evidence package that can pass the repository privacy scan.

Generated `StructureDefinition-*.json` files are a separate exception: they are
the artifacts being reviewed, not human decision records. CI regenerates them,
checks their exact hashes against approved rows, and uploads them with Publisher
evidence.
