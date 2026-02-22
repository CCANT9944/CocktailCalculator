from decimal import Decimal

import pytest

from model import Ingredient, Recipe


def test_ingredient_validation():
    with pytest.raises(ValueError):
        Ingredient(name="", quantity=Decimal("1"), unit="ml", price_per_unit=Decimal("0.5"))
    with pytest.raises(ValueError):
        Ingredient(name="Sugar", quantity=Decimal("0"), unit="g", price_per_unit=Decimal("0.1"))
    with pytest.raises(ValueError):
        Ingredient(name="Sugar", quantity=Decimal("1"), unit="g", price_per_unit=Decimal("-1"))


def test_recipe_validation_and_json_roundtrip(tmp_path):
    ings = [Ingredient(name="A", quantity=Decimal("1"), unit="u", price_per_unit=Decimal("0.5"))]
    r = Recipe(name="R", ingredients=ings, servings=1)
    r.validate()

    p = tmp_path / "r.json"
    r.save_to_json(str(p))
    loaded = Recipe.load_from_json(str(p))
    assert loaded.name == r.name
    assert loaded.servings == r.servings
    assert len(loaded.ingredients) == 1
    assert loaded.ingredients[0].name == "A"
