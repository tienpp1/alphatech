"""Deterministic evidence/lexical checks, NOT a semantic correctness judge."""
import re
import unicodedata
from collections import Counter
from .evidence_metrics import chunk_metrics, numeric_fact_metrics


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', str(text)).casefold().split())


def contains_phrase(answer, phrase):
    phrase = normalized(phrase)
    return bool(phrase) and re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', normalized(answer)) is not None


def score_case(case, response, fallback_message, evaluation_metadata=None):
    answer = response.get('answer') or ''
    sources = response.get('sources') or []
    chunks = chunk_metrics(case, sources)
    numbers = numeric_fact_metrics(case, answer)
    tools = response.get('tools_used') or []
    # Mentioning the refusal inside a fabricated answer is not a safe refusal.
    refused = normalized(answer) == normalized(fallback_message)
    expected_doc = case.get('expected_document')
    expected_tool = case.get('expected_tool')
    document_ok = bool(expected_doc) and any(
        isinstance(source, dict) and normalized(source.get('document_title', '')) == normalized(expected_doc)
        for source in sources
    )
    tool_ok = bool(expected_tool) and any(
        isinstance(tool, dict) and tool.get('tool') == expected_tool and tool.get('status') == 'SUCCESS'
        for tool in tools
    )
    category = case['category']
    evidence_ok = {'DOCUMENT_ONLY': document_ok, 'STRUCTURED_ONLY': tool_ok,
                   'HYBRID': document_ok and tool_ok}.get(category, False)
    # Each group is required; alternatives within a group are allowed explicitly.
    groups = case.get('required_keyword_groups', [[kw] for kw in case.get('expected_keywords', [])])
    matched = [[phrase for phrase in group if contains_phrase(answer, phrase)] for group in groups]
    missing = [group for group, matches in zip(groups, matched) if not matches]
    lexical_ok = bool(groups) and not missing and not refused
    forbidden = case.get('forbidden_keyword_groups', [])
    contradictions = [group for group in forbidden if any(contains_phrase(answer, phrase) for phrase in group)]
    contradiction_detected = bool(contradictions)
    lexical_ok = lexical_ok and not contradiction_detected
    should_refuse = case['should_fallback']
    proxy_pass = refused if should_refuse else evidence_ok and lexical_ok
    if not should_refuse and chunks['chunk_recall'] is not None:
        proxy_pass = proxy_pass and chunks['chunk_recall'] == 1.0
    if not should_refuse and numbers['numeric_facts_ok'] is not None:
        proxy_pass = proxy_pass and numbers['numeric_facts_ok']
    metadata = evaluation_metadata or {}
    return {
        'id': case['id'], 'category': category, 'should_fallback': should_refuse,
        'question': case.get('question'),
        'required_keyword_groups': groups,
        'refused': refused, 'retrieval_ok': None if should_refuse else evidence_ok,
        'citation_ok': document_ok if expected_doc else None,
        'tool_ok': tool_ok if expected_tool else None,
        'lexical_complete': None if should_refuse else lexical_ok,
        'matched_keywords': [phrase for matches in matched for phrase in matches],
        'missing_keyword_groups': [] if should_refuse else missing,
        'contradiction_detected': contradiction_detected,
        'matched_forbidden_keyword_groups': contradictions,
        'proxy_pass': proxy_pass,
        'semantic_correctness': None, 'requires_human_review': True,
        'answer': answer, 'sources': sources, 'tools_used': tools,
        **chunks,
        **numbers,
        'generation_mode': (response.get('generation_metadata') or {}).get('mode', 'UNKNOWN'),
        'generation_metadata': response.get('generation_metadata') or {},
        'retrieval_metadata': response.get('retrieval_metadata', {}),
        # Execution metadata is deliberately separate from application/provider
        # metadata so the benchmark can be audited without exposing exceptions.
        'status': metadata.get('status', 'SCORED'),
        'evaluated_at': metadata.get('evaluated_at'),
        'duration_ms': metadata.get('duration_ms'),
        'error_code': metadata.get('error_code'),
    }


def summarize(details):
    scored = [row for row in details if row.get('status', 'SCORED') == 'SCORED']
    substantive = [row for row in scored if not row['should_fallback']]
    citations = [row for row in substantive if row['citation_ok'] is not None]
    chunk_rows = [row for row in substantive if row.get('chunk_recall') is not None]
    numeric_rows = [row for row in substantive if row.get('numeric_facts_ok') is not None]
    tp = sum(row['refused'] and row['should_fallback'] for row in scored)
    fp = sum(row['refused'] and not row['should_fallback'] for row in scored)
    fn = sum(not row['refused'] and row['should_fallback'] for row in scored)
    def rate(numerator, denominator):
        return round(100 * numerator / denominator, 1) if denominator else None
    proxy = rate(sum(row['proxy_pass'] for row in substantive), len(substantive))
    return {
        'scoring_version': '2.2-annotated-evidence-proxy',
        'metric_kind': 'LEXICAL_AND_EVIDENCE_PROXY_NOT_SEMANTIC_ACCURACY',
        'semantic_correctness_rate': None,
        'limitations': ['Optional forbidden phrases and labelled numeric patterns check only declared facts; this is not semantic entailment or general numerical validation.',
                       'Matching a source title does not establish entailment or chunk relevance; gold chunk IDs measure identity coverage, not semantic entailment.',
                       'Generation metadata reports the application path; simulated providers in tests are not live-run evidence.'],
        'total_evaluated': len(details), 'scored_cases': len(scored),
        'error_cases': len(details) - len(scored),
        'document_and_data_cases': len(substantive),
        'out_of_domain_cases': tp + fn, 'citation_cases': len(citations),
        'retrieval_relevance_rate': rate(sum(row['retrieval_ok'] for row in substantive), len(substantive)),
        'source_presence_rate': rate(sum(row['retrieval_ok'] for row in substantive), len(substantive)),
        'citation_attribution_rate': rate(sum(row['citation_ok'] for row in citations), len(citations)),
        'chunk_annotated_cases': len(chunk_rows),
        'numeric_annotated_cases': len(numeric_rows),
        'numeric_unannotated_cases': len(substantive) - len(numeric_rows),
        'annotated_numeric_pass_rate': rate(sum(row['numeric_facts_ok'] for row in numeric_rows), len(numeric_rows)),
        'chunk_unannotated_cases': len(substantive) - len(chunk_rows),
        'chunk_recall_macro_percent': rate(sum(row['chunk_recall'] for row in chunk_rows), len(chunk_rows)),
        'chunk_precision_macro_percent': rate(sum(row['chunk_precision'] for row in chunk_rows), len(chunk_rows)),
        'lexical_evidence_pass_rate': proxy,
        # Compatibility alias only. Consumers must use the explicitly named proxy.
        'grounded_correctness_rate': proxy,
        'deprecated_metrics': {
            'grounded_correctness_rate': 'Alias of lexical_evidence_pass_rate; NOT semantic correctness.',
            'retrieval_relevance_rate': 'Alias of source_presence_rate; NOT chunk relevance.'},
        'fallback_precision': rate(tp, tp + fp), 'fallback_recall': rate(tp, tp + fn),
        'fallback_true_positives': tp, 'fallback_false_positives': fp, 'fallback_false_negatives': fn,
        'generation_mode_counts': dict(Counter(row['generation_mode'] for row in details)),
        'details': details,
    }
