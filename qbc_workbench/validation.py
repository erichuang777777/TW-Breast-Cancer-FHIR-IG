from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from .models import CaseRecord, Method, ReviewStatus
from .spec import field_specs


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    field: str
    rule: str
    message: str
    location: str = "case"

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"{self.field}: {self.message} [{self.rule}]"


def _value(case: CaseRecord, tag: str) -> str | None:
    candidate = case.candidates.get(tag)
    return candidate.value if candidate and candidate.value not in (None, "") else None


def _tokens(value: str) -> list[str]:
    return value.split(",")


def _valid_date(value: str) -> bool:
    if not re.fullmatch(r"\d{8}", value):
        return False
    try:
        datetime.strptime(value, "%Y%m%d")
        return True
    except ValueError:
        return False


def _issue(issues: list[ValidationIssue], field: str, rule: str, message: str, severity: str = "error", location: str = "case") -> None:
    issues.append(ValidationIssue(severity, field, rule, message, location))


def _require(issues: list[ValidationIssue], case: CaseRecord, tag: str, rule: str, message: str | None = None) -> None:
    if _value(case, tag) is None:
        _issue(issues, tag, rule, message or "required value missing")


def _validate_field(issues: list[ValidationIssue], tag: str, value: str, spec: dict) -> None:
    try:
        value.encode("big5")
    except UnicodeEncodeError:
        _issue(issues, tag, "QBC-ENCODING-BIG5", "contains characters that cannot be encoded as Big5")

    maximum_length = spec.get("max_length")
    if maximum_length and len(value) > maximum_length:
        _issue(issues, tag, "QBC-FORMAT-LENGTH", f"length {len(value)} exceeds X({maximum_length})")
    if tag == "HOSPID" and not re.fullmatch(r"\d{10}", value):
        _issue(issues, tag, "QBC-HOSPID-FORMAT", "must contain exactly 10 digits")
    if tag in {"ID", "P07"} and not re.fullmatch(r"[A-Za-z0-9]{1,10}", value):
        _issue(issues, tag, "QBC-IDENTIFIER-FORMAT", "must contain 1-10 half-width letters or digits")

    data_type = spec["data_type"]
    if data_type == "date" and not _valid_date(value):
        _issue(issues, tag, "QBC-FORMAT-DATE", "must be a real calendar date in YYYYMMDD format")
    elif data_type == "integer" and not re.fullmatch(r"\d+", value):
        _issue(issues, tag, "QBC-FORMAT-INTEGER", "must contain digits only")
    elif data_type == "decimal" and not re.fullmatch(r"\d{1,3}(?:\.\d{1,2})?", value):
        _issue(issues, tag, "QBC-FORMAT-DECIMAL", "must have at most 3 integer and 2 decimal digits")

    raw_values = _tokens(value) if spec.get("multi_select") else [value]
    if spec.get("multi_select"):
        if any(not token or token.strip() != token for token in raw_values):
            _issue(issues, tag, "QBC-FORMAT-CODE-LIST", "must use non-empty codes separated by half-width commas without spaces")
        if len(raw_values) != len(set(raw_values)):
            _issue(issues, tag, "QBC-FORMAT-CODE-LIST", "must not contain duplicate codes")
    allowed = set(spec.get("allowed_values", []))
    invalid = [item for item in raw_values if allowed and item not in allowed]
    if invalid:
        _issue(issues, tag, "QBC-VALUESET", f"unsupported value(s): {','.join(invalid)}")

    if data_type in {"integer", "decimal"} and re.fullmatch(r"\d+(?:\.\d+)?", value):
        try:
            number = Decimal(value)
            if spec.get("minimum") is not None and number < Decimal(str(spec["minimum"])):
                _issue(issues, tag, "QBC-FORMAT-RANGE", f"must be at least {spec['minimum']}")
            if spec.get("maximum") is not None and number > Decimal(str(spec["maximum"])):
                _issue(issues, tag, "QBC-FORMAT-RANGE", f"must be at most {spec['maximum']}")
        except InvalidOperation:
            pass


def _validate_stage(issues: list[ValidationIssue], case: CaseRecord, t: str, n: str, m: str, stage: str) -> None:
    from .rules import calculate_stage

    values = [_value(case, tag) for tag in (t, n, m)]
    if any(values):
        for tag in (t, n, m):
            _require(issues, case, tag, f"QBC-{stage}-TNM-COMPLETE", "all T, N and M fields are required when any TNM component is present")
        _require(issues, case, stage, f"QBC-{stage}-TNM", "stage result is required when TNM components are present")
    actual = _value(case, stage)
    if actual and not re.fullmatch(r"Stage ?(?:0|ⅠA|ⅠB|ⅡA|ⅡB|ⅢA|ⅢB|ⅢC|Ⅳ|X)", actual):
        _issue(issues, stage, "QBC-STAGE-VALUE", "must be Stage 0, Stage I-IV subgroup, or Stage X using the official notation")
    if all(values) and actual:
        expected = calculate_stage(*values)
        if expected and actual.replace(" ", "") != expected.replace(" ", ""):
            _issue(issues, stage, f"QBC-{stage}-TNM-CONSISTENCY", f"TNM components imply {expected}, not {actual}")


def _conditional_rules(issues: list[ValidationIssue], case: CaseRecord) -> None:
    diag = _value(case, "DIAG_TYPE") or case.diagnosis_type
    if case.diagnosis_type and _value(case, "DIAG_TYPE") and case.diagnosis_type != _value(case, "DIAG_TYPE"):
        _issue(issues, "DIAG_TYPE", "QBC-DIAGTYPE-SYNC", "candidate value does not match CaseRecord.diagnosis_type")
    if case.laterality and _value(case, "LATERALITY") and case.laterality != _value(case, "LATERALITY"):
        _issue(issues, "LATERALITY", "QBC-LATERALITY-SYNC", "candidate value does not match CaseRecord.laterality")

    if _value(case, "P02") == "1":
        _require(issues, case, "P05", "QBC-P05-FEMALE", "menopause status is required for female patients")
    elif _value(case, "P05") or _value(case, "P06"):
        _issue(issues, "P05", "QBC-P05-FEMALE", "menopause fields apply only when P02 is female")
    if _value(case, "P05") == "1":
        _require(issues, case, "P06", "QBC-P06-MENOPAUSE", "menopause age is required when P05 is yes")

    if diag == "2":
        _require(issues, case, "D001", "QBC-D001-DIAGTYPE", "required when DIAG_TYPE is 2")
    if diag == "1":
        _require(issues, case, "D025", "QBC-D025-DIAGTYPE", "required when DIAG_TYPE is 1")
        _require(issues, case, "D026", "QBC-D026-DIAGTYPE", "required when DIAG_TYPE is 1")
        if not case.treatments or case.treatments[0].sequence != 1 or case.treatments[0].treatment_type != "1":
            _issue(issues, "TM01", "QBC-TM01-DIRECT-SURGERY", "DIAG_TYPE 1 requires the first treatment to be curative surgery")
    if diag == "3":
        for number in range(58, 86):
            tag = f"D{number:03d}"
            if tag in {"D069", "D071", "D072", "D074", "D075", "D077", "D079", "D081"}:
                continue
            _require(issues, case, tag, "QBC-DIAGTYPE3-RECURRENCE-REQUIRED", "D058-D085 are required when DIAG_TYPE is 3, subject to field-specific conditional rules")
    has_surgery = any(event.treatment_type == "1" for event in case.treatments)
    if has_surgery and diag in {"1", "2"}:
        conditional_postop = {"D036", "D037", "D039", "D040", "D042", "D043", "D045", "D046", "D049", "D051", "D053", "D055"}
        for number in range(27, 58):
            tag = f"D{number:03d}"
            if tag not in conditional_postop:
                _require(issues, case, tag, "QBC-TM02-SURGERY-POSTOP-REQUIRED", "D027-D057 are required for curative surgery, subject to field-specific conditional rules")
    if diag == "2" and has_surgery:
        _require(issues, case, "D024", "QBC-D024-NEOADJUVANT-SURGERY", "required when DIAG_TYPE is 2 and a surgery treatment is present")
    elif _value(case, "D024"):
        _issue(issues, "D024", "QBC-D024-NEOADJUVANT-SURGERY", "must be absent unless DIAG_TYPE is 2 and a surgery treatment is present")

    forbidden = []
    if diag == "1": forbidden = [f"D{i:03d}" for i in range(1, 25)] + [f"D{i:03d}" for i in range(58, 86)]
    if diag == "2": forbidden = ["D025", "D026"] + [f"D{i:03d}" for i in range(58, 86)]
    if diag == "3": forbidden = [f"D{i:03d}" for i in range(1, 58)]
    for tag in forbidden:
        if _value(case, tag) is not None:
            _issue(issues, tag, "QBC-DIAGTYPE-SCOPE", f"must be absent for DIAG_TYPE {diag}")

    if _value(case, "D003") in {"0", "1"} and _value(case, "D004"):
        _issue(issues, "D004", "QBC-D004-HISTOLOGY", "must be absent when D003 is 0 or 1")

    if diag == "2":
        if bool(_value(case, "D011")) == bool(_value(case, "D012")):
            _issue(issues, "D011", "QBC-D011-D012-XOR", "exactly one of D011 or D012 is required for a neoadjuvant case")

    for args in [("D005", "D006", "D007", "D008"), ("D032", "D033", "D034", "D035"), ("D060", "D061", "D062", "D063"), ("D064", "D065", "D066", "D067")]:
        _validate_stage(issues, case, *args)

    for stage, sites, other, other_code in [("D008", "D009", "D010", "12"), ("D035", "D036", "D037", "12"), (None, "D068", "D069", "13")]:
        tokens = _tokens(_value(case, sites) or "")
        if stage and _value(case, sites) and (_value(case, stage) or "").replace(" ", "") != "StageⅣ":
            _issue(issues, sites, f"QBC-{sites}-STAGE4", "may be populated only when the corresponding stage is Stage IV")
        if sites == "D036" and has_surgery and diag in {"1", "2"} and (_value(case, stage) or "").replace(" ", "") == "StageⅣ":
            _require(issues, case, sites, "QBC-D036-STAGE4", "is required for a postoperative Stage IV case")
        if other_code in tokens:
            _require(issues, case, other, f"QBC-{other}-OTHER", "other description is required when the other code is selected")
        elif _value(case, other):
            _issue(issues, other, f"QBC-{other}-OTHER", "must be absent unless the other code is selected")

    if _value(case, "D011") and _value(case, "D012"):
        _issue(issues, "D011", "QBC-D011-D012-XOR", "D011 and D012 are mutually exclusive")
    if _value(case, "D012"):
        _require(issues, case, "D013", "QBC-D013-METHOD", "required when D012 has a value")
    elif _value(case, "D013"):
        _issue(issues, "D013", "QBC-D013-METHOD", "must be absent when D012 is empty")

    for status, result, trigger, rule in [
        ("D014", "D015", "1", "ER"), ("D016", "D017", "1", "PR"),
        ("D018", "D019", "2", "HER2"), ("D020", "D021", "1", "KI67"),
        ("D048", "D049", "1", "ER"), ("D050", "D051", "1", "PR"),
        ("D052", "D053", "2", "HER2"), ("D054", "D055", "1", "KI67"),
        ("D076", "D077", "1", "ER"), ("D078", "D079", "1", "PR"),
        ("D080", "D081", "2", "HER2"),
    ]:
        if _value(case, status) == trigger:
            _require(issues, case, result, f"QBC-{result}-{rule}", f"required when {status} is {trigger}")
        elif _value(case, result):
            _issue(issues, result, f"QBC-{result}-{rule}", f"must be absent unless {status} is {trigger}")

    for status, positive, total in [("D038", "D039", "D040"), ("D041", "D042", "D043"), ("D070", "D071", "D072"), ("D073", "D074", "D075")]:
        if _value(case, status) == "1":
            _require(issues, case, positive, f"QBC-{positive}-POSITIVE", f"required when {status} is positive")
        if _value(case, status) in {"0", "1"}:
            _require(issues, case, total, f"QBC-{total}-EXAMINED", f"required when {status} was examined")
        if _value(case, positive) and _value(case, total) and int(_value(case, positive)) > int(_value(case, total)):
            _issue(issues, positive, f"QBC-{positive}-LE-{total}", f"cannot exceed {total}")
    if _value(case, "D038") == "1" or _value(case, "D041") == "1":
        _require(issues, case, "D044", "QBC-D044-NODE", "required when sentinel or axillary nodes are positive")
        if _value(case, "D044") not in {None, "1"}:
            _issue(issues, "D044", "QBC-D044-NODE-CONSISTENCY", "must be 1 when sentinel or axillary nodes are positive")
    elif has_surgery and diag in {"1", "2"} and _value(case, "D044") not in {None, "0"}:
        _issue(issues, "D044", "QBC-D044-NODE-CONSISTENCY", "must be 0 when neither sentinel nor axillary nodes are positive")
    if _value(case, "D044") == "1" and not (_value(case, "D045") or _value(case, "D046")):
        _issue(issues, "D045", "QBC-D045-D046-ONE", "at least one of D045 or D046 is required when D044 is 1")
    if _value(case, "D044") != "1" and (_value(case, "D045") or _value(case, "D046")):
        _issue(issues, "D045", "QBC-D045-D046-ONE", "D045 and D046 must be absent unless D044 is 1")


def _validate_treatments(issues: list[ValidationIssue], case: CaseRecord) -> None:
    sequences = [event.sequence for event in case.treatments]
    if len(sequences) != len(set(sequences)):
        _issue(issues, "TM01", "QBC-TM01-UNIQUE", "treatment sequence values must be unique", location="treatments")
    if sequences and sorted(sequences) != list(range(1, len(sequences) + 1)):
        _issue(issues, "TM01", "QBC-TM01-CONTIGUOUS", "treatment sequence must start at 1 and be contiguous", location="treatments")
    allowed_drugs = set(field_specs()["TM05"]["allowed_values"])
    allowed_sites = set(field_specs()["TM07"]["allowed_values"])
    for index, event in enumerate(case.treatments):
        location = f"treatments[{index}]"
        if event.treatment_type not in set(field_specs()["TM02"]["allowed_values"]):
            _issue(issues, "TM02", "QBC-VALUESET", "unsupported treatment type", location=location)
        if event.location not in {"1", "2"}:
            _issue(issues, "TM03", "QBC-TM03-REQUIRED", "must be 1 (this hospital) or 2 (other hospital)", location=location)
        if not event.actual_start or not _valid_date(event.actual_start):
            _issue(issues, "TM09", "QBC-TM09-DATE", "a real YYYYMMDD start date is required", location=location)
        if event.treatment_type in {"2", "3", "4", "5", "7"} and (not event.actual_end or not _valid_date(event.actual_end)):
            _issue(issues, "TM10", "QBC-TM10-REQUIRED", "a real YYYYMMDD end date is required for treatment types 2, 3, 4, 5 and 7", location=location)
        if event.actual_start and event.actual_end and _valid_date(event.actual_start) and _valid_date(event.actual_end) and event.actual_end < event.actual_start:
            _issue(issues, "TM10", "QBC-TM10-DATE-ORDER", "must not be earlier than TM09", location=location)
        if case.diagnosis_type == "3" and event.treatment_type == "1" and event.surgery_code not in {"1", "2", "3"}:
            _issue(issues, "TM04", "QBC-TM04-RECURRENCE", "is required for recurrence surgery", location=location)
        if not (case.diagnosis_type == "3" and event.treatment_type == "1") and event.surgery_code:
            _issue(issues, "TM04", "QBC-TM04-RECURRENCE", "must be absent unless this is recurrence surgery", location=location)
        if event.treatment_type in {"4", "5", "7"} and not event.drug_codes:
            _issue(issues, "TM05", "QBC-TM05-TREATMENT", "at least one drug code is required", location=location)
        invalid_drugs = sorted(set(event.drug_codes) - allowed_drugs)
        if invalid_drugs:
            _issue(issues, "TM05", "QBC-VALUESET", f"unsupported drug code(s): {','.join(invalid_drugs)}", location=location)
        permitted_by_type = {
            "4": {"A1", "A2"},
            "5": {f"B{i}" for i in range(1, 13)},
            "7": {"C1"},
        }
        wrong_group = sorted(set(event.drug_codes) - permitted_by_type.get(event.treatment_type, set())) if event.drug_codes else []
        if event.drug_codes and event.treatment_type not in permitted_by_type:
            _issue(issues, "TM05", "QBC-TM05-TREATMENT-TYPE", "drug codes are permitted only for treatment types 4, 5 and 7", location=location)
        elif wrong_group:
            _issue(issues, "TM05", "QBC-TM05-TREATMENT-TYPE", f"drug code(s) do not belong to treatment type {event.treatment_type}: {','.join(wrong_group)}", location=location)
        if {"A2", "B12", "C1"}.intersection(event.drug_codes) and not event.other_drug:
            _issue(issues, "TM06", "QBC-TM06-OTHER", "other drug description is required", location=location)
        if event.other_drug and not {"A2", "B12", "C1"}.intersection(event.drug_codes):
            _issue(issues, "TM06", "QBC-TM06-OTHER", "must be absent unless an other drug code is selected", location=location)
        if event.treatment_type == "3" and not event.site_codes:
            _issue(issues, "TM07", "QBC-TM07-RADIOTHERAPY", "at least one radiotherapy site is required", location=location)
        if event.treatment_type != "3" and event.site_codes:
            _issue(issues, "TM07", "QBC-TM07-RADIOTHERAPY", "must be absent unless treatment type is radiotherapy", location=location)
        invalid_sites = sorted(set(event.site_codes) - allowed_sites)
        if invalid_sites:
            _issue(issues, "TM07", "QBC-VALUESET", f"unsupported site code(s): {','.join(invalid_sites)}", location=location)
        if "A5" in event.site_codes and not event.other_site:
            _issue(issues, "TM08", "QBC-TM08-OTHER", "other site description is required", location=location)
        if event.other_site and "A5" not in event.site_codes:
            _issue(issues, "TM08", "QBC-TM08-OTHER", "must be absent unless A5 is selected", location=location)
        if event.treatment_type in {"1", "6"} and event.actual_end:
            _issue(issues, "TM10", "QBC-TM10-APPLICABILITY", "must be absent for treatment types 1 and 6", location=location)


def _validate_followups(issues: list[ValidationIssue], case: CaseRecord) -> None:
    seen = set()
    seen_years = set()
    if len(case.followups) > 5:
        _issue(issues, "T01", "QBC-T01-MAX-FIVE", "at most five annual follow-up entries are allowed", location="followups")
    enrollment = _value(case, "P09")
    for index, event in enumerate(case.followups):
        location = f"followups[{index}]"
        if not _valid_date(event.trace_date):
            _issue(issues, "T01", "QBC-T01-DATE", "must be a real YYYYMMDD date", location=location)
        if event.trace_date in seen:
            _issue(issues, "T01", "QBC-T01-UNIQUE", "duplicate follow-up date", location=location)
        seen.add(event.trace_date)
        if _valid_date(event.trace_date):
            year = event.trace_date[:4]
            if year in seen_years:
                _issue(issues, "T01", "QBC-T01-ANNUAL", "only one follow-up entry is allowed per calendar year", location=location)
            seen_years.add(year)
            if enrollment and _valid_date(enrollment):
                enrollment_date = datetime.strptime(enrollment, "%Y%m%d").date()
                trace_date = datetime.strptime(event.trace_date, "%Y%m%d").date()
                try:
                    first_allowed = enrollment_date.replace(year=enrollment_date.year + 1)
                except ValueError:  # February 29 -> February 28 in the following non-leap year
                    first_allowed = enrollment_date.replace(year=enrollment_date.year + 1, day=28)
                if trace_date < first_allowed:
                    _issue(issues, "T01", "QBC-T01-AFTER-ONE-YEAR", "follow-up may be entered only after one full year from P09", location=location)
        if event.treatment_status not in {None, "1", "2", "3", "4", "5", "6", "X"}:
            _issue(issues, "T02", "QBC-VALUESET", "unsupported treatment status", location=location)
        if event.followup_status not in {None, "1", "2", "3", "4", "5", "X"}:
            _issue(issues, "T03", "QBC-VALUESET", "unsupported follow-up status", location=location)
        if event.treatment_status in {"1", "2", "4"} and not event.followup_status:
            _issue(issues, "T03", "QBC-T03-TREATMENT", "is required for treatment status 1, 2 or 4", location=location)
        if event.treatment_status == "3" or event.followup_status == "2":
            if not event.transfer_date: _issue(issues, "T04", "QBC-T04-TRANSFER", "transfer date is required", location=location)
        elif event.transfer_date:
            _issue(issues, "T04", "QBC-T04-TRANSFER", "must be absent unless transfer is reported", location=location)
        if event.treatment_status == "6" or event.followup_status in {"3", "5"}:
            if not event.close_date: _issue(issues, "T05", "QBC-T05-CLOSE", "close date is required", location=location)
        elif event.close_date:
            _issue(issues, "T05", "QBC-T05-CLOSE", "must be absent unless case closure is reported", location=location)
        if event.treatment_status == "5" or event.followup_status == "4":
            if not event.death_date: _issue(issues, "T06", "QBC-T06-DEATH", "death date is required", location=location)
        elif event.death_date:
            _issue(issues, "T06", "QBC-T06-DEATH", "must be absent unless death is reported", location=location)
        if event.treatment_status == "6" or event.followup_status == "5":
            _issue(issues, "DIAG_TYPE", "QBC-TRACE-RECURRENCE-CASE", "a new DIAG_TYPE 3 recurrence case must also be created and linked at batch review", severity="warning", location=location)
        for tag, value in [("T04", event.transfer_date), ("T05", event.close_date), ("T06", event.death_date)]:
            if value and not _valid_date(value):
                _issue(issues, tag, "QBC-FORMAT-DATE", "must be a real YYYYMMDD date", location=location)
            if value and _valid_date(value) and _valid_date(event.trace_date) and value < event.trace_date:
                _issue(issues, tag, f"QBC-{tag}-DATE-ORDER", "must not be earlier than T01", location=location)


def validate_case(case: CaseRecord) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    specs = field_specs()
    for spec in specs.values():
        if spec["always_required"]:
            _require(issues, case, spec["tag"], "QBC-REQUIRED")
    for tag, candidate in case.candidates.items():
        if candidate.value in (None, "") or candidate.status == ReviewStatus.NOT_APPLICABLE:
            continue
        spec = specs.get(tag)
        if not spec:
            _issue(issues, tag, "QBC-UNKNOWN-FIELD", "field is not in the 11507 specification")
            continue
        _validate_field(issues, tag, candidate.value, spec)
        if candidate.method in (Method.AI_EXTRACTION, Method.AI_INFERENCE) and candidate.status != ReviewStatus.APPROVED:
            _issue(issues, tag, "QBC-AI-APPROVAL", "AI candidate is not approved")
        if candidate.status in (ReviewStatus.CONFLICT, ReviewStatus.PENDING, ReviewStatus.REJECTED):
            _issue(issues, tag, "QBC-REVIEW-STATUS", f"review status is {candidate.status.value}")
    _conditional_rules(issues, case)
    _validate_treatments(issues, case)
    _validate_followups(issues, case)
    return sorted(set(issues), key=lambda item: (item.severity, item.location, item.field, item.rule, item.message))
