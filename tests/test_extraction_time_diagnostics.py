"""Rejected extraction time claims expose safe evidence categories only."""
import json
import sqlite3
from decimal import Decimal

import httpx
import pytest

from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import DeepSeekModel, ModelFailure


def memory(expression, source_ids=None, anchor='s1'):
    return dict(content='Synthetic painting event.', memory_type='event',
        statement_type='fact', polarity='positive', entity_id='Alex',
        state_dimension='painting', source_ids=source_ids or ['s1'],
        time=dict(original_expression=expression, anchor_source_id=anchor))


def generate(settings, value, context, *, operation='extract', schema=ExtractionBatch, raw=False):
    def provider(_):
        return httpx.Response(200, json=dict(model='deepseek-flash',
            choices=[dict(finish_reason='stop', message=dict(content=value if raw else json.dumps(value)))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 0}),
        api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    return model.generate(operation, {}, schema, context=context)


def test_rejected_expression_in_another_cited_source_gets_safe_diagnostic(settings):
    context = dict(sources={'s1': {'text': 'I painted yesterday.'},
                            's2': {'text': 'I painted last Friday.'}})
    with pytest.raises(ModelFailure) as failure:
        generate(settings, dict(memories=[memory('last Friday', ['s1', 's2'])]), context)
    call = failure.value.metadata['calls'][0]
    assert failure.value.code == call['outcome'] == 'invalid_output'
    assert call['error_code'] == 'extraction_time_expression_required'
    assert call['extraction_time_diagnostics'] == [dict(
        field_path='memories[0]', category='expression_found_in_other_cited_source',
        expression_found_in_other_cited_source=True,
        found_in_supplied_uncited_source=False,
        expression_found_in_anchor_session_time=False,
        whitespace_only_mismatch=False, unicode_nfc_only_mismatch=False)]


@pytest.mark.parametrize('expression,anchor_text,extra,session_time,category', [
    ('Friday', 'I painted yesterday.', {'s2': {'text': 'I painted FRIDAY.'}}, '',
     'found_in_supplied_uncited_source'),
    ('Friday', 'I painted yesterday.', {}, 'Friday, 2 May',
     'expression_found_in_anchor_session_time'),
    ('last  Friday', 'I painted last Friday.', {}, '', 'whitespace_only_mismatch'),
    ('caf\u00e9', 'We met at the cafe\u0301.', {}, '', 'unicode_nfc_only_mismatch'),
    ('the previous day', 'I painted yesterday.', {}, '', 'not_found'),
])
def test_rejected_expression_categories_remain_failures(
        settings, expression, anchor_text, extra, session_time, category):
    sources = {'s1': dict(text=anchor_text, session_time=session_time), **extra}
    with pytest.raises(ModelFailure) as failure:
        generate(settings, dict(memories=[memory(expression)]), dict(sources=sources))
    call = failure.value.metadata['calls'][0]
    assert call['error_code'] == 'extraction_time_expression_required'
    diagnostic, = call['extraction_time_diagnostics']
    assert diagnostic['field_path'] == 'memories[0]'
    assert diagnostic['category'] == category
    assert {key for key, value in diagnostic.items() if value is True} == (
        {category} if category != 'not_found' else set())


@pytest.mark.parametrize('expression,text', [
    ('nextweek', 'We will meet next week.'),
    ('5 May', 'We met on \uff15 May.'),
    ('caf\u00e9  Friday', 'We met at the cafe\u0301 Friday.'),
    (' ', 'Yesterday.'),
])
def test_normalizations_do_not_guess_or_match_empty_text(settings, expression, text):
    value = dict(memories=[memory(expression)])
    value['memories'][0]['content'] = 'Candidate ' + expression
    value['memories'][0]['time']['basis'] = expression
    context = dict(sources={'s1': dict(text=text, session_time=None)})
    with pytest.raises(ModelFailure) as failure:
        generate(settings, value, context)
    assert failure.value.metadata['calls'][0]['error_code'] == 'extraction_time_expression_required'
    diagnostic, = failure.value.metadata['calls'][0]['extraction_time_diagnostics']
    assert diagnostic['category'] == 'not_found'
    assert not any(v is True for v in diagnostic.values())


def test_overlapping_matches_keep_independent_flags_and_fixed_priority(settings):
    context = dict(sources={'s1': dict(text='Yesterday.', session_time='FRIDAY'),
        's2': dict(text='On Friday.'), 's3': dict(text='Friday again.')})
    with pytest.raises(ModelFailure) as failure:
        generate(settings, dict(memories=[memory('Friday', ['s1', 's2'])]), context)
    diagnostic, = failure.value.metadata['calls'][0]['extraction_time_diagnostics']
    assert diagnostic == dict(field_path='memories[0]',
        category='expression_found_in_other_cited_source',
        expression_found_in_other_cited_source=True,
        found_in_supplied_uncited_source=True,
        expression_found_in_anchor_session_time=True,
        whitespace_only_mismatch=False, unicode_nfc_only_mismatch=False)


@pytest.mark.parametrize('operation,schema', [
    ('relate', ExtractionBatch),
    ('extract', type('OtherBatch', (ExtractionBatch,), {})),
])
def test_only_extract_with_the_production_schema_adds_diagnostics(settings, operation, schema):
    with pytest.raises(ModelFailure) as failure:
        generate(settings, dict(memories=[memory('Friday')]),
            dict(sources={'s1': dict(text='Yesterday.')}), operation=operation, schema=schema)
    call = failure.value.metadata['calls'][0]
    assert call['error_code'] == 'extraction_time_expression_required'
    assert 'extraction_time_diagnostics' not in call


@pytest.mark.parametrize('context', [None, {}, {'sources': {}}])
def test_missing_source_context_adds_no_diagnostic(settings, context):
    value = dict(memories=[memory('Friday')])
    if context and 'sources' in context:
        with pytest.raises(ModelFailure) as failure:
            generate(settings, value, context)
        metadata = failure.value.metadata
    else:
        metadata = generate(settings, value, context).metadata
    assert all('extraction_time_diagnostics' not in c for c in metadata['calls'])


@pytest.mark.parametrize('expression', ['yesterday', 'YESTERDAY', ''])
def test_successful_extraction_adds_no_diagnostic(settings, expression):
    result = generate(settings, dict(memories=[memory(expression)]),
        dict(sources={'s1': dict(text='I painted yesterday.')}))
    assert result.metadata['calls'][0]['outcome'] == 'succeeded'
    assert 'extraction_time_diagnostics' not in result.metadata['calls'][0]


@pytest.mark.parametrize('content', [
    'private-invalid-json',
    '[]',
    '{"memories":"private-not-an-array"}',
    '{"memories":[{"time":{"private-untrusted-key":"private-value"}}]}',
])
def test_malicious_or_malformed_json_cannot_supply_diagnostics(settings, content):
    with pytest.raises(ModelFailure) as failure:
        generate(settings, content, dict(sources={'s1': dict(text='Yesterday.')}), raw=True)
    assert 'private-' not in json.dumps(failure.value.metadata)
    assert 'extraction_time_diagnostics' not in failure.value.metadata['calls'][0]


def test_multiple_time_errors_are_kept_when_the_primary_error_is_unrelated(settings):
    unrelated = memory('yesterday')
    unrelated['content'] = ' '
    value = dict(memories=[unrelated, memory('Friday'), memory('Tuesday')])
    context = dict(sources={'s1': dict(text='I painted yesterday.'),
                            's2': dict(text='I painted Friday.')})
    with pytest.raises(ModelFailure) as failure:
        generate(settings, value, context)
    call = failure.value.metadata['calls'][0]
    assert call['error_code'] == 'domain_constraint_failed'
    assert [(d['field_path'], d['category']) for d in call['extraction_time_diagnostics']] == [
        ('memories[1]', 'found_in_supplied_uncited_source'),
        ('memories[2]', 'not_found')]


def test_source_expression_ids_and_untrusted_keys_are_not_serialized(settings):
    value = dict(memories=[memory('private-expression',
        ['private-anchor-id', 'private-cited-id'], 'private-anchor-id')],
        **{'private-untrusted-key': 'private-value'})
    context = dict(sources={
        'private-anchor-id': dict(text='private-source-text: yesterday.'),
        'private-cited-id': dict(text='private-expression was used.'),
        'private-uncited-id': dict(text='private-expression was used again.')})
    with pytest.raises(ModelFailure) as failure:
        generate(settings, value, context)
    assert 'private-' not in json.dumps(failure.value.metadata)
    assert 'private-' not in str(failure.value)
    diagnostic, = failure.value.metadata['calls'][0]['extraction_time_diagnostics']
    assert set(diagnostic) == {'field_path', 'category',
        'expression_found_in_other_cited_source', 'found_in_supplied_uncited_source',
        'expression_found_in_anchor_session_time', 'whitespace_only_mismatch',
        'unicode_nfc_only_mismatch'}
    assert all(type(value) is bool for key, value in diagnostic.items()
               if key not in {'field_path', 'category'})


@pytest.mark.parametrize('diagnostic_fails', [False, True])
def test_diagnostic_observation_cannot_change_retries_feedback_usage_or_budget(
        settings, tmp_path, capsys, diagnostic_fails):
    class UnreadableSource(dict):
        def get(self, *_):
            raise RuntimeError('private-diagnostic-exception')

    context = dict(sources={'s1': dict(text='Yesterday.')})
    if diagnostic_fails:
        context['sources']['private-uncited-id'] = UnreadableSource()
    requests = []
    def provider(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=dict(model='deepseek-flash', choices=[dict(
            finish_reason='stop', message=dict(content=json.dumps(dict(memories=[memory('Friday')])),
                reasoning_content='private-hidden-reasoning'))],
            usage=dict(prompt_tokens=100, completion_tokens=10, total_tokens=110)))
    ledger = tmp_path/'requests.sqlite3'
    guard = BudgetTransport(ledger, httpx.MockTransport(provider), max_requests=2,
        max_usd='0.2619648', model='deepseek-flash', input_usd_per_million='.30',
        output_usd_per_million='1.20', max_input_bytes=160000, max_output_tokens=32768)
    model = DeepSeekModel(settings.model_copy(update={'model_retries': 1}),
        api_key='synthetic-test-key', transport=guard)
    with pytest.raises(ModelFailure) as failure:
        model.generate('extract', {}, ExtractionBatch, context=context)
    calls = failure.value.metadata['calls']
    assert failure.value.code == 'invalid_output'
    assert len(requests) == len(calls) == 2
    assert all(c['error_code'] == 'extraction_time_expression_required' for c in calls)
    assert all(('extraction_time_diagnostics' in c) != diagnostic_fails for c in calls)
    assert all(c['usage'] == dict(prompt_tokens=100, completion_tokens=10, total_tokens=110) for c in calls)
    assert all(body['thinking'] == {'type': 'disabled'} and 'reasoning_effort' not in body for body in requests)
    feedback = json.loads(requests[1]['messages'][1]['content'])['retry_feedback']
    assert set(feedback) == {'error_code', 'field_path', 'instruction'}
    assert feedback['error_code'] == 'extraction_time_expression_required'
    assert feedback['field_path'] == 'memories[0]'
    with sqlite3.connect(ledger) as db:
        rows = db.execute('SELECT reserved_usd,status,usage_json FROM physical_requests').fetchall()
    assert len(rows) == 2 and all(row[1] == 'response_received' for row in rows)
    assert sum(Decimal(row[0]) for row in rows) <= Decimal('0.2619648')
    assert all(Decimal(row[0]) > 0 for row in rows)
    assert all(json.loads(row[2]) == calls[0]['usage'] for row in rows)
    assert 'private-' not in json.dumps([failure.value.metadata, feedback])
    captured = capsys.readouterr()
    assert 'private-' not in captured.out + captured.err
