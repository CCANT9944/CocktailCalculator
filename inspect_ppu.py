from cost_dialog import CocktailCostDialog
from PySide6.QtWidgets import QApplication

app = QApplication([])
dlg = CocktailCostDialog()
# ensure second row exists
qty1 = dlg.table.cellWidget(1, dlg.COL_QTY)
unit1 = dlg.table.cellWidget(1, dlg.COL_UNIT)
row_price1 = dlg.table.cellWidget(1, dlg.COL_ROW_PRICE)
qty1.setText('700')
unit1.setText('25')
row_price1.setText('18')
ppu1 = dlg.table.cellWidget(1, dlg.COL_PRICE_PER_UNIT)
print('ppu1', repr(ppu1.text()))
QApplication.processEvents()
print('after', repr(ppu1.text()))
