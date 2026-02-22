from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import cast

# local import to avoid circular dependency in small package
from model import Recipe

# reasonable precision for recipe cost calculations
getcontext().prec = 28

MONEY_QUANT = Decimal("0.01")


def _quantize_money(d: Decimal) -> Decimal:
    return d.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_total_cost(recipe: Recipe) -> Decimal:
    """Return total cost (Decimal) rounded to 2 decimal places."""
    total = Decimal("0")
    for ing in recipe.ingredients:
        q = Decimal(ing.quantity)
        p = Decimal(ing.price_per_unit)
        total += q * p
    return _quantize_money(total)


def calculate_cost_per_serving(recipe: Recipe) -> Decimal:
    """Return cost per serving (Decimal, rounded). Raises ValueError for invalid servings."""
    if recipe.servings <= 0:
        raise ValueError("Servings must be >= 1")
    total = calculate_total_cost(recipe)
    per = total / Decimal(recipe.servings)
    return _quantize_money(per)
