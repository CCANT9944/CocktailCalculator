from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any
import json


@dataclass
class Ingredient:
    name: str
    quantity: Decimal
    unit: str
    price_per_unit: Decimal

    def __post_init__(self):
        # normalize numeric types to Decimal
        if isinstance(self.quantity, (int, float, str)):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.price_per_unit, (int, float, str)):
            self.price_per_unit = Decimal(str(self.price_per_unit))

        if not self.name or not self.name.strip():
            raise ValueError("Ingredient name must be non-empty")
        if self.quantity <= 0:
            raise ValueError("Ingredient quantity must be > 0")
        if self.price_per_unit < 0:
            raise ValueError("Ingredient price_per_unit must be >= 0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "quantity": str(self.quantity),
            "unit": self.unit,
            "price_per_unit": str(self.price_per_unit),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Ingredient":
        return Ingredient(
            name=d["name"],
            quantity=Decimal(str(d["quantity"])),
            unit=d.get("unit", ""),
            price_per_unit=Decimal(str(d["price_per_unit"])),
        )


@dataclass
class Recipe:
    name: str
    ingredients: List[Ingredient] = field(default_factory=list)
    servings: int = 1

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Recipe name is required")
        if self.servings < 1:
            raise ValueError("Servings must be >= 1")
        for ing in self.ingredients:
            if not isinstance(ing, Ingredient):
                raise ValueError("All ingredients must be Ingredient instances")
            # Ingredient.__post_init__ already validates individual fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "servings": int(self.servings),
            "ingredients": [i.to_dict() for i in self.ingredients],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Recipe":
        ings = [Ingredient.from_dict(i) for i in d.get("ingredients", [])]
        return Recipe(name=d.get("name", ""), ingredients=ings, servings=int(d.get("servings", 1)))

    def save_to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load_from_json(path: str) -> "Recipe":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Recipe.from_dict(data)
