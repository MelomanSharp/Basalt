"""PyQt UI components for Basalt nodes."""

import re
from PyQt5.QtWidgets import (
    QGraphicsProxyWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QTextBrowser, QPushButton
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from basalt_node import BasaltNode, LayoutSettings

class NodeWidget(QWidget):
    def __init__(self, node: BasaltNode, canvas, settings: LayoutSettings):
        super().__init__()
        self.node = node
        self.canvas = canvas
        self.settings = settings
        
        self.setFixedSize(settings.node_width, settings.node_height)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        
        # Определяем выравнивание
        if settings.text_align == "center": align = Qt.AlignCenter
        elif settings.text_align == "right": align = Qt.AlignRight
        else: align = Qt.AlignLeft
        
        # Заголовок
        self.title_edit = QLineEdit(node.title)
        self.title_edit.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.title_edit.setAlignment(align)
        self.title_edit.setStyleSheet("border: none; background: transparent; padding: 0;")
        self.title_edit.editingFinished.connect(self._on_title_changed)
        
        # Пояснение
        self.note_browser = QTextBrowser()
        self.note_browser.setOpenLinks(False)
        self.note_browser.setFont(QFont("Segoe UI", 9))
        self.note_browser.setAlignment(align)
        self.note_browser.setStyleSheet("border: none; background: transparent; padding: 0;")
        self.note_browser.anchorClicked.connect(self._on_link_clicked)
        self._update_note_display()
        
        # Кнопка редактирования
        self.btn_edit = QPushButton("✏️")
        self.btn_edit.setFixedSize(24, 24)
        self.btn_edit.setToolTip("Редактировать пояснение")
        self.btn_edit.setStyleSheet("border: none; background: transparent;")
        self.btn_edit.clicked.connect(self._toggle_edit)
        
        note_layout = QHBoxLayout()
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.addWidget(self.note_browser)
        note_layout.addWidget(self.btn_edit, alignment=Qt.AlignTop)
        
        layout.addWidget(self.title_edit)
        layout.addLayout(note_layout)
        
        self.is_editing = False
        self.note_edit = None

    def _update_note_display(self):
        text = self.node.note
        html = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', 
                      lambda m: f'<a href="{m.group(1)}">{m.group(2) or m.group(1)}</a>', 
                      text)
        html = html.replace('\n', '<br>')
        if not html.strip():
            html = "<i style='color: #9ca3af;'>Нет пояснения</i>"
        self.note_browser.setHtml(html)

    def _on_title_changed(self):
        if self.node.title != self.title_edit.text():
            self.node.title = self.title_edit.text()
            self.canvas.node_changed.emit(self.node.id)

    def _on_link_clicked(self, url):
        self.canvas.link_clicked.emit(url.toString())

    def _toggle_edit(self):
        self.is_editing = not self.is_editing
        note_layout = self.layout().itemAt(1)
        
        if self.is_editing:
            self.btn_edit.setText("💾")
            self.note_browser.hide()
            self.note_edit = QTextEdit(self.node.note)
            self.note_edit.setFont(QFont("Segoe UI", 9))
            self.note_edit.setStyleSheet("border: 1px solid #cbd5e1; background: white; padding: 2px;")
            note_layout.insertWidget(0, self.note_edit)
            self.note_edit.setFocus()
        else:
            self.btn_edit.setText("✏️")
            if self.note_edit:
                self.node.note = self.note_edit.toPlainText()
                self.note_edit.deleteLater()
                self.note_edit = None
            self.note_browser.show()
            self._update_note_display()
            self.canvas.node_changed.emit(self.node.id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.canvas.select_node(self.node.id)
        super().mousePressEvent(event)


class UINode(QGraphicsProxyWidget):
    def __init__(self, node: BasaltNode, canvas, settings: LayoutSettings):
        super().__init__()
        self.node = node
        self.canvas = canvas
        self.settings = settings
        
        self.widget = NodeWidget(node, canvas, settings)
        self.setWidget(self.widget)
        self.setPos(node.x, node.y)
        self.setFlag(QGraphicsProxyWidget.ItemIsMovable, False)
        self.setFlag(QGraphicsProxyWidget.ItemIsSelectable, False)
        self._update_appearance()

    def _update_appearance(self):
        is_selected = self.canvas.selected_id == self.node.id
        bg = "#e8f0ff" if is_selected else "#ffffff"
        border = "#3772d6" if is_selected else "#cbd5e1"
        self.widget.setStyleSheet(f"""
            NodeWidget {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 8px;
            }}
        """)

    def set_selected(self, selected: bool):
        self._update_appearance()