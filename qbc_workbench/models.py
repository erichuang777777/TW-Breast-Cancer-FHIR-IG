from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class Method(str, Enum):
    STRUCTURED="structured"; MASTER_LOOKUP="master_lookup"; RULE_EXTRACTION="rule_extraction"
    RULE_DERIVED="rule_derived"; AI_EXTRACTION="ai_extraction"; AI_INFERENCE="ai_inference"
    MANUAL="manual"; MISSING="missing"

class ReviewStatus(str, Enum):
    AUTO_ACCEPTED="auto_accepted"; PENDING="pending_review"; APPROVED="approved"
    REJECTED="rejected"; CONFLICT="conflict"; MISSING="missing"; NOT_APPLICABLE="not_applicable"

class Evidence(BaseModel):
    source_file:str; source_type:str; source_path:str|None=None; source_date:str|None=None
    text:str|None=None; page:int|None=None; input_hash:str|None=None

class Candidate(BaseModel):
    qbc_tag:str; value:str|None=None; display:str|None=None; method:Method; status:ReviewStatus
    confidence:float=Field(ge=0,le=1,default=1); evidence:list[Evidence]=Field(default_factory=list)
    rule_id:str|None=None; notes:list[str]=Field(default_factory=list)
    reviewed_by:str|None=None; reviewed_at:str|None=None
    def approve(self, reviewer:str, value:str|None=None):
        if value is not None: self.value=value
        self.status=ReviewStatus.APPROVED; self.reviewed_by=reviewer
        self.reviewed_at=datetime.now(timezone.utc).isoformat()

class TreatmentEvent(BaseModel):
    sequence:int; treatment_type:str; location:str|None=None; drug_codes:list[str]=Field(default_factory=list)
    surgery_code:str|None=None
    other_drug:str|None=None; site_codes:list[str]=Field(default_factory=list); other_site:str|None=None
    planned_start:str|None=None; planned_end:str|None=None; actual_start:str|None=None; actual_end:str|None=None
    evidence:list[Evidence]=Field(default_factory=list)

class CarePlanTreatmentFact(BaseModel):
    """A treatment fact stated by the care-plan source before QBC code normalization."""
    sequence:int; category:str; phase:str|None=None; plan_date:str|None=None
    evidence:list[Evidence]=Field(default_factory=list)

class FollowUpEvent(BaseModel):
    trace_date:str
    treatment_status:str|None=None
    followup_status:str|None=None
    transfer_date:str|None=None
    close_date:str|None=None
    death_date:str|None=None
    evidence:list[Evidence]=Field(default_factory=list)

class CaseRecord(BaseModel):
    case_id:str; diagnosis_type:str|None=None; laterality:str|None=None
    diagnosis_type_assessment:str="pending_review"
    candidates:dict[str,Candidate]=Field(default_factory=dict); treatments:list[TreatmentEvent]=Field(default_factory=list)
    care_plan_treatment_facts:list[CarePlanTreatmentFact]=Field(default_factory=list)
    followups:list[FollowUpEvent]=Field(default_factory=list)
    # 惡性葉狀瘤／肉瘤等非乳癌上皮性腫瘤：一般乳癌 TNM 分期不適用，
    # 臨床手填分期優先，不得被自動計算結果推翻。專案決議 2026-08-13。
    non_epithelial_tumor:bool=False
    # 雙側個案必須左右各自建檔與各自上傳；此欄記錄對側的 case_id 供交叉檢查。
    bilateral_counterpart_case_id:str|None=None
    fhir_bundle:dict[str,Any]|None=None; issues:list[str]=Field(default_factory=list)
    source_files:list[str]=Field(default_factory=list); state:str="draft"; version:int=1

class BatchRecord(BaseModel):
    batch_id:str; cases:dict[str,CaseRecord]=Field(default_factory=dict)
    created_at:str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); source_directory:str|None=None
