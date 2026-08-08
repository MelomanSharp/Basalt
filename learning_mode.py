"""Anki-like spaced repetition learning with background notifications."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QMessageBox, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QApplication, QFrame, QDoubleSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from basalt_node import BasaltProject, BasaltNode, TreeLearningConfig


# ═══════════════════════════════════════════════════════════════
#  ФОНОВЫЙ МЕНЕДЖЕР ОБУЧЕНИЯ
# ═══════════════════════════════════════════════════════════════

class LearningManager:
    """Показывает карточки по таймеру, даже когда приложение свёрнуто."""

    def __init__(self, project: BasaltProject, parent=None):
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
        print(f"[LearningManager] Timer tick, active={self.active}")
        if not self.active:
            print("[LearningManager] Not active, returning")
            return
        if self.current_dialog and self.current_dialog.isVisible():
            print("[LearningManager] Dialog already visible")
            return

        due_nodes = self.project.get_due_nodes_for_learning()
        print(f"[LearningManager] Due nodes count: {len(due_nodes)}")
        
        if not due_nodes:
            print("[LearningManager] No due nodes, skipping")
            return
            
        node = due_nodes[0]
        print(f"[LearningManager] Showing node: {node.title}")
        
        try:
            self.current_dialog = NotificationDialog(node, self.project, self.parent)
            self.current_dialog.show()
            print(f"[LearningManager] Dialog shown: {self.current_dialog.isVisible()}")
        except Exception as e:
            print(f"[LearningManager] Error showing dialog: {e}")
            import traceback
            traceback.print_exc()


# ═══════════════════════════════════════════════════════════════
#  ВСПЛЫВАЮЩЕЕ УВЕДОМЛЕНИЕ
# ═══════════════════════════════════════════════════════════════

class NotificationDialog(QDialog):
    """Компактное окно с карточкой, всегда поверх других окон."""

    def __init__(self, node: BasaltNode, project: BasaltProject, parent=None):
        # 1. Передаём None вместо parent. Это делает окно полностью независимым
        # на уровне ОС, поэтому оно не будет сворачиваться вместе с главным окном.
        super().__init__(None) 
        
        self.node = node
        self.project = project
        self.setWindowTitle("Basalt — Повторение")
        
        # 2. Убираем Qt.Tool и явно задаём флаги независимого окна.
        # Qt.WindowStaysOnTopHint оставляет карточку поверх всех окон.
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowStaysOnTopHint | 
            Qt.WindowTitleHint | 
            Qt.WindowCloseButtonHint
        )
        
        self.resize(500, 350)
        self._setup_ui()
        self._show_front()
        self._position_at_bottom_right()
        print(f"[NotificationDialog] Created for node: {node.title}")

    def _position_at_bottom_right(self):
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                x = geometry.width() - self.width() - 20
                y = geometry.height() - self.height() - 40
                self.move(max(0, x), max(0, y))
            else:
                # Fallback: центр экрана
                screen = QApplication.primaryScreen().geometry()
                x = (screen.width() - self.width()) // 2
                y = (screen.height() - self.height()) // 2
                self.move(x, y)
        except Exception as e:
            print(f"[NotificationDialog] Error positioning: {e}")
            self.move(100, 100)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🧠 Интервальное повторение")
        header.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header.setStyleSheet("color: #3772d6; padding-bottom: 4px;")
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #cbd5e1; max-height: 1px;")
        layout.addWidget(sep)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.card_widget = QWidget()
        self.card_layout = QVBoxLayout(self.card_widget)
        self.scroll.setWidget(self.card_widget)
        layout.addWidget(self.scroll)

        self.btn_reveal = QPushButton("Показать ответ (Пробел)")
        self.btn_reveal.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_reveal.setStyleSheet(
            "background-color: #3772d6; color: white; padding: 8px; border-radius: 4px;"
        )
        self.btn_reveal.clicked.connect(self._reveal)
        layout.addWidget(self.btn_reveal)

        self.grade_layout = QHBoxLayout()
        grades = [
            ("Снова (1)", 1, "#e04f5f"), ("Тяжело (2)", 2, "#f59e0b"),
            ("Хорошо (3)", 3, "#10b981"), ("Легко (5)", 5, "#3772d6"),
        ]
        for text, grade, color in grades:
            btn = QPushButton(text)
            btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
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
        lbl = QLabel(f"<h2>{self.node.title}</h2>")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        self.card_layout.addWidget(lbl)

    def _reveal(self):
        self._clear()
        self.btn_reveal.setVisible(False)
        self._set_grading_visible(True)

        lbl = QLabel(f"<h2>{self.node.title}</h2>")
        lbl.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(lbl)

        note = self.node.note or "<i>(Пояснение отсутствует)</i>"
        note_lbl = QLabel(f"<b>Пояснение:</b><br>{note}")
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "background: #f3f4f6; padding: 10px; border-radius: 4px; margin: 8px 0;"
        )
        self.card_layout.addWidget(note_lbl)

        if self.node.children:
            header = QLabel("<b>Непосредственные дочерние узлы:</b>")
            header.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.card_layout.addWidget(header)

            tree = None
            for t in self.project.trees.values():
                if self.node.id in t.nodes:
                    tree = t
                    break
                    
            if tree:
                for cid in self.node.children:
                    child = tree.nodes.get(cid)
                    if not child: continue
                    text = f"<b>{child.title}</b>: {child.note}" if child.note else f"<b>{child.title}</b>"
                    lbl_c = QLabel(text)
                    lbl_c.setWordWrap(True)
                    lbl_c.setStyleSheet(
                        "margin-left: 15px; padding: 5px; border-left: 3px solid #3772d6;"
                    )
                    self.card_layout.addWidget(lbl_c)

    def _grade(self, grade: int):
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
        self.resize(650, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Общие настройки ────────────────────────────────────
        common_group = QGroupBox("Общие настройки")
        common_layout = QFormLayout()

        # Интервал: минуты и секунды
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
        self.chk_shuffle_trees.setToolTip(
            "Если выключено — карточки показываются в порядке списка деревьев слева."
        )
        common_layout.addRow("", self.chk_shuffle_trees)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

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
        btn_test.setToolTip("Показать одну карточку для проверки")
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
        """Показать тестовую карточку для проверки."""
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
            
        node = due_nodes[0]
        dialog = NotificationDialog(node, self.project, self)
        dialog.exec_()

    def apply_settings(self):
        self.project.learning.interval_minutes = self.spin_minutes.value()
        self.project.learning.interval_seconds = self.spin_seconds.value()
        self.project.learning.random_order_trees = self.chk_shuffle_trees.isChecked()
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