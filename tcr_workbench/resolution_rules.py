# -*- coding: utf-8 -*-
"""Breast SSF1-SSF10: the code book's 摘錄原則, as data.

Every rule below is transcribed from 《癌症部位特定因子編碼手冊》民國114年12月
修訂 (codebook_md/ssf_chunk_007, ssf_chunk_008). The `citation` on each rule
names the page, and the step labels quote the manual's own wording, so a
reviewer can check a decision against the printed text without reading code.

What this file is NOT: a general "merge the sources" function. The rules
genuinely differ per field -- SSF6 takes the highest SCORE across multiple
tumours, SSF1 the highest PROPORTION, SSF9 is an OR across every primary-site
report, and SSF3 says the clinician's overall judgement outranks the pathology
report. Collapsing them into one policy would silently break most of them.
"""

from __future__ import annotations

from typing import List

from tcr_decoder.facts import (
    DOC_ONCOTYPE, DOC_PATHOLOGY, DOC_PRIOR_SUBMISSION, HOSPITAL_EXTERNAL,
    HOSPITAL_REPORTING, Observation, PROCEDURE_RESECTION, ResolutionRule,
    SITE_METASTATIC, SITE_PRIMARY, SPECIMEN_IN_SITU, SPECIMEN_INVASIVE,
    TIMING_POST_NEOADJUVANT, TIMING_PRE, drop_doc_types, flag_for_review,
    force_code_if, prefer_doc_priority, prefer_max, prefer_where,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared steps: these four sentences appear almost verbatim under SSF1, SSF2,
# SSF6 and SSF10, so they are written once.
# ─────────────────────────────────────────────────────────────────────────────

_prefer_invasive = prefer_where(
    lambda o: o.specimen != SPECIMEN_IN_SITU,
    '侵襲癌及原位癌皆有檢測時，優先摘錄侵襲癌之數值',
    '原發部位同時有侵襲癌檢測值，原位癌數值不採用')

_prefer_primary = prefer_where(
    lambda o: o.site != SITE_METASTATIC,
    '同時具有原發部位和轉移部位病理報告時，以原發部位之數值為編碼依據',
    '原發部位已有檢測值，轉移部位數值不採用')

_prefer_reporting_hospital = prefer_where(
    lambda o: o.hospital == HOSPITAL_REPORTING,
    '本欄位資料以申報醫院為主，若申報醫院無資料方可參考外院',
    '申報醫院已有資料，外院資料不採用')

_prefer_largest_specimen = prefer_max(
    lambda o: o.specimen_volume_mm if o.procedure == PROCEDURE_RESECTION else None,
    '單顆腫瘤多份標本時，優先摘錄手術切除原發部位最大腫瘤體積的病理報告',
    '同一顆腫瘤已有更大體積之手術切除標本報告')

_drop_prior_submission = drop_doc_types(
    DOC_PRIOR_SUBMISSION,
    reason='既有申報值僅供對照，證據等級低於原始文件，不得覆蓋病理報告')


def _only_post_neoadjuvant(observations: List[Observation]) -> bool:
    return bool(observations) and all(
        o.timing == TIMING_POST_NEOADJUVANT for o in observations)


def _converted_negative_to_positive(observations: List[Observation]) -> bool:
    """治療前陰性、治療後陽性 -> 888（ER/PR/HER2 各自有此碼）。"""
    def positive(o: Observation) -> bool:
        value = o.value
        if isinstance(value, (int, float)):
            return value >= 1
        return str(value).lower() in ('positive', 'pos', '+', '陽性')

    pre = [o for o in observations if o.timing == TIMING_PRE]
    post = [o for o in observations if o.timing == TIMING_POST_NEOADJUVANT]
    return (bool(pre) and bool(post)
            and all(not positive(o) for o in pre)
            and any(positive(o) for o in post))


def _is_positive(observation: Observation) -> bool:
    value = observation.value
    if isinstance(value, (int, float)):
        return value >= 1
    return str(value).lower() in ('positive', 'pos', '+', '陽性')


def _prefer_positive_then_proportion(observations, resolution):
    """當同時有 ER 反應比例與 Allred score 報告時（碼冊 p.128）：
    優先摘錄其陽性報告結果；若報告結果相同時，則優先摘錄 ER 反應比例。"""
    representations = {o.qualifiers.get('representation') for o in observations}
    if not {'proportion', 'allred'} <= representations:
        return observations
    positive = [o for o in observations if _is_positive(o)]
    if positive and len(positive) != len(observations):
        resolution.trace.append(
            '同時有反應比例與 Allred score 時，優先摘錄陽性報告結果')
        for observation in observations:
            if observation not in positive:
                resolution.rejected.append(
                    (observation, '同時有陽性報告時，陰性報告不優先'))
        return positive
    proportion = [o for o in observations
                  if o.qualifiers.get('representation') == 'proportion']
    if proportion and len(proportion) != len(observations):
        resolution.trace.append('報告結果相同時，優先摘錄 ER 反應比例')
        for observation in observations:
            if observation not in proportion:
                resolution.rejected.append(
                    (observation, '結果相同時 Allred score 不優先於反應比例'))
        return proportion
    return observations


def _receptor_rule(field: str, concept: str, citation: str,
                   post_positive_code: str, post_negative_code: str,
                   converted_code: str = '888') -> ResolutionRule:
    """SSF1 (ER) and SSF2 (PR) share one rule set, p.121-128."""
    def only_post_and(sign: bool):
        def predicate(observations: List[Observation]) -> bool:
            if not _only_post_neoadjuvant(observations):
                return False
            values = [o.value for o in observations]
            numeric = [v for v in values if isinstance(v, (int, float))]
            positive = (any(v >= 1 for v in numeric) if numeric
                        else any(str(v).lower() in ('positive', '陽性')
                                 for v in values))
            return positive is sign
        return predicate

    return ResolutionRule(
        field=field, concept=concept, rule_id=f'{field}-摘錄原則',
        citation=citation,
        steps=[
            _drop_prior_submission,
            force_code_if(
                lambda obs: bool(obs) and all(o.doc_type == DOC_ONCOTYPE
                                              for o in obs),
                '988',
                '個案無病理報告資訊而以 Oncotype 進行檢測'),
            drop_doc_types(
                DOC_ONCOTYPE,
                reason='已有病理報告時，Oncotype 結果不作為本欄位依據'),
            force_code_if(_converted_negative_to_positive, converted_code,
                          '治療前陰性、治療後陽性'),
            force_code_if(only_post_and(True), post_positive_code,
                          '僅有前導性治療後的數值且為陽性'),
            force_code_if(only_post_and(False), post_negative_code,
                          '僅有前導性治療後的數值且為陰性'),
            prefer_where(lambda o: o.timing != TIMING_POST_NEOADJUVANT,
                         '不採用前導性治療後的數據',
                         '有治療前數值時，治療後數值不採用'),
            _prefer_invasive,
            _prefer_primary,
            _prefer_reporting_hospital,
            _prefer_positive_then_proportion,
            _prefer_largest_specimen,
            prefer_max(lambda o: o.value if isinstance(o.value, (int, float)) else None,
                       '多顆腫瘤且皆有陽性百分比時，優先摘錄反應比例較高之檢驗值',
                       '同一個案有更高的反應比例檢驗值'),
        ])


BREAST_RULES = {
    'SSF1': _receptor_rule(
        'SSF1', 'er', 'Cancer-SSF-Manual 乳癌 SSF1，p.121-128',
        post_positive_code='111', post_negative_code='121'),

    'SSF2': _receptor_rule(
        'SSF2', 'pr', 'Cancer-SSF-Manual 乳癌 SSF2，p.125-128',
        post_positive_code='111', post_negative_code='121'),

    # SSF3 前導性療法之療效, p.129-130
    'SSF3': ResolutionRule(
        field='SSF3', concept='neoadjuvant_response',
        rule_id='SSF3-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF3，p.129-130',
        steps=[
            _drop_prior_submission,
            prefer_where(
                lambda o: o.qualifiers.get('pcr') is True
                          or o.doc_type != DOC_PATHOLOGY,
                '除 pCR 外，療效以臨床醫師綜合判斷並記載於病歷者為優先',
                '有手術者不得僅依病理報告描述逕自編碼'),
            flag_for_review(
                lambda obs: any(o.qualifiers.get('conflicting_sites') for o in obs),
                '原發腫瘤與淋巴結療效不一致，碼冊要求詢問臨床主責醫師'),
        ]),

    # SSF4/SSF5 哨兵淋巴結, p.131-133
    'SSF4': ResolutionRule(
        field='SSF4', concept='sentinel_nodes_examined',
        rule_id='SSF4-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF4，p.131',
        steps=[
            _drop_prior_submission,
            force_code_if(
                lambda obs: any(o.timing == TIMING_POST_NEOADJUVANT for o in obs),
                '988',
                '接受過前導性治療後手術才做哨兵淋巴結檢查者，不在此收錄'),
            prefer_doc_priority(),
        ]),

    'SSF5': ResolutionRule(
        field='SSF5', concept='sentinel_nodes_positive',
        rule_id='SSF5-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF5，p.132-133',
        steps=[
            _drop_prior_submission,
            force_code_if(
                lambda obs: any(o.timing == TIMING_POST_NEOADJUVANT for o in obs),
                '988',
                '前導性治療後手術之哨兵淋巴結檢查不在此收錄'),
            force_code_if(
                lambda obs: bool(obs) and all(
                    o.qualifiers.get('itc_only') for o in obs),
                '000',
                '哨兵淋巴結僅有 isolated tumor cell (ITCs) 侵犯'),
            prefer_doc_priority(),
        ]),

    # SSF6 Nottingham/BR, p.134/141
    'SSF6': ResolutionRule(
        field='SSF6', concept='nottingham',
        rule_id='SSF6-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF6，p.134/141',
        steps=[
            _drop_prior_submission,
            prefer_where(lambda o: o.timing != TIMING_POST_NEOADJUVANT,
                         '有前導性治療者採用治療前 BR score，勿採用術後 BR score',
                         '術後 BR score 於有治療前數值時不採用'),
            prefer_where(lambda o: o.qualifiers.get('representation') == 'score',
                         '優先順序 (a) BR score 3-9 (b) BR 分級 low/intermediate/high',
                         '有 BR score 時不採用僅有分級的報告'),
            _prefer_invasive,
            _prefer_primary,
            _prefer_reporting_hospital,
            _prefer_largest_specimen,
            prefer_max(lambda o: o.value if isinstance(o.value, (int, float)) else None,
                       '多顆腫瘤分別皆有 BR 分數時，優先摘錄分數最高之數值；'
                       '僅切片且有多份報告時亦取數值最高者',
                       '同一個案有更高的 BR 分數'),
        ]),

    # SSF7 HER2, p.136-145
    'SSF7': ResolutionRule(
        field='SSF7', concept='her2',
        rule_id='SSF7-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF7，p.136-145',
        steps=[
            _drop_prior_submission,
            _prefer_invasive,
            _prefer_primary,
            prefer_max(
                lambda o: {'fish': 3, 'cish': 2, 'ihc': 1}.get(
                    str(o.qualifiers.get('assay', '')).lower()),
                'ISH 實驗數值優先序：FISH > CISH > IHC',
                '同一個案有更高優先序的檢測方法'),
            prefer_where(
                lambda o: o.qualifiers.get('ihc_score') != '2+'
                          or o.qualifiers.get('ish_done') is not False,
                '注意1：IHC 2+ 不可直接編碼 102，應先確認有無 FISH 或其他檢測',
                'IHC 2+ 且尚未確認有無 ISH，先不採用'),
            prefer_where(
                lambda o: o.qualifiers.get('definitive') is True,
                '注意2：多份 IHC 且無 FISH 時，應優先摘錄陽性或陰性結果',
                '多份 IHC 無 ISH 時，equivocal 結果不優先'),
        ]),

    # SSF8 Paget 氏症, p.142/148
    'SSF8': ResolutionRule(
        field='SSF8', concept='paget',
        rule_id='SSF8-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF8，p.142/148',
        steps=[
            _drop_prior_submission,
            prefer_where(lambda o: o.doc_type == DOC_PATHOLOGY,
                         '摘錄臨床或病理的 Paget 氏症，優先登錄病理學檢查結果',
                         '已有病理檢查結果，臨床描述不優先'),
        ]),

    # SSF9 淋巴管或血管侵犯, p.143/149 -- an OR across reports, not a priority
    'SSF9': ResolutionRule(
        field='SSF9', concept='lvi',
        rule_id='SSF9-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF9，p.143/149',
        steps=[
            _drop_prior_submission,
            _prefer_primary,
            force_code_if(
                lambda obs: any(o.value in (True, 'present', 1, '010')
                                and o.site != SITE_METASTATIC for o in obs),
                '010',
                '不論是否接受前導性治療，任一原發部位病理報告記錄有 LVI 即編碼 010'),
        ]),

    # SSF10 Ki-67, p.144/151
    'SSF10': ResolutionRule(
        field='SSF10', concept='ki67',
        rule_id='SSF10-摘錄原則',
        citation='Cancer-SSF-Manual 乳癌 SSF10，p.144/151',
        steps=[
            _drop_prior_submission,
            prefer_where(lambda o: o.timing != TIMING_POST_NEOADJUVANT,
                         '不採用前導性治療後的數據',
                         '有治療前數值時，治療後數值不採用'),
            _prefer_invasive,
            _prefer_primary,
            _prefer_reporting_hospital,
            _prefer_largest_specimen,
            prefer_max(lambda o: o.value if isinstance(o.value, (int, float)) else None,
                       '多顆腫瘤且有多筆檢驗值時，應摘錄百分比較高之數值；'
                       '報告以區間描述時摘錄最高值',
                       '同一個案有更高的 Ki-67 百分比'),
        ]),
}


def rule_for(field: str) -> ResolutionRule:
    if field not in BREAST_RULES:
        raise KeyError(
            f'{field} 尚未轉錄摘錄原則。已轉錄：{", ".join(sorted(BREAST_RULES))}')
    return BREAST_RULES[field]
