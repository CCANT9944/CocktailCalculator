# Cocktail Cost Calculator

This workspace contains a PySide6-based dialog for entering cocktail recipes
and computing ingredient costs. The dialog supports live price-per-unit
calculations, Excel-like navigation, and keyboard shortcuts. Projects include
manually maintained tests (pytest + pytest-qt) verifying UI behavior.

## Features

- Dynamic ingredient table with formula-based price-per-unit
- Enter key navigation and auto-add row behavior
- Price/unit column read-only and formatted with two decimals
- Live capitalization of names
- PPU sum display at bottom
- JSON and database persistence examples in comments

## Usage

Activate the `test000/venv` virtual environment and run the dialog with:

```bash
python -m test000.00  # or import CocktailCostDialog from cost_dialog
```

Run tests with `pytest` from the workspace root.

## Dependencies

See `requirements.txt` for Python packages required to run and test the
application.
