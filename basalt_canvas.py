"""Canvas-based tree visualisation using PyQt (Top-Down orientation)."""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QWheelEvent, QMouseEvent
from PyQt5.QtCore import Qt, pyqtSignal
from basalt_node import BasaltTree, LayoutSettings
from ui_node import UINode

class BasaltCanvas(QGraphicsView):
    node_selected = pyqtSignal(str)
    node_changed = pyqtSignal(str)
    link_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.tree: BasaltTree = None
        self.settings: LayoutSettings = LayoutSettings()
        self.ui_nodes = {}
        self.selected_id = None
        self.collapsed_nodes = set()
        self._panning = False
        self._last_pos = None

    def set_tree(self, tree: BasaltTree, settings: LayoutSettings):
        self.tree = tree
        self.settings = settings
        self.selected_id = None
        self.collapsed_nodes.clear()
        self.redraw()

    def update_settings(self, settings: LayoutSettings):
        self.settings = settings
        if self.tree:
            self.tree.layout_tree(self.settings)
            self.redraw()

    def select_node(self, node_id: str):
        if self.selected_id == node_id: return
        old_id = self.selected_id
        self.selected_id = node_id
        
        if old_id and old_id in self.ui_nodes:
            self.ui_nodes[old_id].set_selected(False)
        if node_id in self.ui_nodes:
            self.ui_nodes[node_id].set_selected(True)
            
        self.node_selected.emit(node_id)

    def redraw(self):
        self.scene.clear()
        self.ui_nodes.clear()
        if not self.tree or not self.tree.nodes: return

        visible_ids = set()
        def collect_visible(nid):
            if nid not in self.tree.nodes: return
            visible_ids.add(nid)
            if nid not in self.collapsed_nodes:
                for cid in self.tree.nodes[nid].children: collect_visible(cid)
        
        if self.tree.root_id: collect_visible(self.tree.root_id)

        # Рисуем связи
        for nid in visible_ids:
            node = self.tree.nodes[nid]
            for cid in node.children:
                if cid in visible_ids: self._draw_link(node, self.tree.nodes[cid])

        # Рисуем узлы
        for nid in visible_ids:
            node = self.tree.nodes[nid]
            ui_node = UINode(node, self, self.settings)
            ui_node.set_selected(nid == self.selected_id)
            self.scene.addItem(ui_node)
            self.ui_nodes[nid] = ui_node

    def _draw_link(self, parent_node, child_node):
        w = self.settings.node_width
        h = self.settings.node_height
        
        start_x = parent_node.x + w / 2
        start_y = parent_node.y + h
        end_x = child_node.x + w / 2
        end_y = child_node.y
        
        path = QPainterPath()
        path.moveTo(start_x, start_y)
        path.cubicTo(start_x, start_y + 40, end_x, end_y - 40, end_x, end_y)
        
        self.scene.addPath(path, QPen(QColor("#aab2bf"), 2))

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
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
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)