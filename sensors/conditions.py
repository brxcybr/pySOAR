"""Safe evaluation of metric threshold expressions (no eval)."""

from __future__ import annotations

import operator

_OPERATORS = (
    ('>=', operator.ge),
    ('<=', operator.le),
    ('==', operator.eq),
    ('!=', operator.ne),
    ('>', operator.gt),
    ('<', operator.lt),
)


def _evaluate_clause(clause: str, metrics: dict) -> bool:
    clause = clause.strip()
    for symbol, func in _OPERATORS:
        if symbol in clause:
            left, _, right = clause.partition(symbol)
            name = left.strip()
            try:
                expected = float(right.strip())
            except ValueError:
                return False
            actual = metrics.get(name)
            if actual is None:
                return False
            try:
                return func(float(actual), expected)
            except (TypeError, ValueError):
                return False
    return False


def evaluate_metric_expression(expression: str, metrics: dict) -> bool:
    """Evaluate expressions like 'beacon_score >= 0.8 and duration_hours > 2'.

    Supports comparison clauses joined by 'and'/'or' ('and' binds tighter).
    Unknown metrics or malformed clauses evaluate to False rather than raising.
    """
    if not expression or not expression.strip():
        return False
    return any(
        all(_evaluate_clause(clause, metrics) for clause in or_branch.split(' and '))
        for or_branch in expression.split(' or ')
    )
