"""In-memory, allowlisted evidence for already rejected time expressions.

These observations neither repair a candidate nor establish semantic support.
Never return source text, expressions, identifiers, hashes or exception details.
"""
import json
import re
import unicodedata


MATCH_CATEGORIES = (
    'expression_found_in_other_cited_source',
    'found_in_supplied_uncited_source',
    'expression_found_in_anchor_session_time',
    'whitespace_only_mismatch',
    'unicode_nfc_only_mismatch',
)


def diagnose_extraction_time(content: str, context: dict | None, errors: list[dict]) -> list[dict]:
    """Casefold like validation; normalize only for the diagnostic comparisons.

    Priority follows MATCH_CATEGORIES, retaining independent flags. A not_found
    result covers only supplied sources, not all history or semantic validity.
    """
    if not isinstance(context, dict) or not isinstance(context.get('sources'), dict):
        return []
    sources = context['sources']
    document = json.loads(content)
    if not isinstance(document, dict) or not isinstance(document.get('memories'), list):
        return []
    result = []
    for error in errors:
        path = error.get('field_path')
        if error.get('error_code') != 'extraction_time_expression_required' or not isinstance(path, str):
            continue
        location = re.fullmatch(r'memories\[(0|[1-9][0-9]*)\]', path)
        if location is None:
            continue
        index = int(location[1])
        if index >= len(document['memories']):
            continue
        memory = document['memories'][index]
        time = memory.get('time', {})
        expression = time.get('original_expression')
        anchor = time.get('anchor_source_id')
        cited = memory.get('source_ids', [])
        if not isinstance(expression, str) or anchor not in cited or anchor not in sources:
            continue
        needle = expression.casefold()
        anchor_text = sources[anchor].get('text', '')
        if not isinstance(anchor_text, str) or needle in anchor_text.casefold():
            continue
        matches = dict.fromkeys(MATCH_CATEGORIES, False)
        matches['expression_found_in_other_cited_source'] = any(
            sid != anchor and isinstance(sources.get(sid), dict)
            and isinstance(sources[sid].get('text'), str)
            and needle in sources[sid]['text'].casefold() for sid in cited)
        matches['found_in_supplied_uncited_source'] = any(
            sid not in cited and isinstance(source, dict)
            and isinstance(source.get('text'), str)
            and needle in source['text'].casefold() for sid, source in sources.items())
        session_time = sources[anchor].get('session_time')
        matches['expression_found_in_anchor_session_time'] = (
            isinstance(session_time, str) and needle in session_time.casefold())
        normalized_expression = ' '.join(needle.split())
        matches['whitespace_only_mismatch'] = bool(normalized_expression) and (
            normalized_expression in ' '.join(anchor_text.casefold().split()))
        matches['unicode_nfc_only_mismatch'] = (
            unicodedata.normalize('NFC', needle)
            in unicodedata.normalize('NFC', anchor_text.casefold()))
        category = next((key for key in MATCH_CATEGORIES if matches[key]), 'not_found')
        result.append(dict(field_path=path, category=category, **matches))
    return result
