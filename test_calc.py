from decimal import Decimal

from model import Ingredient, Recipe
from calc import calculate_total_cost, calculate_cost_per_serving


def test_calculate_total_and_per_serving():
    ingredients = [
        Ingredient(name="Gin", quantity=Decimal("50"), unit="ml", price_per_unit=Decimal("0.02")),
        Ingredient(name="Tonic", quantity=Decimal("150"), unit="ml", price_per_unit=Decimal("0.001")),
    ]
    recipe = Recipe(name="G&T", ingredients=ingredients, servings=2)

    total = calculate_total_cost(recipe)
    # 50*0.02 = 1.00 ; 150*0.001 = 0.15 ; total = 1.15
    assert total == Decimal("1.15")

    per = calculate_cost_per_serving(recipe)
    # 1.15 / 2 = 0.575 -> rounded to 0.58
    assert per == Decimal("0.58")


def test_empty_ingredients_total_zero():
    recipe = Recipe(name="Empty", ingredients=[], servings=1)
    assert calculate_total_cost(recipe) == Decimal("0.00")


def test_invalid_servings_raises():
    recipe = Recipe(name="Bad", ingredients=[], servings=0)
    try:
        calculate_cost_per_serving(recipe)
        assert False, "expected ValueError"
    except ValueError:
        pass
