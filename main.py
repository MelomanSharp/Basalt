import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QToolBar, QAction, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

from basalt_node import BasaltTree, BasaltNode
from basalt_canvas import BasaltCanvas
from ui_node import NodeInspector


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Basalt - Knowledge Tree")
        self.resize(1200, 800)
        
        self.current_tree = BasaltTree(title="Структура клетки")
        
        self._setup_ui()
        self._setup_toolbar()
        self._init_dummy_data()
        
        self.canvas.set_tree(self.current_tree)

    def _setup_ui(self):
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Сплиттер: Холст слева, Инспектор справа
        self.splitter = QSplitter(Qt.Horizontal)
        
        self.canvas = BasaltCanvas()
        self.canvas.node_selected.connect(self._on_node_selected)
        
        self.inspector = NodeInspector()
        self.inspector.save_requested.connect(self._on_save_node)
        self.inspector.setMaximumWidth(350)
        
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)

    def _setup_toolbar(self):
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)
        
        # Действия
        self.act_add_child = QAction("➕ Дочерний узел", self)
        self.act_add_child.triggered.connect(self.add_child_node)
        toolbar.addAction(self.act_add_child)
        
        self.act_add_parent = QAction("🔼 Родительский узел", self)
        self.act_add_parent.triggered.connect(self.add_parent_node)
        toolbar.addAction(self.act_add_parent)
        
        self.act_delete = QAction("❌ Удалить узел", self)
        self.act_delete.triggered.connect(self.delete_node)
        toolbar.addAction(self.act_delete)
        
        toolbar.addSeparator()
        
        self.act_export = QAction("💾 Экспорт JSON", self)
        self.act_export.triggered.connect(self.export_json)
        toolbar.addAction(self.act_export)
        
        self.act_import = QAction("📂 Импорт JSON", self)
        self.act_import.triggered.connect(self.import_json)
        toolbar.addAction(self.act_import)

    def _init_dummy_data(self):
        # Создаем тестовые данные через новый API
        root = self.current_tree.create_root("Клетка")
        root.note = "Базовая структурная единица всех живых организмов."
        
        child1 = self.current_tree.add_child(root.id, "Ядро")
        child1.note = "Хранит генетическую информацию (ДНК)."
        
        child2 = self.current_tree.add_child(root.id, "Цитоплазма")
        child2.note = "Внутренняя среда клетки, обеспечивает обмен веществ."
        
        subchild = self.current_tree.add_child(child1.id, "Ядерная пора (NPC)")
        subchild.note = "Канал для транспорта молекул между ядром и цитоплазмой."

    def _on_node_selected(self, node_id: str):
        if node_id in self.current_tree.nodes:
            node = self.current_tree.nodes[node_id]
            self.inspector.show_node(node)
        else:
            self.inspector.clear()

    def _on_save_node(self, node_id: str, title: str, note: str):
        if node_id in self.current_tree.nodes:
            node = self.current_tree.nodes[node_id]
            node.title = title
            node.note = note
            self.canvas.redraw()

    def add_child_node(self):
        if not self.canvas.selected_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел на холсте.")
            return
        new_node = self.current_tree.add_child(self.canvas.selected_id, "Новый дочерний узел")
        self.canvas.redraw()
        self.canvas.select_node(new_node.id)

    def add_parent_node(self):
        if not self.canvas.selected_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите узел на холсте.")
            return
        if self.current_tree.root_id == self.canvas.selected_id:
            new_node = self.current_tree.add_parent(self.canvas.selected_id, "Новый корень")
        else:
            new_node = self.current_tree.add_parent(self.canvas.selected_id, "Новый родитель")
        self.canvas.redraw()
        self.canvas.select_node(new_node.id)

    def delete_node(self):
        if not self.canvas.selected_id:
            return
        reply = QMessageBox.question(self, "Подтверждение", "Удалить узел и все его дочерние элементы?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.current_tree.remove_node(self.canvas.selected_id)
            self.inspector.clear()
            self.canvas.selected_id = None
            self.canvas.redraw()

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в JSON", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.current_tree.to_json())
            QMessageBox.information(self, "Успех", "Дерево успешно экспортировано.")

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт из JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.current_tree = BasaltTree.from_json(data)
                self.canvas.set_tree(self.current_tree)
                self.inspector.clear()
                QMessageBox.information(self, "Успех", "Дерево успешно импортировано.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать файл:\n{e}")


if __name__ == "__main__":
    # Базовая настройка стиля приложения
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())