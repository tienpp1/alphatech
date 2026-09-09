"""
Transformation Pipeline Coordinator for Data Mapping.
Applies active MappingRules sequentially to raw external record payloads.
"""

from typing import Dict, Any, List, Tuple, Sequence, Optional
from apps.mapping.models import MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.engine.converters import (
    to_string,
    to_decimal,
    to_integer,
    to_float,
    to_boolean,
    to_date,
    to_datetime,
    to_list,
)
from apps.mapping.engine.value_mappers import apply_value_mapping
from apps.mapping.engine.safe_evaluator import (
    evaluate_safe_expression,
    SecurityValidationError,
    FormulaEvaluationError,
)
from apps.mapping.canonical import get_canonical_model, CanonicalFieldType


def transform_field_value(
    raw_val: Any,
    rule: MappingRule,
    target_field_type: Optional[str] = None,
    raw_record: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, Optional[str]]:
    """
    Applies the specific transformation rule logic to raw_val.
    Returns (transformed_val, error_message).
    """
    cfg = rule.transformation_config or {}

    try:
        if rule.rule_type == RuleType.FIELD_MAPPING:
            # Direct mapping - auto-cast to string if null-stripped
            if raw_val is None:
                return None, None
            return raw_val, None

        elif rule.rule_type == RuleType.TYPE_CONVERSION:
            target_type = (cfg.get("target_type") or target_field_type or "STRING").upper()
            custom_format = cfg.get("format")

            if target_type == CanonicalFieldType.DECIMAL:
                return to_decimal(raw_val, default=cfg.get("default")), None
            elif target_type == CanonicalFieldType.INTEGER:
                return to_integer(raw_val, default=cfg.get("default")), None
            elif target_type == CanonicalFieldType.FLOAT:
                return to_float(raw_val, default=cfg.get("default")), None
            elif target_type == CanonicalFieldType.BOOLEAN:
                return to_boolean(raw_val, default=cfg.get("default")), None
            elif target_type == CanonicalFieldType.DATE:
                return to_date(raw_val, custom_format=custom_format), None
            elif target_type == CanonicalFieldType.DATETIME:
                return to_datetime(raw_val, custom_format=custom_format), None
            elif target_type == CanonicalFieldType.LIST:
                return to_list(raw_val), None
            else:
                return to_string(raw_val), None

        elif rule.rule_type == RuleType.VALUE_MAPPING:
            v_map = cfg.get("value_map", {})
            default_val = cfg.get("default")
            res = apply_value_mapping(raw_val, v_map, default_val=default_val)
            return res, None

        elif rule.rule_type == RuleType.BUSINESS_FORMULA:
            expr = cfg.get("expression") or rule.source_field
            if not expr:
                return None, "Formula expression is missing."
            record_ctx = raw_record or {}
            computed = evaluate_safe_expression(expr, record_ctx)
            return computed, None

        elif rule.rule_type == RuleType.AI_ASSISTED_MAPPING:
            # AI rule requires human confirmation
            if rule.ai_status != AIConfirmationStatus.ACCEPTED:
                return None, f"AI suggestion '{rule.target_field}' requires human confirmation before application."

            # If accepted, check if it specifies a type conversion or simple field copy
            sub_type = cfg.get("type_conversion")
            if sub_type:
                temp_rule = MappingRule(
                    rule_type=RuleType.TYPE_CONVERSION,
                    transformation_config={"target_type": sub_type, "format": cfg.get("format")},
                )
                return transform_field_value(raw_val, temp_rule, target_field_type, raw_record)
            return raw_val, None

        return raw_val, None

    except (SecurityValidationError, FormulaEvaluationError, ValueError, TypeError) as e:
        return None, str(e)


def transform_single_record(
    raw_data: Dict[str, Any],
    rules: Sequence[MappingRule],
    target_entity: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Transforms an external record dictionary using a sequence of MappingRules into
    a Canonical Standard Data Model dictionary.

    Returns:
      (canonical_data_dict, errors_list)
      where errors_list contains: [{"target_field": str, "source_field": str, "error": str}]
    """
    canonical_data: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []

    model_def = get_canonical_model(target_entity)

    # Sort rules by order
    sorted_rules = sorted([r for r in rules if r.is_active], key=lambda r: (r.order, r.id or 0))

    for rule in sorted_rules:
        # Check human confirmation gate for AI rules
        if rule.rule_type == RuleType.AI_ASSISTED_MAPPING and rule.ai_status != AIConfirmationStatus.ACCEPTED:
            continue

        target_field = rule.target_field
        target_fdef = model_def.get_field(target_field) if model_def else None
        target_type = target_fdef.field_type if target_fdef else None

        # Determine source value
        if rule.rule_type == RuleType.BUSINESS_FORMULA:
            raw_val = None
        else:
            raw_val = raw_data.get(rule.source_field)

        transformed_val, err = transform_field_value(
            raw_val=raw_val,
            rule=rule,
            target_field_type=target_type,
            raw_record=raw_data,
        )

        if err:
            errors.append({
                "target_field": target_field,
                "source_field": rule.source_field,
                "error": err,
                "rule_type": rule.rule_type,
            })
        else:
            canonical_data[target_field] = transformed_val

    return canonical_data, errors
