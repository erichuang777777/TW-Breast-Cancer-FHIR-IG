import argparse,json
from pathlib import Path
from .exporter import export_case
from .fhir import build_bundle
from .importers import import_batch
from .store import JsonStore
from .xml_validation import receive_qbc_xml, validate_xml_file

def main():
    p=argparse.ArgumentParser(prog="qbc-workbench"); sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("serve"); s.add_argument("--host",default="127.0.0.1"); s.add_argument("--port",type=int,default=8765)
    i=sub.add_parser("import"); i.add_argument("source"); i.add_argument("--batch",required=True); i.add_argument("--case",action="append")
    e=sub.add_parser("export"); e.add_argument("--batch",required=True); e.add_argument("--case",required=True); e.add_argument("--filename",required=True)
    v=sub.add_parser("validate-xml"); v.add_argument("file",type=Path)
    m=sub.add_parser("mock-receive"); m.add_argument("file",type=Path)
    a=p.parse_args(); store=JsonStore(Path("runtime/batches"))
    if a.cmd=="serve":
        import uvicorn; uvicorn.run("qbc_workbench.web:app",host=a.host,port=a.port,reload=False)
    elif a.cmd=="import":
        b=import_batch(Path(a.source),a.batch,a.case); [setattr(c,"fhir_bundle",build_bundle(c)) for c in b.cases.values()]; store.save(b); print(json.dumps({"batch":b.batch_id,"cases":list(b.cases)},ensure_ascii=False))
    elif a.cmd=="export":
        b=store.load(a.batch); print(export_case(b.cases[a.case],Path("runtime/exports")/a.batch,a.filename))
    elif a.cmd=="validate-xml":
        print(json.dumps(validate_xml_file(a.file),ensure_ascii=False,indent=2))
    elif a.cmd=="mock-receive":
        print(json.dumps(receive_qbc_xml(a.file.name,a.file.read_bytes()),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
