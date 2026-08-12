from pathlib import Path
import pytest
from qbc_workbench.exporter import export_case,validate_filename
from qbc_workbench.models import CaseRecord,Method,TreatmentEvent
from qbc_workbench.rules import ev,put

def test_filename():
    assert validate_filename("QBC_3501200000_11508_001.xml")
    assert not validate_filename("bad.xml")

def test_export_is_blocked_when_required_fields_missing(tmp_path:Path):
    with pytest.raises(ValueError,match="not export-ready"):
        export_case(CaseRecord(case_id="x"),tmp_path,"QBC_3501200000_11508_001.xml")

def test_big5_xml_export(tmp_path:Path):
    c=CaseRecord(case_id="x",diagnosis_type="2")
    values={"HOSPID":"3501200000","ID":"A123456789","BIRTHDAY":"19800101","DIAG_TYPE":"2","LATERALITY":"L","P01":"王大明","P02":"1","P03":"160","P04":"55","P05":"2","P07":"B123456789","P08":"1","P09":"20260101","D001":"20251231","D011":"1"}
    for tag,value in values.items(): put(c,tag,value,Method.MANUAL,ev("test","test"),"test")
    c.treatments.append(TreatmentEvent(sequence=1,treatment_type="2",location="1",actual_start="20260102",actual_end="20260202"))
    xml,_=export_case(c,tmp_path,"QBC_3501200000_11508_001.xml")
    data=xml.read_bytes(); assert b'encoding="Big5"' in data; assert "王大明" in data.decode("big5")
