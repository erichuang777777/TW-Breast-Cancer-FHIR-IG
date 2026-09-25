from pathlib import Path
from collections import Counter
import json

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
EXTRACTED_SPEC = ROOT / "qbc_workbench" / "data" / "qbc_fields.json"
OUTDIR = ROOT / "outputs" / "qbc_ig_mapping"
OUT = OUTDIR / "QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx"

TWCORE = "https://twcore.mohw.gov.tw/ig/twcore/"
MCODE = "https://hl7.org/fhir/us/mcode/"
FHIR = "https://hl7.org/fhir/R4/"


def section_for(tag):
    if tag in {"HOSPID", "ID", "BIRTHDAY", "DIAG_TYPE", "LATERALITY"}:
        return "個案鍵值"
    if tag.startswith("P"):
        return "基本資料"
    if tag.startswith("D"):
        n = int(tag[1:])
        if n <= 23:
            return "新輔助－術前診斷"
        if n <= 57:
            return "術後病理"
        return "復發／de novo mBC"
    if tag.startswith("TM"):
        return "治療療程"
    return "年度追蹤"


def profile_url(name):
    return f"{MCODE}StructureDefinition-{name}.html" if name else ""


def map_field(tag, label):
    m = {
        "canonical_entity": "",
        "fhir_resource": "",
        "fhir_path": "",
        "tw_core": "",
        "mcode": "",
        "terminology": "",
        "standard_code": "",
        "decision": "Reuse FHIR",
        "extension": "No",
        "extension_name": "",
        "source_priority": "",
        "transform": "",
        "confidence": "High",
        "review_note": "",
    }

    base = {
        "HOSPID": ("Organization", "Organization", "Organization.identifier", "TW Core Organization", "", "臺灣醫事機構代碼", "", "系統設定 > 機構主檔"),
        "ID": ("Patient", "Patient", "Patient.identifier", "TW Core Patient", "CancerPatient（內容對齊）", "臺灣身分證／居留證／護照識別規則", "", "病人主檔"),
        "BIRTHDAY": ("Patient", "Patient", "Patient.birthDate", "TW Core Patient", "CancerPatient（內容對齊）", "FHIR date", "", "病人主檔"),
        "LATERALITY": ("CancerCase", "Condition", "Condition.bodySite", "TW Core Condition", "PrimaryCancerCondition", "SNOMED CT body structure／laterality", "", "癌登 > 病理報告 > ICD-10-CM laterality"),
        "P01": ("Patient", "Patient", "Patient.name", "TW Core Patient", "CancerPatient（內容對齊）", "HumanName", "", "病人主檔"),
        "P02": ("Patient", "Patient", "Patient.gender", "TW Core Patient", "CancerPatient（內容對齊）", "FHIR AdministrativeGender", "", "病人主檔"),
        "P03": ("ClinicalObservation", "Observation", "Observation.valueQuantity", "TW Core Observation", "", "LOINC + UCUM", "8302-2；cm", "護理生命徵象 > EMR"),
        "P04": ("ClinicalObservation", "Observation", "Observation.valueQuantity", "TW Core Observation", "", "LOINC + UCUM", "29463-7；kg", "護理生命徵象 > EMR"),
        "P05": ("ClinicalObservation", "Observation", "Observation.valueCodeableConcept", "TW Core Observation", "", "SNOMED CT／LOINC（待術語確認）", "", "門診 Note > 出院病摘 > 個管"),
        "P06": ("ClinicalObservation", "Observation", "Observation.valueQuantity", "TW Core Observation", "", "LOINC（待確認）+ UCUM", "a", "門診 Note > 出院病摘 > 個管"),
        "P07": ("ResponsiblePractitioner", "Practitioner", "Practitioner.identifier", "TW Core Practitioner", "", "臺灣身分證／專業人員識別", "", "醫師主檔（受控）"),
        "P09": ("QBCEnrollment", "EpisodeOfCare", "EpisodeOfCare.period.start", "TW Core EpisodeOfCare（若有）", "", "FHIR date", "", "個管系統 > 癌症計畫書"),
    }
    if tag in base:
        vals = base[tag]
        keys = ["canonical_entity", "fhir_resource", "fhir_path", "tw_core", "mcode", "terminology", "standard_code", "source_priority"]
        m.update(dict(zip(keys, vals)))
        if tag == "LATERALITY":
            m["decision"] = "Reuse mCODE/TW Core"
        return m

    if tag == "DIAG_TYPE":
        m.update(canonical_entity="QBCEnrollment", fhir_resource="EpisodeOfCare", fhir_path="EpisodeOfCare.extension",
                 tw_core="TW Core EpisodeOfCare（若有）", terminology="QBC CodeSystem",
                 decision="QBC Extension", extension="Yes", extension_name="qbc-enrollment-type",
                 source_priority="個管系統 + Stage + 治療路徑規則",
                 transform="真正首次復發或 de novo Stage IV → 3；其餘依直接手術／新輔助判定",
                 confidence="High", review_note="不得由『是否首復發』單一欄位直接決定。")
        return m
    if tag == "P08":
        m.update(canonical_entity="QBCEnrollment", fhir_resource="EpisodeOfCare", fhir_path="EpisodeOfCare.extension",
                 tw_core="TW Core EpisodeOfCare（若有）", terminology="QBC CodeSystem",
                 decision="QBC Extension", extension="Yes", extension_name="qbc-case-class",
                 source_priority="癌症計畫書 Class > 個管系統",
                 transform="de novo mBC 仍為 Class 1/2；真正首次復發才使用 3",
                 confidence="High", review_note="與 DIAG_TYPE 分開保存。")
        return m

    if tag.startswith("D"):
        n = int(tag[1:])
        context = "術前" if n <= 23 else ("術後" if n <= 57 else "復發")
        m.update(canonical_entity="PathologyOrCancerAssessment", source_priority="病理 LIS > 癌症計畫書 > 人工核對")

        date_tags = {1, 25, 58}
        facility_tags = {2, 26, 59}
        histology_tags = {3, 30}
        grade_tags = {4, 31}
        t_tags = {5, 32, 60, 64}
        n_tags = {6, 33, 61, 65}
        m_tags = {7, 34, 62, 66}
        stage_tags = {8, 35, 63, 67}
        metastasis_tags = {9, 36, 68}
        metastasis_other_tags = {10, 37, 69}
        er_tags = {14, 48, 76}
        er_value_tags = {15, 49, 77}
        pr_tags = {16, 50, 78}
        pr_value_tags = {17, 51, 79}
        her2_tags = {18, 52, 80}
        fish_tags = {19, 53, 81}
        ki_status_tags = {20, 54, 82}
        ki_value_tags = {21, 55, 83}
        brca_tags = {22, 56, 84}
        pdl1_tags = {23, 57, 85}

        if n in date_tags:
            m.update(fhir_resource="Condition/DiagnosticReport", fhir_path="Condition.onsetDateTime / DiagnosticReport.effectiveDateTime",
                     tw_core="TW Core Condition／DiagnosticReport", mcode="PrimaryCancerCondition", terminology="FHIR date",
                     source_priority="病理 LIS 報告日／診斷日 > 癌症計畫書")
        elif n in facility_tags:
            m.update(canonical_entity="DiagnosisProvenance", fhir_resource="Provenance/Encounter", fhir_path="Provenance.agent.who / Encounter.serviceProvider",
                     tw_core="TW Core Provenance／Encounter", decision="QBC Extension or derived flag", extension="Review",
                     extension_name="qbc-diagnosis-facility-class", terminology="QBC CodeSystem",
                     source_priority="來源院所／機構代碼", confidence="Medium",
                     review_note="FHIR 保存實際 Organization；1/2 為 QBC 匯出時衍生。")
        elif n in histology_tags:
            m.update(fhir_resource="Condition", fhir_path="PrimaryCancerCondition.extension[histologyMorphologyBehavior]",
                     tw_core="TW Core Condition", mcode="PrimaryCancerCondition", terminology="SNOMED CT morphology／ICD-O-3",
                     decision="Reuse mCODE", source_priority="病理 LIS")
        elif n in grade_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     terminology="SNOMED CT／NAACCR（待臺灣術語治理）", source_priority="病理 LIS", confidence="Medium")
        elif n in t_tags | n_tags | m_tags:
            kind = "TNMPrimaryTumorCategory" if n in t_tags else ("TNMRegionalNodesCategory" if n in n_tags else "TNMDistantMetastasesCategory")
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     mcode=kind, terminology="AJCC TNM（版本與授權需註記）", decision="Reuse mCODE",
                     source_priority="癌症計畫書 > 癌登 > 病理 LIS",
                     transform="保留原始細分值；另產 QBC 正規化值（如 T1c→T1、N0(i-)→N0）")
        elif n in stage_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     mcode="TNMStageGroup", terminology="AJCC Stage Group（版本與授權需註記）", decision="Reuse mCODE",
                     source_priority="依正規化 TNM 計算 > 癌症計畫書",
                     transform="由 QBC TNM 規則重算，與來源 Stage 比較；衝突送人工。")
        elif n in metastasis_tags:
            m.update(fhir_resource="Condition", fhir_path="SecondaryCancerCondition.bodySite", tw_core="TW Core Condition",
                     mcode="SecondaryCancerCondition / HistoryOfMetastaticCancer", terminology="SNOMED CT body structure",
                     decision="Reuse mCODE", source_priority="影像／病理 > 癌症計畫書")
        elif n in metastasis_other_tags:
            m.update(fhir_resource="Condition", fhir_path="Condition.bodySite.text / Condition.note", tw_core="TW Core Condition",
                     mcode="SecondaryCancerCondition", terminology="SNOMED CT + free text", decision="Reuse mCODE",
                     source_priority="影像／病理 > 癌症計畫書")
        elif n in {11, 12, 13}:
            m.update(fhir_resource="Procedure/DiagnosticReport", fhir_path="Procedure.code / DiagnosticReport.result",
                     tw_core="TW Core Procedure／DiagnosticReport", terminology="SNOMED CT + Observation interpretation",
                     source_priority="病理 LIS／處置紀錄", confidence="Medium")
        elif n in er_tags | er_value_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept / valueQuantity",
                     tw_core="TW Core Observation", mcode="TumorMarkerTest", terminology="LOINC + UCUM",
                     standard_code="85329-1；%", decision="Reuse mCODE", source_priority="病理 LIS")
        elif n in pr_tags | pr_value_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept / valueQuantity",
                     tw_core="TW Core Observation", mcode="TumorMarkerTest", terminology="LOINC + UCUM（精確 assay code 待確認）",
                     standard_code="%", decision="Reuse mCODE", source_priority="病理 LIS", confidence="Medium")
        elif n in her2_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     mcode="TumorMarkerTest", terminology="LOINC", standard_code="85319-2",
                     decision="Reuse mCODE", source_priority="病理 LIS")
        elif n in fish_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     mcode="TumorMarkerTest / GenomicsReport", terminology="LOINC（HER2 ISH/FISH assay code 待確認）",
                     decision="Reuse mCODE", source_priority="病理 LIS／分生系統", confidence="Medium")
        elif n in ki_status_tags | ki_value_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept / valueQuantity",
                     tw_core="TW Core Observation", mcode="TumorMarkerTest", terminology="LOINC + UCUM",
                     standard_code="85330-9；%", decision="Reuse mCODE", source_priority="病理 LIS")
        elif n in brca_tags:
            m.update(fhir_resource="DiagnosticReport/Observation", fhir_path="GenomicsReport.result / GenomicVariant",
                     tw_core="TW Core DiagnosticReport／Observation", mcode="GenomicsReport / GenomicVariant",
                     terminology="LOINC + HGNC + ClinVar（依報告）", decision="Reuse mCODE",
                     source_priority="分生／基因檢測報告")
        elif n in pdl1_tags:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept / component",
                     tw_core="TW Core Observation", mcode="TumorMarkerTest", terminology="LOINC（assay／score 待確認）",
                     decision="Reuse mCODE", source_priority="病理 LIS", confidence="Medium")
        elif n == 24:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueCodeableConcept", tw_core="TW Core Observation",
                     mcode="CancerDiseaseStatus（語意對齊，非直接等價）", terminology="SNOMED CT／QBC ValueSet",
                     decision="FHIR Profile + QBC ValueSet", extension="No", source_priority="術後病理 + 腫瘤團隊判讀",
                     confidence="Medium", review_note="pCR 是臨床概念，宜建獨立 Observation Profile。")
        elif n in {27, 29}:
            m.update(fhir_resource="Procedure", fhir_path="Procedure.code", tw_core="TW Core Procedure",
                     mcode="CancerRelatedSurgicalProcedure", terminology="SNOMED CT／院內手術碼 ConceptMap",
                     decision="Reuse mCODE", source_priority="手術紀錄 > 癌症計畫書")
        elif n == 28:
            m.update(fhir_resource="Observation/DiagnosticReport", fhir_path="Observation.valueCodeableConcept / DiagnosticReport.result",
                     tw_core="TW Core Observation／DiagnosticReport", terminology="LOINC/SNOMED CT（margin status）",
                     source_priority="術後病理", confidence="Medium")
        elif n in {38, 41, 70, 73}:
            m.update(fhir_resource="Observation", fhir_path="Observation.interpretation / valueCodeableConcept",
                     tw_core="TW Core Observation", terminology="SNOMED CT／LOINC interpretation",
                     source_priority="病理 LIS")
        elif n in {39, 40, 42, 43, 45, 46, 71, 72, 74, 75}:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueInteger / component",
                     tw_core="TW Core Observation", terminology="LOINC（lymph nodes examined/positive；精確碼待確認）",
                     source_priority="病理 LIS", confidence="Medium")
        elif n == 44:
            m.update(fhir_resource="Observation", fhir_path="Observation.valueBoolean / interpretation",
                     tw_core="TW Core Observation", terminology="SNOMED CT", source_priority="病理 LIS")
        elif n == 47:
            m.update(fhir_resource="Observation", fhir_path="TumorSize.valueQuantity", tw_core="TW Core Observation",
                     mcode="TumorSize", terminology="LOINC + UCUM", standard_code="cm",
                     decision="Reuse mCODE", source_priority="術後病理")
        else:
            m.update(fhir_resource="Observation", fhir_path="Observation.value[x]", tw_core="TW Core Observation",
                     terminology="Terminology review required", confidence="Low", review_note=f"需針對 {context} 語意再確認。")
        return m

    if tag.startswith("TM"):
        n = int(tag[2:])
        m.update(canonical_entity="CancerTreatment", source_priority="實際治療系統 > 癌症計畫書 > 醫囑／藥局")
        if n == 1:
            m.update(fhir_resource="Bundle/List", fhir_path="Bundle.entry ordering / List.entry",
                     decision="Transform-only", extension="No", terminology="QBC sequence",
                     transform="依實際治療開始日與業務排序產生，不應成為臨床 Extension。")
        elif n == 2:
            m.update(fhir_resource="Procedure/MedicationAdministration/RadiotherapyCourseSummary", fhir_path="Resource.code",
                     tw_core="TW Core Procedure／MedicationAdministration", mcode="CancerRelatedSurgicalProcedure / CancerRelatedMedicationAdministration / RadiotherapyCourseSummary",
                     terminology="SNOMED CT／ATC／臺灣藥碼 + QBC ConceptMap", decision="Reuse mCODE + transform")
        elif n == 3:
            m.update(fhir_resource="Procedure/MedicationAdministration", fhir_path="performer.actor / location",
                     tw_core="TW Core Organization／Location", terminology="Organization identifier",
                     transform="比較執行機構與 HOSPID，衍生本院／他院。")
        elif n == 4:
            m.update(fhir_resource="Procedure", fhir_path="Procedure.code / bodySite", tw_core="TW Core Procedure",
                     mcode="CancerRelatedSurgicalProcedure", terminology="SNOMED CT", decision="Reuse mCODE")
        elif n in {5, 6}:
            m.update(fhir_resource="MedicationAdministration", fhir_path="MedicationAdministration.medicationCodeableConcept",
                     tw_core="TW Core MedicationAdministration", mcode="CancerRelatedMedicationAdministration",
                     terminology="臺灣健保藥品碼／ATC／RxNorm ConceptMap", decision="Reuse mCODE",
                     transform="標準藥碼映射至 QBC A/B/C 代碼；其他保留原文。")
        elif n in {7, 8}:
            m.update(fhir_resource="RadiotherapyCourseSummary/RadiotherapyVolume", fhir_path="bodySite / location",
                     tw_core="TW Core Procedure/BodyStructure", mcode="RadiotherapyCourseSummary / RadiotherapyVolume",
                     terminology="SNOMED CT body structure", decision="Reuse mCODE",
                     transform="標準部位映射至 QBC A1-A5；其他保留原文。")
        elif n == 9:
            m.update(fhir_resource="Procedure/MedicationAdministration", fhir_path="performedPeriod.start / effectivePeriod.start",
                     tw_core="TW Core Procedure／MedicationAdministration", mcode="mCODE treatment profiles", terminology="FHIR date")
        elif n == 10:
            m.update(fhir_resource="Procedure/MedicationAdministration", fhir_path="performedPeriod.end / effectivePeriod.end",
                     tw_core="TW Core Procedure／MedicationAdministration", mcode="mCODE treatment profiles", terminology="FHIR date")
        return m

    # Follow-up fields
    m.update(canonical_entity="QBCFollowUp", source_priority="個管系統 > EMR > 死亡／轉院主檔")
    n = int(tag[1:])
    if n == 1:
        m.update(fhir_resource="Observation/QuestionnaireResponse", fhir_path="effectiveDateTime / authored",
                 tw_core="TW Core Observation", terminology="FHIR date", decision="QBC Profile",
                 extension="No", review_note="建議建立 QBC Follow-up Observation/QuestionnaireResponse Profile。")
    elif n in {2, 3}:
        m.update(fhir_resource="EpisodeOfCare/Observation", fhir_path="EpisodeOfCare.status / Observation.valueCodeableConcept",
                 tw_core="TW Core EpisodeOfCare／Observation", terminology="QBC CodeSystem",
                 decision="QBC Extension", extension="Yes",
                 extension_name="qbc-treatment-status" if n == 2 else "qbc-followup-status",
                 review_note="QBC 組合狀態不是單一 FHIR status 的直接等價。")
    elif n == 4:
        m.update(fhir_resource="EpisodeOfCare", fhir_path="EpisodeOfCare.period.end / extension",
                 tw_core="TW Core EpisodeOfCare（若有）", terminology="FHIR date",
                 decision="QBC Extension", extension="Yes", extension_name="qbc-transfer-date")
    elif n == 5:
        m.update(fhir_resource="EpisodeOfCare", fhir_path="EpisodeOfCare.period.end",
                 tw_core="TW Core EpisodeOfCare（若有）", terminology="FHIR date", decision="FHIR Profile")
    elif n == 6:
        m.update(fhir_resource="Patient", fhir_path="Patient.deceasedDateTime", tw_core="TW Core Patient",
                 mcode="CancerPatient（內容對齊）", terminology="FHIR date", decision="Reuse TW Core")
    return m


def load_fields():
    payload = json.loads(EXTRACTED_SPEC.read_text(encoding="utf-8"))
    if payload.get("status") != "unofficial-derived-draft":
        raise RuntimeError(f"Unexpected extracted QBC specification status in {EXTRACTED_SPEC}")
    rows = []
    for item, spec in enumerate(payload["fields"], start=1):
        tag = spec["tag"]
        label = spec["label"]
        required = spec["required_marker"]
        fmt = spec["source_format"]
        rule = spec["source_rule"]
        if spec["section"] != section_for(tag):
            raise RuntimeError(f"Section mismatch for {tag} in {EXTRACTED_SPEC}")
        mapped = map_field(tag, label)
        rows.append({
            "項次": str(item),
            "區段": spec["section"],
            "QBC Tag": tag,
            "QBC 中文名稱": label,
            "必要性": required,
            "QBC 格式": fmt,
            "QBC 原始規則": rule,
            "Canonical Entity": mapped["canonical_entity"],
            "FHIR Resource": mapped["fhir_resource"],
            "FHIR Path": mapped["fhir_path"],
            "TW Core 對應": mapped["tw_core"],
            "mCODE 對應": mapped["mcode"],
            "術語系統": mapped["terminology"],
            "建議標準碼／單位": mapped["standard_code"],
            "設計決策": mapped["decision"],
            "需要 Extension": mapped["extension"],
            "Extension 候選名稱": mapped["extension_name"],
            "院內來源優先序": mapped["source_priority"],
            "轉換／驗證規則": mapped["transform"],
            "映射信心": mapped["confidence"],
            "待確認事項": mapped["review_note"],
        })
    if len(rows) != 115:
        raise RuntimeError(f"Expected 115 fields, got {len(rows)}")
    return rows


def style_sheet(ws, widths, freeze="A2", filter_ref=None):
    ws.freeze_panes = freeze
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = filter_ref or ws.dimensions
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="0F766E")
        cell.font = Font(name="Arial", color="FFFFFF", bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 34
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=9)
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def add_table(ws, name):
    tab = Table(displayName=name, ref=ws.dimensions)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
    ws.add_table(tab)


def build():
    fields = load_fields()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("README")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "QBC × FHIR R4 × TW Core × mCODE 對照表"
    ws["A1"].font = Font(name="Arial", size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="0F766E")
    ws.merge_cells("A1:F1")
    ws["A3"] = "目的"
    ws["B3"] = "將健保署 QBC 乳癌 XML 115 個欄位映射至跨院共同資料模型，優先重用 FHIR/TW Core/mCODE/LOINC，僅在無標準語意時提出 QBC Extension。"
    ws["A4"] = "版本"
    ws["B4"] = "0.1（設計草案；非衛福部、健保署、TW Core 或 HL7 官方發布）"
    ws["A5"] = "基準"
    ws["B5"] = "QBC XML 格式說明 11507 定版；TW Core IG v1.0.0；mCODE v4.0.0；FHIR R4"
    ws["A7"] = "判讀方式"
    ws["B7"] = "High＝可直接採標準；Medium＝模型方向明確但需術語／Profile 確認；Low＝需領域專家與治理會議決定。"
    ws["A9"] = "重要架構決策"
    decisions = [
        "TW Core 是臺灣基礎層；mCODE 用於腫瘤內容對齊，但因 mCODE 為 US Realm，不假設可與 TW Core 直接多重繼承。",
        "保留原始臨床值與 QBC 正規化值，例如 pT1c 與 T1 同時保存。",
        "de novo mBC：臨床首次復發=false，但 DIAG_TYPE=3；P08 仍依 Class 1/2，不得連動成 3。",
        "QBC XML 是輸出格式；canonical/FHIR 模型是跨醫院資料交換層。",
        "所有人工或 LLM 擷取值須保留 Provenance／Evidence，不直接覆寫來源資料。",
    ]
    for i, d in enumerate(decisions, 10):
        ws[f"A{i}"] = f"{i-9}."
        ws[f"B{i}"] = d
    ws["A17"] = "官方參考"
    refs = [
        ("TW Core IG", TWCORE),
        ("mCODE v4.0.0", MCODE),
        ("FHIR R4 Profiling", FHIR + "profiling.html"),
        ("FHIR StructureDefinition", FHIR + "structuredefinition.html"),
        ("LOINC", "https://loinc.org/"),
    ]
    for i, (name, url) in enumerate(refs, 18):
        ws[f"A{i}"] = name
        ws[f"B{i}"] = url
        ws[f"B{i}"].hyperlink = url
        ws[f"B{i}"].style = "Hyperlink"
    for c in ["A3", "A4", "A5", "A7", "A9", "A17"]:
        ws[c].font = Font(name="Arial", bold=True, color="0F766E")
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 115
    for row in ws.iter_rows():
        for c in row:
            c.font = c.font.copy(name="Arial")
            c.alignment = Alignment(vertical="top", wrap_text=True)

    ws = wb.create_sheet("Field_Mapping_115")
    headers = list(fields[0].keys())
    ws.append(headers)
    for row in fields:
        ws.append([row[h] for h in headers])
    widths = {
        "A": 8, "B": 18, "C": 14, "D": 35, "E": 9, "F": 12, "G": 70,
        "H": 24, "I": 28, "J": 45, "K": 30, "L": 34, "M": 38, "N": 24,
        "O": 25, "P": 16, "Q": 28, "R": 42, "S": 55, "T": 12, "U": 45,
    }
    style_sheet(ws, widths, freeze="A2", filter_ref=f"A1:U{ws.max_row}")
    add_table(ws, "QBCFieldMapping")
    yes_fill = PatternFill("solid", fgColor="FDE68A")
    review_fill = PatternFill("solid", fgColor="FED7AA")
    low_fill = PatternFill("solid", fgColor="FECACA")
    ws.conditional_formatting.add(f"P2:P{ws.max_row}", FormulaRule(formula=["$P2=\"Yes\""], fill=yes_fill))
    ws.conditional_formatting.add(f"P2:P{ws.max_row}", FormulaRule(formula=["$P2=\"Review\""], fill=review_fill))
    ws.conditional_formatting.add(f"T2:T{ws.max_row}", FormulaRule(formula=["$T2=\"Low\""], fill=low_fill))

    ext_rows = [r for r in fields if r["需要 Extension"] in {"Yes", "Review"}]
    ws = wb.create_sheet("Extension_Candidates")
    ext_headers = ["QBC Tag", "QBC 中文名稱", "FHIR Resource", "FHIR Path", "需要 Extension", "Extension 候選名稱", "設計決策", "理由／待確認"]
    ws.append(ext_headers)
    for r in ext_rows:
        ws.append([r["QBC Tag"], r["QBC 中文名稱"], r["FHIR Resource"], r["FHIR Path"], r["需要 Extension"], r["Extension 候選名稱"], r["設計決策"], r["待確認事項"]])
    style_sheet(ws, {"A": 14, "B": 36, "C": 28, "D": 44, "E": 16, "F": 30, "G": 25, "H": 65})
    add_table(ws, "QBCExtensionCandidates")

    ws = wb.create_sheet("Hospital_Source_Model")
    source_headers = ["資料領域", "共同 Canonical Entity", "優先來源", "次要來源", "跨院最低共同輸入", "人工核對重點"]
    ws.append(source_headers)
    source_rows = [
        ["病人基本資料", "Patient", "病人主檔", "EMR", "標準 Excel／FHIR Patient", "識別碼串接與生日"],
        ["收案與分類", "QBCEnrollment", "個管系統", "癌症計畫書", "標準 Excel", "DIAG_TYPE、P08、de novo mBC"],
        ["癌症分期", "CancerStage", "癌症計畫書／癌登", "病理與影像", "FHIR Observation／標準 Excel", "TNM 正規化與 Stage 衝突"],
        ["病理與生物標記", "PathologyAssessment", "病理 LIS", "已簽章計畫書 PDF", "DiagnosticReport/Observation／標準 Excel", "術前、術後、復發檢體不可混用"],
        ["手術", "CancerTreatment", "手術紀錄", "癌症計畫書", "Procedure／標準 Excel", "排除 Port-A 等非治癒性手術"],
        ["藥物治療", "CancerTreatment", "實際給藥／藥局", "癌症計畫書", "MedicationAdministration／標準 Excel", "計畫與實際執行差異"],
        ["放射治療", "CancerTreatment", "放療系統", "癌症計畫書", "RadiotherapyCourseSummary／標準 Excel", "部位與完成日期"],
        ["追蹤與結案", "QBCFollowUp", "個管系統", "死亡／轉院主檔", "標準 Excel", "年度、轉出、結案、死亡條件"],
        ["文件證據", "Evidence/Provenance", "來源系統稽核軌跡", "PDF", "Provenance/DocumentReference", "來源版本、簽章、頁碼"],
    ]
    for r in source_rows:
        ws.append(r)
    style_sheet(ws, {"A": 20, "B": 28, "C": 32, "D": 32, "E": 42, "F": 55})
    add_table(ws, "HospitalSourceModel")

    ws = wb.create_sheet("Terminology_Register")
    term_headers = ["用途", "優先術語／標準", "已確認代碼／單位", "狀態", "備註", "官方來源"]
    ws.append(term_headers)
    terms = [
        ["身高", "LOINC + UCUM", "8302-2；cm", "Confirmed", "", "https://loinc.org/8302-2"],
        ["體重", "LOINC + UCUM", "29463-7；kg", "Confirmed", "", "https://loinc.org/29463-7"],
        ["ER 百分比", "LOINC + UCUM", "85329-1；%", "Confirmed", "乳癌檢體免疫染色", "https://loinc.org/85329-1"],
        ["HER2 IHC", "LOINC", "85319-2", "Confirmed", "乳癌檢體免疫染色序位結果", "https://loinc.org/85319-2"],
        ["Ki-67 百分比", "LOINC + UCUM", "85330-9；%", "Confirmed", "乳癌檢體免疫染色", "https://loinc.org/85330-9"],
        ["PR 百分比", "LOINC + UCUM", "待選定 assay-specific code；%", "Review", "由病理與術語專家確認", "https://loinc.org/"],
        ["HER2 ISH/FISH", "LOINC", "待選定 assay-specific code", "Review", "需區分方法與結果", "https://loinc.org/"],
        ["PD-L1", "LOINC", "待選定 assay／score-specific code", "Review", "需保存 assay、CPS/TPS 等", "https://loinc.org/"],
        ["TNM／Stage", "AJCC", "版本必須保存", "Governance", "注意授權與 QBC 降階映射", "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/"],
        ["診斷／部位／手術", "SNOMED CT", "ConceptMap 待建", "Review", "與院內碼、ICD-10-CM、QBC 代碼對照", "https://www.snomed.org/"],
        ["藥品", "臺灣健保藥品碼／ATC", "ConceptMap 待建", "Review", "必要時保留院內藥碼；不強迫 RxNorm", "https://www.nhi.gov.tw/"],
    ]
    for r in terms:
        ws.append(r)
    style_sheet(ws, {"A": 25, "B": 28, "C": 30, "D": 16, "E": 55, "F": 75})
    add_table(ws, "TerminologyRegister")
    for row in ws.iter_rows(min_row=2, min_col=6, max_col=6):
        cell = row[0]
        if cell.value:
            cell.hyperlink = cell.value
            cell.style = "Hyperlink"
            cell.font = Font(name="Arial", color="0563C1", underline="single", size=9)

    ws = wb.create_sheet("Mapping_Summary")
    ws.append(["指標", "數量", "說明"])
    decisions_count = Counter(r["設計決策"] for r in fields)
    confidence_count = Counter(r["映射信心"] for r in fields)
    summary = [
        ["QBC 欄位總數", len(fields), "由官方 Word 規格擷取"],
        ["Extension=Yes", sum(r["需要 Extension"] == "Yes" for r in fields), "明確方案特有概念"],
        ["Extension=Review", sum(r["需要 Extension"] == "Review" for r in fields), "可能以衍生旗標取代 Extension"],
        ["High confidence", confidence_count["High"], "可直接採用既有標準或明確轉換"],
        ["Medium confidence", confidence_count["Medium"], "需術語或 Profile 審查"],
        ["Low confidence", confidence_count["Low"], "需領域／治理決議"],
    ]
    for k, v in sorted(decisions_count.items()):
        summary.append([f"Decision: {k}", v, "Field_Mapping_115 的設計決策分類"])
    for r in summary:
        ws.append(r)
    style_sheet(ws, {"A": 35, "B": 14, "C": 75})
    add_table(ws, "MappingSummary")

    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(OUT)
    from formalize_qbc_mapping import formalize
    formalize(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
