import hashlib,json,re
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,tostring
from .models import CaseRecord,ReviewStatus
from .rules import validate

ROOT_TAGS=["HOSPID","ID","BIRTHDAY","DIAG_TYPE","LATERALITY"]
SEC01=[f"P{i:02d}" for i in range(1,10)]; SEC02=[f"D{i:03d}" for i in range(1,86)]

def validate_filename(name): return bool(re.fullmatch(r"QBC_\d{10}_\d{5}_\d{3}\.xml",name,re.I))

def export_case(case:CaseRecord,output:Path,filename:str):
    if not validate_filename(filename): raise ValueError("invalid QBC filename")
    if problems:=validate(case): raise ValueError("case is not export-ready: "+"; ".join(problems))
    root=Element("QBC"); node=SubElement(root,"CASE")
    def emit(parent,tags):
        for tag in tags:
            c=case.candidates.get(tag)
            if c and c.value is not None and c.status!=ReviewStatus.NOT_APPLICABLE: SubElement(parent,tag).text=c.value
    emit(node,ROOT_TAGS); emit(SubElement(node,"SEC01"),SEC01); emit(SubElement(node,"SEC02"),SEC02)
    if case.treatments:
        treatments=SubElement(node,"TREATMENTS")
        for x in sorted(case.treatments,key=lambda y:y.sequence):
            t=SubElement(treatments,"TREATMENT")
            vals={"TM01":str(x.sequence),"TM02":x.treatment_type,"TM03":x.location,"TM04":x.surgery_code,"TM05":",".join(x.drug_codes) or None,"TM06":x.other_drug,"TM07":",".join(x.site_codes) or None,"TM08":x.other_site,"TM09":x.actual_start,"TM10":x.actual_end}
            for tag in [f"TM{i:02d}" for i in range(1,11)]:
                if vals.get(tag) is not None: SubElement(t,tag).text=vals[tag]
    if case.followups:
        traces=SubElement(node,"TRACES")
        for x in sorted(case.followups,key=lambda y:y.trace_date):
            trace=SubElement(traces,"TRACE")
            vals={"T01":x.trace_date,"T02":x.treatment_status,"T03":x.followup_status,"T04":x.transfer_date,"T05":x.close_date,"T06":x.death_date}
            for tag in [f"T{i:02d}" for i in range(1,7)]:
                if vals.get(tag) is not None: SubElement(trace,tag).text=vals[tag]
    body=tostring(root,encoding="big5",xml_declaration=False); data=b'<?xml version="1.0" encoding="Big5"?>\r\n'+body
    from .xml_validation import validate_xml_bytes
    report=validate_xml_bytes(data,filename,case)
    if not report["accepted"]:
        raise ValueError("generated XML failed pre-validation: "+"; ".join(item["message"] for item in report["issues"] if item["severity"]=="error"))
    output.mkdir(parents=True,exist_ok=True); xml=output/filename; xml.write_bytes(data)
    audit={"case_id":case.case_id,"xml_file":filename,"sha256":hashlib.sha256(data).hexdigest(),"validation":report,"fields":{k:v.model_dump(mode="json") for k,v in case.candidates.items()}}
    audit_path=xml.with_suffix(".audit.json"); audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    return xml,audit_path
