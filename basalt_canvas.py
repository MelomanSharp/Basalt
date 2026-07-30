"""Canvas-based tree visualisation using PyQt."""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QWheelEvent, QMouseEvent
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from basalt_node import BasaltTree
from ui_node import UINode


class BasaltCanvas(QGraphicsView):
    """Бесконечный холст с поддержкой масштабирования и панорамирования"""
    node_selected = pyqtSignal(str)  # Сигнал при клике на узел

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        
        # Отключаем стандартный DragMode, чтобы левая кнопка мыши работала для узлов
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.tree: BasaltTree = None
        self.ui_nodes = {}
        self.selected_id = None
        self.collapsed_nodes = set()
        
        # Для панорамирования (ПКМ или СКМ)
        self._panning = False
        self._last_pos = None

    def set_tree(self, tree: BasaltTree):
        self.tree = tree
        self.selected_id = None
        self.collapsed_nodes.clear()
        self.redraw()

    def select_node(self, node_id: str):
        if self.selected_id == node_id:
            return
        self.selected_id = node_id
        for nid, ui_node in self.ui_nodes.items():
            ui_node.set_selected(nid == node_id)
        self.node_selected.emit(node_id)

    def toggle_collapse(self, node_id: str):
        if node_id in self.collapsed_nodes:
            self.collapsed_nodes.remove(node_id)
        else:
            self.collapsed_nodes.add(node_id)
        self.redraw()

    def redraw(self):
        self.scene.clear()
        self.ui_nodes.clear()
        if not self.tree or not self.tree.nodes:
            return

        visible_ids = set()
        def collect_visible(nid):
            if nid not in self.tree.nodes: return
            visible_ids.add(nid)
            if nid not in self.collapsed_nodes:
                for child_id in self.tree.nodes[nid].children:
                    collect_visible(child_id)
        
        if self.tree.root_id:
            collect_visible(self.tree.root_id)

        # Рисуем связи
        for nid in visible_ids:
            node = self.tree.nodes[nid]
            for child_id in node.children:
                if child_id in visible_ids:
                    self._draw_link(node, self.tree.nodes[child_id])

        # Рисуем узлы
        for nid in visible_ids:
            node = self.tree.nodes[nid]
            ui_node = UINode(node, self)
            ui_node.set_selected(nid == self.selected_id)
            self.scene.addItem(ui_node)
            self.ui_nodes[nid] = ui_node

    def _draw_link(self, parent_node, child_node):
        start_x = parent_node.x + UINode.WIDTH
        start_y = parent_node.y + UINode.HEIGHT / 2
        end_x = child_node.x
        end_y = child_node.y + UINode.HEIGHT / 2
        
        path = QPainterPath()
        path.moveTo(start_x, start_y)
        
        # Красивая кривая Безье
        ctrl1_x = start_x + 50
        ctrl2_x = end_x - 50
        path.cubicTo(ctrl1_x, start_y, ctrl2_x, end_y, end_x, end_y)
        
        pen = QPen(QColor("#aab2bf"), 2)
        self.scene.addPath(path, pen)

    # --- Обработка событий мыши ---

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._panning = True
            self._last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.pos() - self._last_pos
            self._last_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)