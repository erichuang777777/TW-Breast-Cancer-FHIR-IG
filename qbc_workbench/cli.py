import argparse
import json
from pathlib import Path

from .care_plan import build_cancer_care_plan_bundle, parse_cancer_care_plan_json
from .exporter import export_case
from .fhir import build_bundle
from .importers import import_batch
from .store import JsonStore
from .task_alignment import build_parallel_task_alignment_outputs
from .xml_validation import receive_qbc_xml, validate_xml_file


def _add_case_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", type=Path, required=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="qbc-workbench")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("source")
    import_parser.add_argument("--batch", required=True)
    import_parser.add_argument("--case", action="append")

    export = subparsers.add_parser("export")
    export.add_argument("--batch", required=True)
    export.add_argument("--case", required=True)
    export.add_argument("--filename", required=True)

    validate = subparsers.add_parser("validate-xml")
    validate.add_argument("file", type=Path)

    mock = subparsers.add_parser("mock-receive")
    mock.add_argument("file", type=Path)

    care_plan = subparsers.add_parser("transform-care-plan")
    _add_case_source_arguments(care_plan)

    alignment = subparsers.add_parser("check-task-alignment")
    _add_case_source_arguments(alignment)

    args = parser.parse_args()
    store = JsonStore(Path("runtime/batches"))

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run(
            "qbc_workbench.web:app",
            host=args.host,
            port=args.port,
            reload=False,
        )
    elif args.cmd == "import":
        batch = import_batch(Path(args.source), args.batch, args.case)
        for case in batch.cases.values():
            case.fhir_bundle = build_bundle(case)
        store.save(batch)
        print(
            json.dumps(
                {"batch": batch.batch_id, "cases": list(batch.cases)},
                ensure_ascii=False,
            )
        )
    elif args.cmd == "export":
        batch = store.load(args.batch)
        print(
            export_case(
                batch.cases[args.case],
                Path("runtime/exports") / args.batch,
                args.filename,
            )
        )
    elif args.cmd == "validate-xml":
        print(json.dumps(validate_xml_file(args.file), ensure_ascii=False, indent=2))
    elif args.cmd == "mock-receive":
        result = receive_qbc_xml(args.file.name, args.file.read_bytes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "transform-care-plan":
        record = parse_cancer_care_plan_json(args.file, args.case)
        bundle = build_cancer_care_plan_bundle(record)
        args.output.mkdir(parents=True, exist_ok=True)
        care_path = args.output / f"{args.case}.care-plan.fhir.json"
        care_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"care_plan": str(care_path)}, ensure_ascii=False))
    elif args.cmd == "check-task-alignment":
        outputs = build_parallel_task_alignment_outputs(args.file, args.case)
        args.output.mkdir(parents=True, exist_ok=True)
        care_path = args.output / f"{args.case}.care-plan.check.fhir.json"
        qbc_path = args.output / f"{args.case}.qbc.check.fhir.json"
        care_path.write_text(
            json.dumps(outputs.care_plan_check_bundle, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        qbc_path.write_text(
            json.dumps(outputs.qbc_check_bundle, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "relationship": outputs.relationship,
                    "care_plan_check": str(care_path),
                    "qbc_check": str(qbc_path),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
