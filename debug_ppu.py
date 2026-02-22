from cost_dialog import CocktailCostDialog
from PySide6.QtWidgets import QApplication

# instantiate dialog and create sample rows
app = QApplication([])
dlg = CocktailCostDialog()
# row 0: set price and qty/unit to produce 1.8
dlg.table.cellWidget(0, dlg.COL_QTY).setText("700")
dlg.table.cellWidget(0, dlg.COL_UNIT).setText("60")
dlg.table.cellWidget(0, dlg.COL_ROW_PRICE).setText("21")
# trigger update
QApplication.processEvents()
print("row0 ppu", repr(dlg.table.cellWidget(0, dlg.COL_PRICE_PER_UNIT).text()))

# add row and set values matching screenshot
dlg.add_row()
dlg.table.cellWidget(1, dlg.COL_QTY).setText("700")
dlg.table.cellWidget(1, dlg.COL_UNIT).setText("25")
dlg.table.cellWidget(1, dlg.COL_ROW_PRICE).setText("18")
QApplication.processEvents()
print("row1 ppu", repr(dlg.table.cellWidget(1, dlg.COL_PRICE_PER_UNIT).text()))

# new row auto added on Enter flow expand
# simulate pressing enter in spec field
idx = dlg.table.cellWidget(1, dlg.COL_UNIT)
idx.setText("25")
# normally Enter triggers new row but we can just call add_row(copy_ppu=False)
dlg.add_row(copy_ppu=False)
print("row2 ppu", repr(dlg.table.cellWidget(2, dlg.COL_PRICE_PER_UNIT).text()))

# print formatting of some decimals
from decimal import Decimal
for val in [Decimal('0.2'), Decimal('0.64'), Decimal('1.8'), Decimal('0.200000'), Decimal('0.642857')]:
    print(val, '->', dlg._format_ppu(val))
