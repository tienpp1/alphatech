"""
Safe Expression Evaluator using Python AST (Abstract Syntax Tree).
Enforces zero code execution vulnerabilities: strictly bans eval(), exec(),
function calls, attributes, and imports. Whitelists only safe mathematical
operators (+, -, *, /) and string concatenation.
"""

import ast
import operator
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Union


class SecurityValidationError(ValueError):
    """Raised when an expression contains forbidden or dangerous AST constructs."""
    pass


class FormulaEvaluationError(ValueError):
    """Raised when a mathematical formula fails to compute at runtime (e.g. division by zero)."""
    pass


# Whitelisted binary operations
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

# Whitelisted unary operations
_SAFE_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _validate_ast_safety(node: ast.AST):
    """
    Recursively inspects the AST node to ensure it contains ONLY whitelisted safe constructs.
    Explicitly rejects any calls, attribute lookups, subscripts, lambdas, or imports.
    """
    for child in ast.walk(node):
        # Whitelisted node types
        if isinstance(
            child,
            (
                ast.Expression,
                ast.BinOp,
                ast.UnaryOp,
                ast.Constant,
                ast.Name,
                ast.Load,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.UAdd,
                ast.USub,
            ),
        ):
            if isinstance(child, ast.BinOp) and type(child.op) not in _SAFE_OPERATORS:
                raise SecurityValidationError(
                    f"Forbidden operator '{type(child.op).__name__}'. Only +, -, *, / are allowed."
                )
            if isinstance(child, ast.UnaryOp) and type(child.op) not in _SAFE_UNARY_OPERATORS:
                raise SecurityValidationError(
                    f"Forbidden unary operator '{type(child.op).__name__}'."
                )
            continue

        # Backward compatibility for Python < 3.8 (Num, Str)
        if hasattr(ast, "Num") and isinstance(child, getattr(ast, "Num")):
            continue
        if hasattr(ast, "Str") and isinstance(child, getattr(ast, "Str")):
            continue

        # All other AST nodes are strictly prohibited
        raise SecurityValidationError(
            f"Security Violation: Prohibited AST construct '{type(child).__name__}' in formula. "
            "Arbitrary execution, function calls, attributes, and imports are strictly forbidden."
        )


def _eval_node(node: ast.AST, variables: Dict[str, Any]) -> Any:
    """
    Evaluates a verified safe AST node using provided variables dictionary.
    """
    if isinstance(node, ast.Constant):
        return node.value

    # Backward compatibility
    if hasattr(ast, "Num") and isinstance(node, getattr(ast, "Num")):
        return node.n
    if hasattr(ast, "Str") and isinstance(node, getattr(ast, "Str")):
        return node.s

    if isinstance(node, ast.Name):
        var_name = node.id
        if var_name not in variables:
            raise FormulaEvaluationError(f"Variable '{var_name}' not found in record payload.")
        raw_val = variables[var_name]
        if raw_val is None:
            return None
        # Attempt to convert to Decimal if numeric string
        if isinstance(raw_val, (int, float)):
            return Decimal(str(raw_val))
        if isinstance(raw_val, str):
            clean = raw_val.strip().replace(",", "")
            try:
                return Decimal(clean)
            except InvalidOperation:
                return raw_val
        return raw_val

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, variables)
        if operand is None:
            return None
        op_func = _SAFE_UNARY_OPERATORS.get(type(node.op))
        if op_func is None:
            raise SecurityValidationError(f"Unsupported unary operator '{type(node.op).__name__}'.")
        return op_func(operand)

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)

        if left is None or right is None:
            return None

        # String concatenation
        if isinstance(left, str) or isinstance(right, str):
            if isinstance(node.op, ast.Add):
                return str(left) + str(right)
            raise FormulaEvaluationError(f"Cannot apply operator '{type(node.op).__name__}' to strings.")

        # Numeric operation
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise SecurityValidationError(f"Unsupported operator '{type(node.op).__name__}'.")

        # Convert float to Decimal for high precision
        if isinstance(left, (int, float)) and not isinstance(left, Decimal):
            left = Decimal(str(left))
        if isinstance(right, (int, float)) and not isinstance(right, Decimal):
            right = Decimal(str(right))

        if isinstance(node.op, ast.Div) and right == 0:
            raise FormulaEvaluationError("Division by zero in formula evaluation.")

        try:
            return op_func(left, right)
        except Exception as e:
            raise FormulaEvaluationError(f"Formula evaluation error: {str(e)}")

    raise SecurityValidationError(f"Unexpected AST node: {type(node).__name__}")


def evaluate_safe_expression(
    expression: str,
    record: Dict[str, Any],
) -> Any:
    """
    Safely parses and evaluates a mathematical or concatenation expression against a record dict.
    Strictly forbids eval(), exec(), and arbitrary python execution.

    Example expressions:
      - "unit_price * quantity - discount"
      - "last_name + ' ' + first_name"
      - "(duration_minutes / 60) * hourly_rate"
    """
    if not expression or not expression.strip():
        raise FormulaEvaluationError("Expression cannot be empty.")

    clean_expr = expression.strip()

    try:
        parsed_tree = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise FormulaEvaluationError(f"Formula syntax error: {str(e)}")

    # Strict AST safety validation
    _validate_ast_safety(parsed_tree)

    # Compute value
    result = _eval_node(parsed_tree.body, record)
    return result
