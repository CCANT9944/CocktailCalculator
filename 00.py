"""Entry point for the Cocktail Cost Calculator (PySide6)

Run: python 00.py
"""

from PySide6.QtWidgets import QApplication
from cost_dialog import CocktailCostDialog


def main() -> None:
    import sys

    app = QApplication(sys.argv)
    dlg = CocktailCostDialog()
    if dlg.exec():
        recipe = dlg.get_recipe()
        # simple stdout summary for now
        print("Recipe:", recipe.to_dict())
    else:
        print("Cancelled")


if __name__ == "__main__":
    main()
