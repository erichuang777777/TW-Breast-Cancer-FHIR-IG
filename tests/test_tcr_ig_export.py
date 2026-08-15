# -*- coding: utf-8 -*-
"""The generated FHIR artefacts must be internally consistent.

There is no FHIR validator in this environment, so these tests check the
invariants a validator would care about and that a generator can get wrong:
ids match filenames, canonical URLs are unique, every answerValueSet a
Questionnaire references is actually produced, every code in the example
QuestionnaireResponse exists in the CodeSystem it cites, and no code table is
claimed for a field this package cannot verify.
"""

import json

import pytest

from tcr_decoder.code_ranges import CODE_RANGES
from tcr_workbench.ig_export import (
    DEFAULT_BASE_URL, FIELD_MAP, NUMERIC_FIELDS, SECTIONS, build_ig,
    build_questionnaire, field_has_code_table,
)


@pytest.fixture(scope='module')
def ig(tmp_path_factory):
    out = tmp_path_factory.mktemp('fhir')
    summary = build_ig(out, cancer_group='breast')
    resources = {}
    for path in out.rglob('*.json'):
        resources[path.stem] = json.loads(path.read_text(encoding='utf-8'))
    return summary, resources, out


class TestStructure:
    def test_every_file_id_matches_its_filename(self, ig):
        _summary, resources, out = ig
        for path in out.rglob('*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            assert data['id'] == path.stem, path
            assert path.parent.name == data['resourceType'], path

    def test_canonical_urls_are_unique(self, ig):
        _summary, resources, _out = ig
        urls = [r['url'] for r in resources.values() if 'url' in r]
        assert len(urls) == len(set(urls))

    def test_every_resource_declares_draft_experimental_status(self, ig):
        """These are generated artefacts, not published conformance."""
        _summary, resources, _out = ig
        for r in resources.values():
            if r['resourceType'] in ('Task', 'QuestionnaireResponse'):
                continue
            assert r.get('status') == 'draft', r['id']
            assert r.get('experimental') is True, r['id']


class TestTerminology:
    def test_code_systems_cover_exactly_the_verified_fields(self, ig):
        _summary, resources, _out = ig
        generated = {r['id'].replace('tcr-breast-', '')
                     for r in resources.values()
                     if r['resourceType'] == 'CodeSystem'}
        expected = {f.lower().replace('_', '-') for f, _z, _s, _d in FIELD_MAP
                    if field_has_code_table('breast', f)}
        assert generated == expected

    def test_ssf_code_systems_contain_every_legal_code(self, ig):
        _summary, resources, _out = ig
        for ssf_key in (f'SSF{i}' for i in range(1, 11)):
            cs = resources[f'tcr-breast-{ssf_key.lower()}']
            codes = {c['code'] for c in cs['concept']}
            assert codes == set(CODE_RANGES['breast'][ssf_key][1]), ssf_key
            assert cs['count'] == len(codes)

    def test_every_concept_has_chinese_display_and_english_designation(self, ig):
        _summary, resources, _out = ig
        for ssf_key in (f'SSF{i}' for i in range(1, 11)):
            for concept in resources[f'tcr-breast-{ssf_key.lower()}']['concept']:
                assert concept['display'].strip(), concept
                designations = concept.get('designation', [])
                assert any(d['language'] == 'en' and d['value'].strip()
                           for d in designations), concept

    def test_concept_maps_leave_every_target_unmapped(self, ig):
        """A guessed LOINC/SNOMED target would be worse than a visible gap."""
        _summary, resources, _out = ig
        maps = [r for r in resources.values() if r['resourceType'] == 'ConceptMap']
        assert maps
        for cm in maps:
            for group in cm['group']:
                for element in group['element']:
                    for target in element['target']:
                        assert target['equivalence'] == 'unmatched'
                        assert 'code' not in target


class TestQuestionnaire:
    def test_covers_all_99_longform_fields_exactly_once(self, ig):
        _summary, resources, _out = ig
        q = resources['tcr-breast-longform']
        link_ids = [item['linkId'] for group in q['item'] for item in group['item']]
        assert len(link_ids) == len(set(link_ids))
        assert set(link_ids) == {f for f, _z, _s, _d in FIELD_MAP}
        assert len(link_ids) == 99

    def test_every_answer_value_set_is_generated(self, ig):
        _summary, resources, _out = ig
        q = resources['tcr-breast-longform']
        produced = {r['url'] for r in resources.values()
                    if r['resourceType'] == 'ValueSet'}
        for group in q['item']:
            for item in group['item']:
                vs = item.get('answerValueSet')
                if vs:
                    assert vs in produced, item['linkId']

    def test_fields_without_a_verified_code_table_are_flagged(self, ig):
        _summary, resources, _out = ig
        q = resources['tcr-breast-longform']
        for group in q['item']:
            for item in group['item']:
                field = item['linkId']
                pending = any(
                    e['url'].endswith('tcr-codetable-pending')
                    for e in item.get('extension', []))
                if item.get('answerValueSet'):
                    assert not pending, field
                elif item['type'] == 'string' and field != 'PK':
                    assert pending, f'{field} has neither a ValueSet nor a flag'

    def test_ebrt_repeats_because_the_field_is_additive(self, ig):
        _summary, resources, _out = ig
        q = resources['tcr-breast-longform']
        ebrt = [item for group in q['item'] for item in group['item']
                if item['linkId'] == 'EBRT'][0]
        assert ebrt.get('repeats') is True
        assert ebrt['type'] == 'choice'

    def test_sections_match_the_field_map(self):
        sectioned = [f for _id, _label, fields in SECTIONS for f in fields]
        assert sorted(sectioned) == sorted(f for f, _z, _s, _d in FIELD_MAP)


class TestExample:
    def test_example_response_only_cites_codes_that_exist(self, ig):
        _summary, resources, _out = ig
        qr = resources['tcr-breast-example']
        systems = {r['url']: {c['code'] for c in r['concept']}
                   for r in resources.values() if r['resourceType'] == 'CodeSystem'}
        checked = 0
        for group in qr['item']:
            for item in group['item']:
                for answer in item['answer']:
                    coding = answer.get('valueCoding')
                    if not coding:
                        continue
                    assert coding['system'] in systems, item['linkId']
                    assert coding['code'] in systems[coding['system']], (
                        f"{item['linkId']}: {coding['code']}")
                    checked += 1
        assert checked >= 10

    def test_example_is_tagged_synthetic(self, ig):
        _summary, resources, _out = ig
        qr = resources['tcr-breast-example']
        assert any(t['code'] == 'synthetic' for t in qr['meta']['tag'])

    def test_task_example_declares_its_inputs_and_output(self, ig):
        _summary, resources, _out = ig
        task = resources['tcr-breast-abstraction-example']
        assert task['resourceType'] == 'Task'
        assert len(task['input']) >= 3
        assert task['output'][0]['valueReference']['reference'].startswith(
            'QuestionnaireResponse/')


def test_summary_reports_the_real_coverage_gap(ig):
    summary, _resources, _out = ig
    assert summary['申報欄位總數'] == 99
    assert summary['已有驗證碼表的欄位'] == 18
    # The gap is the point of the summary: it must not silently read as done.
    assert summary['待補碼表的欄位'] > 0


def test_base_url_is_a_placeholder_that_must_be_overridden():
    """The default canonical base must not look like a real authority."""
    assert 'example.org' in DEFAULT_BASE_URL
    q = build_questionnaire('breast', 'https://my.org/fhir')
    assert q['url'].startswith('https://my.org/fhir/')


class TestIGScaffold:
    """The SUSHI / IG-Publisher repository layout."""

    @pytest.fixture(scope='class')
    def scaffold(self, tmp_path_factory):
        from tcr_workbench.ig_export import build_ig_scaffold
        repo = tmp_path_factory.mktemp('ig')
        summary = build_ig_scaffold(
            repo, cancer_group='breast',
            canonical='https://example.org/fhir/breast-ig')
        return summary, repo

    def test_layout_matches_what_ig_publisher_reads(self, scaffold):
        _summary, repo = scaffold
        for expected in ('sushi-config.yaml', 'ig.ini', 'README.md',
                         'input/fsh/extensions.fsh',
                         'input/fsh/task-registry-abstraction.fsh',
                         'input/ignoreWarnings.txt',
                         'input/pagecontent/index.md',
                         'input/pagecontent/cancer-registry-task.md',
                         'input/pagecontent/terminology.md'):
            assert (repo / expected).exists(), expected

    def test_generated_resources_are_flat_under_input_resources(self, scaffold):
        """IG Publisher silently skips sub-folders of input/resources."""
        _summary, repo = scaffold
        res = repo / 'input' / 'resources'
        assert not [d for d in res.iterdir() if d.is_dir()]
        assert len(list(res.glob('*.json'))) >= 50

    def test_sushi_config_is_valid_yaml_with_the_given_canonical(self, scaffold):
        yaml = pytest.importorskip('yaml')
        _summary, repo = scaffold
        config = yaml.safe_load(
            (repo / 'sushi-config.yaml').read_text(encoding='utf-8'))
        assert config['canonical'] == 'https://example.org/fhir/breast-ig'
        assert config['fhirVersion'] == '4.0.1'
        assert set(config['pages']) == {
            'index.md', 'cancer-registry-task.md', 'terminology.md'}

    def test_generated_resources_use_the_scaffold_canonical(self, scaffold):
        _summary, repo = scaffold
        for path in (repo / 'input' / 'resources').glob('*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            if 'url' in data:
                assert data['url'].startswith('https://example.org/fhir/breast-ig/')

    def test_task_fsh_does_not_constrain_elements_r4_task_lacks(self, scaffold):
        """Regression: the profile used to constrain Task.subject, which does
        not exist in R4 -- SUSHI failed with 'No element found at path'."""
        _summary, repo = scaffold
        fsh = (repo / 'input' / 'fsh' / 'task-registry-abstraction.fsh').read_text(
            encoding='utf-8')
        assert '* subject' not in fsh
        assert '* for 1..1' in fsh
        assert '* focus only Reference(Condition)' in fsh

    def test_rerun_keeps_hand_authored_files(self, scaffold):
        """Re-generating after a code-book change must not clobber FSH edits."""
        from tcr_workbench.ig_export import build_ig_scaffold
        _summary, repo = scaffold
        authored = repo / 'input' / 'fsh' / 'extensions.fsh'
        authored.write_text('// edited by hand\n', encoding='utf-8')
        build_ig_scaffold(repo, cancer_group='breast',
                          canonical='https://example.org/fhir/breast-ig')
        assert authored.read_text(encoding='utf-8') == '// edited by hand\n'
