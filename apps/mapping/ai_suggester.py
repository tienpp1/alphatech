"""
AI-Assisted Mapping Recommendation Engine.
Provides semantic schema suggestions with confidence scores and reasoning.
Operates STRICTLY in recommendation mode: recommendations remain in
PENDING_CONFIRMATION status until a human manager explicitly clicks ACCEPT.
"""

import os
import re
from typing import Dict, Any, List, Optional
from apps.mapping.canonical import get_canonical_model, CanonicalFieldType
from apps.mapping.models import RuleType, AIConfirmationStatus


def _clean_token(s: str) -> str:
    """Removes underscores, hyphens, spaces, and lowers string for fuzzy comparison."""
    return re.sub(r"[_\-\s]+", "", str(s).lower())


def suggest_mappings_for_fields(
    source_columns: List[str],
    target_entity: str,
    sample_values: Optional[Dict[str, List[Any]]] = None,
    inferred_types: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Analyzes source column names, data samples, and inferred types against
    the target canonical entity definition to propose mapping rules.

    Returns:
    [
        {
            "source_field": str,
            "suggested_target_field": str,
            "confidence": float,
            "suggested_rule_type": str,
            "transformation_config": dict,
            "reason": str,
            "ai_status": "PENDING_CONFIRMATION",
        }
    ]
    """
    model_def = get_canonical_model(target_entity)
    if not model_def:
        return []

    sample_values = sample_values or {}
    inferred_types = inferred_types or {}
    suggestions = []
    assigned_targets = set()

    for col in source_columns:
        col_clean = _clean_token(col)
        best_match: Optional[str] = None
        highest_confidence: float = 0.0
        match_reason: str = ""
        suggested_rule_type = RuleType.FIELD_MAPPING
        suggested_config: Dict[str, Any] = {}

        # 1. Exact or alias match against canonical fields
        for fname, fdef in model_def.fields.items():
            fname_clean = _clean_token(fname)
            aliases_clean = [_clean_token(a) for a in fdef.aliases]

            # Exact field name match
            if col_clean == fname_clean:
                confidence = 0.98
                reason = f"Exact field name match with canonical attribute '{fname}'."
            # Exact alias match
            elif col_clean in aliases_clean:
                confidence = 0.95
                reason = f"Source column '{col}' directly matches recognized canonical alias for '{fname}'."
            # Substring match
            elif any(a in col_clean or col_clean in a for a in aliases_clean if len(a) > 2):
                confidence = 0.82
                reason = f"Source column '{col}' closely aligns with canonical alias pattern for '{fname}'."
            elif fname_clean in col_clean or col_clean in fname_clean:
                confidence = 0.80
                reason = f"Partial name similarity with canonical attribute '{fname}'."
            else:
                confidence = 0.0
                reason = ""

            # Check sample values to boost or adjust confidence
            samples = sample_values.get(col, [])
            inferred = inferred_types.get(col, "STRING")

            if confidence > 0.6:
                # Type alignment adjustments
                if fdef.field_type == CanonicalFieldType.DECIMAL:
                    suggested_rule_type = RuleType.TYPE_CONVERSION
                    suggested_config = {"target_type": "DECIMAL"}
                    if any(isinstance(s, str) and any(c in s for c in ("đ", "VND", "$", ",")) for s in samples):
                        confidence = min(1.0, confidence + 0.04)
                        reason += " Sample values contain monetary formatting."

                elif fdef.field_type in (CanonicalFieldType.DATE, CanonicalFieldType.DATETIME):
                    suggested_rule_type = RuleType.TYPE_CONVERSION
                    suggested_config = {"target_type": fdef.field_type}
                    if any(isinstance(s, str) and any(sep in s for sep in ("/", "-", "T")) for s in samples):
                        confidence = min(1.0, confidence + 0.04)
                        reason += " Sample values contain calendar timestamp format."

                elif fdef.field_type == CanonicalFieldType.BOOLEAN:
                    suggested_rule_type = RuleType.TYPE_CONVERSION
                    suggested_config = {"target_type": "BOOLEAN"}

                elif fdef.field_type == CanonicalFieldType.ENUM:
                    suggested_rule_type = RuleType.VALUE_MAPPING
                    suggested_config = {"value_map": {}, "default": fdef.default}

                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = fname
                    match_reason = reason

        if best_match and highest_confidence >= 0.70:
            suggestions.append({
                "source_field": col,
                "suggested_target_field": best_match,
                "confidence": round(highest_confidence, 2),
                "suggested_rule_type": suggested_rule_type,
                "transformation_config": suggested_config,
                "reason": match_reason,
                "ai_status": AIConfirmationStatus.PENDING,
            })
            assigned_targets.add(best_match)

    return suggestions
