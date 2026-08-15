# -*- coding: utf-8 -*-
"""The fact layer: keep every observation, resolve per the code book's rule.

These tests pin the behaviour that makes "different sources complement each
other" safe: gap filling and refinement are automatic, genuine conflicts are
either decided by an explicit code-book rule (with the reason recorded) or
escalated to a human -- never silently averaged or overwritten.
"""

import pytest

from tcr_workbench.demo_er import run, sample_observations, to_qbc_d014_d015, to_tcr_ssf1
from tcr_decoder.facts import (
    DOC_IMAGING, DOC_ONCOTYPE, DOC_PATHOLOGY, DOC_PHYSICIAN_STATEMENT,
    DOC_PRIOR_SUBMISSION, Evidence, HOSPITAL_EXTERNAL, Observation,
    PROCEDURE_BIOPSY, PROCEDURE_RESECTION, SITE_METASTATIC, SITE_PRIMARY,
    SPECIMEN_IN_SITU, SPECIMEN_INVASIVE, TIMING_POST_NEOADJUVANT, TIMING_PRE,
)
from tcr_workbench.resolution_rules import BREAST_RULES, rule_for


def er(value, **kwargs):
    kwargs.setdefault('timing', TIMING_PRE)
    kwargs.setdefault('doc_type', DOC_PATHOLOGY)
    kwargs.setdefault('qualifiers', {'representation': 'proportion'})
    return Observation(concept='er', value=value, **kwargs)


class TestRuleCoverage:
    def test_every_breast_ssf_field_has_a_transcribed_rule(self):
        assert set(BREAST_RULES) == {f'SSF{i}' for i in range(1, 11)}

    def test_every_rule_cites_the_code_book(self):
        for field, rule in BREAST_RULES.items():
            assert 'Cancer-SSF-Manual' in rule.citation, field
            assert 'p.' in rule.citation, field

    def test_unknown_field_fails_loudly(self):
        with pytest.raises(KeyError, match='尚未轉錄'):
            rule_for('SSF99')


class TestSelection:
    def test_invasive_beats_in_situ(self):
        resolution = rule_for('SSF1').resolve([
            er(15, specimen=SPECIMEN_IN_SITU, site=SITE_PRIMARY),
            er(70, specimen=SPECIMEN_INVASIVE, site=SITE_PRIMARY),
        ])
        assert resolution.chosen.value == 70
        assert any('原位癌' in reason for _o, reason in resolution.rejected)

    def test_primary_beats_metastatic(self):
        resolution = rule_for('SSF1').resolve([
            er(30, specimen=SPECIMEN_INVASIVE, site=SITE_METASTATIC),
            er(70, specimen=SPECIMEN_INVASIVE, site=SITE_PRIMARY),
        ])
        assert resolution.chosen.value == 70

    def test_reporting_hospital_beats_external(self):
        resolution = rule_for('SSF1').resolve([
            er(8, site=SITE_PRIMARY, hospital=HOSPITAL_EXTERNAL),
            er(70, site=SITE_PRIMARY),
        ])
        assert resolution.chosen.value == 70

    def test_multiple_tumours_take_the_highest_proportion(self):
        """碼冊：多顆腫瘤且皆有陽性百分比時，優先摘錄反應比例較高者。"""
        resolution = rule_for('SSF1').resolve([
            er(40, site=SITE_PRIMARY, tumor_id='T1'),
            er(85, site=SITE_PRIMARY, tumor_id='T2'),
        ])
        assert resolution.chosen.value == 85
        assert not resolution.needs_review

    def test_single_tumour_takes_the_largest_resection_specimen(self):
        resolution = rule_for('SSF1').resolve([
            er(8, site=SITE_PRIMARY, tumor_id='T1',
               procedure=PROCEDURE_BIOPSY, specimen_volume_mm=4.0),
            er(70, site=SITE_PRIMARY, tumor_id='T1',
               procedure=PROCEDURE_RESECTION, specimen_volume_mm=22.0),
        ])
        assert resolution.chosen.value == 70


class TestComplementaritySafety:
    def test_gap_filling_is_automatic(self):
        """A has nothing, B has a value -> B is used, no review needed."""
        resolution = rule_for('SSF1').resolve([er(55, site=SITE_PRIMARY)])
        assert resolution.chosen.value == 55
        assert not resolution.needs_review

    def test_prior_submission_never_overrides_a_source_document(self):
        resolution = rule_for('SSF1').resolve([
            er(70, site=SITE_PRIMARY),
            er(30, doc_type=DOC_PRIOR_SUBMISSION),
        ])
        assert resolution.chosen.value == 70
        assert any('證據等級低於原始文件' in reason
                   for _o, reason in resolution.rejected)

    def test_prior_submission_alone_still_needs_review(self):
        """既有申報值可以提示，但不能自己變成新的申報值。"""
        resolution = rule_for('SSF1').resolve([
            er(70, doc_type=DOC_PRIOR_SUBMISSION)])
        assert resolution.chosen is None
        assert resolution.needs_review

    def test_unresolvable_conflict_is_escalated_not_averaged(self):
        """Two equally-ranked pathology reports of the SAME tumour: the code
        book gives no rule beyond the ones already applied, so a human must
        decide. Nothing is averaged and nothing is silently dropped."""
        resolution = rule_for('SSF9').resolve([
            Observation(concept='lvi', value='absent', site=SITE_PRIMARY),
            Observation(concept='lvi', value='not_assessable', site=SITE_PRIMARY),
        ])
        assert resolution.needs_review
        assert '人工判斷' in resolution.review_reason

    def test_rejected_observations_are_kept_with_reasons(self):
        resolution = rule_for('SSF1').resolve(sample_observations())
        assert len(resolution.rejected) == 4
        for _observation, reason in resolution.rejected:
            assert reason.strip()


class TestTimingIsNotASource:
    def test_only_post_neoadjuvant_positive_is_111(self):
        resolution = rule_for('SSF1').resolve([
            er(60, timing=TIMING_POST_NEOADJUVANT, site=SITE_PRIMARY)])
        assert resolution.forced_code == '111'

    def test_only_post_neoadjuvant_negative_is_121(self):
        resolution = rule_for('SSF1').resolve([
            er(0, timing=TIMING_POST_NEOADJUVANT, site=SITE_PRIMARY)])
        assert resolution.forced_code == '121'

    def test_negative_before_positive_after_is_888(self):
        """治療前陰性、治療後陽性 -> 888。這不是衝突，是一個專屬代碼。"""
        resolution = rule_for('SSF1').resolve([
            er(0, timing=TIMING_PRE, site=SITE_PRIMARY),
            er(80, timing=TIMING_POST_NEOADJUVANT, site=SITE_PRIMARY),
        ])
        assert resolution.forced_code == '888'

    def test_pre_treatment_value_wins_when_both_exist(self):
        resolution = rule_for('SSF1').resolve([
            er(70, timing=TIMING_PRE, site=SITE_PRIMARY),
            er(20, timing=TIMING_POST_NEOADJUVANT, site=SITE_PRIMARY),
        ])
        assert resolution.chosen.value == 70


class TestFieldSpecificRules:
    def test_ssf6_takes_the_highest_score_not_the_highest_percentage(self):
        resolution = rule_for('SSF6').resolve([
            Observation(concept='nottingham', value=6, site=SITE_PRIMARY,
                        qualifiers={'representation': 'score'}),
            Observation(concept='nottingham', value=9, site=SITE_PRIMARY,
                        qualifiers={'representation': 'score'}),
        ])
        assert resolution.chosen.value == 9

    def test_ssf6_prefers_score_over_grade_only(self):
        resolution = rule_for('SSF6').resolve([
            Observation(concept='nottingham', value='high', site=SITE_PRIMARY,
                        qualifiers={'representation': 'grade'}),
            Observation(concept='nottingham', value=7, site=SITE_PRIMARY,
                        qualifiers={'representation': 'score'}),
        ])
        assert resolution.chosen.value == 7

    def test_ssf9_is_an_or_across_primary_site_reports(self):
        """任一份原發部位病理報告記錄有 LVI 即編碼 010 -- 不是來源優先序。"""
        resolution = rule_for('SSF9').resolve([
            Observation(concept='lvi', value='absent', site=SITE_PRIMARY),
            Observation(concept='lvi', value='present', site=SITE_PRIMARY),
        ])
        assert resolution.forced_code == '010'

    def test_ssf5_itc_only_is_zero(self):
        resolution = rule_for('SSF5').resolve([
            Observation(concept='sentinel_nodes_positive', value=1,
                        qualifiers={'itc_only': True})])
        assert resolution.forced_code == '000'

    def test_ssf4_post_neoadjuvant_sentinel_is_not_collected(self):
        resolution = rule_for('SSF4').resolve([
            Observation(concept='sentinel_nodes_examined', value=3,
                        timing=TIMING_POST_NEOADJUVANT)])
        assert resolution.forced_code == '988'

    def test_ssf7_prefers_fish_over_ihc(self):
        resolution = rule_for('SSF7').resolve([
            Observation(concept='her2', value='2+', site=SITE_PRIMARY,
                        qualifiers={'assay': 'IHC', 'ihc_score': '2+',
                                    'ish_done': True, 'definitive': True}),
            Observation(concept='her2', value='amplified', site=SITE_PRIMARY,
                        qualifiers={'assay': 'FISH', 'definitive': True}),
        ])
        assert resolution.chosen.qualifiers['assay'] == 'FISH'

    def test_oncotype_only_is_988(self):
        resolution = rule_for('SSF1').resolve([
            er(70, doc_type=DOC_ONCOTYPE, site=SITE_PRIMARY)])
        assert resolution.forced_code == '988'


class TestTwoTargetsOneResolution:
    def test_demo_produces_both_submissions_from_one_decision(self):
        result = run()
        assert result['SSF1'] == 'S70'
        assert result['QBC'] == {'D014': '1', 'D015': '70'}
        assert 'Strong staining, 70%' in result['SSF1_meaning']

    def test_tcr_keeps_intensity_that_qbc_cannot_express(self):
        """The whole argument against task-to-task conversion, as a test."""
        result = run()
        assert result['SSF1'].startswith('S')          # 強度保留在癌登碼
        assert result['QBC']['D015'] == '70'           # QBC 只有百分比
        # 反過來從 QBC 推癌登只會得到 '070'，強度已經不在資料裡
        assert result['SSF1'] != '070'

    def test_special_codes_reach_both_encoders(self):
        resolution = rule_for('SSF1').resolve([
            er(0, timing=TIMING_PRE, site=SITE_PRIMARY),
            er(80, timing=TIMING_POST_NEOADJUVANT, site=SITE_PRIMARY),
        ])
        assert to_tcr_ssf1(resolution) == '888'
        assert to_qbc_d014_d015(resolution)['D014'] == '1'


class TestExplainability:
    def test_explanation_names_the_rule_and_the_page(self):
        resolution = rule_for('SSF1').resolve(sample_observations())
        text = resolution.explain()
        assert 'SSF1-摘錄原則' in text
        assert 'p.121-128' in text
        assert '排除' in text

    def test_every_chosen_observation_keeps_its_evidence(self):
        resolution = rule_for('SSF1').resolve(sample_observations())
        assert resolution.chosen.evidence
        evidence = resolution.chosen.evidence[0]
        assert evidence.document_id.startswith('DiagnosticReport/')
        assert evidence.span is not None
