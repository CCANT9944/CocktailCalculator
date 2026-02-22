from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QApplication,
    QAbstractItemDelegate,
)

from model import Ingredient, Recipe
from calc import calculate_total_cost, calculate_cost_per_serving



class CocktailCostDialog(QDialog):
    """Modal dialog to collect a recipe and compute costs.

    Minimal, testable implementation using QTableWidget for ingredient rows.
    """

    COL_NAME = 0
    COL_ROW_PRICE = 1        # user-entered row price (editable)
    COL_QTY = 2
    COL_UNIT = 3
    COL_PRICE_PER_UNIT = 4   # price per unit (editable)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Cocktail Cost Calculator")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        # cocktail name
        hl_top = QHBoxLayout()
        hl_top.addWidget(QLabel("Cocktail name:"))
        self.name_edit = QLineEdit()
        # auto-capitalize first letter of cocktail name
        self.name_edit.textChanged.connect(lambda _t, w=self.name_edit: self._capitalize_first(w))
        hl_top.addWidget(self.name_edit)
        layout.addLayout(hl_top)

        # ingredients table (now 5 columns: Ingredient Name, Price (£), Product Quantity, Unit Spec(ml), Price / unit)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Ingredient Name", "Price (£)", "Product Quantity", "Unit Spec(ml)", "Price / unit"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # add / remove buttons
        hr = QHBoxLayout()
        self.add_btn = QPushButton("+ Add ingredient")
        # clicked signal passes a boolean (checked state) which would be
        # interpreted as the `name` parameter by add_row, so swallow it here.
        self.add_btn.clicked.connect(lambda checked=None: self.add_row())
        hr.addWidget(self.add_btn)
        self.remove_btn = QPushButton("- Remove selected")
        # similarly ignore boolean parameter
        self.remove_btn.clicked.connect(lambda checked=None: self.remove_selected_row())
        hr.addWidget(self.remove_btn)
        hr.addStretch()
        layout.addLayout(hr)

        # summary (without servings)
        hr2 = QHBoxLayout()
        # (only PPU sum indicator remains)
        self.ppu_sum_label = QLabel("PPU sum: 0.00")
        # make the label stand out
        font = self.ppu_sum_label.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.ppu_sum_label.setFont(font)
        hr2.addWidget(self.ppu_sum_label, alignment=Qt.AlignCenter)
        # center the entire summary row beneath the table
        hr2.setAlignment(Qt.AlignCenter)
        layout.addLayout(hr2)
 
        # action buttons
        br = QHBoxLayout()
        br.addStretch()
        self.ok_btn = QPushButton("OK")
        # commit edits when OK is pressed as well
        self.ok_btn.pressed.connect(self._commit_table_editors)
        self.ok_btn.clicked.connect(self.accept)
        br.addWidget(self.ok_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        br.addWidget(self.cancel_btn)
        layout.addLayout(br)

        self.setLayout(layout)

        # make window larger so additional table columns are visible
        # and ensure the table has enough minimum width for more columns
        self.resize(900, 520)
        self.setMinimumSize(760, 420)
        self.table.setMinimumWidth(840)

        # adjust column widths so `Price / unit` is narrower (room for future columns)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_ROW_PRICE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_QTY, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_UNIT, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_PRICE_PER_UNIT, QHeaderView.Fixed)
        # make Price / unit purposely smaller
        self.table.setColumnWidth(self.COL_PRICE_PER_UNIT, 100)

        # start with one empty row
        self.add_row()

    def add_row(self, name: str = "", qty: str = "", unit: str = "", price: str = "", *, copy_ppu: bool = True) -> None:
        """Append a new empty ingredient row.

        If ``copy_ppu`` is True (the default) the new row's price-per-unit field
        will be pre-filled from the previous row, mimicking the behaviour of the
        explicit +Add button. When a row is created via Enter key in the unit
        column we set ``copy_ppu`` to False so that the value is only momentary
        until the user types something.
        """
        row = self.table.rowCount()

        # capture active editor text for the previous row's Price (£) cell if present
        active_editor_row_price_text = None
        if row > 0:
            fw = self.table.focusWidget() or QApplication.focusWidget()
            if isinstance(fw, QLineEdit):
                try:
                    idx = self.table.indexAt(fw.mapTo(self.table.viewport(), QPoint(0, 0)))
                    if idx.isValid() and idx.row() == row - 1 and idx.column() == self.COL_ROW_PRICE:
                        active_editor_row_price_text = fw.text().strip()
                except Exception:
                    active_editor_row_price_text = None

                # fallback: if the current table item is the Price cell for previous
                # row, use the focused editor's text directly (more robust in tests)
                if active_editor_row_price_text is None:
                    curr = self.table.currentItem()
                    if curr is not None and curr.row() == row - 1 and curr.column() == self.COL_ROW_PRICE:
                        try:
                            active_editor_row_price_text = fw.text().strip()
                        except Exception:
                            active_editor_row_price_text = None
        # expose the last active-editor text for diagnostics/tests
        try:
            self._last_active_editor_text = active_editor_row_price_text
        except Exception:
            self._last_active_editor_text = None

        # prepare default price per unit for the new row if none provided
        if copy_ppu and row > 0 and not price:
            # commit any active editor so that uncommitted text is not lost
            self._commit_table_editors()

            # attempt to compute ppu from the previous row's entered price
            ppu_copy = None
            try:
                # check for an active editor value first (previous row's Price £)
                rp_text = None
                if active_editor_row_price_text:
                    rp_text = active_editor_row_price_text
                else:
                    prev_price_w = self.table.cellWidget(row - 1, self.COL_ROW_PRICE)
                    if prev_price_w is not None:
                        rp_text = prev_price_w.text().strip()
                if rp_text:
                    rp = Decimal(rp_text)
                    qty_w = self.table.cellWidget(row - 1, self.COL_QTY)
                    unit_w = self.table.cellWidget(row - 1, self.COL_UNIT)
                    qty_val = Decimal(qty_w.text() or "0")
                    unit_spec_val = Decimal(unit_w.text() or "0")
                    if qty_val > 0 and unit_spec_val > 0:
                        ppu_copy = (rp * (unit_spec_val / qty_val)).quantize(Decimal("0.000001"))
                        # also update the displayed PPU in the previous row immediately
                        try:
                            prev_ppu_w = self.table.cellWidget(row - 1, self.COL_PRICE_PER_UNIT)
                            if prev_ppu_w is not None:
                                prev_ppu_w.setText(self._format_ppu(ppu_copy))
                        except Exception:
                            pass
            except Exception:
                ppu_copy = None

            if ppu_copy is not None:
                price = format(ppu_copy.normalize(), 'f')
            else:
                # fallback: if previous PPU widget already had a value, copy it
                prev_ppu_w = self.table.cellWidget(row - 1, self.COL_PRICE_PER_UNIT)
                if prev_ppu_w and prev_ppu_w.text().strip():
                    price = prev_ppu_w.text()

        self.table.insertRow(row)

        name_edit = QLineEdit(name)
        name_edit.setObjectName(f"name-{row}")
        # auto-capitalize ingredient name
        name_edit.textChanged.connect(lambda _t, w=name_edit: self._capitalize_first(w))
        # pressing Enter jumps to next logical field
        name_edit.returnPressed.connect(lambda r=row, c=self.COL_NAME: self._focus_next(r, c))
        name_edit.installEventFilter(self)
        self.table.setCellWidget(row, self.COL_NAME, name_edit)
        row_price_edit = QLineEdit("")
        row_price_edit.setObjectName(f"row-price-{row}")
        row_price_edit.setValidator(QDoubleValidator(0.0, 1e9, 6))
        row_price_edit.returnPressed.connect(lambda r=row, c=self.COL_ROW_PRICE: self._focus_next(r, c))
        row_price_edit.installEventFilter(self)
        self.table.setCellWidget(row, self.COL_ROW_PRICE, row_price_edit)
        qty_edit = QLineEdit(qty)
        qty_edit.setObjectName(f"qty-{row}")
        # allow decimal input
        qty_edit.setValidator(QDoubleValidator(0.0, 1e9, 6))
        qty_edit.returnPressed.connect(lambda r=row, c=self.COL_QTY: self._focus_next(r, c))
        qty_edit.installEventFilter(self)
        self.table.setCellWidget(row, self.COL_QTY, qty_edit)
        unit_edit = QLineEdit(unit)
        unit_edit.setObjectName(f"unit-{row}")
        unit_edit.setValidator(QDoubleValidator(0.0, 1e9, 6))
        unit_edit.returnPressed.connect(lambda r=row, c=self.COL_UNIT: self._focus_next(r, c))
        unit_edit.installEventFilter(self)
        self.table.setCellWidget(row, self.COL_UNIT, unit_edit)

        # Price per unit (read-only, may be auto-filled or copied)
        price_edit = QLineEdit(price)
        price_edit.setObjectName(f"price-{row}")
        price_edit.setValidator(QDoubleValidator(0.0, 1e9, 6))
        price_edit.setReadOnly(True)
        # users should not be able to edit or even focus this column
        price_edit.setFocusPolicy(Qt.NoFocus)
        price_edit.installEventFilter(self)
        self.table.setCellWidget(row, self.COL_PRICE_PER_UNIT, price_edit)

        # connect edits to auto-update Price / unit when relevant fields change
        row_price_edit.textChanged.connect(self._update_all_price_per_unit)
        row_price_edit.editingFinished.connect(self._update_all_price_per_unit)
        qty_edit.textChanged.connect(self._update_all_price_per_unit)
        qty_edit.editingFinished.connect(self._update_all_price_per_unit)
        unit_edit.textChanged.connect(self._update_all_price_per_unit)
        unit_edit.editingFinished.connect(self._update_all_price_per_unit)
        price_edit.textChanged.connect(lambda _text, r=row: (self._on_price_per_unit_edited(r), self._update_ppu_sum()))

        # make the new row visible and focus the Ingredient Name so typing starts immediately
        self.table.setCurrentCell(row, self.COL_NAME)
        # bring the dialog to the front and focus the name editor so typing starts immediately
        try:
            self.activateWindow()
            self.raise_()
            name_edit.setFocus(Qt.TabFocusReason)
            QApplication.processEvents()
        except Exception:
            # best-effort — ignore if running headless or focus cannot be set
            name_edit.setFocus()

        # ensure row is visible
        self.table.scrollToBottom()
        # recalc PPU sum in case a value was copied into the new row
        self._update_ppu_sum()

    def remove_selected_row(self) -> None:
        selected = set(idx.row() for idx in self.table.selectedIndexes())
        for r in sorted(selected, reverse=True):
            self.table.removeRow(r)
        self._update_all_price_per_unit()

    def eventFilter(self, obj, event) -> bool:
        # intercept Enter/Return on any QLineEdit in the table and move focus
        if event.type() == QEvent.KeyPress and isinstance(obj, QLineEdit):
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                idx = self.table.indexAt(obj.mapTo(self.table.viewport(), QPoint(0, 0)))
                if idx.isValid():
                    # when hitting Enter in the unit (spec) column of the last
                    # row, automatically append a fresh row before moving focus.
                    if idx.column() == self.COL_UNIT and idx.row() == self.table.rowCount() - 1:
                        # row created by Enter should not permanently copy PPU
                        self.add_row(copy_ppu=False)
                    self._focus_next(idx.row(), idx.column())
                    return True
        return super().eventFilter(obj, event)

    def _focus_next(self, row: int, col: int) -> None:

        # move focus to the next cell widget in logical order
        next_col = col + 1
        next_row = row
        # after Unit moves to name of next row
        if next_col > self.COL_UNIT:
            next_col = self.COL_NAME
            next_row = row + 1
        if next_row >= self.table.rowCount():
            return
        w = self.table.cellWidget(next_row, next_col)
        if w is not None:
            w.setFocus()

        # (no longer commit editors; get_recipe deals with active editors)
        # ensure any itemChanged signals are processed just in case
        try:
            QApplication.processEvents()
        except Exception:
            pass

    def remove_selected_row(self) -> None:
        selected = set(idx.row() for idx in self.table.selectedIndexes())
        for r in sorted(selected, reverse=True):
            self.table.removeRow(r)
        self._update_all_price_per_unit()

    def _update_all_price_per_unit(self, *_args) -> None:
        for row in range(self.table.rowCount()):
            self._update_price_per_unit_for_row(row)
        # recalc and display PPU sum after every sweep
        self._update_ppu_sum()

    def _capitalize_first(self, widget: QLineEdit) -> None:
        """Ensure the first character of the widget text is uppercase."""
        text = widget.text()
        if text:
            new = text[0].upper() + text[1:]
            if new != text:
                widget.blockSignals(True)
                widget.setText(new)
                widget.blockSignals(False)

    def _set_debug(self, row: int, price: str, qty: str, spec: str, ppu: str) -> None:
        # show last computation in debug label
        self.debug_label.setText(f"r{row}: price={price} qty={qty} spec={spec} ppu={ppu}")

    def _parse_decimal(self, text: str) -> Decimal:
        try:
            return Decimal(text.strip())
        except (InvalidOperation, AttributeError):
            raise ValueError(f"Invalid numeric value: {text}")

    def _update_ppu_sum(self) -> None:
        """Compute the sum of all PPU entries and display it."""
        total = Decimal('0')
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, self.COL_PRICE_PER_UNIT)
            if w is not None and w.text().strip():
                try:
                    total += Decimal(w.text())
                except Exception:
                    pass
        # format with two decimals
        txt = self._format_ppu(total)
        try:
            self.ppu_sum_label.setText(f"PPU sum: {txt}")
        except Exception:
            pass

    def get_recipe(self) -> Recipe:
        name = self.name_edit.text().strip()
        # servings control removed; default to 1
        servings = 1
        ingredients = []

        # gather any open delegate editors so we can read uncommitted values
        active_editor_text = {}
        cell_widgets = set()
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                w = self.table.cellWidget(r, c)
                if w is not None:
                    cell_widgets.add(w)

        for editor in self.table.findChildren(QLineEdit):
            if editor in cell_widgets:
                continue
            if not editor.isVisible():
                continue
            idx = self.table.indexAt(editor.mapTo(self.table.viewport(), QPoint(0, 0)))
            if idx.isValid():
                active_editor_text[(idx.row(), idx.column())] = editor.text()

        for r in range(self.table.rowCount()):
            name_w: QLineEdit = self.table.cellWidget(r, self.COL_NAME)
            row_price_w: QLineEdit = self.table.cellWidget(r, self.COL_ROW_PRICE)
            qty_w: QLineEdit = self.table.cellWidget(r, self.COL_QTY)
            unit_w: QLineEdit = self.table.cellWidget(r, self.COL_UNIT)
            price_w: QLineEdit = self.table.cellWidget(r, self.COL_PRICE_PER_UNIT)

            if not name_w or not name_w.text().strip():
                continue  # skip empty rows
            ing_name = name_w.text().strip()
            qty = self._parse_decimal(qty_w.text() or "0")
            unit = (unit_w.text() or "").strip()

            # prefer user-entered total price (row price)
            row_price_val = None
            if row_price_w and row_price_w.text().strip():
                try:
                    row_price_val = Decimal(row_price_w.text().strip())
                except Exception:
                    row_price_val = None

            if row_price_val is not None and qty > 0:
                price = row_price_val / qty
            else:
                price = self._parse_decimal(price_w.text() or "0")

            ingredient = Ingredient(name=ing_name, quantity=qty, unit=unit, price_per_unit=price)
            ingredients.append(ingredient)

        recipe = Recipe(name=name, ingredients=ingredients, servings=servings)
        return recipe

    def validate(self) -> None:
        recipe = self.get_recipe()
        # basic validation — reuse model validation
        recipe.validate()

    def _on_price_per_unit_edited(self, row: int) -> None:
        """Called when the editable Price / unit QLineEdit is edited by the user.

        We treat manual edits as an explicit override — do nothing automatic here.
        """
        # no automatic action required; leave value as user-entered
        return

    def _format_ppu(self, value: Decimal) -> str:
        """Return a string for *value* rounded to two decimal places.

        The UI should always display exactly two digits after the decimal
        point (e.g. ``0.20`` rather than ``0.2`` or ``0.200000``).  We use
        ROUND_HALF_UP to mimic typical financial rounding.
        """
        try:
            out = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # format with 'f' to preserve trailing zeros
            return format(out, 'f')
        except Exception:
            # fallback to whatever string representation the Decimal gives
            return str(value)

    def _update_price_per_unit_for_row(self, r: int) -> None:
        """Compute Price / unit from: Price / (Product Quantity / UnitSpec)

        Formula: price_per_unit = row_price * (unit_spec / product_quantity)
        This runs when Price (row), Product Quantity or Unit Spec change.
        """
        try:
            # get widgets/items for the row
            row_price_w: QLineEdit = self.table.cellWidget(r, self.COL_ROW_PRICE)
            qty_w: QLineEdit = self.table.cellWidget(r, self.COL_QTY)
            unit_spec_w: QLineEdit = self.table.cellWidget(r, self.COL_UNIT)
            ppu_w: QLineEdit = self.table.cellWidget(r, self.COL_PRICE_PER_UNIT)

            row_price_text = (row_price_w.text().strip() if row_price_w and row_price_w.text() else "")

            qty_text = (qty_w.text().strip() if qty_w and qty_w.text() else "0")
            unit_spec_text = (unit_spec_w.text().strip() if unit_spec_w and unit_spec_w.text() else "0")

            # parse numbers
            try:
                row_price = Decimal(row_price_text) if row_price_text else None
            except Exception:
                row_price = None
            try:
                qty = Decimal(qty_text)
            except Exception:
                qty = Decimal("0")
            try:
                unit_spec = Decimal(unit_spec_text)
            except Exception:
                unit_spec = Decimal("0")

            if row_price is not None and qty > 0 and unit_spec > 0:
                # price_per_unit = row_price / (qty / unit_spec) == row_price * (unit_spec / qty)
                ppu = (row_price * (unit_spec / qty)).quantize(Decimal("0.000001"))
                # format for display with exactly two decimals
                ppu_str = self._format_ppu(ppu)
                if ppu_w is not None:
                    ppu_w.setText(ppu_str)
                # debug information no longer shown
                # (retain _set_debug for potential logging)
                self._set_debug(r, row_price_text, qty_text, unit_spec_text, ppu_str)
            elif row_price_text:
                # if user has started entering row price but required numeric
                # inputs are incomplete/invalid, clear ppu for this row.
                if ppu_w is not None:
                    ppu_w.setText("")
                self._set_debug(r, row_price_text, qty_text, unit_spec_text, "")
                if ppu_w is not None:
                    ppu_w.setText("")
        except Exception:
            # ignore errors in auto-update
            return

    def on_calculate(self) -> None:
        try:
            recipe = self.get_recipe()
            # ensure at least one ingredient
            if not recipe.ingredients:
                QMessageBox.warning(self, "Validation", "Add at least one ingredient")
                return
            recipe.validate()
            total = calculate_total_cost(recipe)
            per = calculate_cost_per_serving(recipe)

            # update per-row price column (quantity * price_per_unit) — but preserve user-entered values
            for r in range(self.table.rowCount()):
                name_w: QLineEdit = self.table.cellWidget(r, self.COL_NAME)
                if not name_w or not name_w.text().strip():
                    continue
                row_price_w: QLineEdit = self.table.cellWidget(r, self.COL_ROW_PRICE)
                qty_w: QLineEdit = self.table.cellWidget(r, self.COL_QTY)
                price_w: QLineEdit = self.table.cellWidget(r, self.COL_PRICE_PER_UNIT)
                item_text = (row_price_w.text().strip() if row_price_w and row_price_w.text() else "")

                # parse numeric qty and ppu for computed fallback
                try:
                    qty = Decimal(qty_w.text() or "0")
                except Exception:
                    qty = Decimal("0")
                try:
                    ppu = Decimal(price_w.text() or "0")
                except Exception:
                    ppu = Decimal("0")

                # if user provided a row price, use it; otherwise compute from qty*ppu
                if item_text:
                    try:
                        displayed_row_cost = Decimal(item_text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    except Exception:
                        displayed_row_cost = Decimal("0.00")
                else:
                    displayed_row_cost = (qty * ppu).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                # keep user-entered row price when provided; otherwise show computed
                # value in the editable row-price widget for transparency.
                if row_price_w is not None and not item_text:
                    row_price_w.setText(str(displayed_row_cost))

            # total/per labels removed from UI; application logic unaffected
            pass
        except Exception as exc:
            QMessageBox.warning(self, "Validation", str(exc))

    def accept(self) -> None:
        try:
            # validate before accepting
            recipe = self.get_recipe()
            recipe.validate()
            super().accept()
        except Exception as exc:
            QMessageBox.warning(self, "Validation", str(exc))

    def _commit_table_editors(self) -> None:
        """Close or commit any active editor so edits are written to the item.

        This handles both persistent editors (closePersistentEditor) and
        the normal delegate-created editor (commitData/closeEditor) by
        inspecting the currently focused widget.
        """
        try:
            # snapshot cell widgets so we don't accidentally treat them as
            # transient delegate editors below
            cell_widgets = set()
            for r in range(self.table.rowCount()):
                for c in range(self.table.columnCount()):
                    w = self.table.cellWidget(r, c)
                    if w is not None:
                        cell_widgets.add(w)

            # If the currently focused widget is a delegate editor inside the table,
            # commit and close it immediately (pressed/release ordering can change focus).
            # However we must **not** operate on persistent cell widgets, only on
            # editors created by the item delegate.  The focus widget is sometimes one
            # of our QLineEdit cell widgets, so skip it if it appears in the set above.
            fw = self.table.focusWidget() or QApplication.focusWidget()
            if isinstance(fw, QLineEdit) and fw not in cell_widgets:
                parent = fw
                while parent is not None:
                    # delegate editors are often children of the viewport — accept either
                    if parent is self.table or parent is self.table.viewport():
                        try:
                            self.table.commitData(fw)
                            self.table.closeEditor(fw, QAbstractItemDelegate.NoHint)
                        except Exception:
                            pass
                        break
                    parent = parent.parent()

            # attempt to find any other delegate-created editor widgets (QLineEdit)
            # inside the table and commit/close them. Exclude cellWidget editors.
            for child in self.table.findChildren(QLineEdit):
                if child in cell_widgets:
                    continue
                if not child.isVisible():
                    continue
                try:
                    self.table.commitData(child)
                    self.table.closeEditor(child, QAbstractItemDelegate.NoHint)
                except Exception:
                    pass

            # also ensure persistent editor (if any) is closed for the current item
            current = self.table.currentItem()
            if current is not None:
                self.table.closePersistentEditor(current)
        except Exception:
            pass
