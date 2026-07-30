import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QToolBar, QAction, QFileDialog, QMessageBox, QListWidget, 
    QListWidgetItem, QLabel, QAbstractItemView
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QTimer

from basalt_node import BasaltProject, BasaltTree
from basalt_canvas import BasaltCanvas
from learning_mode import LearningDialog
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
    painter.setPen(Qt.NoPen)
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
        
        self.project = BasaltProject()
        self.current_tree_id = None
        self._pending_tree = None
        self._is_new_tree = False
        
        self._setup_ui()
        self._setup_toolbar()
        self._init_dummy_data()
        
        if self.project.trees:
            self.tree_list.setCurrentRow(0)

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
        self.tree_list.currentRowChanged.connect(self._on_tree_selected)
        sidebar_layout.addWidget(self.tree_list)
        
        self.canvas = BasaltCanvas()
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.node_changed.connect(self._on_node_changed)
        self.canvas.link_clicked.connect(self._navigate_to_tree)
        
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
        
        self.act_new_tree = QAction("➕ Новое дерево", self)
        self.act_new_tree.triggered.connect(self.add_new_tree)
        toolbar.addAction(self.act_new_tree)
        
        toolbar.addSeparator()
        
        self.act_add_child = QAction("➕ Дочерний узел", self)
        self.act_add_child.triggered.connect(self.add_child_node)
        toolbar.addAction(self.act_add_child)
        
        self.act_add_parent = QAction("🔼 Родительский узел", self)
        self.act_add_parent.triggered.connect(self.add_parent_node)
        toolbar.addAction(self.act_add_parent)
        
        self.act_delete = QAction("❌ Удалить узел", self)
        self.act_delete.triggered.connect(self.delete_node)
        toolbar.addAction(self.act_delete)

        self.act_layout = QAction("📐 Выровнять дерево", self)
        self.act_layout.triggered.connect(self.auto_layout)
        toolbar.addAction(self.act_layout)
        
        toolbar.addSeparator()

        self.act_settings = QAction("⚙️ Настройки вида", self)
        self.act_settings.triggered.connect(self.open_settings)
        toolbar.addAction(self.act_settings)

        toolbar.addSeparator()
        
        self.act_learn = QAction("🧠 Начать обучение", self)
        self.act_learn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.act_learn.triggered.connect(self.start_learning)
        toolbar.addAction(self.act_learn)
        
        toolbar.addSeparator()
        
        self.act_export = QAction("💾 Экспорт БД", self)
        self.act_export.triggered.connect(self.export_project)
        toolbar.addAction(self.act_export)
        
        self.act_import = QAction("📂 Импорт БД", self)
        self.act_import.triggered.connect(self.import_project)
        toolbar.addAction(self.act_import)

    def _init_dummy_data(self):
        tree1 = self.project.add_tree("Структура клетки")
        root = tree1.nodes[tree1.root_id]
        root.title = "Клетка"
        root.note = "Базовая структурная единица всех живых организмов. См. также [[Биология]]."
        
        c1 = tree1.add_child(root.id, "Ядро")
        c1.note = "Хранит генетическую информацию (ДНК)."
        tree1.add_child(c1.id, "Ядерная пора (NPC)")
        
        c2 = tree1.add_child(root.id, "Цитоплазма")
        c2.note = "Внутренняя среда клетки. См. [[Биология]]."

        tree2 = self.project.add_tree("Биология")
        root2 = tree2.nodes[tree2.root_id]
        root2.title = "Биология"
        root2.note = "Наука о живых организмах. См. [[Структура клетки]]."
        
        self._refresh_tree_list()
        self.auto_layout()

    def _refresh_tree_list(self):
        self.tree_list.clear()
        for tree in self.project.trees.values():
            item = QListWidgetItem(tree.title)
            item.setData(Qt.UserRole, tree.id)
            self.tree_list.addItem(item)

    def _on_tree_selected(self, row):
        if row < 0: return
        item = self.tree_list.item(row)
        tree_id = item.data(Qt.UserRole)
        self.current_tree_id = tree_id
        tree = self.project.trees.get(tree_id)
        if tree:
            self.canvas.set_tree(tree, self.project.settings)

    def _on_node_selected(self, node_id: str):
        pass 

    def _on_node_changed(self, node_id: str):
        tree = self.project.trees.get(self.current_tree_id)
        if tree and node_id in tree.nodes:
            if node_id == tree.root_id:
                self._refresh_tree_list()
                for i in range(self.tree_list.count()):
                    if self.tree_list.item(i).data(Qt.UserRole) == tree.id:
                        self.tree_list.setCurrentRow(i)
                        break

    def _navigate_to_tree(self, target_title: str):
        """Переход по wiki-ссылке. Если дерева нет - создает его автоматически."""
        target_title = target_title.strip()
        if not target_title:
            return

        target_tree = self.project.find_tree_by_title(target_title)
        self._is_new_tree = False
        
        if not target_tree:
            target_tree = self.project.add_tree(target_title)
            target_tree.layout_tree(self.project.settings)
            self._is_new_tree = True
            
        # СОХРАНЯЕМ дерево и ОТКЛАДЫВАЕМ навигацию.
        # Это критически важно, чтобы избежать краша Qt при удалении виджета,
        # который только что сгенерировал событие клика по ссылке.
        self._pending_tree = target_tree
        QTimer.singleShot(0, self._apply_navigation)

    def _apply_navigation(self):
        """Выполняется на следующем тике event loop, когда событие клика уже завершено."""
        target_tree = self._pending_tree
        if not target_tree:
            return
            
        if self._is_new_tree:
            QMessageBox.information(self, "Создано новое дерево", 
                                    f"Дерево «{target_tree.title}» не существовало и было создано автоматически.\n"
                                    "Начни заполнять его прямо сейчас!")
            
        self.current_tree_id = target_tree.id
        self._refresh_tree_list()
        
        for i in range(self.tree_list.count()):
            if self.tree_list.item(i).data(Qt.UserRole) == target_tree.id:
                self.tree_list.setCurrentRow(i)
                break
                
        # Теперь безопасно перерисовываем сцену
        self.canvas.set_tree(target_tree, self.project.settings)
        self._pending_tree = None

    def add_new_tree(self):
        tree = self.project.add_tree("Новое дерево")
        self._refresh_tree_list()
        self.tree_list.setCurrentRow(self.tree_list.count() - 1)

    def add_child_node(self):
        if not self.canvas.selected_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел.")
            return
        tree = self.project.trees[self.current_tree_id]
        new_node = tree.add_child(self.canvas.selected_id, "Новый дочерний узел")
        tree.layout_tree(self.project.settings)
        self.canvas.set_tree(tree, self.project.settings)
        self.canvas.select_node(new_node.id)

    def add_parent_node(self):
        if not self.canvas.selected_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел.")
            return
        tree = self.project.trees[self.current_tree_id]
        new_node = tree.add_parent(self.canvas.selected_id, "Новый родитель")
        tree.layout_tree(self.project.settings)
        self.canvas.set_tree(tree, self.project.settings)
        self.canvas.select_node(new_node.id)

    def delete_node(self):
        if not self.canvas.selected_id: return
        reply = QMessageBox.question(self, "Подтверждение", "Удалить узел и его ветку?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            tree = self.project.trees[self.current_tree_id]
            tree.remove_node(self.canvas.selected_id)
            self.canvas.selected_id = None
            tree.layout_tree(self.project.settings)
            self.canvas.set_tree(tree, self.project.settings)

    def auto_layout(self):
        tree = self.project.trees.get(self.current_tree_id)
        if tree:
            tree.layout_tree(self.project.settings)
            self.canvas.set_tree(tree, self.project.settings)

    def open_settings(self):
        dialog = SettingsDialog(self.project.settings, self)
        if dialog.exec_():
            self.project.settings = dialog.get_settings()
            self.auto_layout()

    def start_learning(self):
        dialog = LearningDialog(self.project, self)
        dialog.exec_()

    def export_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт базы знаний", "basalt_db.json", "JSON (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.project.to_json())
            QMessageBox.information(self, "Успех", "База знаний экспортирована.")

    def import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт базы знаний", "", "JSON (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.project = BasaltProject.from_json(f.read())
                self._refresh_tree_list()
                if self.project.trees:
                    self.tree_list.setCurrentRow(0)
                QMessageBox.information(self, "Успех", "База знаний импортирована.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка импорта:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())