"""Real, unmodified HTTP with an ephemeral, allowlisted quote audit."""
import json

import httpx


class QuoteAuditTransport(httpx.BaseTransport):
    def __init__(self, context):
        self.context = context
        self.http = httpx.HTTPTransport()
        self.observations = []

    def handle_request(self, request):
        response = self.http.handle_request(request)
        response.read()
        if response.status_code == 200:
            try:
                choice = response.json()['choices'][0]
                if choice.get('finish_reason') != 'stop':
                    return response
                output = json.loads(choice['message']['content'])
                known = {m['memory_id'] for m in self.context['history']}
                for index, judgment in enumerate(output.get('judgments', [])):
                    if not isinstance(judgment, dict):
                        continue
                    quote, ids = judgment.get('support_quote'), judgment.get('source_ids', [])
                    ids = ids if isinstance(ids, list) else []
                    cited = [s for s in ids if isinstance(s, str) and s in self.context['sources']]
                    texts = [self.context['sources'][s]['text'] for s in cited]
                    has_quote = isinstance(quote, str) and bool(quote.strip())
                    label = judgment.get('label')
                    self.observations.append({'output_index': index,
                        'old_memory_id': judgment.get('old_memory_id') if judgment.get('old_memory_id') in known else None,
                        'label': label if label in ('RETAIN', 'UPDATE', 'SUPERSEDE', 'CONFLICT', 'undetermined') else None,
                        'quote_present': has_quote,
                        'quote_length': len(quote) if isinstance(quote, str) else None,
                        'exact_in_cited_source': bool(has_quote and any(quote in text for text in texts)),
                        'casefold_match': bool(has_quote and any(quote.casefold() in text.casefold() for text in texts)),
                        'whitespace_normalized_match': bool(has_quote and any(' '.join(quote.split()) in ' '.join(text.split()) for text in texts)),
                        'contains_ellipsis': bool(has_quote and ('...' in quote or '\u2026' in quote)),
                        'all_source_ids_known': bool(ids) and len(cited) == len(ids)})
            except (ValueError, KeyError, TypeError, IndexError):
                # Diagnostics are supplemental. The production validator decides acceptance.
                self.observations.append({'observation': 'unrecognized_output_shape'})
        return response

    def close(self):
        self.http.close()
