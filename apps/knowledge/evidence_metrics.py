"""Gold-chunk measurements; source identity is not semantic entailment.

Gold IDs must be selected independently of the returned answer and scoped to the
same immutable dataset/run. Missing annotation remains unmeasured, never zero.
"""
import re
from decimal import Decimal, InvalidOperation


def numeric_fact_metrics(case, answer):
    """Check explicitly annotated labelled quantities, not arbitrary numbers.

    Patterns are trusted local benchmark configuration, never user input. Each
    uses a named `value` group and includes the fact label and unit. Decimal dots
    are accepted; locale/thousands conversion must be explicit in the rubric.
    Matching cannot establish negation, conditions, entailment or completeness.
    """
    facts = case.get('required_numeric_facts')
    if facts is None:
        return {'numeric_facts_ok': None, 'numeric_fact_checks': []}
    if not isinstance(facts, (list, tuple)) or not facts:
        raise ValueError('required_numeric_facts must be a nonempty list')
    checks, seen = [], set()
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get('id'), str) or not fact['id'].strip():
            raise ValueError('Numeric facts require a nonempty id')
        if fact['id'] in seen:
            raise ValueError('Numeric fact IDs must be unique')
        seen.add(fact['id'])
        try:
            expected = Decimal(str(fact['expected']))
            pattern = re.compile(fact['pattern'], re.IGNORECASE)
            if not expected.is_finite() or 'value' not in pattern.groupindex:
                raise ValueError()
        except (KeyError, TypeError, ValueError, InvalidOperation, re.error) as exc:
            raise ValueError('Numeric rubric requires finite expected and a value capture') from exc
        observed, invalid = [], False
        for match in pattern.finditer(answer):
            try:
                value = Decimal(match.group('value'))
                if not value.is_finite():
                    raise InvalidOperation()
                observed.append(value)
            except (InvalidOperation, TypeError):
                invalid = True
        passed = bool(observed) and not invalid and all(value == expected for value in observed)
        checks.append({'id': fact['id'], 'expected': str(expected),
                       'observed': [str(value) for value in observed],
                       'invalid_value': invalid, 'passed': passed})
    return {'numeric_facts_ok': all(row['passed'] for row in checks), 'numeric_fact_checks': checks}


def chunk_metrics(case, sources):
    gold = case.get("expected_chunk_ids")
    if gold is None:
        return {"chunk_recall": None, "chunk_precision": None,
                "expected_chunk_ids": None, "matched_chunk_ids": [],
                "missing_chunk_ids": [], "unidentified_source_count": 0}
    if (not isinstance(gold, (list, tuple)) or not gold
            or any(type(value) not in (int, str) or not str(value).strip() for value in gold)):
        raise ValueError("expected_chunk_ids must be a nonempty list of integer/string IDs")
    expected = {str(value) for value in gold}
    retrieved, unidentified = set(), 0
    for source in sources:
        value = source.get("chunk_id") if isinstance(source, dict) else None
        if type(value) not in (int, str) or not str(value).strip():
            unidentified += 1
        else:
            retrieved.add(str(value))
    matched = expected & retrieved
    denominator = len(retrieved) + unidentified
    return {"chunk_recall": len(matched) / len(expected),
            "chunk_precision": len(matched) / denominator if denominator else 0.0,
            "expected_chunk_ids": sorted(expected), "matched_chunk_ids": sorted(matched),
            "missing_chunk_ids": sorted(expected - retrieved),
            "unidentified_source_count": unidentified}
