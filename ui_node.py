"""PyQt UI components for Basalt nodes."""

import re
from PyQt5.QtWidgets import (
    QGraphicsProxyWidget, QWidget, QVBoxLayout,
    QLineEdit, QTextEdit, QTextBrowser, QStackedWidget, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from basalt_node import BasaltNode, LayoutSettings


class NoteBrowser(QTextBrowser):
    """Режим чтения. Умеет отличать клик по ссылке от клика по тексту."""
    edit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setStyleSheet("""
            QTextBrowser {
                border: none; 
                background: transparent; 
                padding: 2px;
                color: #334155;
            }
        """)
        self.setFont(QFont("Segoe UI", 9))
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Проверяем, попал ли клик по HTML-ссылке
            anchor = self.anchorAt(event.pos())
            if not anchor:
                # Клик по тексту/фону -> запрашиваем переход в режим редактирования
                self.edit_requested.emit()
                event.accept()
                return
        super().mousePressEvent(event)


class NoteEditor(QTextEdit):
    """Режим редактирования."""
    editing_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setStyleSheet("""
            QTextEdit {
                border: 1px solid #93c5fd; 
                background: #ffffff; 
                padding: 2px;
                border-radius: 4px;
                color: #0f172a;
            }
        """)
        self.setFont(QFont("Segoe UI", 9))
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.editing_finished.emit()

    def keyPressEvent(self, event):
        # Выход из режима редактирования по Esc или Ctrl+Enter
        if event.key() == Qt.Key_Escape:
            self.clearFocus()
            event.accept()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.ControlModifier:
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)


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
        self.title_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid transparent; 
                background: transparent; 
                padding: 2px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                background: #ffffff;
                border: 1px solid #93c5fd;
            }
        """)
        self.title_edit.editingFinished.connect(self._on_title_changed)
        
        # Пояснение (Стек для переключения между чтением и редактурой)
        self.note_browser = NoteBrowser()
        self.note_browser.setAlignment(align)
        self.note_browser.anchorClicked.connect(self._on_link_clicked)
        self.note_browser.edit_requested.connect(self._start_editing)
        self._update_note_display()
        
        self.note_edit = NoteEditor()
        self.note_edit.setAlignment(align)
        self.note_edit.editing_finished.connect(self._stop_editing)
        
        self.note_stack = QStackedWidget()
        self.note_stack.addWidget(self.note_browser)
        self.note_stack.addWidget(self.note_edit)
        self.note_stack.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.title_edit)
        layout.addWidget(self.note_stack, 1) # 1 = занимает всё оставшееся место

    def _update_note_display(self):
        text = self.node.note
        # Превращаем [[Ссылки]] в кликабельные HTML-теги с красивым стилем
        html = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', 
                      lambda m: f'<a href="{m.group(1)}" style="color: #2563eb; text-decoration: underline;">{m.group(2) or m.group(1)}</a>', 
                      text)
        html = html.replace('\n', '<br>')
        if not html.strip():
            html = "<i style='color: #9ca3af;'>Нет пояснения (кликните, чтобы добавить)</i>"
        self.note_browser.setHtml(html)

    def _on_title_changed(self):
        new_title = self.title_edit.text()
        if self.node.title != new_title:
            self.node.title = new_title
            node_id = self.node.id
            canvas = self.canvas
            QTimer.singleShot(0, lambda: canvas.node_changed.emit(node_id))

    def _on_link_clicked(self, url):
        self.canvas.link_clicked.emit(url.toString())

    def _start_editing(self):
        self.note_edit.setPlainText(self.node.note)
        self.note_stack.setCurrentWidget(self.note_edit)
        self.note_edit.setFocus()
        # Ставим курсор в конец текста
        cursor = self.note_edit.textCursor()
        cursor.movePosition(cursor.End)
        self.note_edit.setTextCursor(cursor)

    def _stop_editing(self):
        new_note = self.note_edit.toPlainText()
        if self.node.note != new_note:
            self.node.note = new_note
            self.canvas.node_changed.emit(self.node.id)
        self._update_note_display()
        self.note_stack.setCurrentWidget(self.note_browser)

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