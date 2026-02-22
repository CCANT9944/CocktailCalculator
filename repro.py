from PySide6.QtWidgets import QApplication
from cost_dialog import CocktailCostDialog
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

app=QApplication([])
dlg=CocktailCostDialog()
dlg.name_edit.setText('TestCocktail')
name_w=dlg.table.cellWidget(0, dlg.COL_NAME)
qty_w=dlg.table.cellWidget(0, dlg.COL_QTY)
unit_w=dlg.table.cellWidget(0, dlg.COL_UNIT)
price_w=dlg.table.cellWidget(0, dlg.COL_PRICE_PER_UNIT)
name_w.setText('Gin')
qty_w.setText('50')
unit_w.setText('ml')
price_w.setText('0.02')
dlg.add_row()
name_w=dlg.table.cellWidget(1, dlg.COL_NAME)
qty_w=dlg.table.cellWidget(1, dlg.COL_QTY)
unit_w=dlg.table.cellWidget(1, dlg.COL_UNIT)
price_w=dlg.table.cellWidget(1, dlg.COL_PRICE_PER_UNIT)
name_w.setText('Tonic')
qty_w.setText('150')
unit_w.setText('ml')
price_w.setText('0.001')
# total label removed
print('debug', dlg.debug_label.text())
print('recipe', dlg.get_recipe())
