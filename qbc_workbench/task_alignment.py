from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .care_plan import build_cancer_care_plan_bundle, parse_cancer_care_plan_json
from .fhir import build_bundle as build_qbc_bundle
from .importers import import_case_json
from .models import CaseRecord


class ParallelTaskAlignmentOutputs(BaseModel):
    relationship: Literal["parallel-task-alignment-check"] = "parallel-task-alignment-check"
    care_plan_check_bundle: dict[str, Any]
    qbc_check_bundle: dict[str, Any]


def build_parallel_task_alignment_outputs(
    path: Path, case_id: str
) -> ParallelTaskAlignmentOutputs:
    """Build independent task views from one test source for reconciliation only.

    Neither Bundle is used to generate the other. The production target is for
    both task adapters to consume the same reviewed breast-cancer FHIR facts.
    """
    care_plan_record = parse_cancer_care_plan_json(path, case_id)
    qbc_case = CaseRecord(case_id=case_id)
    import_case_json(path, qbc_case)
    return ParallelTaskAlignmentOutputs(
        care_plan_check_bundle=build_cancer_care_plan_bundle(care_plan_record),
        qbc_check_bundle=build_qbc_bundle(qbc_case),
    )
