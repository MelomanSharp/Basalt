"""Anki-like spaced repetition learning with background notifications."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QMessageBox, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QApplication, QFrame, QDoubleSpinBox,
    QFontComboBox, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
from basalt_node import BasaltProject, BasaltNode, BasaltTree, TreeLearningConfig


# ═══════════════════════════════════════════════════════════════
#  ФОНОВЫЙ МЕНЕДЖЕР ОБУЧЕНИЯ
# ═══════════════════════════════════════════════════════════════

class LearningManager(QObject):
    """Показывает карточки по таймеру, даже когда приложение свёрнуто."""
    navigate_to_node = pyqtSignal(str, str)

    def __init__(self, project: BasaltProject, parent=None):
        super().__init__()
        self.project = project
        self.parent = parent
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer)
        self.active = False
        self.current_dialog: NotificationDialog | None = None

    def start(self):
        interval_ms = self.project.learning.get_interval_ms()
        if interval_ms < 1000:
            interval_ms = 1000
        self.timer.start(interval_ms)
        self.active = True
        QTimer.singleShot(3000, self._on_timer)

    def stop(self):
        self.timer.stop()
        self.active = False
        if self.current_dialog and self.current_dialog.isVisible():
            self.current_dialog.close()

    def _on_timer(self):
        if not self.active: return
        if self.current_dialog and self.current_dialog.isVisible(): return

        due_nodes = self.project.get_due_nodes_for_learning()
        if not due_nodes: return
            
        tree, node = due_nodes[0]
        
        try:
            self.current_dialog = NotificationDialog(node, tree, self.project, self.parent, manager=self)
            self.current_dialog.show()
        except Exception as e:
            import traceback
            traceback.print_exc()


# ═══════════════════════════════════════════════════════════════
#  ВСПЛЫВАЮЩЕЕ УВЕДОМЛЕНИЕ
# ═══════════════════════════════════════════════════════════════

class NotificationDialog(QDialog):
    """Компактное окно с карточкой, всегда поверх других окон."""

    def __init__(self, node: BasaltNode, tree: BasaltTree, project: BasaltProject, parent=None, manager=None):
        super().__init__(parent) 
        
        self.node = node
        self.tree = tree
        self.project = project
        self.manager = manager
        self.tree_title = self.tree.title if self.tree else "Неизвестное дерево"
        
        self.setWindowTitle("Basalt — Повторение")
        
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowStaysOnTopHint | 
            Qt.WindowTitleHint | 
            Qt.WindowCloseButtonHint
        )
        
        # Применяем настройки карточки
        cs = self.project.learning.card_settings
        self.resize(cs.card_width, cs.card_height)
        font = QFont(cs.font_family, cs.font_size)
        self.setFont(font)
        
        self._setup_ui()
        self._show_front()
        self._position_window()

    def _position_window(self):
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                self.move(100, 100)
                return
                
            geo = screen.availableGeometry()
            pos = self.project.learning.card_settings.window_position
            
            if pos == "center":
                x = geo.x() + geo.width() // 2 - self.width() // 2
                y = geo.y() + geo.height() // 2 - self.height() // 2
            elif pos == "top_left":
                x = geo.x() + 20
                y = geo.y() + 40
            elif pos == "top_right":
                x = geo.x() + geo.width() - self.width() - 20
                y = geo.y() + 40
            else: # bottom_right
                x = geo.x() + geo.width() - self.width() - 20
                y = geo.y() + geo.height() - self.height() - 40
                
            self.move(max(geo.x(), x), max(geo.y(), y))
        except Exception:
            self.move(100, 100)

    def _sync_node(self) -> bool:
        """Проверяет, существует ли узел до сих пор, и обновляет его."""
        if self.tree and self.node and self.node.id in self.tree.nodes:
            self.node = self.tree.nodes[self.node.id]
            return True
        else:
            self._clear()
            lbl = QLabel("⚠️ Этот узел был удален или перемещен во время обучения.")
            lbl.setStyleSheet("color: #e04f5f; font-weight: bold; margin: 20px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            self.btn_reveal.setVisible(False)
            self._set_grading_visible(False)
            if hasattr(self, 'btn_open_tree'):
                self.btn_open_tree.setVisible(False)
            return False

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🧠 Интервальное повторение")
        header.setFont(QFont(self.font().family(), self.font().pointSize() + 1, QFont.Bold))
        header.setStyleSheet("color: #3772d6; padding-bottom: 4px;")
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #cbd5e1; max-height: 1px;")
        layout.addWidget(sep)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.card_widget = QWidget()
        self.card_layout = QVBoxLayout(self.card_widget)
        self.scroll.setWidget(self.card_widget)
        layout.addWidget(self.scroll)

        btn_layout = QHBoxLayout()
        
        self.btn_open_tree = QPushButton("📂 В дереве")
        self.btn_open_tree.setToolTip("Открыть этот узел в основном окне для редактирования")
        self.btn_open_tree.setStyleSheet("padding: 8px; background: #64748b; color: white; border-radius: 4px;")
        self.btn_open_tree.clicked.connect(self._open_in_tree)
        btn_layout.addWidget(self.btn_open_tree)
        
        if self.manager is None:
            self.btn_open_tree.setVisible(False)

        btn_layout.addStretch()

        self.btn_reveal = QPushButton("Показать ответ (Пробел)")
        self.btn_reveal.setFont(QFont(self.font().family(), self.font().pointSize(), QFont.Bold))
        self.btn_reveal.setStyleSheet(
            "background-color: #3772d6; color: white; padding: 8px 16px; border-radius: 4px;"
        )
        self.btn_reveal.clicked.connect(self._reveal)
        btn_layout.addWidget(self.btn_reveal)

        layout.addLayout(btn_layout)

        self.grade_layout = QHBoxLayout()
        grades = [
            ("Снова (1)", 1, "#e04f5f"), ("Тяжело (2)", 2, "#f59e0b"),
            ("Хорошо (3)", 3, "#10b981"), ("Легко (5)", 5, "#3772d6"),
        ]
        for text, grade, color in grades:
            btn = QPushButton(text)
            btn.setFont(QFont(self.font().family(), self.font().pointSize() - 1, QFont.Bold))
            btn.setStyleSheet(
                f"background-color: {color}; color: white; padding: 6px; border-radius: 4px;"
            )
            btn.clicked.connect(lambda _, g=grade: self._grade(g))
            self.grade_layout.addWidget(btn)
        layout.addLayout(self.grade_layout)
        self._set_grading_visible(False)

    def _clear(self):
        while self.card_layout.count():
            c = self.card_layout.takeAt(0)
            if c.widget(): c.widget().deleteLater()

    def _show_front(self):
        self._clear()
        if not self._sync_node(): return
        
        tree_lbl = QLabel(f"🌳 <i>{self.tree_title}</i>")
        tree_lbl.setAlignment(Qt.AlignCenter)
        tree_lbl.setStyleSheet("color: #64748b; margin-bottom: 8px;")
        self.card_layout.addWidget(tree_lbl)
        
        lbl = QLabel(f"<h2>{self.node.title}</h2>")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        self.card_layout.addWidget(lbl)

    def _reveal(self):
        self._clear()
        if not self._sync_node(): return
        
        self.btn_reveal.setVisible(False)
        self._set_grading_visible(True)

        tree_lbl = QLabel(f"🌳 <i>{self.tree_title}</i>")
        tree_lbl.setAlignment(Qt.AlignCenter)
        tree_lbl.setStyleSheet("color: #64748b; margin-bottom: 8px;")
        self.card_layout.addWidget(tree_lbl)

        lbl = QLabel(f"<h2>{self.node.title}</h2>")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        self.card_layout.addWidget(lbl)

        note = self.node.note or "<i>(Пояснение отсутствует)</i>"
        note_lbl = QLabel(f"<b>Пояснение:</b><br>{note}")
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "background: #f3f4f6; padding: 10px; border-radius: 4px; margin: 8px 0;"
        )
        self.card_layout.addWidget(note_lbl)

        if self.node.children and self.tree:
            header = QLabel("<b>Дочерние узлы:</b>")
            header.setFont(QFont(self.font().family(), self.font().pointSize(), QFont.Bold))
            self.card_layout.addWidget(header)

            show_notes = self.project.learning.card_settings.show_children_notes
            for cid in self.node.children:
                child = self.tree.nodes.get(cid)
                if not child: continue
                
                if show_notes:
                    text = f"• <a href='child:{cid}' style='color: #2563eb; text-decoration: underline;'><b>{child.title}</b></a><br><span style='color: #475569;'>{child.note or ''}</span>"
                else:
                    text = f"• <a href='child:{cid}' style='color: #2563eb; text-decoration: underline;'><b>{child.title}</b></a>"
                    
                lbl_c = QLabel(text)
                lbl_c.setOpenExternalLinks(False)
                lbl_c.linkActivated.connect(lambda link, c=child: self._open_child_node(c))
                lbl_c.setWordWrap(True)
                lbl_c.setStyleSheet(
                    "margin-left: 15px; padding: 5px; border-left: 3px solid #3772d6;"
                )
                self.card_layout.addWidget(lbl_c)

    def _open_child_node(self, child_node):
        dialog = NotificationDialog(child_node, self.tree, self.project, self, manager=self.manager)
        dialog.exec_()

    def _open_in_tree(self):
        if self.manager and self.tree and self.node:
            self.manager.navigate_to_node.emit(self.tree.id, self.node.id)
            self.close()

    def _grade(self, grade: int):
        if self._sync_node():
            self.node.review.schedule(grade)
        self.close()

    def _set_grading_visible(self, visible: bool):
        for i in range(self.grade_layout.count()):
            self.grade_layout.itemAt(i).widget().setVisible(visible)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self.btn_reveal.isHidden():
            self._reveal()
        else:
            super().keyPressEvent(event)


# ═══════════════════════════════════════════════════════════════
#  ДИАЛОГ НАСТРОЕК ПЕРЕД ЗАПУСКОМ
# ═══════════════════════════════════════════════════════════════

class LearningSettingsDialog(QDialog):
    """Окно настроек перед запуском фонового обучения."""

    def __init__(self, project: BasaltProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Настройки режима обучения")
        self.resize(650, 700)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Общие настройки ────────────────────────────────────
        common_group = QGroupBox("Общие настройки")
        common_layout = QFormLayout()

        interval_layout = QHBoxLayout()
        self.spin_minutes = QSpinBox()
        self.spin_minutes.setRange(0, 60)
        self.spin_minutes.setValue(self.project.learning.interval_minutes)
        self.spin_minutes.setSuffix(" мин")
        interval_layout.addWidget(self.spin_minutes)
        
        self.spin_seconds = QSpinBox()
        self.spin_seconds.setRange(0, 59)
        self.spin_seconds.setValue(self.project.learning.interval_seconds)
        self.spin_seconds.setSuffix(" сек")
        interval_layout.addWidget(self.spin_seconds)
        
        common_layout.addRow("Интервал показов:", interval_layout)

        self.chk_shuffle_trees = QCheckBox("Перемешивать порядок деревьев между собой")
        self.chk_shuffle_trees.setChecked(self.project.learning.random_order_trees)
        common_layout.addRow("", self.chk_shuffle_trees)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # ── Настройки карточки ─────────────────────────────────
        card_group = QGroupBox("Настройки окна карточки")
        card_layout = QFormLayout()
        
        cs = self.project.learning.card_settings
        
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(cs.font_family))
        card_layout.addRow("Шрифт:", self.font_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 36)
        self.font_size_spin.setValue(cs.font_size)
        self.font_size_spin.setSuffix(" pt")
        card_layout.addRow("Размер шрифта:", self.font_size_spin)
        
        size_layout = QHBoxLayout()
        self.card_width_spin = QSpinBox()
        self.card_width_spin.setRange(300, 1600)
        self.card_width_spin.setValue(cs.card_width)
        self.card_width_spin.setSuffix(" px")
        size_layout.addWidget(self.card_width_spin)
        
        self.card_height_spin = QSpinBox()
        self.card_height_spin.setRange(200, 1000)
        self.card_height_spin.setValue(cs.card_height)
        self.card_height_spin.setSuffix(" px")
        size_layout.addWidget(self.card_height_spin)
        card_layout.addRow("Размеры окна:", size_layout)
        
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["По центру", "Снизу справа", "Сверху справа", "Сверху слева"])
        pos_map = {"center": 0, "bottom_right": 1, "top_right": 2, "top_left": 3}
        self.pos_combo.setCurrentIndex(pos_map.get(cs.window_position, 0))
        card_layout.addRow("Позиция на экране:", self.pos_combo)
        
        self.chk_show_children_notes = QCheckBox("Показывать текст дочерних узлов сразу")
        self.chk_show_children_notes.setChecked(cs.show_children_notes)
        self.chk_show_children_notes.setToolTip(
            "Если выключено — показываются только заголовки дочерних узлов.\n"
            "Клик по заголовку открывает карточку этого узла вне очереди."
        )
        card_layout.addRow("", self.chk_show_children_notes)
        
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)

        # ── Настройки для каждого дерева ───────────────────────
        trees_group = QGroupBox("Настройки для каждого дерева отдельно")
        trees_layout = QVBoxLayout()

        self.tree_list = QListWidget()
        self.tree_list.setSelectionMode(QListWidget.NoSelection)

        for tree in self.project.trees.values():
            item = QListWidgetItem()
            cfg = self.project.learning.get_tree_config(tree.id)
            widget = TreeConfigWidget(tree, cfg)
            item.setSizeHint(widget.sizeHint())
            self.tree_list.addItem(item)
            self.tree_list.setItemWidget(item, widget)

        trees_layout.addWidget(self.tree_list)
        trees_group.setLayout(trees_layout)
        layout.addWidget(trees_group)

        # ── Кнопки ────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        
        btn_test = QPushButton("🧪 Тест карточки")
        btn_test.setStyleSheet("padding: 10px; background: #f59e0b; color: white; border-radius: 4px;")
        btn_test.clicked.connect(self._test_card)
        btn_layout.addWidget(btn_test)
        
        btn_layout.addStretch()

        btn_start = QPushButton("🚀 Начать обучение")
        btn_start.setFont(QFont("Segoe UI", 10, QFont.Bold))
        btn_start.setStyleSheet(
            "background-color: #10b981; color: white; padding: 10px; border-radius: 4px;"
        )
        btn_start.clicked.connect(self.accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("padding: 10px;")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_start)
        layout.addLayout(btn_layout)

    def _test_card(self):
        due_nodes = self.project.get_due_nodes_for_learning()
        if not due_nodes:
            QMessageBox.warning(
                self, "Нет карточек",
                "Нет карточек для повторения.\n\n"
                "Возможные причины:\n"
                "• Все карточки уже повторены на сегодня\n"
                "• Деревья отключены в настройках\n"
                "• Нет деревьев в проекте"
            )
            return
            
        tree, node = due_nodes[0]
        dialog = NotificationDialog(node, tree, self.project, self)
        dialog.exec_()

    def apply_settings(self):
        self.project.learning.interval_minutes = self.spin_minutes.value()
        self.project.learning.interval_seconds = self.spin_seconds.value()
        self.project.learning.random_order_trees = self.chk_shuffle_trees.isChecked()
        
        pos_map_rev = {0: "center", 1: "bottom_right", 2: "top_right", 3: "top_left"}
        self.project.learning.card_settings.font_family = self.font_combo.currentFont().family()
        self.project.learning.card_settings.font_size = self.font_size_spin.value()
        self.project.learning.card_settings.card_width = self.card_width_spin.value()
        self.project.learning.card_settings.card_height = self.card_height_spin.value()
        self.project.learning.card_settings.window_position = pos_map_rev.get(self.pos_combo.currentIndex(), "center")
        self.project.learning.card_settings.show_children_notes = self.chk_show_children_notes.isChecked()
        
        for i in range(self.tree_list.count()):
            item = self.tree_list.item(i)
            w: TreeConfigWidget = self.tree_list.itemWidget(item)
            w.apply_to_config()


class TreeConfigWidget(QWidget):
    """Строка настроек одного дерева в списке."""

    def __init__(self, tree, config: TreeLearningConfig, parent=None):
        super().__init__(parent)
        self.tree = tree
        self.config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.chk_enabled = QCheckBox(self.tree.title)
        self.chk_enabled.setChecked(self.config.enabled)
        self.chk_enabled.setMinimumWidth(200)
        layout.addWidget(self.chk_enabled)

        layout.addStretch()

        self.rb_random = QRadioButton("Случайно")
        self.rb_sequential = QRadioButton("Последовательно")
        self.rb_sequential.setToolTip(
            "Сначала основная ветка сверху вниз, затем ответвления. "
            "Узлы одного дерева показываются подряд."
        )
        if self.config.mode == "sequential":
            self.rb_sequential.setChecked(True)
        else:
            self.rb_random.setChecked(True)

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_random)
        self.btn_group.addButton(self.rb_sequential)

        layout.addWidget(self.rb_random)
        layout.addWidget(self.rb_sequential)

    def apply_to_config(self):
        self.config.enabled = self.chk_enabled.isChecked()
        self.config.mode = "sequential" if self.rb_sequential.isChecked() else "random"

    def sizeHint(self):
        from PyQt5.QtCore import QSize
        return QSize(400, 40)