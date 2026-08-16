import sys
import os
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QAction, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QLabel, QAbstractItemView, QInputDialog, QDialog,
    QRadioButton, QButtonGroup, QPushButton, QTextEdit
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QTimer, QSettings

from basalt_node import BasaltProject, BasaltTree, new_id
from basalt_canvas import BasaltCanvas
from learning_mode import LearningManager, LearningSettingsDialog
from ui_settings import SettingsDialog


def create_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#2d2d2d"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QPen(QColor("#3772d6"), 3))
    painter.drawLine(32, 20, 32, 32)
    painter.drawLine(32, 32, 18, 44)
    painter.drawLine(32, 32, 46, 44)
    painter.setBrush(QColor("#3772d6"))
    painter.drawEllipse(28, 14, 8, 8)
    painter.drawEllipse(14, 40, 8, 8)
    painter.drawEllipse(42, 40, 8, 8)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Basalt - Knowledge Tree")
        self.resize(1400, 850)
        self.setWindowIcon(create_app_icon())

        self.qsettings = QSettings("Basalt", "Basalt")
        self.current_file_path: str | None = None
        self._dirty = False
        self._autosave_pending = False

        last_file = self.qsettings.value("last_file", None)
        if last_file and os.path.isfile(last_file):
            try:
                with open(last_file, "r", encoding="utf-8") as f:
                    self.project = BasaltProject.from_json(f.read())
                self.current_file_path = last_file
            except Exception:
                self.project = BasaltProject()
                self.current_file_path = None
        else:
            self.project = BasaltProject()
            self.current_file_path = None

        self.current_tree_id = None
        self._pending_tree = None
        self._is_new_tree = False

        self._setup_ui()
        self._setup_toolbar()
        self._update_title()

        # Менеджер фонового обучения
        self.learning_manager = LearningManager(self.project, self)
        self.learning_manager.navigate_to_node.connect(self._navigate_to_node_from_learning)

        if self.project.trees:
            self.tree_list.setCurrentRow(0)

        if not self.current_file_path and not self.project.trees:
            QTimer.singleShot(200, self._show_welcome)

    # ══════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Horizontal)

        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)

        lbl_trees = QLabel("📚 Мои деревья")
        lbl_trees.setFont(QFont("Segoe UI", 11, QFont.Bold))
        sidebar_layout.addWidget(lbl_trees)

        self.tree_list = QListWidget()
        self.tree_list.setFont(QFont("Segoe UI", 10))
        self.tree_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_list.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.tree_list.currentRowChanged.connect(self._on_tree_selected)
        self.tree_list.itemChanged.connect(self._on_tree_renamed)
        sidebar_layout.addWidget(self.tree_list)

        self.canvas = BasaltCanvas()
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.node_changed.connect(self._on_node_changed)
        self.canvas.link_clicked.connect(self._navigate_to_tree)
        self.canvas.add_child_requested.connect(self.add_child_node)
        self.canvas.add_parent_requested.connect(self.add_parent_node)
        self.canvas.delete_node_requested.connect(self.delete_node)

        self.splitter.addWidget(sidebar_widget)
        self.splitter.addWidget(self.canvas)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([250, 1150])
        main_layout.addWidget(self.splitter)

    def _setup_toolbar(self):
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.act_open = QAction("📂 Открыть...", self)
        self.act_open.triggered.connect(self.open_project)
        toolbar.addAction(self.act_open)

        self.act_save = QAction("💾 Сохранить", self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self.save_project)
        toolbar.addAction(self.act_save)

        self.act_save_as = QAction("💾 Сохранить как...", self)
        self.act_save_as.triggered.connect(self.save_project_as)
        toolbar.addAction(self.act_save_as)

        self.act_export = QAction("📤 Экспорт...", self)
        self.act_export.triggered.connect(self.export_project)
        toolbar.addAction(self.act_export)

        toolbar.addSeparator()

        self.act_new_tree = QAction("➕ Новое дерево", self)
        self.act_new_tree.triggered.connect(self.add_new_tree)
        toolbar.addAction(self.act_new_tree)

        self.act_import_tree = QAction("📥 Импорт дерева", self)
        self.act_import_tree.triggered.connect(self.import_tree)
        toolbar.addAction(self.act_import_tree)

        self.act_rename_tree = QAction("✏️ Переименовать", self)
        self.act_rename_tree.triggered.connect(self.rename_current_tree)
        toolbar.addAction(self.act_rename_tree)

        self.act_delete_tree = QAction("🗑 Удалить дерево", self)
        self.act_delete_tree.triggered.connect(self.delete_current_tree)
        toolbar.addAction(self.act_delete_tree)

        toolbar.addSeparator()

        self.act_layout = QAction("📐 Выровнять", self)
        self.act_layout.triggered.connect(self.auto_layout)
        toolbar.addAction(self.act_layout)

        toolbar.addSeparator()

        self.act_settings = QAction("⚙️ Вид", self)
        self.act_settings.triggered.connect(self.open_settings)
        toolbar.addAction(self.act_settings)

        toolbar.addSeparator()

        self.act_learn = QAction("🧠 Начать обучение", self)
        self.act_learn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.act_learn.triggered.connect(self.start_learning)
        toolbar.addAction(self.act_learn)

        self.act_learn_stop = QAction("⏹ Остановить", self)
        self.act_learn_stop.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.act_learn_stop.triggered.connect(self.stop_learning)
        self.act_learn_stop.setVisible(False)
        toolbar.addAction(self.act_learn_stop)

    def _update_title(self):
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
        else:
            name = "Новая база"
        dirty = " *" if self._dirty else ""
        self.setWindowTitle(f"Basalt - {name}{dirty}")

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_title()
        self._autosave_pending = True
        QTimer.singleShot(1500, self._try_autosave)

    def _try_autosave(self):
        if not self._autosave_pending:
            return
        self._autosave_pending = False
        if self._dirty and self.current_file_path:
            self._save_to_path(self.current_file_path)

    def save_project(self):
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
        else:
            self.save_project_as()

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить базу знаний",
            "basalt_db.json", "JSON (*.json)"
        )
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self.current_file_path = path
            self.qsettings.setValue("last_file", path)
            self._save_to_path(path)

    def export_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспортировать базу знаний",
            "basalt_export.json", "JSON (*.json)"
        )
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self._save_to_path(path, silent=True)
            QMessageBox.information(self, "Успех", f"База экспортирована в:\n{path}")

    def open_project(self):
        if self._dirty and not self._ask_save_changes():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть базу знаний", "", "JSON (*.json)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.project = BasaltProject.from_json(f.read())
                self.current_file_path = path
                self.qsettings.setValue("last_file", path)
                self.learning_manager.stop()
                self._refresh_tree_list()
                if self.project.trees:
                    self.tree_list.setCurrentRow(0)
                else:
                    self.current_tree_id = None
                    self.canvas.scene.clear()
                self._dirty = False
                self._update_title()
                QMessageBox.information(self, "Успех", f"База «{os.path.basename(path)}» загружена.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")

    def _save_to_path(self, path: str, silent: bool = False):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.project.to_json())
            self._dirty = False
            self._update_title()
            if not silent:
                self.statusBar().showMessage(f"💾 Сохранено: {path}", 2500)
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")

    def closeEvent(self, event):
        if self._dirty:
            if not self._ask_save_changes():
                event.ignore()
                return
        event.accept()

    def _ask_save_changes(self) -> bool:
        name = os.path.basename(self.current_file_path) if self.current_file_path else "Новая база"
        msg = QMessageBox(self)
        msg.setWindowTitle("Несохранённые изменения")
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"В базе «{name}» есть несохранённые изменения.")
        msg.setInformativeText("Сохранить их перед выходом?")
        btn_save = msg.addButton("💾 Сохранить", QMessageBox.AcceptRole)
        btn_discard = msg.addButton("Не сохранять", QMessageBox.DestructiveRole)
        msg.addButton(QMessageBox.Cancel)
        msg.exec_()
        clicked = msg.clickedButton()
        if clicked == btn_save:
            self.save_project()
            return True
        elif clicked == btn_discard:
            return True
        else:
            return False

    def _show_welcome(self):
        QMessageBox.information(
            self, "Добро пожаловать в Basalt!",
            "У вас пока нет сохранённой базы знаний.\n\n"
            "Создайте первое дерево через кнопку «➕ Новое дерево» "
            "или загрузите существующую базу через «📂 Открыть...»."
        )

    def _refresh_tree_list(self):
        self.tree_list.blockSignals(True)
        self.tree_list.clear()
        for tree in self.project.trees.values():
            item = QListWidgetItem(tree.title)
            item.setData(Qt.UserRole, tree.id)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tree_list.addItem(item)
        self.tree_list.blockSignals(False)

    def _on_tree_selected(self, row):
        if row < 0: return
        item = self.tree_list.item(row)
        if not item: return
        tree_id = item.data(Qt.UserRole)
        self.current_tree_id = tree_id
        tree = self.project.trees.get(tree_id)
        if tree:
            self.canvas.set_tree(tree, self.project.settings)

    def _on_tree_renamed(self, item: QListWidgetItem):
        tree_id = item.data(Qt.UserRole)
        tree = self.project.trees.get(tree_id)
        if not tree: return
        new_title = item.text().strip()
        if new_title:
            tree.title = new_title
            self._mark_dirty()
        else:
            item.setText(tree.title)

    def rename_current_tree(self):
        if not self.current_tree_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите дерево.")
            return
        tree = self.project.trees.get(self.current_tree_id)
        if not tree: return
        new_title, ok = QInputDialog.getText(
            self, "Переименовать дерево", "Новое название:", text=tree.title
        )
        if ok and new_title.strip():
            tree.title = new_title.strip()
            self._refresh_tree_list()
            self._mark_dirty()
            for i in range(self.tree_list.count()):
                if self.tree_list.item(i).data(Qt.UserRole) == tree.id:
                    self.tree_list.setCurrentRow(i)
                    break

    def delete_current_tree(self):
        if not self.current_tree_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите дерево.")
            return
        tree = self.project.trees.get(self.current_tree_id)
        if not tree: return
        reply = QMessageBox.question(
            self, "Удалить дерево",
            f"Удалить дерево «{tree.title}» и все его узлы?\n"
            "Это действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.project.remove_tree(self.current_tree_id)
            self.current_tree_id = None
            self._refresh_tree_list()
            if self.project.trees:
                self.tree_list.setCurrentRow(0)
            else:
                self.canvas.scene.clear()
            self._mark_dirty()

    def import_tree(self):
        dlg = ImportTreeDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.imported_tree:
            tree = dlg.imported_tree
            
            existing = self.project.find_tree_by_title(tree.title)
            if existing:
                reply = QMessageBox.question(
                    self, "Дерево с таким именем уже существует",
                    f"Дерево с названием «{tree.title}» уже есть в базе.\n"
                    "Ссылки вида [[...]] могут работать некорректно.\n"
                    "Всё равно добавить?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            self.project.trees[tree.id] = tree
            self.project.learning.get_tree_config(tree.id)
            
            self._refresh_tree_list()
            for i in range(self.tree_list.count()):
                if self.tree_list.item(i).data(Qt.UserRole) == tree.id:
                    self.tree_list.setCurrentRow(i)
                    break
                    
            has_custom_layout = any(n.x != 0.0 or n.y != 0.0 for n in tree.nodes.values())
            if not has_custom_layout:
                tree.layout_tree(self.project.settings)
                
            self.canvas.set_tree(tree, self.project.settings)
            self._mark_dirty()
            QMessageBox.information(self, "Успех", f"Дерево «{tree.title}» успешно импортировано!")

    def _on_node_selected(self, node_id: str): pass

    def _on_node_changed(self, node_id: str):
        tree = self.project.trees.get(self.current_tree_id)
        if tree and node_id in tree.nodes and node_id == tree.root_id:
            QTimer.singleShot(0, self._sync_tree_list_after_rename)
        self._mark_dirty()

    def _sync_tree_list_after_rename(self):
        tree = self.project.trees.get(self.current_tree_id)
        if not tree: return
        self._refresh_tree_list()
        for i in range(self.tree_list.count()):
            if self.tree_list.item(i).data(Qt.UserRole) == tree.id:
                self.tree_list.setCurrentRow(i)
                break

    def _navigate_to_tree(self, target_title: str):
        target_title = target_title.strip()
        if not target_title: return
        target_tree = self.project.find_tree_by_title(target_title)
        self._is_new_tree = False
        if not target_tree:
            target_tree = self.project.add_tree(target_title)
            target_tree.layout_tree(self.project.settings)
            self._is_new_tree = True
            self._mark_dirty()
        self._pending_tree = target_tree
        QTimer.singleShot(0, self._apply_navigation)

    def _apply_navigation(self):
        target_tree = self._pending_tree
        if not target_tree: return
        if self._is_new_tree:
            QMessageBox.information(
                self, "Создано новое дерево",
                f"Дерево «{target_tree.title}» не существовало и было создано автоматически."
            )
        self.current_tree_id = target_tree.id
        self._refresh_tree_list()
        for i in range(self.tree_list.count()):
            if self.tree_list.item(i).data(Qt.UserRole) == target_tree.id:
                self.tree_list.setCurrentRow(i)
                break
        self.canvas.set_tree(target_tree, self.project.settings)
        self._pending_tree = None

    def add_new_tree(self):
        tree = self.project.add_tree("Новое дерево")
        self._refresh_tree_list()
        self.tree_list.setCurrentRow(self.tree_list.count() - 1)
        self._mark_dirty()

    def _get_tree_for_node(self, node_id: str):
        if self.current_tree_id and self.current_tree_id in self.project.trees:
            tree = self.project.trees[self.current_tree_id]
            if node_id in tree.nodes:
                return tree
        
        for tree in self.project.trees.values():
            if node_id in tree.nodes:
                self.current_tree_id = tree.id
                for i in range(self.tree_list.count()):
                    if self.tree_list.item(i).data(Qt.UserRole) == tree.id:
                        self.tree_list.blockSignals(True)
                        self.tree_list.setCurrentRow(i)
                        self.tree_list.blockSignals(False)
                        break
                return tree
        return None

    def add_child_node(self, node_id=None):
        target_id = node_id or self.canvas.selected_id
        if not target_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел.")
            return
            
        tree = self._get_tree_for_node(target_id)
        if not tree:
            QMessageBox.warning(self, "Ошибка", "Узел не найден ни в одном дереве.")
            return

        new_node = tree.add_child(target_id, "Новый дочерний узел")
        tree.layout_tree(self.project.settings)
        self.canvas.set_tree(tree, self.project.settings)
        self.canvas.select_node(new_node.id)
        self._mark_dirty()

    def add_parent_node(self, node_id=None):
        target_id = node_id or self.canvas.selected_id
        if not target_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел.")
            return
            
        tree = self._get_tree_for_node(target_id)
        if not tree:
            QMessageBox.warning(self, "Ошибка", "Узел не найден ни в одном дереве.")
            return

        dlg = AddParentDialog(self.project, tree.id, target_id, self)
        if dlg.exec_() == QDialog.Accepted:
            if dlg.choice == "new":
                new_node = tree.add_parent(target_id, "Новый родитель")
                tree.layout_tree(self.project.settings)
                self.canvas.set_tree(tree, self.project.settings)
                self.canvas.select_node(new_node.id)
                self._mark_dirty()
            elif dlg.choice == "existing":
                selected_target_id = dlg.selected_node_id
                if tree.reparent_node(target_id, selected_target_id):
                    tree.layout_tree(self.project.settings)
                    self.canvas.set_tree(tree, self.project.settings)
                    self._mark_dirty()
                else:
                    QMessageBox.warning(
                        self, "Нельзя",
                        "Этот узел нельзя сделать родителем: он сам является "
                        "потомком выбранного узла (образуется цикл)."
                    )

    def delete_node(self, node_id=None):
        target_id = node_id or self.canvas.selected_id
        if not target_id: return

        msg = QMessageBox(self)
        msg.setWindowTitle("Удаление узла")
        msg.setIcon(QMessageBox.Question)
        msg.setText("Как удалить выбранный узел?")
        msg.setInformativeText(
            "<b>Только узел</b> — его дети будут подвешены к его родителям.<br>"
            "<b>Всю ветку</b> — узел вместе со всеми потомками."
        )
        btn_only = msg.addButton("Только узел", QMessageBox.YesRole)
        btn_branch = msg.addButton("Всю ветку", QMessageBox.DestructiveRole)
        msg.addButton(QMessageBox.Cancel)

        msg.exec_()
        clicked = msg.clickedButton()
        if clicked == msg.button(QMessageBox.Cancel): return

        tree = self._get_tree_for_node(target_id)
        if not tree: return

        if clicked == btn_only:
            tree.remove_node_only(target_id)
        else:
            tree.remove_node(target_id)

        self.canvas.selected_id = None
        tree.layout_tree(self.project.settings)
        self.canvas.set_tree(tree, self.project.settings)
        self._mark_dirty()

    def auto_layout(self):
        tree = self.project.trees.get(self.current_tree_id)
        if tree:
            tree.layout_tree(self.project.settings)
            self.canvas.set_tree(tree, self.project.settings)
            self._mark_dirty()

    def open_settings(self):
        dialog = SettingsDialog(self.project.settings, self)
        if dialog.exec_():
            self.project.settings = dialog.get_settings()
            self.auto_layout()

    # ══════════════════════════════════════════════════════════
    #  Learning Mode
    # ══════════════════════════════════════════════════════════

    def start_learning(self):
        dlg = LearningSettingsDialog(self.project, self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply_settings()
            self.learning_manager.start()
            self.act_learn.setVisible(False)
            self.act_learn_stop.setVisible(True)
            self._mark_dirty()
            QMessageBox.information(
                self, "Режим обучения запущен",
                f"Карточки будут всплывать каждые {self.project.learning.interval_minutes} мин.\n"
                "Занимайтесь своими делами — приложение работает в фоне."
            )

    def stop_learning(self):
        self.learning_manager.stop()
        self.act_learn.setVisible(True)
        self.act_learn_stop.setVisible(False)
        QMessageBox.information(self, "Обучение остановлено", "Фоновый режим остановлен.")

    def _navigate_to_node_from_learning(self, tree_id, node_id):
        self.current_tree_id = tree_id
        self._refresh_tree_list()
        for i in range(self.tree_list.count()):
            if self.tree_list.item(i).data(Qt.UserRole) == tree_id:
                self.tree_list.setCurrentRow(i)
                break
        tree = self.project.trees.get(tree_id)
        if tree:
            self.canvas.set_tree(tree, self.project.settings)
            self.canvas.select_node(node_id)
            node = tree.nodes.get(node_id)
            if node:
                self.canvas.centerOn(node.x + self.project.settings.node_width/2, node.y + self.project.settings.node_height/2)


# ══════════════════════════════════════════════════════════════
#  ADDITION FUNCTIONS AND CLASSES FOR IMPORT
# ══════════════════════════════════════════════════════════════

def remove_json_comments(json_str: str) -> str:
    pattern = r'("(?:\\.|[^"\\])*")|//.*|/\*[\s\S]*?\*/'
    def replacer(match):
        if match.group(1):
            return match.group(1)
        return ' '
    clean = re.sub(pattern, replacer, json_str)
    clean = re.sub(r',(\s*[\]}])', r'\1', clean)
    return clean


class ImportTreeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт дерева из JSON")
        self.resize(750, 650)
        self.imported_tree = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel("Вставьте JSON-код дерева ниже. Вы можете использовать шаблон в качестве основы.\n"
                     "Поддерживаются комментарии (// и /* */), а также висячие запятые — они будут автоматически очищены.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setPlainText(self._get_template())
        layout.addWidget(self.text_edit)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: red; font-weight: bold;")
        self.error_lbl.setWordWrap(True)
        layout.addWidget(self.error_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_import = QPushButton("Добавить дерево")
        self.btn_import.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_import.setStyleSheet(
            "background-color: #10b981; color: white; padding: 10px; border-radius: 4px;"
        )
        self.btn_import.clicked.connect(self._try_import)
        btn_layout.addWidget(self.btn_import)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("padding: 10px;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _get_template(self):
        return """{
    // Название вашего дерева
    "title": "Название нового дерева",
    
    // ID корневого узла (должен совпадать с одним из id в списке nodes)
    "root_id": "node_1",
    
    /* 
       Список всех узлов дерева.
       Каждый узел должен иметь уникальный id.
       parents и children — это массивы id связанных узлов.
    */
    "nodes": [
        {
            "id": "node_1",
            "title": "Главный вопрос или концепция. Их рекомендуется формулировать так, чтобы они были понятны независимо от других узлов, то есть в полном виде и эксплицидно (чтобы не рушить случайное повторение в learning mode)",
            "note": "Ответ или подробное описание.",
            "parents": [],
            "children": ["node_2"],
            "x": 400, // Координата X (можно не указывать)
            "y": 50   // Координата Y
        },
        {
            "id": "node_2",
            "title": "Уточняющий вопрос",
            "note": "Детали, которые развивают тему.",
            "parents": ["node_1"],
            "children": [],
        }
    ]
}"""

    def _try_import(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.error_lbl.setText("Поле ввода пустое.")
            return

        clean_text = remove_json_comments(text)
        
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError as e:
            self.error_lbl.setText(f"Ошибка синтаксиса JSON: {e.msg} (строка {e.lineno}, колонка {e.colno}).")
            return

        is_valid, err_msg = self._validate(data)
        if not is_valid:
            self.error_lbl.setText(f"Ошибка структуры: {err_msg}")
            return

        try:
            tree = BasaltTree.from_dict(data)
            tree.id = new_id() 
            self.imported_tree = tree
            self.accept()
        except Exception as e:
            self.error_lbl.setText(f"Непредвиденная ошибка при создании дерева: {e}")

    def _validate(self, data):
        if not isinstance(data, dict):
            return False, "Ожидается JSON-объект (словарь) в корне."
        
        if "title" not in data or not isinstance(data.get("title"), str):
            return False, "Отсутствует или некорректно поле 'title' (должно быть строкой)."
            
        if "nodes" not in data:
            return False, "Отсутствует поле 'nodes'."
            
        nodes_data = data["nodes"]
        if isinstance(nodes_data, dict):
            nodes_list = list(nodes_data.values())
        elif isinstance(nodes_data, list):
            nodes_list = nodes_data
        else:
            return False, "Поле 'nodes' должно быть списком или словарем."
            
        if not nodes_list:
            return False, "Список узлов 'nodes' пуст."
            
        node_ids = set()
        for n in nodes_list:
            if not isinstance(n, dict):
                return False, "Каждый узел в 'nodes' должен быть объектом."
            if "id" not in n:
                return False, "У одного из узлов отсутствует поле 'id'."
            node_ids.add(str(n["id"]))
            
        for n in nodes_list:
            for p in n.get("parents", []):
                if str(p) not in node_ids:
                    return False, f"Узел '{n.get('id')}' ссылается на несуществующего родителя '{p}'."
            for c in n.get("children", []):
                if str(c) not in node_ids:
                    return False, f"Узел '{n.get('id')}' ссылается на несуществующего потомка '{c}'."
                    
        root_id = data.get("root_id")
        if root_id and str(root_id) not in node_ids:
            return False, f"Указанный root_id '{root_id}' не найден среди узлов."
            
        if not root_id:
            has_root = any(not n.get("parents") for n in nodes_list)
            if not has_root:
                return False, "Не указан root_id, и нет ни одного узла без родителей."
                
        return True, ""


class AddParentDialog(QDialog):
    def __init__(self, project: BasaltProject, current_tree_id: str, node_id: str, parent=None):
        super().__init__(parent)
        self.project = project
        self.current_tree_id = current_tree_id
        self.node_id = node_id
        self.choice = "new"
        self.selected_node_id = None
        self.setWindowTitle("Добавить родительский узел")
        self.resize(560, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.rb_new = QRadioButton("➕ Создать новый родительский узел")
        self.rb_existing = QRadioButton("🔎 Выбрать существующий узел")
        self.rb_new.setChecked(True)

        grp = QButtonGroup(self)
        grp.addButton(self.rb_new)
        grp.addButton(self.rb_existing)
        layout.addWidget(self.rb_new)
        layout.addWidget(self.rb_existing)

        self.node_list = QListWidget()
        self.node_list.setEnabled(False)

        self._populate_node_list()
        self.rb_existing.toggled.connect(lambda c: self.node_list.setEnabled(c))
        layout.addWidget(self.node_list)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet(
            "background-color: #3772d6; color: white; padding: 8px; border-radius: 4px;"
        )
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _populate_node_list(self):
        descendants = self._collect_descendants()

        for tree in self.project.trees.values():
            header = QListWidgetItem(f"━━━ {tree.title} ━━━")
            header.setFlags(header.flags() & ~Qt.ItemIsEnabled)
            font = header.font(); font.setBold(True); header.setFont(font)
            self.node_list.addItem(header)

            if not tree.root_id:
                continue

            visited = set()
            def add_node(nid, depth=0):
                if nid in visited or nid not in tree.nodes: return
                visited.add(nid)
                n = tree.nodes[nid]

                is_locked = (nid in descendants) or (tree.id != self.current_tree_id)
                lock_text = ""
                if nid in descendants:
                    lock_text = " (нельзя: потомок)"
                elif tree.id != self.current_tree_id:
                    lock_text = " (только внутри дерева)"

                prefix = "   " * depth
                item = QListWidgetItem(prefix + n.title + lock_text)
                item.setData(Qt.UserRole, (tree.id, nid))
                if is_locked:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                self.node_list.addItem(item)

                for c in n.children:
                    add_node(c, depth + 1)

            add_node(tree.root_id)

    def _collect_descendants(self) -> set:
        tree = self.project.trees.get(self.current_tree_id)
        if not tree or self.node_id not in tree.nodes:
            return set()
        result = {self.node_id}
        stack = list(tree.nodes[self.node_id].children)
        while stack:
            nid = stack.pop()
            if nid in result or nid not in tree.nodes: continue
            result.add(nid)
            stack.extend(tree.nodes[nid].children)
        return result

    def _on_accept(self):
        if self.rb_new.isChecked():
            self.choice = "new"
        else:
            item = self.node_list.currentItem()
            if not item or not (item.flags() & Qt.ItemIsEnabled):
                QMessageBox.warning(self, "Ошибка", "Выберите доступный узел из списка.")
                return
            data = item.data(Qt.UserRole)
            if not data: return
            tree_id, node_id = data
            if tree_id != self.current_tree_id:
                QMessageBox.warning(
                    self, "Ограничение",
                    "Перемещение узлов между деревьями пока не поддерживается.\n"
                    "Выберите узел в текущем дереве."
                )
                return
            self.choice = "existing"
            self.selected_node_id = node_id
        self.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())