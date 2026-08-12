from qbc_workbench.models import CaseRecord
from qbc_workbench.rules import derive_stage,ev,extract_pathology,put
from qbc_workbench.models import Method

def test_stage_rules():
    c=CaseRecord(case_id="x")
    for tag,value in [("D005","T2"),("D006","N0"),("D007","M0")]: put(c,tag,value,Method.STRUCTURED,ev("x","test"),"test")
    derive_stage(c,"D005","D006","D007","D008")
    assert c.candidates["D008"].value=="StageⅡA"

def test_pathology_node_parser_requires_review():
    c=CaseRecord(case_id="x")
    extract_pathology(c,"Lymph node, axillary, left, core biopsy, invasive carcinoma of no special type. involved/total: 7/13", "p.txt")
    assert c.candidates["D012"].value=="2"
    assert c.candidates["D013"].value=="1"
    assert c.candidates["D012"].status.value=="pending_review"
    assert c.candidates["D042"].value=="7" and c.candidates["D043"].value=="13"

