# -*- coding: utf-8 -*-
"""FHIR R4 artefacts for reporting the Taiwan Cancer Registry from clinical data.

This module turns the verified TCR code tables in this package into the
conformance resources a breast-cancer Implementation Guide needs in order to
carry "abstract and submit the cancer-registry fields" as one of its tasks:

    CodeSystem      one per TCR field that has a verified code table, with the
                    code book's own Chinese wording as `display` and the
                    decoded English clinical label as an `en` designation
    ValueSet        one per field, for binding a Questionnaire item or an
                    Observation.valueCodeableConcept
    Questionnaire   the whole Longform submission as a structured form: 99
                    items, grouped, each bound to its ValueSet where one exists
    Task            profile + example modelling the abstraction job itself
                    (inputs = the source documents, output = the completed
                    QuestionnaireResponse / registry row)
    ConceptMap      skeletons for TCR code -> standard terminology; targets are
                    deliberately left EMPTY for a terminologist to fill, since
                    inventing LOINC/SNOMED mappings would be worse than an
                    honest gap
    ImplementationGuide  a manifest listing everything above

Nothing here invents a code table: a field is only given a ValueSet if this
package can prove its codes round-trip (see tcr_decoder/code_ranges.py and
tests/test_codebook_conformance.py). Fields whose code table has not been
transcribed yet are still present in the Questionnaire, as free-text items
carrying the `tcr-codetable-pending` extension, so the form is complete and
the gaps are visible rather than silently missing.

CANONICAL URLs: `base_url` defaults to a placeholder. Set it to the canonical
base your IG actually publishes under before using these artefacts anywhere
real -- a canonical URL is an identity claim, not a formatting detail.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from tcr_decoder.code_ranges import CODE_RANGES, LONGFORM, SURGERY_CODES
from tcr_decoder.ssf_registry import get_ssf_profile
from tcr_decoder.validation import zh_definition

DEFAULT_BASE_URL = 'https://example.org/fhir/tcr'
FHIR_VERSION = '4.0.1'

# ─────────────────────────────────────────────────────────────────────────────
# The 99 Longform fields: section, Chinese label, and where the value comes
# from in a FHIR-native EMR. `source` is the extraction layer's contract --
# it says which resource a fact should be read from, not that the mapping is
# automatic.
# ─────────────────────────────────────────────────────────────────────────────

# (raw field, zh label, FHIR source hint, source document type)
FIELD_MAP: Tuple[Tuple[str, str, str, str], ...] = (
    # ── 人口學與就診 ────────────────────────────────────────────────────────
    ('PK',        '病歷號／個案識別碼', 'Patient.identifier', 'ADT'),
    ('SEX',       '性別', 'Patient.gender', 'ADT'),
    ('AGE',       '診斷時年齡', 'Patient.birthDate + Condition.onsetDateTime', 'ADT'),
    ('DX_YEAR',   '診斷年', 'Condition.onsetDateTime', '病理報告'),
    ('DXDATE',    '診斷日期', 'Condition.onsetDateTime', '病理報告'),
    ('VISTDATE',  '首次就診日期', 'Encounter.period.start', 'ADT'),
    ('SMOKING',   '吸菸／檳榔／飲酒', 'Observation (social history)', '門診紀錄'),
    ('HEIGHT',    '身高', 'Observation LOINC 8302-2', '門診紀錄'),
    ('WEIGHT',    '體重', 'Observation LOINC 29463-7', '門診紀錄'),
    ('KPSECOG',   '體能狀態 ECOG/KPS', 'Observation (performance status)', '門診紀錄'),
    ('CLASS95',   '個案分類', 'derived: Encounter + Condition + Procedure', '院內系統'),
    ('CLASSOFDIAG', '診斷分類（本院／他院）', 'derived: DiagnosticReport.performer', '院內系統'),
    ('CLASSOFTREAT', '治療分類（本院／他院）', 'derived: Procedure.performer', '院內系統'),
    ('SEQ1',      '腫瘤總數', 'count of Condition (primary neoplasm)', '院內系統'),
    ('SEQ2',      '本腫瘤序號', 'ordinal of Condition.onsetDateTime', '院內系統'),

    # ── 腫瘤特性 ────────────────────────────────────────────────────────────
    ('TCODE1',    '原發部位 ICD-O-3', 'Condition.bodySite / Observation ICD-O-3 topography', '病理報告'),
    ('LAT95',     '側性', 'Condition.bodySite laterality qualifier', '病理報告'),
    ('MCODE',     '組織型態 ICD-O-3', 'Observation ICD-O-3 morphology', '病理報告'),
    ('MCODE5',    '行為碼', 'Observation ICD-O-3 behavior', '病理報告'),
    ('MCODE6',    '病理分化度', 'Observation (histologic grade)', '病理報告'),
    ('MCODE6C',   '臨床分化度', 'Observation (histologic grade, clinical)', '影像／門診'),
    ('CONFER',    '診斷確認方式', 'DiagnosticReport.category', '病理報告'),
    ('CSIZE95',   '腫瘤大小 (mm)', 'Observation (tumor size)', '病理報告'),
    ('PNI',       '神經周圍侵犯', 'Observation (perineural invasion)', '病理報告'),
    ('LVI',       '淋巴血管侵犯', 'Observation (lymphovascular invasion)', '病理報告'),
    ('LNEXAM',    '區域淋巴結檢查數', 'Observation (nodes examined)', '病理報告'),
    ('LN_POSITI', '區域淋巴結侵犯數', 'Observation (nodes positive)', '病理報告'),

    # ── 分期 ────────────────────────────────────────────────────────────────
    ('AJCC',      'AJCC 版本', 'Condition.stage.type', '病理報告'),
    ('CT',        '臨床 T', 'Condition.stage.assessment (clinical)', '影像／門診'),
    ('CN',        '臨床 N', 'Condition.stage.assessment (clinical)', '影像／門診'),
    ('CM',        '臨床 M', 'Condition.stage.assessment (clinical)', '影像／門診'),
    ('CSTG',      '臨床期別', 'Condition.stage.summary (clinical)', '影像／門診'),
    ('PT',        '病理 T', 'Condition.stage.assessment (pathologic)', '病理報告'),
    ('PN',        '病理 N', 'Condition.stage.assessment (pathologic)', '病理報告'),
    ('PM',        '病理 M', 'Condition.stage.assessment (pathologic)', '病理報告'),
    ('PSTG',      '病理期別', 'Condition.stage.summary (pathologic)', '病理報告'),
    ('SUMSTG',    '合併期別', 'derived: clinical + pathologic stage', '衍生'),
    ('OSTG',      '其他分期系統', 'Condition.stage.type', '病理報告'),
    ('OCSTG',     '其他系統臨床期別', 'Condition.stage.summary', '病理報告'),
    ('OPSTG',     '其他系統病理期別', 'Condition.stage.summary', '病理報告'),
    ('META1',     '遠端轉移部位 1', 'Condition (secondary neoplasm).bodySite', '影像報告'),
    ('META2',     '遠端轉移部位 2', 'Condition (secondary neoplasm).bodySite', '影像報告'),
    ('META3',     '遠端轉移部位 3', 'Condition (secondary neoplasm).bodySite', '影像報告'),

    # ── 手術 ────────────────────────────────────────────────────────────────
    ('S',         '本院手術', 'Procedure (surgical) exists', '手術紀錄'),
    ('FSDATE',    '首次手術日期', 'Procedure.performedDateTime', '手術紀錄'),
    ('PRESTYPE',  '他院手術方式', 'Procedure.code (external)', '轉診資料'),
    ('STYPE95',   '本院手術方式', 'Procedure.code', '手術紀錄'),
    ('MINS',      '微創手術', 'Procedure.category / method', '手術紀錄'),
    ('MARG95',    '手術切緣狀態', 'Observation (margin status)', '病理報告'),
    ('MARGDIS',   '手術切緣距離 (mm)', 'Observation (margin distance)', '病理報告'),
    ('PRESLNSCO', '他院區域淋巴結手術', 'Procedure.code (external)', '轉診資料'),
    ('SLNSCO95',  '本院區域淋巴結手術', 'Procedure.code', '手術紀錄'),

    # ── 癌症部位特定因子 SSF1-10 ───────────────────────────────────────────
    ('SSF1',  'SSF1 動情激素接受體 ER', 'Observation (ER)', '病理報告'),
    ('SSF2',  'SSF2 黃體激素接受體 PR', 'Observation (PR)', '病理報告'),
    ('SSF3',  'SSF3 前導性療法之療效', 'Observation (treatment response)', '門診／病理報告'),
    ('SSF4',  'SSF4 哨兵淋巴結檢查數目', 'Observation (sentinel nodes examined)', '病理報告'),
    ('SSF5',  'SSF5 哨兵淋巴結侵犯數目', 'Observation (sentinel nodes positive)', '病理報告'),
    ('SSF6',  'SSF6 Nottingham/BR 分數與級數', 'Observation (histologic grade)', '病理報告'),
    ('SSF7',  'SSF7 HER2 IHC/ISH', 'Observation (HER2)', '病理報告'),
    ('SSF8',  'SSF8 Paget 氏症', 'Observation (Paget disease)', '病理報告'),
    ('SSF9',  'SSF9 淋巴管或血管侵犯', 'Observation (lymphovascular invasion)', '病理報告'),
    ('SSF10', 'SSF10 Ki-67', 'Observation (Ki-67)', '病理報告'),

    # ── 放射治療 ────────────────────────────────────────────────────────────
    ('R',      '本院放射治療', 'Procedure (radiotherapy) exists', '放療紀錄'),
    ('RTAR',   '放療標的總結', 'Procedure.bodySite', '放療紀錄'),
    ('RMOD',   '放療方式', 'Procedure.code', '放療紀錄'),
    ('EBRT',   '體外放射治療技術', 'Procedure.code (technique)', '放療紀錄'),
    ('HTAR',   '高劑量標的', 'Procedure.bodySite', '放療紀錄'),
    ('HDOSE',  '高劑量劑量 (cGy)', 'Procedure / Observation (dose)', '放療紀錄'),
    ('HNO',    '高劑量分次數', 'Procedure / Observation (fractions)', '放療紀錄'),
    ('LTAR',   '低劑量標的', 'Procedure.bodySite', '放療紀錄'),
    ('LDOSE',  '低劑量劑量 (cGy)', 'Procedure / Observation (dose)', '放療紀錄'),
    ('LNO',    '低劑量分次數', 'Procedure / Observation (fractions)', '放療紀錄'),
    ('SEQRS',  '放療與手術順序', 'derived: Procedure.performedDateTime', '衍生'),
    ('SEQLS',  '局部與全身治療順序', 'derived: Procedure/MedicationAdministration dates', '衍生'),

    # ── 全身性治療 ──────────────────────────────────────────────────────────
    ('PREC',   '他院化學治療', 'MedicationAdministration (external)', '轉診資料'),
    ('C',      '本院化學治療', 'MedicationAdministration (antineoplastic)', '化療紀錄'),
    ('PREH',   '他院荷爾蒙治療', 'MedicationAdministration (external)', '轉診資料'),
    ('H',      '本院荷爾蒙治療', 'MedicationAdministration (hormone)', '化療／門診紀錄'),
    ('PREI',   '他院免疫治療', 'MedicationAdministration (external)', '轉診資料'),
    ('I',      '本院免疫治療', 'MedicationAdministration (immunotherapy)', '化療紀錄'),
    ('PREB',   '他院骨髓／幹細胞移植', 'Procedure (external)', '轉診資料'),
    ('B',      '本院骨髓／幹細胞移植', 'Procedure (transplant)', '移植紀錄'),
    ('PRETAR', '他院標靶治療', 'MedicationAdministration (external)', '轉診資料'),
    ('TAR',    '本院標靶治療', 'MedicationAdministration (targeted)', '化療紀錄'),
    ('OTH',    '其他治療', 'Procedure / MedicationAdministration', '門診紀錄'),
    ('PREP',   '安寧緩和照護', 'Procedure / CarePlan (palliative)', '門診紀錄'),
    ('WATCHWAITING', '積極監測', 'CarePlan (active surveillance)', '門診紀錄'),

    # ── 追蹤與結果 ──────────────────────────────────────────────────────────
    ('VSTA',      '生命狀態（首次追蹤）', 'Patient.deceased / Encounter', '追蹤紀錄'),
    ('CSTA',      '癌症狀態（首次追蹤）', 'Condition.clinicalStatus', '追蹤紀錄'),
    ('LCD',       '最後接觸日期', 'Encounter.period.end', '追蹤紀錄'),
    ('REDATE',    '復發日期', 'Condition (recurrence).onsetDateTime', '追蹤紀錄'),
    ('RETYPE95',  '復發型態', 'Condition (recurrence).code', '追蹤紀錄'),
    ('DIECAUSE',  '死亡原因', 'Patient.deceased + Observation (cause of death)', '死亡證明'),
    ('VSTA6',     '生命狀態（延長追蹤）', 'Patient.deceased', '追蹤紀錄'),
    ('LCD6',      '最後接觸日期（延長追蹤）', 'Encounter.period.end', '追蹤紀錄'),
    ('SURVY6',    '存活年數', 'derived: onset -> last contact', '衍生'),
    ('REDATE6',   '復發日期（延長追蹤）', 'Condition (recurrence).onsetDateTime', '追蹤紀錄'),
    ('RETYPE6',   '復發型態（延長追蹤）', 'Condition (recurrence).code', '追蹤紀錄'),
    ('DIECAUSE6', '死亡原因（延長追蹤）', 'Observation (cause of death)', '死亡證明'),
)

SECTIONS: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ('demographics', '人口學與就診', (
        'PK', 'SEX', 'AGE', 'DX_YEAR', 'DXDATE', 'VISTDATE', 'SMOKING',
        'HEIGHT', 'WEIGHT', 'KPSECOG', 'CLASS95', 'CLASSOFDIAG',
        'CLASSOFTREAT', 'SEQ1', 'SEQ2')),
    ('tumour', '腫瘤特性', (
        'TCODE1', 'LAT95', 'MCODE', 'MCODE5', 'MCODE6', 'MCODE6C', 'CONFER',
        'CSIZE95', 'PNI', 'LVI', 'LNEXAM', 'LN_POSITI')),
    ('staging', '分期', (
        'AJCC', 'CT', 'CN', 'CM', 'CSTG', 'PT', 'PN', 'PM', 'PSTG', 'SUMSTG',
        'OSTG', 'OCSTG', 'OPSTG', 'META1', 'META2', 'META3')),
    ('surgery', '手術', (
        'S', 'FSDATE', 'PRESTYPE', 'STYPE95', 'MINS', 'MARG95', 'MARGDIS',
        'PRESLNSCO', 'SLNSCO95')),
    ('ssf', '癌症部位特定因子 (SSF1-10)', tuple(f'SSF{i}' for i in range(1, 11))),
    ('radiotherapy', '放射治療', (
        'R', 'RTAR', 'RMOD', 'EBRT', 'HTAR', 'HDOSE', 'HNO', 'LTAR', 'LDOSE',
        'LNO', 'SEQRS', 'SEQLS')),
    ('systemic', '全身性治療', (
        'PREC', 'C', 'PREH', 'H', 'PREI', 'I', 'PREB', 'B', 'PRETAR', 'TAR',
        'OTH', 'PREP', 'WATCHWAITING')),
    ('followup', '追蹤與結果', (
        'VSTA', 'CSTA', 'LCD', 'REDATE', 'RETYPE95', 'DIECAUSE', 'VSTA6',
        'LCD6', 'SURVY6', 'REDATE6', 'RETYPE6', 'DIECAUSE6')),
)

# Fields whose value is a number or a date, not a coded concept.
# LNEXAM and LN_POSITI look numeric but are NOT: 95-99 are sentinel codes,
# so 95 means "nodes not surgically removed", not ninety-five nodes. They are
# choice items bound to their code table, like every other coded field.
NUMERIC_FIELDS = frozenset({
    'AGE', 'CSIZE95', 'MARGDIS', 'HDOSE', 'HNO', 'LDOSE', 'LNO',
    'HEIGHT', 'WEIGHT', 'SURVY6', 'DX_YEAR',
})
DATE_FIELDS = frozenset({
    'DXDATE', 'VISTDATE', 'FSDATE', 'LCD', 'REDATE', 'LCD6', 'REDATE6',
})
STRING_FIELDS = frozenset({'PK'})

# Structural (non-SSF) fields whose code table this package owns and verifies.
STRUCTURAL_CODE_TABLES = ('AJCC', 'PRESTYPE', 'STYPE95', 'PRESLNSCO',
                          'SLNSCO95', 'LNEXAM', 'LN_POSITI', 'EBRT')

# EBRT is an ADDITIVE field: the submitted value is the sum of the technique
# codes used across all phases, so the ValueSet enumerates the components and
# the Questionnaire item repeats instead of offering the 128 possible sums.
REPEATING_FIELDS = frozenset({'EBRT'})


# ─────────────────────────────────────────────────────────────────────────────
# Concept extraction from the verified code tables
# ─────────────────────────────────────────────────────────────────────────────

def _ssf_concepts(cancer_group: str, ssf_key: str) -> List[dict]:
    """One FHIR concept per legal code: zh display + en designation."""
    width, codes, ref = CODE_RANGES[cancer_group][ssf_key]
    field = get_ssf_profile(cancer_group).fields[ssf_key]
    numeric = sorted((c for c in codes if c.isdigit()), key=int)
    ordered = numeric + sorted(c for c in codes if not c.isdigit())
    labels = field.decoder(pd.Series(ordered, dtype=object))
    concepts = []
    for code, english in zip(ordered, labels):
        chinese = zh_definition(cancer_group, ssf_key, code)
        concepts.append({
            'code': code,
            'display': chinese or english,
            'definition': f'{chinese} / {english}'.strip(' /'),
            'designation': [{
                'language': 'en',
                'value': str(english),
            }],
        })
    return concepts


# Fields whose concepts come from a decoder run over the official 編碼範圍
# rather than from a plain dict.
_COUNT_FIELD_DECODERS = {
    'LNEXAM':    'decode_lnexam',
    'LN_POSITI': 'decode_lnpositive',
}


def _structural_concepts(field: str) -> List[dict]:
    """Concepts for a structural Longform field this package can decode.

    Only codes inside the official 編碼範圍 are emitted. The decoder also
    understands pre-2025 legacy codes so historical files still read, but a
    submission ValueSet must not offer them.
    """
    from tcr_decoder import decoders
    from tcr_decoder.core import AJCC_MAP, LNSCO_MAP, PRESTYPE_MAP, STYPE95_MAP

    if field in _COUNT_FIELD_DECODERS:
        _width, codes, _ref = LONGFORM[field]
        ordered = sorted(codes, key=lambda c: int(c))
        decode = getattr(decoders, _COUNT_FIELD_DECODERS[field])
        labels = decode(pd.Series(ordered, dtype=object))
        return [{'code': c, 'display': str(l), 'definition': str(l)}
                for c, l in zip(ordered, labels)]

    if field == 'EBRT':
        from tcr_decoder.decoders import EBRT_COMPONENTS
        concepts = [{'code': str(code), 'display': label,
                     'definition': f'{label}（加總碼，可複選）'}
                    for code, label in sorted(EBRT_COMPONENTS.items())]
        concepts += [
            {'code': '0', 'display': 'No EBRT', 'definition': '未執行體外放射治療'},
            {'code': '-1', 'display': 'EBRT NOS', 'definition': '有體外放射治療但技術不明'},
            {'code': '999', 'display': 'Unknown', 'definition': '不詳'},
        ]
        return concepts

    table = {'AJCC': AJCC_MAP, 'PRESTYPE': PRESTYPE_MAP, 'STYPE95': STYPE95_MAP,
             'PRESLNSCO': LNSCO_MAP, 'SLNSCO95': LNSCO_MAP}[field]

    # Surgery of primary site draws on Appendix B, which is per-site; the two
    # node-surgery fields share one 1-character table. Where the engine has
    # transcribed the official range, restrict the CodeSystem to it so the
    # legacy 1- and 2-character codes stay decode-only.
    legal = None
    if field in ('PRESTYPE', 'STYPE95'):
        legal = SURGERY_CODES.get('breast', (0, None, ''))[1]
    elif field in ('PRESLNSCO', 'SLNSCO95'):
        legal = LONGFORM.get(field, (0, None, ''))[1]
    if legal:
        table = {code: label for code, label in table.items() if code in legal}

    return [{'code': str(code), 'display': str(label), 'definition': str(label)}
            for code, label in sorted(table.items())]


def field_has_code_table(cancer_group: str, field: str) -> bool:
    """True if this package can enumerate and verify the field's codes."""
    if field.startswith('SSF') and field[3:].isdigit():
        return field in CODE_RANGES.get(cancer_group, {})
    return field in STRUCTURAL_CODE_TABLES


def legal_code_set(cancer_group: str, field: str) -> frozenset:
    """Every code this field's CodeSystem contains."""
    return frozenset(c['code'] for c in _concepts_for(cancer_group, field))


def normalise_code(cancer_group: str, field: str, value: str):
    """Return (code, is_legal) for a raw value from a registry file.

    A file that lost its leading zeros (Excel turning '00' into 0) still has
    to produce a legal code here, so the value is retried zero-padded to the
    widths this field uses. A value that matches nothing is returned as-is
    and flagged, never silently coerced into a neighbouring code.
    """
    codes = legal_code_set(cancer_group, field)
    raw = str(value).strip()
    for candidate in (raw, raw.zfill(2), raw.zfill(3)):
        if candidate in codes:
            return candidate, True
    return raw, False


def _concepts_for(cancer_group: str, field: str) -> List[dict]:
    if field.startswith('SSF') and field[3:].isdigit():
        return _ssf_concepts(cancer_group, field)
    return _structural_concepts(field)


# ─────────────────────────────────────────────────────────────────────────────
# Resource builders
# ─────────────────────────────────────────────────────────────────────────────

def _slug(cancer_group: str, field: str) -> str:
    return f'tcr-{cancer_group}-{field.lower().replace("_", "-")}'


def build_code_system(cancer_group: str, field: str, base_url: str) -> dict:
    concepts = _concepts_for(cancer_group, field)
    ident = _slug(cancer_group, field)
    zh_label = dict((f, z) for f, z, _s, _d in FIELD_MAP).get(field, field)
    ref = (CODE_RANGES[cancer_group][field][2]
           if field.startswith('SSF') and field in CODE_RANGES.get(cancer_group, {})
           else LONGFORM[field][2] if field in LONGFORM
           else '長表編碼手冊')
    return {
        'resourceType': 'CodeSystem',
        'id': ident,
        'url': f'{base_url}/CodeSystem/{ident}',
        'version': FHIR_VERSION,
        'name': f'TCR{cancer_group.title().replace("_", "")}{field}CodeSystem',
        'title': f'台灣癌症登記 {zh_label}（{field}）',
        'status': 'draft',
        'experimental': True,
        'publisher': 'TCR decoding project',
        'description': (f'Taiwan Cancer Registry code table for {field} '
                        f'({zh_label}). 碼冊出處：{ref}. Generated from '
                        f'tcr_decoder; every code round-trips through '
                        f'decode/encode (tests/test_codebook_conformance.py).'),
        'caseSensitive': True,
        'content': 'complete',
        'count': len(concepts),
        'concept': concepts,
    }


def build_value_set(cancer_group: str, field: str, base_url: str) -> dict:
    ident = _slug(cancer_group, field)
    zh_label = dict((f, z) for f, z, _s, _d in FIELD_MAP).get(field, field)
    return {
        'resourceType': 'ValueSet',
        'id': f'{ident}-vs',
        'url': f'{base_url}/ValueSet/{ident}-vs',
        'version': FHIR_VERSION,
        'name': f'TCR{cancer_group.title().replace("_", "")}{field}ValueSet',
        'title': f'台灣癌症登記 {zh_label}（{field}）值集',
        'status': 'draft',
        'experimental': True,
        'compose': {'include': [{'system': f'{base_url}/CodeSystem/{ident}'}]},
    }


def build_concept_map_skeleton(cancer_group: str, field: str,
                               base_url: str) -> dict:
    """TCR code -> standard terminology, with every target left unmapped.

    The element list is complete so a terminologist can see exactly what needs
    a target; filling them in with guesses would put invented LOINC/SNOMED
    codes into a submission pipeline.
    """
    ident = _slug(cancer_group, field)
    concepts = _concepts_for(cancer_group, field)
    return {
        'resourceType': 'ConceptMap',
        'id': f'{ident}-to-standard',
        'url': f'{base_url}/ConceptMap/{ident}-to-standard',
        'version': FHIR_VERSION,
        'name': f'TCR{field}ToStandardTerminology',
        'status': 'draft',
        'experimental': True,
        'description': (
            'SKELETON ONLY: every element is listed with an "unmatched" '
            'target so the mapping work is visible. No LOINC/SNOMED target '
            'has been guessed. Fill in `target` after terminology review.'),
        'sourceCanonical': f'{base_url}/ValueSet/{ident}-vs',
        'group': [{
            'source': f'{base_url}/CodeSystem/{ident}',
            'element': [{
                'code': c['code'],
                'display': c['display'],
                'target': [{'equivalence': 'unmatched',
                            'comment': 'TODO: terminology review'}],
            } for c in concepts],
        }],
    }


def build_questionnaire(cancer_group: str, base_url: str) -> dict:
    """The Longform submission as a structured form, grouped by section."""
    zh = dict((f, z) for f, z, _s, _d in FIELD_MAP)
    source = dict((f, s) for f, _z, s, _d in FIELD_MAP)
    doc = dict((f, d) for f, _z, _s, d in FIELD_MAP)

    items = []
    for section_id, section_label, fields in SECTIONS:
        children = []
        for field in fields:
            item = {
                'linkId': field,
                'text': f'[{field}] {zh.get(field, field)}',
                'type': 'string',
            }
            if field in NUMERIC_FIELDS:
                item['type'] = 'decimal' if field in ('SURVY6',) else 'integer'
            elif field in DATE_FIELDS:
                item['type'] = 'date'
            elif field in STRING_FIELDS:
                item['type'] = 'string'
            elif field_has_code_table(cancer_group, field):
                item['type'] = 'choice'
                item['answerValueSet'] = (
                    f'{base_url}/ValueSet/{_slug(cancer_group, field)}-vs')
                if field in REPEATING_FIELDS:
                    item['repeats'] = True
            else:
                # No verified code table yet: keep the item, flag the gap.
                item['extension'] = [{
                    'url': f'{base_url}/StructureDefinition/tcr-codetable-pending',
                    'valueBoolean': True,
                }]
            item.setdefault('extension', []).extend([
                {'url': f'{base_url}/StructureDefinition/tcr-source-hint',
                 'valueString': source.get(field, '')},
                {'url': f'{base_url}/StructureDefinition/tcr-source-document',
                 'valueString': doc.get(field, '')},
            ])
            children.append(item)
        items.append({
            'linkId': section_id,
            'text': section_label,
            'type': 'group',
            'item': children,
        })

    return {
        'resourceType': 'Questionnaire',
        'id': f'tcr-{cancer_group}-longform',
        'url': f'{base_url}/Questionnaire/tcr-{cancer_group}-longform',
        'version': FHIR_VERSION,
        'name': f'TCR{cancer_group.title().replace("_", "")}LongformQuestionnaire',
        'title': f'台灣癌症登記長表申報（{cancer_group}）',
        'status': 'draft',
        'experimental': True,
        'subjectType': ['Patient'],
        'description': (
            'One item per Longform field. Items bound to an answerValueSet '
            'have a code table verified against the printed manual; items '
            'carrying tcr-codetable-pending do not have one in this package '
            'yet and must be reviewed manually.'),
        'item': items,
    }


def build_task_profile(base_url: str) -> dict:
    """Profile for the abstraction job itself."""
    return {
        'resourceType': 'StructureDefinition',
        'id': 'tcr-registry-abstraction-task',
        'url': f'{base_url}/StructureDefinition/tcr-registry-abstraction-task',
        'version': FHIR_VERSION,
        'name': 'TCRRegistryAbstractionTask',
        'title': '癌症登記摘錄任務 (TCR Registry Abstraction Task)',
        'status': 'draft',
        'experimental': True,
        'fhirVersion': FHIR_VERSION,
        'kind': 'resource',
        'abstract': False,
        'type': 'Task',
        'baseDefinition': 'http://hl7.org/fhir/StructureDefinition/Task',
        'derivation': 'constraint',
        'description': (
            'Abstracting the cancer-registry fields for one primary tumour: '
            'inputs are the source documents (pathology report, clinic notes, '
            'chemotherapy records), output is the completed '
            'QuestionnaireResponse and the generated Longform row.'),
        'differential': {'element': [
            {'id': 'Task', 'path': 'Task',
             'short': 'Cancer-registry abstraction for one primary tumour'},
            {'id': 'Task.focus', 'path': 'Task.focus', 'min': 1,
             'type': [{'code': 'Reference',
                       'targetProfile': [
                           'http://hl7.org/fhir/StructureDefinition/Condition']}],
             'short': 'The primary cancer being reported'},
            {'id': 'Task.for', 'path': 'Task.for', 'min': 1,
             'short': 'The patient'},
            {'id': 'Task.input', 'path': 'Task.input', 'min': 1,
             'short': 'Source documents to abstract from '
                      '(DocumentReference / DiagnosticReport)'},
            {'id': 'Task.output', 'path': 'Task.output', 'min': 0,
             'short': 'QuestionnaireResponse with the abstracted fields, and '
                      'the generated registry row'},
        ]},
    }


def build_task_example(cancer_group: str, base_url: str) -> dict:
    return {
        'resourceType': 'Task',
        'id': f'tcr-{cancer_group}-abstraction-example',
        'meta': {'profile': [
            f'{base_url}/StructureDefinition/tcr-registry-abstraction-task']},
        'status': 'requested',
        'intent': 'order',
        'description': f'癌症登記長表摘錄（{cancer_group}）',
        'focus': {'reference': 'Condition/example-breast-cancer'},
        'for': {'reference': 'Patient/example'},
        'input': [
            {'type': {'text': '病理報告'},
             'valueReference': {'reference': 'DiagnosticReport/example-pathology'}},
            {'type': {'text': '門診紀錄'},
             'valueReference': {'reference': 'DocumentReference/example-opd-note'}},
            {'type': {'text': '化療紀錄'},
             'valueReference': {'reference': 'DocumentReference/example-chemo'}},
        ],
        'output': [
            {'type': {'text': 'QuestionnaireResponse'},
             'valueReference': {
                 'reference': f'QuestionnaireResponse/tcr-{cancer_group}-example'}},
        ],
    }


def build_questionnaire_response(cancer_group: str, base_url: str,
                                 raw_row: Optional[pd.Series] = None) -> dict:
    """A filled form for one (synthetic) case, for use as an IG example."""
    if raw_row is None:
        from tcr_decoder.synth import SyntheticTCRGenerator
        raw_row = SyntheticTCRGenerator(
            cancer_group=cancer_group, n=1, seed=20260814).generate().iloc[0]

    items = []
    for section_id, section_label, fields in SECTIONS:
        children = []
        for field in fields:
            value = raw_row.get(f'{field}_raw', '')
            if value is None or str(value).strip() in ('', 'nan'):
                continue
            value = str(value).strip()
            if field in DATE_FIELDS:
                answer = {'valueString': value}      # TCR allows day=99
            elif field in NUMERIC_FIELDS:
                try:
                    answer = {'valueInteger': int(float(value))}
                except ValueError:
                    answer = {'valueString': value}
            elif field_has_code_table(cancer_group, field):
                code, legal = normalise_code(cancer_group, field, value)
                if legal:
                    answer = {'valueCoding': {
                        'system': f'{base_url}/CodeSystem/{_slug(cancer_group, field)}',
                        'code': code,
                    }}
                else:
                    # Not a code this field defines. Emitting a Coding here
                    # would cite a concept that does not exist, so the value
                    # is carried as text and marked for review instead.
                    answer = {
                        'valueString': code,
                        'extension': [{
                            'url': f'{base_url}/StructureDefinition/tcr-illegal-code',
                            'valueString': (f'{code!r} is not in the 編碼範圍 for '
                                            f'{field}; needs review'),
                        }],
                    }
            else:
                answer = {'valueString': value}
            children.append({'linkId': field, 'answer': [answer]})
        if children:
            items.append({'linkId': section_id, 'item': children})

    return {
        'resourceType': 'QuestionnaireResponse',
        'id': f'tcr-{cancer_group}-example',
        'questionnaire': f'{base_url}/Questionnaire/tcr-{cancer_group}-longform',
        'status': 'in-progress',
        'subject': {'reference': 'Patient/example'},
        'item': items,
        'meta': {'tag': [{'code': 'synthetic',
                          'display': 'Synthetic data — not a real patient'}]},
    }


def build_extension_definitions(base_url: str) -> List[dict]:
    """StructureDefinitions for the four extensions the Questionnaire uses.

    An IG that references an undefined extension fails validation, so these
    are generated alongside the artefacts that use them.
    """
    specs = [
        ('tcr-codetable-pending', 'TCRCodeTablePending',
         '此欄位的官方碼表尚未轉錄 (TCR code table not yet transcribed)',
         'boolean',
         'True when this package has no verified code table for the field, so '
         'the item is a free-text placeholder rather than a coded answer.'),
        ('tcr-source-hint', 'TCRSourceHint',
         '來源資源路徑提示 (FHIR source hint)', 'string',
         'Where the value is expected to come from in a FHIR-native EMR, '
         'e.g. "Observation (ER)". Guidance for the extraction layer.'),
        ('tcr-source-document', 'TCRSourceDocument',
         '來源文件類型 (source document type)', 'string',
         'Which clinical document the fact is abstracted from, e.g. 病理報告.'),
        ('tcr-illegal-code', 'TCRIllegalCode',
         '不在官方編碼範圍內的值 (value outside the 編碼範圍)', 'string',
         'Carried on an answer whose raw value is not a legal code for the '
         'field, so the discrepancy is visible instead of being coerced.'),
    ]
    out = []
    for ident, name, title, value_type, description in specs:
        out.append({
            'resourceType': 'StructureDefinition',
            'id': ident,
            'url': f'{base_url}/StructureDefinition/{ident}',
            'version': FHIR_VERSION,
            'name': name,
            'title': title,
            'status': 'draft',
            'experimental': True,
            'fhirVersion': FHIR_VERSION,
            'kind': 'complex-type',
            'abstract': False,
            'context': [{'type': 'element', 'expression': 'Questionnaire.item'},
                        {'type': 'element',
                         'expression': 'QuestionnaireResponse.item.answer'}],
            'type': 'Extension',
            'baseDefinition':
                'http://hl7.org/fhir/StructureDefinition/Extension',
            'derivation': 'constraint',
            'description': description,
            'differential': {'element': [
                {'id': 'Extension', 'path': 'Extension', 'short': title},
                {'id': 'Extension.url', 'path': 'Extension.url',
                 'fixedUri': f'{base_url}/StructureDefinition/{ident}'},
                {'id': 'Extension.value[x]', 'path': 'Extension.value[x]',
                 'min': 1, 'type': [{'code': value_type}]},
            ]},
        })
    return out


def build_implementation_guide(cancer_group: str, base_url: str,
                               resources: List[dict]) -> dict:
    return {
        'resourceType': 'ImplementationGuide',
        'id': f'tcr-{cancer_group}-registry',
        'url': f'{base_url}/ImplementationGuide/tcr-{cancer_group}-registry',
        'version': FHIR_VERSION,
        'name': f'TCR{cancer_group.title().replace("_", "")}RegistryReporting',
        'title': f'台灣癌症登記申報（{cancer_group}）',
        'status': 'draft',
        'experimental': True,
        'packageId': f'tw.tcr.{cancer_group}',
        'license': 'CC0-1.0',
        'fhirVersion': [FHIR_VERSION],
        'description': (
            'Cancer-registry reporting as a task within a breast-cancer IG. '
            'Terminology is generated from verified TCR code tables; the '
            'ConceptMaps to standard terminology are intentionally unmapped.'),
        'definition': {'resource': [
            {'reference': {'reference': f"{r['resourceType']}/{r['id']}"},
             'name': r.get('title', r['id'])}
            for r in resources
        ]},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────────

def _task_page_source():
    """The narrative page for this module, if it is checked in next to it.

    Looked up by name rather than a hard-coded path, so moving this module
    between repositories does not silently drop the page.
    """
    root = Path(__file__).resolve().parents[1]
    for candidate in (root / 'docs' / 'tcr-registry-task.md',
                      root / 'docs' / 'fhir_ig_breast_registry.md'):
        if candidate.exists():
            return candidate.read_text(encoding='utf-8')
    return None

def build_ig(output_dir: Union[str, Path], cancer_group: str = 'breast',
             base_url: str = DEFAULT_BASE_URL,
             include_concept_maps: bool = True) -> Dict[str, object]:
    """Write every artefact to `output_dir` and return a summary."""
    out = Path(output_dir)
    for sub in ('CodeSystem', 'ValueSet', 'ConceptMap', 'Questionnaire',
                'StructureDefinition', 'Task', 'QuestionnaireResponse',
                'ImplementationGuide'):
        (out / sub).mkdir(parents=True, exist_ok=True)

    coded_fields = [f for f, _z, _s, _d in FIELD_MAP
                    if field_has_code_table(cancer_group, f)]
    pending_fields = [f for f, _z, _s, _d in FIELD_MAP
                      if not field_has_code_table(cancer_group, f)
                      and f not in NUMERIC_FIELDS | DATE_FIELDS | STRING_FIELDS]

    written: List[dict] = []

    def _write(resource: dict):
        path = out / resource['resourceType'] / f"{resource['id']}.json"
        path.write_text(json.dumps(resource, ensure_ascii=False, indent=2),
                        encoding='utf-8')
        written.append(resource)

    total_concepts = 0
    for field in coded_fields:
        cs = build_code_system(cancer_group, field, base_url)
        total_concepts += cs['count']
        _write(cs)
        _write(build_value_set(cancer_group, field, base_url))
        if include_concept_maps:
            _write(build_concept_map_skeleton(cancer_group, field, base_url))

    for extension in build_extension_definitions(base_url):
        _write(extension)
    _write(build_questionnaire(cancer_group, base_url))
    _write(build_task_profile(base_url))
    _write(build_task_example(cancer_group, base_url))
    _write(build_questionnaire_response(cancer_group, base_url))
    _write(build_implementation_guide(cancer_group, base_url, written[:]))

    return {
        '癌別': cancer_group,
        '輸出目錄': str(out),
        'canonical base': base_url,
        '申報欄位總數': len(FIELD_MAP),
        '已有驗證碼表的欄位': len(coded_fields),
        '純數值／日期欄位': len(NUMERIC_FIELDS | DATE_FIELDS | STRING_FIELDS),
        '待補碼表的欄位': len(pending_fields),
        '待補欄位清單': ', '.join(pending_fields),
        'CodeSystem 概念總數': total_concepts,
        '產生的資源數': len(written),
    }

# ─────────────────────────────────────────────────────────────────────────────
# IG repository scaffold (SUSHI + HL7 IG Publisher layout)
# ─────────────────────────────────────────────────────────────────────────────

_SUSHI_CONFIG = """# SUSHI configuration -- https://fshschool.org/docs/sushi/configuration/
id: {package_id}
canonical: {canonical}
name: {ig_name}
title: "{ig_title}"
description: >-
  台灣乳癌 FHIR Implementation Guide。癌症登記（Taiwan Cancer Registry）申報是
  本 IG 底下的一個 task：從病理報告、門診紀錄、手術／放療／化療紀錄摘錄出
  申報所需欄位，經確定性規則轉成官方代碼後產生申報檔。
status: draft
license: CC0-1.0
version: 0.1.0
fhirVersion: 4.0.1
copyrightYear: 2026+
releaseLabel: ci-build
publisher:
  name: {publisher}

# TW Core 之類的相依套件請自行確認 package id 與版本後再打開，
# 寫錯的相依會讓 IG Publisher 直接失敗：
# dependencies:
#   tw.gov.mohw.twcore: <version>

parameters:
  show-inherited-invariants: false

pages:
  index.md:
    title: 首頁
  cancer-registry-task.md:
    title: 癌症登記申報 Task
  terminology.md:
    title: 代碼系統與值集

menu:
  首頁: index.html
  癌症登記申報 Task: cancer-registry-task.html
  代碼系統: terminology.html
  Artifacts: artifacts.html
"""

_IG_INI = """[IG]
ig = fsh-generated/resources/ImplementationGuide-{package_id}.json
template = fhir.base.template#current
"""

_EXTENSIONS_FSH = """// 癌症登記摘錄用的四個擴充。
// 這些檔案由 tcr_decoder.fhir 產生的 Questionnaire 會引用到，
// 未定義的擴充會讓 IG Publisher 驗證失敗。

Extension: TCRCodeTablePending
Id: tcr-codetable-pending
Title: "此欄位的官方碼表尚未轉錄"
Description: "True 代表本工具尚未轉錄該癌登欄位的官方編碼範圍，Questionnaire 以自由文字暫代，需人工複核。"
* value[x] only boolean
* valueBoolean 1..1
* ^context[0].type = #element
* ^context[0].expression = "Questionnaire.item"

Extension: TCRSourceHint
Id: tcr-source-hint
Title: "來源資源路徑提示"
Description: "在 FHIR 原生 EMR 中，這個欄位的值預期來自哪個資源／元素，供抽取層參考。"
* value[x] only string
* valueString 1..1
* ^context[0].type = #element
* ^context[0].expression = "Questionnaire.item"

Extension: TCRSourceDocument
Id: tcr-source-document
Title: "來源文件類型"
Description: "這個欄位要從哪一類臨床文件摘錄，例如：病理報告、門診紀錄、化療紀錄。"
* value[x] only string
* valueString 1..1
* ^context[0].type = #element
* ^context[0].expression = "Questionnaire.item"

Extension: TCRIllegalCode
Id: tcr-illegal-code
Title: "不在官方編碼範圍內的值"
Description: "標記某個答案的原始值不是該欄位的合法碼；保留原值並標記，不擅自改成鄰近的碼。"
* value[x] only string
* valueString 1..1
* ^context[0].type = #element
* ^context[0].expression = "QuestionnaireResponse.item.answer"
"""

_TASK_FSH = """// 癌症登記摘錄任務：本 IG 的其中一個 task。

Profile: TCRRegistryAbstractionTask
Parent: Task
Id: tcr-registry-abstraction-task
Title: "癌症登記摘錄任務"
Description: "為某一顆原發乳癌完成癌症登記長表摘錄：input 是來源文件，output 是填好的 QuestionnaireResponse 與產生的申報列。"
* focus 1..1
* focus only Reference(Condition)
* focus ^short = "被申報的原發癌症"
// R4 Task 沒有 subject 元素，病人掛在 Task.for
* for 1..1
* for only Reference(Patient)
* input 1..*
* input ^short = "來源文件：病理報告、門診／手術／放療／化療紀錄"
* output 0..*
* output ^short = "填好的 QuestionnaireResponse 與產生的癌登申報列"
"""

_INDEX_MD = """# {ig_title}

本 IG 描述台灣乳癌照護資料的 FHIR 表達方式。**癌症登記申報是其中一個 task**：
見「[癌症登記申報 Task](cancer-registry-task.html)」。

## 這個 IG 目前包含什麼

| 模組 | 內容 | 狀態 |
|---|---|---|
| 癌症登記申報 | Task profile、長表 99 欄位 Questionnaire、{n_cs} 個 CodeSystem（{n_concepts} 個概念）、ValueSet、ConceptMap 骨架 | 草稿，代碼已逐碼驗證 |
| 乳癌臨床資料 profile | （待補）Condition / Observation / Procedure / MedicationAdministration | 未開始 |

## 代碼從哪裡來

癌登代碼系統不是手打的，是從《癌症部位特定因子編碼手冊》與《長表編碼手冊》
轉錄後、由程式產生的：每一個碼都通過「解碼→編碼→逐字還原」驗證，
`display` 用碼冊中文原文，並附英文 designation。

重新產生：

```bash
python -m tcr_decoder --build-fhir <輸出目錄> --cancer breast \\
    --fhir-base-url {canonical}
```
"""

_TERMINOLOGY_MD = """# 代碼系統與值集

本 IG 的癌登代碼系統由 [tcr_decoder](https://github.com/erichuang777777/TCRD_decoding)
從官方碼冊產生，共 **{n_cs} 個 CodeSystem、{n_concepts} 個概念**。

## 產生方式與保證

每個 CodeSystem 的概念都同時通過四項檢查（`tests/test_codebook_conformance.py`）：

1. 每個官方合法碼都能解碼成臨床意義
2. 同一欄位內沒有兩個碼共用同一句意義（解碼是單射）
3. `encode(decode(code)) == code` 逐字相等
4. 編碼結果一定是合法碼且欄位寬度正確

## 欄位對照

| 欄位 | 中文 | 概念數 |
|---|---|---|
{terminology_rows}

## ConceptMap 為什麼都是 unmatched

`ConceptMap` 只提供骨架：每個癌登碼都列出來，但 `target` 一律標成 `unmatched`。
把 TCR 碼硬對到 LOINC/SNOMED 需要術語專家判斷，猜一個對應碼進到申報管線，
比留下明顯的缺口更糟。
"""

_IGNORE_WARNINGS = """== Suppressed Messages ==
# 產生的癌登 CodeSystem 沒有對應到標準術語，這是刻意的（見 terminology.html）
"""

_REPO_README = """# {ig_title}

台灣乳癌 FHIR Implementation Guide（草稿）。

## 建置

```bash
npm install -g fsh-sushi          # 產生 fsh-generated/
sushi .
./_genonce.sh                     # 或 _genonce.bat：跑 HL7 IG Publisher
```

## 癌症登記模組怎麼更新

`input/resources/` 底下的 CodeSystem / ValueSet / ConceptMap / Questionnaire
都是**產生的**，不要手改。
碼冊改版時重新產生：

```bash
python -m tcr_decoder --build-fhir . --cancer breast \\
    --fhir-base-url {canonical} --ig-layout
```

（產生器與碼表驗證：<https://github.com/erichuang777777/TCRD_decoding>）
"""


def build_ig_scaffold(repo_dir: Union[str, Path],
                      cancer_group: str = 'breast',
                      canonical: str = 'https://example.org/fhir/breast-ig',
                      package_id: str = 'tw.breast.cancer.ig',
                      ig_name: str = 'TWBreastCancerIG',
                      ig_title: str = '台灣乳癌 FHIR Implementation Guide',
                      publisher: str = 'TW Breast Cancer IG community draft',
                      overwrite_authored: bool = False) -> Dict[str, object]:
    """Write a SUSHI + IG-Publisher repository layout.

    Generated terminology goes to `input/resources/`, which IG Publisher
    copies through untouched; hand-authored conformance (the Task profile and
    the four extensions) goes to `input/fsh/` so it stays editable as FSH.

    `overwrite_authored=False` (default) leaves any existing FSH and page
    content alone, so re-running after the code book changes refreshes only
    the generated artefacts.
    """
    repo = Path(repo_dir)
    fsh_dir = repo / 'input' / 'fsh'
    # IG Publisher only picks up files DIRECTLY under input/resources -- a
    # terminology/ or examples/ sub-folder is silently skipped (SUSHI warns
    # about it), so everything generated lands flat, with the resource type
    # in the filename.
    res_dir = repo / 'input' / 'resources'
    term_dir = q_dir = ex_dir = res_dir
    page_dir = repo / 'input' / 'pagecontent'
    for d in (fsh_dir, res_dir, page_dir, repo / 'input' / 'images'):
        d.mkdir(parents=True, exist_ok=True)

    coded_fields = [f for f, _z, _s, _d in FIELD_MAP
                    if field_has_code_table(cancer_group, f)]
    zh = dict((f, z) for f, _z2, _s, _d in FIELD_MAP for z in [_z2])

    written, concept_total = [], 0
    rows = []
    for field in coded_fields:
        cs = build_code_system(cancer_group, field, canonical)
        vs = build_value_set(cancer_group, field, canonical)
        cm = build_concept_map_skeleton(cancer_group, field, canonical)
        concept_total += cs['count']
        rows.append(f"| {field} | {zh.get(field, '')} | {cs['count']} |")
        for resource in (cs, vs, cm):
            path = term_dir / f"{resource['resourceType']}-{resource['id']}.json"
            path.write_text(json.dumps(resource, ensure_ascii=False, indent=2),
                            encoding='utf-8')
            written.append(path)

    questionnaire = build_questionnaire(cancer_group, canonical)
    (q_dir / f"Questionnaire-{questionnaire['id']}.json").write_text(
        json.dumps(questionnaire, ensure_ascii=False, indent=2), encoding='utf-8')
    written.append(q_dir / f"Questionnaire-{questionnaire['id']}.json")

    for resource in (build_task_example(cancer_group, canonical),
                     build_questionnaire_response(cancer_group, canonical)):
        path = ex_dir / f"{resource['resourceType']}-{resource['id']}.json"
        path.write_text(json.dumps(resource, ensure_ascii=False, indent=2),
                        encoding='utf-8')
        written.append(path)

    # Hand-authored FSH + config: only written if absent (or forced).
    authored = {
        repo / 'sushi-config.yaml': _SUSHI_CONFIG.format(
            package_id=package_id, canonical=canonical, ig_name=ig_name,
            ig_title=ig_title, publisher=publisher),
        repo / 'ig.ini': _IG_INI.format(package_id=package_id),
        fsh_dir / 'extensions.fsh': _EXTENSIONS_FSH,
        fsh_dir / 'task-registry-abstraction.fsh': _TASK_FSH,
        repo / 'input' / 'ignoreWarnings.txt': _IGNORE_WARNINGS,
        repo / 'README.md': _REPO_README.format(ig_title=ig_title,
                                                canonical=canonical),
    }
    for path, content in authored.items():
        if overwrite_authored or not path.exists():
            path.write_text(content, encoding='utf-8')
            written.append(path)

    # Pages are regenerated (they carry the current counts), except any page
    # the author has clearly taken over.
    pages = {
        page_dir / 'index.md': _INDEX_MD.format(
            ig_title=ig_title, n_cs=len(coded_fields), n_concepts=concept_total,
            canonical=canonical),
        page_dir / 'terminology.md': _TERMINOLOGY_MD.format(
            n_cs=len(coded_fields), n_concepts=concept_total,
            terminology_rows='\n'.join(rows)),
    }
    for path, content in pages.items():
        if overwrite_authored or not path.exists():
            path.write_text(content, encoding='utf-8')
            written.append(path)

    task_page = page_dir / 'cancer-registry-task.md'
    if overwrite_authored or not task_page.exists():
        source_doc = _task_page_source()
        if source_doc:
            task_page.write_text(source_doc, encoding='utf-8')
            written.append(task_page)

    pending = [f for f, _z, _s, _d in FIELD_MAP
               if not field_has_code_table(cancer_group, f)
               and f not in NUMERIC_FIELDS | DATE_FIELDS | STRING_FIELDS]
    return {
        'repo': str(repo),
        'canonical': canonical,
        'package_id': package_id,
        'CodeSystem 數': len(coded_fields),
        '概念總數': concept_total,
        '待補碼表欄位數': len(pending),
        '寫出的檔案數': len(written),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bridge to the TW-Breast-Cancer-FHIR-IG repository (QBC Review Workbench)
#
# That repo already carries a breast-cancer IG and a review workbench driven by
# a machine-readable field spec (`qbc_workbench/data/qbc_fields.json`, 115 QBC
# fields). Cancer-registry reporting is a SECOND submission target for the same
# clinical facts, so it plugs in as another module rather than a parallel
# project: the same spec schema, the same FSH conventions, one more Task.
# ─────────────────────────────────────────────────────────────────────────────

# QBC's `data_type` vocabulary: string / code / date / integer / decimal.
_SPEC_DATE_LENGTH = 8          # YYYYMMDD, as QBC dates are stored
_SPEC_DEFAULT_LENGTH = 3       # every SSF field is 3 characters


def _spec_data_type(cancer_group: str, field: str) -> str:
    if field in DATE_FIELDS:
        return 'date'
    if field in NUMERIC_FIELDS:
        return 'integer'
    if field_has_code_table(cancer_group, field):
        return 'code'
    return 'string'


def _spec_max_length(cancer_group: str, field: str) -> int:
    if field in DATE_FIELDS:
        return _SPEC_DATE_LENGTH
    from tcr_decoder.code_ranges import field_width
    if field.startswith('SSF'):
        return field_width(cancer_group, field) or _SPEC_DEFAULT_LENGTH
    if field in LONGFORM:
        return LONGFORM[field][0]
    if field_has_code_table(cancer_group, field):
        return max(len(c) for c in legal_code_set(cancer_group, field))
    return 10


def build_field_spec(cancer_group: str = 'breast') -> dict:
    """The Longform fields in the QBC workbench's own spec schema.

    Same shape as `qbc_workbench/data/qbc_fields.json`, so the existing
    validator (`_validate_field`), exporter and review UI can drive a cancer
    registry submission without a second spec format.

    `allowed_values` is the honest part: it is populated ONLY from code
    tables this package verifies end to end, and left empty for the fields
    whose 編碼範圍 has not been transcribed yet -- exactly the same
    convention QBC uses for its free-text fields.
    """
    zh = dict((f, z) for f, z, _s, _d in FIELD_MAP)
    source = dict((f, s) for f, _z, s, _d in FIELD_MAP)
    document = dict((f, d) for f, _z, _s, d in FIELD_MAP)
    section_of = {field: label
                  for _id, label, fields in SECTIONS for field in fields}

    fields = []
    for field, _zh, _src, _doc in FIELD_MAP:
        coded = field_has_code_table(cancer_group, field)
        if coded:
            codes = legal_code_set(cancer_group, field)
            allowed = sorted(codes, key=lambda c: (not c.isdigit(), c))
            entry = CODE_RANGES.get(cancer_group, {}).get(field)
            rule = (entry[2] if entry
                    else LONGFORM[field][2] if field in LONGFORM
                    else '長表編碼手冊')
        else:
            allowed = []
            rule = '碼表尚未轉錄；值域待補（see docs/codebook_conformance_findings.md）'
        width = _spec_max_length(cancer_group, field)
        fields.append({
            'tag': field,
            'label': zh.get(field, field),
            'section': section_of.get(field, ''),
            'data_type': _spec_data_type(cancer_group, field),
            'source_format': f'X({width})',
            'source_rule': rule,
            'allowed_values': allowed,
            'always_required': False,
            'required_marker': '',
            'required_when': [],
            'rule_ids': [],
            'max_length': width,
            'maximum': None,
            'minimum': None,
            'multi_select': field in REPEATING_FIELDS,
            'fhir_source_hint': source.get(field, ''),
            'source_document': document.get(field, ''),
            'code_table_verified': coded,
        })

    verified = sum(1 for f in fields if f['code_table_verified'])
    return {
        'schema_version': 1,
        'status': 'draft',
        'source': ('Taiwan Cancer Registry Longform + Cancer-SSF-Manual '
                   '(民國114年12月修訂). Codes generated from tcr_decoder; '
                   'every allowed_values list round-trips through '
                   'decode/encode (tests/test_codebook_conformance.py).'),
        'cancer_group': cancer_group,
        'notes': [
            '欄位必填性（always_required / required_marker / required_when）'
            '尚未由長表碼冊轉錄，一律留空，不要當成「非必填」使用。',
            f'{verified}/{len(fields)} 個欄位的 allowed_values 已逐碼驗證；'
            '其餘欄位的值域為空集合，代表碼表待補，不代表可自由填寫。',
        ],
        'section_rules': [],
        'program_rules': [],
        'fields': fields,
    }


def build_field_code_system_fsh(cancer_group: str = 'breast',
                                canonical: str = DEFAULT_BASE_URL) -> str:
    """`TCRFieldCodeSystem` in the same FSH style as QBC's `qbc-field`."""
    lines = [
        '// 癌症登記長表欄位代碼。與 QBC 的 qbc-field 同一個用途：',
        '// 保存來源欄位代號，不取代國健署公布之申報規格。',
        '',
        'CodeSystem: TCRFieldCodeSystem',
        'Id: tcr-field',
        'Title: "TCR Longform Field Codes"',
        'Description: "非官方台灣癌症登記長表欄位代碼彙整。"',
        # No explicit ^url: SUSHI derives it from the IG canonical + Id, so
        # the FSH stays portable if the canonical ever changes. (A bare URL
        # here is parsed as an Instance reference and fails.)
        '* ^status = #draft',
        '* ^experimental = true',
        '* ^caseSensitive = true',
        '* ^content = #complete',
    ]
    for field, label, _src, _doc in FIELD_MAP:
        lines.append(f'* #{field} "{label}"')
    return '\n'.join(lines) + '\n'


def build_module_fsh(cancer_group: str = 'breast',
                     canonical: str = DEFAULT_BASE_URL) -> str:
    """Observation + Task profiles for the registry module, QBC-style."""
    return f"""// 癌症登記模組：與 QBC 模組平行的第二個申報目標。
// Observation profile 沿用 QBC 的分層方式（基礎 / raw / 日期 / 整數），
// 讓兩個模組的中介資料形狀一致。

Profile: TCRDataItemObservation
Parent: Observation
Id: tcr-data-item-observation
Title: "TCR Data Item Observation Base"
Description: "癌症登記長表欄位 Observation 的共同基礎限制。"
* ^status = #draft
* ^experimental = true
* status = #final (exactly)
* status MS
* code 1..1
* code from TCRFieldValueSet (required)
* code MS
* subject 1..1
* subject MS
* value[x] 1..1
* value[x] MS

Profile: TCRRawDataItemObservation
Parent: TCRDataItemObservation
Id: tcr-raw-data-item-observation
Title: "TCR Raw Data Item Observation"
Description: "以 valueString 保存原始癌登值的可逆中介層；不表示已完成臨床術語標準化。"
* ^status = #draft
* ^experimental = true
* value[x] only string

Profile: TCRCodedDataItemObservation
Parent: TCRDataItemObservation
Id: tcr-coded-data-item-observation
Title: "TCR Coded Data Item Observation"
Description: "值域已由本 IG 的癌登 CodeSystem 驗證的欄位。"
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept

ValueSet: TCRFieldValueSet
Id: tcr-field-vs
Title: "TCR Longform Field Codes"
Description: "癌症登記長表欄位代碼值集。"
* ^status = #draft
* ^experimental = true
* include codes from system TCRFieldCodeSystem

Profile: TCRRegistryAbstractionTask
Parent: Task
Id: tcr-registry-abstraction-task
Title: "癌症登記摘錄任務"
Description: "為某一顆原發乳癌完成癌症登記長表摘錄：input 是來源文件，output 是填好的 QuestionnaireResponse 與產生的申報列。與 QBC 申報並列為本 IG 的另一個 task。"
* ^status = #draft
* ^experimental = true
* focus 1..1
* focus only Reference(Condition)
* focus ^short = "被申報的原發癌症"
* for 1..1
* for only Reference(Patient)
* input 1..*
* input ^short = "來源文件：病理報告、門診／手術／放療／化療紀錄"
* output 0..*
* output ^short = "填好的 QuestionnaireResponse 與產生的癌登申報列"
"""


def export_to_breast_ig(repo_dir: Union[str, Path],
                        cancer_group: str = 'breast',
                        canonical: str = DEFAULT_BASE_URL,
                        ig_subdir: str = 'ig',
                        spec_dir: str = 'tcr_workbench/data') -> Dict[str, object]:
    """Write the registry module into an existing TW-Breast-Cancer-FHIR-IG clone.

    Nothing outside the paths listed in the returned summary is touched, and
    no existing file is overwritten unless it is one this exporter owns.
    """
    repo = Path(repo_dir)
    fsh_dir = repo / ig_subdir / 'input' / 'fsh'
    res_dir = repo / ig_subdir / 'input' / 'resources'
    page_dir = repo / ig_subdir / 'input' / 'pagecontent'
    data_dir = repo / spec_dir
    for d in (fsh_dir, res_dir, page_dir, data_dir):
        d.mkdir(parents=True, exist_ok=True)

    written = []

    def _write_text(path: Path, text: str):
        path.write_text(text, encoding='utf-8')
        written.append(str(path.relative_to(repo)))

    def _write_json(path: Path, data: dict):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding='utf-8')
        written.append(str(path.relative_to(repo)))

    # 1. machine-readable field spec, in the workbench's own schema
    spec = build_field_spec(cancer_group)
    _write_json(data_dir / 'tcr_fields.json', spec)

    # 2. FSH: field CodeSystem + module profiles
    _write_text(fsh_dir / 'tcr-terminology.fsh',
                build_field_code_system_fsh(cancer_group, canonical))
    _write_text(fsh_dir / 'tcr-profiles.fsh',
                build_module_fsh(cancer_group, canonical))

    # 3. generated code tables, questionnaire and examples
    concept_total = 0
    for field, _z, _s, _d in FIELD_MAP:
        if not field_has_code_table(cancer_group, field):
            continue
        cs = build_code_system(cancer_group, field, canonical)
        concept_total += cs['count']
        _write_json(res_dir / f"CodeSystem-{cs['id']}.json", cs)
        vs = build_value_set(cancer_group, field, canonical)
        _write_json(res_dir / f"ValueSet-{vs['id']}.json", vs)
        cm = build_concept_map_skeleton(cancer_group, field, canonical)
        _write_json(res_dir / f"ConceptMap-{cm['id']}.json", cm)

    for extension in build_extension_definitions(canonical):
        _write_json(res_dir / f"StructureDefinition-{extension['id']}.json",
                    extension)
    questionnaire = build_questionnaire(cancer_group, canonical)
    _write_json(res_dir / f"Questionnaire-{questionnaire['id']}.json",
                questionnaire)
    for example in (build_task_example(cancer_group, canonical),
                    build_questionnaire_response(cancer_group, canonical)):
        _write_json(res_dir / f"{example['resourceType']}-{example['id']}.json",
                    example)

    # 4. page content
    doc = _task_page_source()
    if doc:
        _write_text(page_dir / 'tcr-code-tables.md', doc)

    verified = sum(1 for f in spec['fields'] if f['code_table_verified'])
    return {
        'repo': str(repo),
        'canonical': canonical,
        '寫出的檔案': written,
        '欄位規格': f'{spec_dir}/tcr_fields.json（{len(spec["fields"])} 欄，'
                    f'{verified} 欄值域已驗證）',
        'CodeSystem 概念數': concept_total,
        '需手動加入 sushi-config.yaml 的頁面': 'tcr-registry-task.md',
    }
