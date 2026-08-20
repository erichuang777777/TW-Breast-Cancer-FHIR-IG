/*
Breast cancer case management indicators.

Normative expression of the twenty measures defined in
mappings/case-management/case-management-population-criteria.csv: the six
multidisciplinary-team quality and core indicators (bc-qi-01..06), the five
case-management quarterly rates (bc-qr-01..05) and the nine distribution
tables (bc-qr-10..18). One library, because the two report families run on the
same clinical facts; only the output is split. Every define below carries the
criterion_id from that file; the Python reference implementation is checked
against the same table, and the two must agree case by case on synthetic data
before either is trusted.

Cohort membership (Class 1/2, criterion IP-CLASS) is task-only administrative
data with no clinical resource behind it. It is applied by evaluating the
measure against a Group whose members are this quarter's Class 1/2 cases, not by
logic in this library.

Committee exclusions and numerator add-backs (X1-TEAM, X5-TEAM, N5-ADH-RULE)
are deliberate human decisions recorded per case with a reason. They are applied
to the MeasureReport by the task layer and are intentionally absent here. The
same holds for the case manager's own adjudications: which unstaged case is
really stage IV, whether a refusal was total or partial, whether a case counts
as lost to follow-up.

Case management workflow data (case entry category, case status, retention and
treatment disposition) has no clinical resource behind it either. It is read
from Task.input, typed by the local administrative code system declared in
case-management-terminology.fsh. Reading it from Task rather than inferring it
from clinical resources is deliberate: an inferred administrative category
would be a guess presented as a fact.

STATUS: drafted. The full library translates successfully. All 46 population
and stratifier expressions referenced by the twenty Measures are smoke-executed
in CI against a synthetic empty-caseload R4 Bundle. bc-qi-01 through bc-qi-06,
bc-qr-01 through bc-qr-05 and bc-qr-10 through bc-qr-18 additionally have
asserted synthetic branches;
bc-qi-01 also has a generated summary MeasureReport. The bc-qr-04 assertions are
conditional on an explicitly loaded prior-year cohort, and bc-qr-05 still tests
a candidate rule requiring manual adjudication. The test-only terminology codes
are not published in the IG ValueSets. Clinical execution also waits for the
terminology in
mappings/case-management/breast-common-to-case-management.csv to be verified
against a published release and for source-to-FHIR integration. The administrative
code systems are enumerated because the case management team is their authority.
*/

library BreastCancerCaseManagement version '1.0.0'

using FHIR version '4.0.1'

include hl7.fhir.uv.cql.FHIRHelpers version '4.0.1' called FHIRHelpers

// --- observation identification -------------------------------------------
valueset "Clinical Stage Group Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-clinical-stage-group-code'
valueset "Pathological Stage Group Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-pathological-stage-group-code'
valueset "Pathological Node Category Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-pathological-n-category-code'
valueset "Pathological Tumor Category Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-pathological-t-category-code'
valueset "Estrogen Receptor Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-estrogen-receptor-code'
valueset "HER2 Immunohistochemistry Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-her2-ihc-code'
valueset "HER2 In Situ Hybridization Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-her2-ish-code'

// --- procedures and medications --------------------------------------------
valueset "Breast Surgery": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-breast-surgery-procedure'
valueset "Breast Conserving Surgery": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-breast-conserving-surgery-procedure'
valueset "Total Mastectomy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-total-mastectomy-procedure'
valueset "Sentinel Lymph Node Biopsy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-sentinel-lymph-node-biopsy-procedure'
valueset "Core Needle Biopsy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-core-needle-biopsy-procedure'
valueset "Radiotherapy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-radiotherapy-procedure'
valueset "Hormone Therapy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-hormone-therapy-medication'
valueset "Cytotoxic Chemotherapy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-cytotoxic-chemotherapy-medication'
valueset "Anti HER2 Therapy": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-anti-her2-medication'

// --- quarterly report only --------------------------------------------------
valueset "Progesterone Receptor Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-progesterone-receptor-code'
valueset "Histology Morphology Code": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/cm-histology-morphology-code'

// --- case management workflow: local administrative codes -------------------
codesystem "Task Input Type": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-task-input-type'
codesystem "Case Entry Category CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-case-entry-category'
codesystem "Case Status CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-case-status'
codesystem "Closure Reason CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-closure-reason'
codesystem "Registry Case Class CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-registry-case-class'
codesystem "Retention Disposition CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-retention-disposition'
codesystem "Curative Treatment Disposition CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-curative-treatment-disposition'
codesystem "Treatment Completion CS": 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-treatment-completion'

parameter "Measurement Period" Interval<DateTime>

// Indicator 6 has two readings of one written exclusion; see the task page.
// 'practice' reproduces the historical calculation, 'definition' follows the
// text. The variant is chosen by the caller, never silently.
parameter "Indicator 6 Variant" String default 'practice'

// The quarterly report is calculated per case manager: one worksheet column is
// one caseload, and a facility figure is the sum of the reports. Left null the
// library reports the whole caseload, which is a different number and must
// never be filed as a case manager's own.
parameter "Reporting Case Manager" String default null

// Logical id of the Organization that represents the reporting hospital system
// root. Required for bc-qr-02: Organization.partOf alone only says that an
// organization has a parent and cannot identify which system owns that parent.
parameter "Reporting Organization System Root" String default null

// bc-qr-04 needs the prior-year new diagnosis cohort. A single-period export
// has never carried it; see "Denominator QR4".
parameter "Prior Year Cohort Available" Boolean default false

context Patient

// ==========================================================================
// shared definitions
// ==========================================================================

// IP-QUARTER
define "Reporting Episode":
  [EpisodeOfCare] Episode
    where Episode.period."start" in day of "Measurement Period"

define "Initial Population":
  exists "Reporting Episode"

define "Case Entry Date":
  Min("Reporting Episode" Episode return date from Episode.period."start")

define "Age At Case Entry":
  AgeInYearsAt("Case Entry Date")

// FHIR deceased[x] is a choice. Presence alone is not death because an
// explicitly recorded deceasedBoolean=false is a valid living-patient value.
define "Patient Is Deceased":
  Coalesce((Patient.deceased as FHIR.boolean).value, false)
    or (Patient.deceased as FHIR.dateTime) is not null

// Stage groups are read as the plain category string ('IA', 'IIIC', 'IV').
// The coding is still carried; only the code value is compared, because the
// staging code system binding is not settled yet.
define function "Stage Value"(Report Observation):
  First(((Report.value as FHIR.CodeableConcept).coding) C return C.code.value)

define "Clinical Stage":
  First(
    [Observation: "Clinical Stage Group Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return "Stage Value"(Report)
  )

define "Pathological Stage":
  First(
    [Observation: "Pathological Stage Group Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return "Stage Value"(Report)
  )

define "Pathological Node Category":
  First(
    [Observation: "Pathological Node Category Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return "Stage Value"(Report)
  )

define "Pathological Tumor Category":
  First(
    [Observation: "Pathological Tumor Category Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return "Stage Value"(Report)
  )

define function "Is Stage I To III"(Stage String):
  Stage in { 'I', 'IA', 'IB', 'II', 'IIA', 'IIB', 'III', 'IIIA', 'IIIB', 'IIIC' }

define function "Is Stage I To II"(Stage String):
  Stage in { 'I', 'IA', 'IB', 'II', 'IIA', 'IIB' }

define "Is Metastatic":
  Coalesce("Clinical Stage" = 'IV', false)
    or Coalesce("Pathological Stage" = 'IV', false)

// The pathological stage wins when it exists; otherwise the clinical stage
// stands in. Used by indicator 1.
define "Effective Stage":
  Coalesce("Pathological Stage", "Clinical Stage")

define function "Is Node Negative"(Category String):
  Category in { 'N0', 'N0(i-)', 'N0(i+)' }

define function "Is Node Positive"(Category String):
  Category is not null and not "Is Node Negative"(Category)

// N1mi counts as node positive; N2 or higher means at least four involved nodes.
define function "Is Node N2 Or Higher"(Category String):
  Category is not null
    and (StartsWith(Category, 'N2') or StartsWith(Category, 'N3'))

// FHIRHelpers 4.0.1 only overloads ToInterval for FHIR.Period and FHIR.Range,
// not the full performed[x] choice type (dateTime | Period | string | Age |
// Range), so a fluent Choice.toInterval() call is ambiguous to the translator.
// This does explicitly, per the value's actual runtime type, what that fluent
// call was attempting - it does not change which cases are counted. string
// and Age are not resolvable to a calendar date and fall through to null,
// same as an absent value would.
define function "Interval From Performed"(Performed Choice<FHIR.dateTime, FHIR.Period, FHIR.string, FHIR.Age, FHIR.Range>):
  case
    when Performed is FHIR.Period then FHIRHelpers.ToInterval(Performed as FHIR.Period)
    when Performed is FHIR.dateTime then
      Interval[FHIRHelpers.ToDateTime(Performed as FHIR.dateTime), FHIRHelpers.ToDateTime(Performed as FHIR.dateTime)]
    else null
  end

define "Completed Breast Surgery":
  [Procedure: "Breast Surgery"] Operation
    where Operation.status = 'completed'

define "Earliest Breast Surgery Date":
  Min("Completed Breast Surgery" Operation return date from start of "Interval From Performed"(Operation.performed))

define "Systemic Therapy Start Dates":
  ([MedicationRequest: "Hormone Therapy"]
    union [MedicationRequest: "Cytotoxic Chemotherapy"]
    union [MedicationRequest: "Anti HER2 Therapy"]) Request
    where Request.status in { 'active', 'completed' }
    return date from Request.authoredOn

define "Earliest Systemic Therapy Date":
  Min("Systemic Therapy Start Dates")

define "Completed Radiotherapy":
  [Procedure: "Radiotherapy"] Course
    where Course.status = 'completed'

// ==========================================================================
// bc-qi-01  ER 陽性給予賀爾蒙治療
// ==========================================================================

define "Estrogen Receptor Percent":
  First(
    [Observation: "Estrogen Receptor Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
        and Report.value is FHIR.Quantity
      return (Report.value as FHIR.Quantity).value
  )

// D1-STAGE
define "Denominator 1":
  "Initial Population"
    and "Is Stage I To III"("Effective Stage")

// D1-ER, X1-ER-LOW: ER >= 10% is expressed as the complement of this
// exclusion, not as a Denominator 1 conjunct - a denominator-exclusion must be
// a subset of the denominator, and "ER >= 10.0" AND'ed into both would make
// the exclusion empty. An ER result below 10%, or one that was never
// obtained, is excluded here; stated explicitly so a missing result is
// visibly excluded rather than quietly false.
define "Denominator 1 Exclusion":
  "Estrogen Receptor Percent" is null
    or "Estrogen Receptor Percent" < 10.0

// N1-HT
define "Numerator 1":
  exists ([MedicationRequest: "Hormone Therapy"] Request
    where Request.status in { 'active', 'completed' })

// ==========================================================================
// bc-qi-02  哨兵淋巴結取樣術
// ==========================================================================

// D2-SURGERY-FIRST: the criterion the worksheet could only approximate.
define "Surgery Was First Treatment":
  "Earliest Breast Surgery Date" is not null
    and (
      "Earliest Systemic Therapy Date" is null
        or "Earliest Breast Surgery Date" before "Earliest Systemic Therapy Date"
    )

// D2-STAGE, D2-NODE, D2-SURGERY-FIRST
define "Denominator 2":
  "Initial Population"
    and "Is Stage I To II"("Clinical Stage")
    and "Is Node Negative"("Pathological Node Category")
    and "Surgery Was First Treatment"

// N2-SLNB
define "Numerator 2":
  exists ([Procedure: "Sentinel Lymph Node Biopsy"] Operation
    where Operation.status = 'completed')

// ==========================================================================
// bc-qi-03  淋巴結陽性≧4顆全切除後放射治療
// ==========================================================================

// D3-NODE, D3-MASTECTOMY, D3-STAGE
define "Denominator 3":
  "Initial Population"
    and "Is Node N2 Or Higher"("Pathological Node Category")
    and exists ([Procedure: "Total Mastectomy"] Operation
      where Operation.status = 'completed')
    and "Is Stage I To III"("Pathological Stage")

// X3-STAGE4
define "Denominator 3 Exclusion":
  "Is Metastatic"

// N3-DOSE: the dose is carried on the radiotherapy course summary, which does
// not exist yet in the common layer, so this criterion is not evaluated at
// all - not "false", not approximated. Kept as its own define, deliberately
// unused below, so the gap stays visible instead of being silently dropped.
define "Total Radiotherapy Dose cGy":
  null as System.Quantity

// N3-RT. N3-DOSE (>= 4000 cGy) is NOT enforced here - see the comment above
// "Total Radiotherapy Dose cGy". bc-qi-03's result is therefore an upper bound:
// every case counted here received radiotherapy, but not all of them are
// verified to have received a therapeutic dose. See the Measure Description
// and the task page's known-divergence table.
define "Numerator 3":
  exists "Completed Radiotherapy"

// ==========================================================================
// bc-qi-04  HER2 陽性淋巴轉移給予 anti HER2
// ==========================================================================

define "HER2 IHC Result":
  First(
    [Observation: "HER2 Immunohistochemistry Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return First(((Report.value as FHIR.CodeableConcept).coding) C return C.display.value)
  )

define "HER2 ISH Positive":
  exists (
    [Observation: "HER2 In Situ Hybridization Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
        and Report.interpretation.coding.code contains 'POS'
  )

// D4-HER2: 3+, or 2+ resolved by a positive in situ hybridisation result.
define "HER2 Positive":
  "HER2 IHC Result" = '3+'
    or ("HER2 IHC Result" = '2+' and "HER2 ISH Positive")

// D4-SURGERY, D4-HER2, D4-NODE
define "Denominator 4":
  "Initial Population"
    and exists "Completed Breast Surgery"
    and "HER2 Positive"
    and "Is Node Positive"("Pathological Node Category")

// X4-STAGE4
define "Denominator 4 Exclusion":
  "Is Metastatic"

// N4-ANTIHER2: neoadjuvant and adjuvant administration both count.
define "Numerator 4":
  exists ([MedicationRequest: "Anti HER2 Therapy"] Request
    where Request.status in { 'active', 'completed' })

// ==========================================================================
// bc-qi-05  手術前組織學確診
// ==========================================================================

// D5-SURGERY, D5-STAGE
define "Denominator 5":
  "Initial Population"
    and exists "Completed Breast Surgery"
    and ("Is Stage I To III"("Clinical Stage") or "Is Stage I To III"("Pathological Stage"))

// X5-INSITU-STAGE4
define "Denominator 5 Exclusion":
  "Is Metastatic"
    or Coalesce("Effective Stage" = '0', false)

define "Earliest Core Needle Biopsy Date":
  Min(([Procedure: "Core Needle Biopsy"] Biopsy
    where Biopsy.status = 'completed'
    return date from start of "Interval From Performed"(Biopsy.performed)))

// N5-BIOPSY-BEFORE: at least one day before, so a same-day biopsy does not count.
define "Numerator 5":
  "Earliest Core Needle Biopsy Date" is not null
    and "Earliest Breast Surgery Date" is not null
    and "Earliest Core Needle Biopsy Date" before day of "Earliest Breast Surgery Date"

// ==========================================================================
// bc-qi-06  乳房保留手術後放射線治療
// ==========================================================================

define "Had Breast Conserving Surgery":
  exists ([Procedure: "Breast Conserving Surgery"] Operation
    where Operation.status = 'completed')

// D6-INVASIVE: stage 0 and a Tis category both mean non-invasive disease.
// A post-neoadjuvant ypStage is a real stage and must not be recorded as
// "not applicable"; see the blocking data gap on the task page.
define "Is Invasive Disease":
  "Pathological Stage" is not null
    and "Pathological Stage" != '0'
    and Coalesce("Pathological Tumor Category", '') != 'Tis'

// D6-SURGERY-BCT, D6-INVASIVE
define "Denominator 6":
  "Initial Population"
    and "Had Breast Conserving Surgery"
    and "Is Invasive Disease"

// X6-STAGE4 plus whichever reading of the age/node exclusion the caller chose.
define "Denominator 6 Exclusion":
  "Is Metastatic"
    or (
      if "Indicator 6 Variant" = 'definition'
        then "Definition Age Node Exclusion"
        else "Practice Age Node Exclusion"
    )

// X6-AGE-NODE-DEF: the written text, a single AND condition.
define "Definition Age Node Exclusion":
  "Age At Case Entry" >= 70
    and "Is Node Negative"("Pathological Node Category")

// X6-AGE-PRACTICE and X6-NODE-PRACTICE: the historical calculation, which
// splits the same sentence into two independent exclusions.
define "Practice Age Node Exclusion":
  "Age At Case Entry" >= 70
    or not "Is Node Positive"("Pathological Node Category")

// N6-RT: radiotherapy after the operation, not merely present.
define "Numerator 6":
  exists ("Completed Radiotherapy" Course
    where "Earliest Breast Surgery Date" is null
      or start of "Interval From Performed"(Course.performed) same day or after "Earliest Breast Surgery Date")

// ==========================================================================
// 個管季報 quarterly：共用定義
// ==========================================================================

// The quarterly report counts one case manager's caseload. Matching on the
// careManager reference keeps the figure attributable; with no case manager
// supplied every episode counts, which is the facility figure and must never
// be filed as one person's.
define "Reporting Case Manager Episodes":
  "Reporting Episode" Episode
    where "Reporting Case Manager" is null
      or EndsWith(Coalesce(Episode.careManager.reference.value, ''), "Reporting Case Manager")

// IP-CASELOAD: the only population that uses the whole caseload rather than
// the new diagnoses. bc-qr-10 reports it; every other quarterly table starts
// from IP-NEWDX.
define "Quarterly Caseload":
  exists "Reporting Case Manager Episodes"

// --- task-only workflow data -----------------------------------------------
// Read from Task.input, never inferred. An inferred administrative category is
// a guess wearing the clothes of a recorded fact.

define function "Case Input Code"(InputType String, ValueSystem String, AllowedCodes List<String>):
  First(
    (flatten(
      [Task] CaseTask
        where CaseTask.status in { 'ready', 'in-progress', 'completed' }
        return CaseTask.input
    )) TaskInput
      where exists (
        TaskInput.type.coding TypeCoding
          where TypeCoding.system = 'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-task-input-type'
            and TypeCoding.code = InputType
      )
      return First(
        ((TaskInput.value as FHIR.CodeableConcept).coding) ValueCoding
          where ValueCoding.system = ValueSystem
            and ValueCoding.code in AllowedCodes
          return ValueCoding.code.value
      )
  )

// S10-IDENTITY and IP-NEWDX (CM-TASK-002)
define "Case Entry Category":
  "Case Input Code"(
    'case-entry-category',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-case-entry-category',
    { 'new-diagnosis', 'existing-case', 'delayed-entry-same-year',
      'delayed-entry-prior-year', 'first-recurrence-curable',
      'first-recurrence-noncurable' }
  )

// S12-DYNAMIC (CM-TASK-003)
define "Case Status":
  "Case Input Code"(
    'case-status',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-case-status',
    { 'diagnosis', 'treatment', 'clinical-trial', 'follow-up', 'palliative',
      'refused-interrupted', 'closed' }
  )

// S13-CLOSURE (CM-TASK-003, supported by CM-BC-031 and CM-BC-036)
define "Closure Reason":
  "Case Input Code"(
    'closure-reason',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-closure-reason',
    { 'death', 'transferred', 'refused-return', 'critical-aad' }
  )

// S15-CLASS (CM-TASK-001)
define "Registry Case Class":
  "Case Input Code"(
    'registry-case-class',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-registry-case-class',
    { 'class-0', 'class-1', 'class-2', 'class-3' }
  )

// CM-TASK-004 and CM-TASK-005
define "Retention Disposition":
  "Case Input Code"(
    'retention-disposition',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-retention-disposition',
    { 'stay', 'transfer-during-staging', 'no-treatment-no-return',
      'untreated-return-over-1m', 'considering-return-under-1m',
      'staging-in-progress', 'death-during-staging' }
  )

// CM-TASK-006
define "Curative Treatment Disposition":
  "Case Input Code"(
    'curative-treatment-disposition',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-curative-treatment-disposition',
    { 'in-curative-treatment', 'death-during-treatment',
      'transfer-during-treatment', 'physician-advised-stop', 'not-advisable',
      'active-surveillance', 'noncurative' }
  )

// CM-TASK-007
define "Treatment Completion":
  "Case Input Code"(
    'treatment-completion',
    'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/cm-treatment-completion',
    { 'completed-here', 'completed-then-death', 'completed-then-transfer',
      'incomplete-refused-part', 'incomplete-interrupted' }
  )

// IP-NEWDX: only new diagnoses enter the quarterly tables and rates.
define "New Diagnosis Case":
  "Quarterly Caseload"
    and Coalesce("Case Entry Category" = 'new-diagnosis', false)

// --- staging state ----------------------------------------------------------
// The worksheet writes '?' for three different situations. Separating them is
// the whole point of CM-BC-033 and CM-BC-034.

define "Stage Group Observations":
  [Observation: "Clinical Stage Group Code"]
    union [Observation: "Pathological Stage Group Code"]

// X1-STAGING (CM-BC-033): staging started and has not finished.
define "Staging In Progress":
  exists (
    "Stage Group Observations" StageReport
      where exists (
        StageReport.dataAbsentReason.coding AbsentCoding
          where AbsentCoding.code = 'temp-unknown'
      )
  )

// S12-DYNAMIC reporting correction. The current source records a patient who
// is still being staged as treatment; the worksheet then moves that case to
// diagnosis by hand. Keep the recorded Task value available as "Case Status",
// but make the report projection explicit and evidence-based.
define "Case Status Reported":
  if "Staging In Progress" then 'diagnosis' else "Case Status"

// The outside hospital staged the patient and this hospital cannot obtain the
// record: an absent reason of 'unknown', not 'temp-unknown'. Neither is a
// stage, and the two land in different columns of the distribution table.
define "Stage Unobtainable From Outside Facility":
  exists (
    "Stage Group Observations" StageReport
      where exists (
        StageReport.dataAbsentReason.coding AbsentCoding
          where AbsentCoding.code = 'unknown'
      )
  )

// X1-NOSTAY-TRANSFER (CM-BC-034): care moved to another organisation before
// any treatment happened here.
define "Receiving Organisation":
  First(
    "Reporting Case Manager Episodes" Episode
      where Episode.status in { 'finished', 'entered-in-error' }
      return Episode.managingOrganization
  )

define "Transferred During Staging":
  Coalesce("Retention Disposition" = 'transfer-during-staging', false)

// CM-BC-034 through Organization.partOf, replacing the hospital-name keyword
// list. False when either the receiver or the governed system root cannot be
// resolved, rather than treating membership in any organization tree as NTUH.
define "Transferred Within NTUH System":
  "Transferred During Staging"
    and "Reporting Organization System Root" is not null
    and exists (
      [Organization] Receiver
        where Receiver.id = Last(Split(Coalesce("Receiving Organisation".reference.value, ''), '/'))
          and Last(Split(Coalesce(Receiver.partOf.reference.value, ''), '/'))
            = "Reporting Organization System Root"
    )

// X1-STAGING-DEATH (CM-BC-036 with CM-BC-035)
define "Any Curative Treatment Resource":
  ([Procedure: "Breast Surgery"] union [Procedure: "Radiotherapy"]) CurativeProcedure
    where CurativeProcedure.status in { 'in-progress', 'completed' }

define "Died Before Curative Treatment":
  "Patient Is Deceased"
    and not exists "Any Curative Treatment Resource"
    and not exists ([MedicationRequest] Request
      where Request.status in { 'active', 'completed' })

// ==========================================================================
// bc-qr-01  留院治療率
// ==========================================================================

// D1-BASE
define "Denominator QR1":
  "New Diagnosis Case"

// X1-STAGING, X1-STAGING-DEATH, X1-CONSIDERING
define "Denominator QR1 Exclusion":
  "Staging In Progress"
    or "Died Before Curative Treatment"
    or Coalesce("Retention Disposition" = 'considering-return-under-1m', false)

// N1-STAY (CM-BC-034 with CM-TASK-004)
define "Numerator QR1":
  Coalesce("Retention Disposition" = 'stay', false)

// X1-NOSTAY-TRANSFER, X1-NOSTAY-REFUSE
define "Numerator QR1 Exclusion":
  "Transferred During Staging"
    or Coalesce("Retention Disposition" in { 'no-treatment-no-return', 'untreated-return-over-1m' }, false)

// ==========================================================================
// bc-qr-02  留院治療率（臺大體系內矯正後）
// ==========================================================================

// D2-BASE: the bc-qr-01 denominator after its exclusions.
define "Denominator QR2":
  "Denominator QR1" and not "Denominator QR1 Exclusion"

// N2-STAY-INSYS
define "Numerator QR2":
  "Numerator QR1" or "Transferred Within NTUH System"

// ==========================================================================
// bc-qr-03  完成治療率
// ==========================================================================

// D3-BASE
define "Denominator QR3":
  "New Diagnosis Case"

// X3-ONGOING (CM-BC-035): a curative plan exists and nothing has completed.
define "Curative Treatment Still Running":
  Coalesce("Curative Treatment Disposition" = 'in-curative-treatment', false)
    or (
      exists "Any Curative Treatment Resource"
        and not exists ("Any Curative Treatment Resource" CurativeProcedure
          where CurativeProcedure.status = 'completed')
    )

// X3-STAGING, X3-ONGOING, X3-TX-EVENT, X3-NONCURATIVE
define "Denominator QR3 Exclusion":
  "Staging In Progress"
    or "Died Before Curative Treatment"
    or "Transferred During Staging"
    or "Curative Treatment Still Running"
    or Coalesce("Curative Treatment Disposition" in {
      'death-during-treatment', 'transfer-during-treatment',
      'physician-advised-stop', 'not-advisable', 'active-surveillance',
      'noncurative'
    }, false)

// N3-COMPLETE (CM-BC-035 with CM-BC-036): completing and then dying or
// transferring still counts as treatment completed here.
define "Numerator QR3":
  Coalesce("Treatment Completion" in {
    'completed-here', 'completed-then-death', 'completed-then-transfer'
  }, false)

// X3-INCOMPLETE (CM-TASK-007): part of the plan refused, or treatment
// interrupted. Not derivable from resource status; the case manager records it.
define "Numerator QR3 Exclusion":
  Coalesce("Treatment Completion" in {
    'incomplete-refused-part', 'incomplete-interrupted'
  }, false)

// ==========================================================================
// bc-qr-04  失聯率 — BLOCKED
//
// D4-COHORT needs the prior-year new diagnosis cohort. The single-period export
// this task runs on has never carried it, so the denominator cannot be built
// and the figure on the form is typed in by hand. These defines stay empty
// unless the caller states the cohort is loaded, so an unloaded run reports no
// population rather than a number that looks calculated.
// ==========================================================================

// D4-COHORT (CM-BC-038 with CM-BC-036)
define "Prior Year And Current New Diagnosis Cohort":
  "Prior Year Cohort Available"
    and (
      "New Diagnosis Case"
        or exists ([EpisodeOfCare] Episode
          where Episode.period."start" during Interval[
            start of "Measurement Period" - 1 year,
            start of "Measurement Period")
        )
    )

define "Denominator QR4":
  "Prior Year And Current New Diagnosis Cohort"
    and not "Patient Is Deceased"

// N4-LOST (CM-BC-037): a year with no contact of any kind.
define "Last Contact Date":
  Max(
    ([Encounter] Contact
      where Contact.status in { 'finished', 'in-progress' }
      return date from end of Contact.period)
  )

define "Numerator QR4":
  "Denominator QR4"
    and "Last Contact Date" is not null
    and "Last Contact Date" same day or before (date from end of "Measurement Period" - 1 year)

// ==========================================================================
// bc-qr-05  重返治療率
// ==========================================================================

// D5-QUIT (CM-TASK-007)
define "Denominator QR5":
  "Quarterly Caseload"
    and (
      Coalesce("Case Status" = 'refused-interrupted', false)
        or Coalesce("Treatment Completion" in {
          'incomplete-refused-part', 'incomplete-interrupted'
        }, false)
    )

// N5-RETURN (CM-BC-035): curative-intent treatment starting after the
// interruption. The case manager adjudicates this today and no interruption
// date is recorded to compare against, so this expression is a candidate, not
// a settled rule. It must be checked case by case against the manual
// determination before it replaces it.
define "Interruption Date":
  Max(
    "Reporting Case Manager Episodes" Episode
      where Episode.status in { 'onhold', 'cancelled' }
      return date from end of Episode.period
  )

define "Numerator QR5":
  "Denominator QR5"
    and "Interruption Date" is not null
    and exists (
      "Any Curative Treatment Resource" CurativeProcedure
        where date from start of "Interval From Performed"(CurativeProcedure.performed) after "Interruption Date"
    )

// ==========================================================================
// 九張分布表的 stratifier
// ==========================================================================

// S11-MONTH (CM-BC-002)
define "Case Entry Month":
  month from "Case Entry Date"

// S14-SEX (CM-BC-030): administrative gender as recorded. The report has no
// column for anything other than male and female; a third value is a reporting
// gap to raise, not a value to fold into one of the two.
define "Administrative Sex":
  Patient.gender.value

// S14-AGEBAND (CM-BC-001 with CM-BC-002): computed from the birth date against
// the case entry date, replacing the precomputed band code in the export.
define "Age Band At Case Entry":
  case
    when "Age At Case Entry" is null then null
    when "Age At Case Entry" < 10 then '<10'
    when "Age At Case Entry" >= 90 then '>=90'
    else ToString(("Age At Case Entry" div 10) * 10) + '-' + ToString((("Age At Case Entry" div 10) * 10) + 9)
  end

// S15-CLASS (CM-TASK-001 with CM-BC-033): a case still being staged reports as
// 診斷中 whatever class was recorded, because the class is not settled yet.
define "Registry Case Class Reported":
  if "Staging In Progress" then 'staging-in-progress' else "Registry Case Class"

// S15-CLASS3: class 3 sits outside the class table and is reported as a note.
define "Is Registry Class 3":
  "Registry Case Class" = 'class-3'

// S16-STAGE (CM-BC-004, CM-BC-005, CM-BC-033, CM-BC-034): the three situations
// the worksheet writes as '?' land in three different columns.
define "Reported Stage Group":
  case
    when "Effective Stage" = '0' then '0'
    when "Effective Stage" in { 'I', 'IA', 'IB' } then 'I'
    when "Effective Stage" in { 'II', 'IIA', 'IIB' } then 'II'
    when "Effective Stage" in { 'III', 'IIIA', 'IIIB', 'IIIC' } then 'III'
    when "Effective Stage" = 'IV' then 'IV'
    when "Effective Stage" is not null then 'other-unspecified'
    when "Staging In Progress" then 'staging-in-progress'
    when "Transferred During Staging" then 'other-transferred-during-staging'
    when "Stage Unobtainable From Outside Facility" then 'other-outside-records-insufficient'
    else 'other-unspecified'
  end

// S17-HISTOLOGY (CM-BC-032): coded morphology. DCIS with microinvasion groups
// with invasive carcinoma; DCIS and phyllodes are their own strata and stay
// out of the invasive denominator.
define "Histology Morphology":
  First(
    [Observation: "Histology Morphology Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
      return First(((Report.value as FHIR.CodeableConcept).coding) C return C.code.value)
  )

// The ten groups currently enumerated by S17-HISTOLOGY, from the morphology code.
// Source documentation says eleven groups; that unresolved discrepancy remains
// a publication blocker rather than being filled with an invented category. The worksheet reaches the
// same groups from free text through an ordered table of 27 spellings; that
// table is the proxy this replaces. ICD-O-3 morphology codes are still marked
// candidate-unverified in the mapping, so this grouping cannot be trusted until
// they are checked against the published release.
define "Histology Group":
  case
    when "Histology Morphology" is null then null
    when "Histology Morphology" = '8520/3' then 'ilc'
    when "Histology Morphology" = '8522/3' then 'ic-and-ilc'
    when "Histology Morphology" = '8480/3' then 'ic-with-mucin'
    when "Histology Morphology" = '8541/3' then 'ic-and-paget'
    when "Histology Morphology" = '8574/3' then 'ic-with-neuroendocrine'
    when "Histology Morphology" = '8575/3' then 'metaplastic'
    when "Histology Morphology" = '8200/3' then 'adenoid-cystic'
    when "Histology Morphology" in { '9020/0', '9020/1', '9020/3' } then 'phyllodes'
    when "Histology Morphology" = '8500/2' and "Has Microinvasion" then 'ic'
    when "Histology Morphology" = '8500/2' then 'dcis'
    when "Histology Morphology" = '8500/3' then 'ic'
    else null
  end

// DCIS with microinvasion counts as invasive disease and is reported with the
// invasive carcinomas. The microinvasion lives in the T category, not in the
// morphology code, which is why it is read separately.
define "Has Microinvasion":
  Coalesce("Pathological Tumor Category", '') = 'T1mi'

// The invasive denominator for bc-qr-17 and bc-qr-18. Pure DCIS and phyllodes
// are out; so is any case with no morphology, because a missing morphology is
// not evidence of invasion.
define "Is Invasive Histology":
  "Histology Group" is not null
    and not ("Histology Group" in { 'dcis', 'phyllodes' })

// S18-SUBTYPE (CM-BC-008 with CM-BC-009, CM-BC-010, CM-BC-011): derived from
// the marker observations. The hand-typed letter A/B1/B2/H/T is not stored; its
// + and - values were the ER status of an in-situ case, which is why the
// invasive denominator is decided from histology and not from the letter.
define "Progesterone Receptor Percent":
  First(
    [Observation: "Progesterone Receptor Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
        and Report.value is FHIR.Quantity
      return (Report.value as FHIR.Quantity).value
  )

define "Hormone Receptor Positive":
  Coalesce("Estrogen Receptor Percent", 0.0) >= 1.0
    or Coalesce("Progesterone Receptor Percent", 0.0) >= 1.0

define "Hormone Receptor Negative":
  "Estrogen Receptor Percent" is not null
    and "Progesterone Receptor Percent" is not null
    and "Estrogen Receptor Percent" < 1.0
    and "Progesterone Receptor Percent" < 1.0

define "HER2 ISH Negative":
  exists (
    [Observation: "HER2 In Situ Hybridization Code"] Report
      where Report.status in { 'final', 'amended', 'corrected' }
        and Report.interpretation.coding.code contains 'NEG'
  )

define "HER2 Negative":
  "HER2 IHC Result" in { '0', '1+' }
    or ("HER2 IHC Result" = '2+' and "HER2 ISH Negative")

define "HR HER2 Subtype":
  case
    when not "Is Invasive Histology" then null
    when "Hormone Receptor Positive" and "HER2 Positive" then 'hr-positive-her2-positive'
    when "Hormone Receptor Positive" and "HER2 Negative" then 'hr-positive-her2-negative'
    when "Hormone Receptor Negative" and "HER2 Positive" then 'hr-negative-her2-positive'
    when "Hormone Receptor Negative" and "HER2 Negative" then 'triple-negative'
    else 'indeterminate'
  end
