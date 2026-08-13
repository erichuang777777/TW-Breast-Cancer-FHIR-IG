from __future__ import annotations
import re
from .models import Candidate,CaseRecord,Evidence,Method,ReviewStatus

STAGE={"TisN0M0":"Stage0","T1N0M0":"StageⅠA","T0N1miM0":"StageⅠB","T1N1miM0":"StageⅠB",
"T2N0M0":"StageⅡA","T0N1M0":"StageⅡA","T1N1M0":"StageⅡA","T3N0M0":"StageⅡB","T2N1M0":"StageⅡB",
"T3N1M0":"StageⅢA","T3N2M0":"StageⅢA","T0N2M0":"StageⅢA","T1N2M0":"StageⅢA","T2N2M0":"StageⅢA",
"T4N0M0":"StageⅢB","T4N1M0":"StageⅢB","T4N2M0":"StageⅢB"}

def calculate_stage(t, n, m):
    if m == "M1": return "StageⅣ"
    if n == "N3" and m == "M0": return "StageⅢC"
    if t == "Tx" and n == "Nx" and m in {"Mx", "M0"}: return "StageX"
    return STAGE.get(f"{t}{n}{m}")

# 「較嚴重」的判定順序。專案決議 2026-08-13：以期別群組排序 Ⅲ > Ⅱ > Ⅰ，
# 同期別再以腫瘤大小排序。Ⅳ > Ⅲ 與 Ⅰ > 0 為依臨床邏輯之延伸，Stage X（未知）
# 無法排序，一律交人工判定。用於同側多型態擇一申報，以及雙側個案的較嚴重側判定。
STAGE_GROUP = {"0": 0, "Ⅰ": 1, "Ⅱ": 2, "Ⅲ": 3, "Ⅳ": 4}


def stage_group(stage):
    """把 StageⅢA 之類的分期值轉成群組序數；未知或無法解析回傳 None。"""
    if not stage: return None
    text = str(stage).replace(" ", "").removeprefix("Stage")
    if text.upper() == "X": return None
    return STAGE_GROUP.get(text[:1])


def severity_rank(stage, tumor_size_cm=None):
    """回傳可比較的嚴重度序數；分期未知時回傳 None，代表必須人工判定。"""
    group = stage_group(stage)
    if group is None: return None
    try:
        size = float(tumor_size_cm) if tumor_size_cm not in (None, "") else -1.0
    except (TypeError, ValueError):
        size = -1.0
    return (group, size)


def more_severe(lesions):
    """從 [(識別, 分期, 腫瘤大小), ...] 選出較嚴重者。

    任一病灶分期未知即回傳 None——寧可要求人工判定，也不猜測。
    嚴重度完全相同時同樣回傳 None，因為排序無法決定申報哪一筆。
    """
    ranked = [(severity_rank(stage, size), key) for key, stage, size in lesions]
    if not ranked or any(rank is None for rank, _ in ranked): return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]: return None
    return ranked[0][1]

def ev(file,kind,text=None,path=None): return Evidence(source_file=file,source_type=kind,text=text,source_path=path)

def put(case,tag,value,method,evidence,rule,display=None,confidence=1.0,review=False):
    status=ReviewStatus.PENDING if review or method in (Method.AI_EXTRACTION,Method.AI_INFERENCE) else ReviewStatus.AUTO_ACCEPTED
    new=Candidate(qbc_tag=tag,value=None if value is None else str(value),display=display,method=method,status=status,
                  confidence=confidence,evidence=[evidence],rule_id=rule)
    old=case.candidates.get(tag)
    if old and old.value!=new.value:
        old.status=ReviewStatus.CONFLICT; old.notes.append(f"conflicting candidate: {new.value}"); old.evidence.append(evidence)
    else: case.candidates[tag]=new

def derive_stage(case,t,n,m,out):
    vals=[case.candidates.get(x) for x in (t,n,m)]
    if not all(vals) or not all(x.value for x in vals): return
    key="".join(x.value for x in vals); stage=calculate_stage(*(x.value for x in vals))
    if stage: put(case,out,stage,Method.RULE_DERIVED,ev("rule-engine","derived",key),"AJCC8_STAGE")

def extract_pathology(case,text,filename):
    e=ev(filename,"pathology",text[:2000]); low=text.lower()
    if re.search(r"lymph node\s*,?\s*axillary\s*,?\s*(left|right).*?core biopsy",low,re.S) and re.search(r"invasive carcinoma|metastatic carcinoma|positive",low):
        put(case,"D012","2",Method.RULE_EXTRACTION,e,"PATH_AXILLARY_CORE","粗針切片",.98,True)
        put(case,"D013","1",Method.RULE_EXTRACTION,e,"PATH_AXILLARY_POSITIVE","陽性",.95,True)
    ratio=re.search(r"involved\s*/\s*total\s*:\s*(\d+)\s*/\s*(\d+)",low)
    if ratio:
        p,t=ratio.groups(); put(case,"D041","1" if int(p) else "0",Method.RULE_EXTRACTION,e,"PATH_ALND_RESULT")
        put(case,"D042",p,Method.RULE_EXTRACTION,e,"PATH_ALND_POSITIVE"); put(case,"D043",t,Method.RULE_EXTRACTION,e,"PATH_ALND_TOTAL")
        put(case,"D044","1" if int(p) else "0",Method.RULE_DERIVED,e,"NODE_POSITIVE_DERIVED")
    for tag,pattern,rule in [("D045",r"no\.\s*micrometastases[^:]*:\s*(\d+)","PATH_MICRO_COUNT"),("D046",r"no\.\s*macrometastases[^:]*:\s*(\d+)","PATH_MACRO_COUNT"),("D047",r"size of invasive carcinoma\s*:\s*([0-9.]+)\s*cm","PATH_TUMOR_SIZE")]:
        if m:=re.search(pattern,low): put(case,tag,m.group(1),Method.RULE_EXTRACTION,e,rule)
    if "no definite response to presurgical" in low or "residual invasive carcinoma" in low:
        put(case,"D024","0",Method.RULE_EXTRACTION,e,"PATH_NON_PCR","Non-pCR",.98)

def mark_applicability(case,tags):
    for tag in tags:
        d=case.diagnosis_type
        na=(d=="2" and (tag in {"D025","D026"} or "D058"<=tag<="D085")) or (d=="1" and ("D001"<=tag<="D024" or "D058"<=tag<="D085")) or (d=="3" and "D001"<=tag<="D057")
        if na and tag not in case.candidates: case.candidates[tag]=Candidate(qbc_tag=tag,method=Method.MISSING,status=ReviewStatus.NOT_APPLICABLE)

def validate(case):
    from .validation import validate_case
    case.issues = [str(issue) for issue in validate_case(case) if issue.severity == "error"]
    return case.issues
