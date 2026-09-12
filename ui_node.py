"""PyQt UI components for Basalt nodes."""
import re
from PyQt5.QtWidgets import (
    QGraphicsProxyWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QTextBrowser, QStackedWidget, QFrame, QPushButton,
    QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from basalt_node import BasaltNode, LayoutSettings
from i18n import tr

class NoteBrowser(QTextBrowser):
    """Read mode. Can distinguish between link clicks and text clicks."""
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
            anchor = self.anchorAt(event.pos())
            if not anchor:
                self.edit_requested.emit()
                event.accept()
                return
        super().mousePressEvent(event)

class NoteEditor(QTextEdit):
    """Edit mode."""
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

        if settings.text_align == "center": align = Qt.AlignCenter
        elif settings.text_align == "right": align = Qt.AlignRight
        else: align = Qt.AlignLeft

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

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 5, 0, 0)
        actions_layout.setSpacing(4)

        # --- Move Buttons ---
        self.btn_move_left = QPushButton(tr("move_left_btn"))
        self.btn_move_left.setCursor(Qt.PointingHandCursor)
        self.btn_move_left.setToolTip(tr("move_left_tooltip"))
        self.btn_move_left.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_move_left.setStyleSheet("""
            QPushButton {
                color: #6d28d9; background: transparent; border: 1px solid transparent;
                padding: 2px 4px; font-size: 9px; border-radius: 4px;
            }
            QPushButton:hover { background: #ede9fe; border: 1px solid #c4b5fd; }
        """)

        self.btn_move_right = QPushButton(tr("move_right_btn"))
        self.btn_move_right.setCursor(Qt.PointingHandCursor)
        self.btn_move_right.setToolTip(tr("move_right_tooltip"))
        self.btn_move_right.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_move_right.setStyleSheet("""
            QPushButton {
                color: #6d28d9; background: transparent; border: 1px solid transparent;
                padding: 2px 4px; font-size: 9px; border-radius: 4px;
            }
            QPushButton:hover { background: #ede9fe; border: 1px solid #c4b5fd; }
        """)

        self.btn_move_left.clicked.connect(self._on_move_left)
        self.btn_move_right.clicked.connect(self._on_move_right)
        # --------------------

        btn_parent = QPushButton(tr("parent_btn"))
        btn_parent.setCursor(Qt.PointingHandCursor)
        btn_parent.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_parent.setStyleSheet("""
            QPushButton {
                color: #3772d6; background: transparent; border: 1px solid transparent;
                padding: 2px 4px; font-size: 9px; border-radius: 4px;
            }
            QPushButton:hover { background: #e8f0ff; border: 1px solid #93c5fd; }
        """)

        btn_child = QPushButton(tr("child_btn"))
        btn_child.setCursor(Qt.PointingHandCursor)
        btn_child.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_child.setStyleSheet("""
            QPushButton {
                color: #10b981; background: transparent; border: 1px solid transparent;
                padding: 2px 4px; font-size: 9px; border-radius: 4px;
            }
            QPushButton:hover { background: #dcfce7; border: 1px solid #86efac; }
        """)

        btn_delete = QPushButton(tr("delete_btn"))
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_delete.setStyleSheet("""
            QPushButton {
                color: #e04f5f; background: transparent; border: 1px solid transparent;
                padding: 2px 4px; font-size: 9px; border-radius: 4px;
            }
            QPushButton:hover { background: #ffe4e6; border: 1px solid #fca5a5; }
        """)

        btn_parent.clicked.connect(self._on_add_parent)
        btn_child.clicked.connect(self._on_add_child)
        btn_delete.clicked.connect(self._on_delete)

        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_move_left)
        actions_layout.addWidget(self.btn_move_right)
        actions_layout.addWidget(btn_parent)
        actions_layout.addWidget(btn_child)
        actions_layout.addWidget(btn_delete)

        layout.addWidget(self.title_edit)
        layout.addWidget(self.note_stack, 1)
        layout.addLayout(actions_layout)

        # Initialize visibility based on current state
        self._update_move_buttons_visibility()

    def _update_move_buttons_visibility(self):
        tree = getattr(self.canvas, "tree", None)
        if tree is None:
            self.btn_move_left.setVisible(False)
            self.btn_move_right.setVisible(False)
            return

        info = tree.get_sibling_info(self.node.id)
        if info is None:
            self.btn_move_left.setVisible(False)
            self.btn_move_right.setVisible(False)
            return

        _parent_id, siblings, index = info

        if len(siblings) <= 1:
            self.btn_move_left.setVisible(False)
            self.btn_move_right.setVisible(False)
            return

        self.btn_move_left.setVisible(index > 0)
        self.btn_move_right.setVisible(index < len(siblings) - 1)

    def _on_move_left(self):
        self.canvas.select_node(self.node.id)
        node_id = self.node.id
        QTimer.singleShot(0, lambda: self.canvas.move_child_left_requested.emit(node_id))

    def _on_move_right(self):
        self.canvas.select_node(self.node.id)
        node_id = self.node.id
        QTimer.singleShot(0, lambda: self.canvas.move_child_right_requested.emit(node_id))

    def _on_add_child(self):
        self.canvas.select_node(self.node.id)
        node_id = self.node.id
        QTimer.singleShot(0, lambda: self.canvas.add_child_requested.emit(node_id))

    def _on_add_parent(self):
        self.canvas.select_node(self.node.id)
        node_id = self.node.id
        QTimer.singleShot(0, lambda: self.canvas.add_parent_requested.emit(node_id))

    def _on_delete(self):
        self.canvas.select_node(self.node.id)
        node_id = self.node.id
        QTimer.singleShot(0, lambda: self.canvas.delete_node_requested.emit(node_id))

    def _update_note_display(self):
        text = self.node.note
        html = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',
                      lambda m: f'<a href="{m.group(1)}" style="color: #2563eb; text-decoration: underline;">{m.group(2) or m.group(1)}</a>',
                      text)
        html = html.replace('\n', '<br>')
        if not html.strip():
            html = tr("no_note_placeholder")
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