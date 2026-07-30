"""PyQt UI components for Basalt nodes and inspector."""

from PyQt5.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton
)
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainter
from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from basalt_node import BasaltNode


class UINode(QGraphicsRectItem):
    """Графическое представление узла на холсте"""
    WIDTH = 200
    HEIGHT = 80

    def __init__(self, node: BasaltNode, canvas):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)
        self.node = node
        self.canvas = canvas
        self.is_selected = False
        self.is_collapsed = False
        
        # Статичное расположение (Пространственная память)
        self.setPos(node.x, node.y)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, False) # Управляем выделением сами
        
        self._update_appearance()
        self._draw_text()

    def _update_appearance(self):
        if self.is_selected:
            self.setBrush(QBrush(QColor("#e8f0ff")))
            self.setPen(QPen(QColor("#3772d6"), 2))
        else:
            self.setBrush(QBrush(QColor("#ffffff")))
            self.setPen(QPen(QColor("#cbd5e1"), 1))

    def _draw_text(self):
        # Заголовок
        self.title_item = QGraphicsTextItem(self.node.title, self)
        self.title_item.setDefaultTextColor(QColor("#172033"))
        self.title_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.title_item.setTextWidth(self.WIDTH - 20)
        self.title_item.setPos(10, 10)
        
        # Пояснение (превью)
        if self.node.note:
            note_preview = self.node.note.replace('\n', ' ')
            if len(note_preview) > 60:
                note_preview = note_preview[:57] + "..."
            self.note_item = QGraphicsTextItem(note_preview, self)
            self.note_item.setDefaultTextColor(QColor("#526074"))
            self.note_item.setFont(QFont("Segoe UI", 8))
            self.note_item.setTextWidth(self.WIDTH - 20)
            self.note_item.setPos(10, 35)
        else:
            self.note_item = None

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_appearance()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.canvas.select_node(self.node.id)
            event.accept()
        else:
            super().mousePressEvent(event)


class NodeInspector(QWidget):
    """Панель инспектора для редактирования узла"""
    save_requested = pyqtSignal(str, str, str)  # node_id, title, note

    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_id = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_title = QLabel("Узел")
        self.lbl_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(self.lbl_title)
        
        layout.addWidget(QLabel("Название:"))
        self.edit_title = QLineEdit()
        self.edit_title.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.edit_title)
        
        layout.addWidget(QLabel("Пояснение:"))
        self.edit_note = QTextEdit()
        self.edit_note.setFont(QFont("Segoe UI", 10))
        self.edit_note.setPlaceholderText("Введите определение, ответ или детали...")
        layout.addWidget(self.edit_note)
        
        self.btn_save = QPushButton("Сохранить изменения")
        self.btn_save.setFont(QFont("Segoe UI", 10))
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)
        
        self.set_enabled(False)

    def show_node(self, node: BasaltNode):
        self.node_id = node.id
        self.edit_title.setText(node.title)
        self.edit_note.setPlainText(node.note)
        self.set_enabled(True)

    def clear(self):
        self.node_id = None
        self.edit_title.clear()
        self.edit_note.clear()
        self.set_enabled(False)

    def set_enabled(self, enabled: bool):
        self.edit_title.setEnabled(enabled)
        self.edit_note.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)

    def _on_save(self):
        if self.node_id:
            self.save_requested.emit(self.node_id, self.edit_title.text(), self.edit_note.toPlainText())