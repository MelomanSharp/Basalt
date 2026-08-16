"""Canvas-based tree visualisation using PyQt (Top-Down orientation)."""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsProxyWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QWheelEvent, QMouseEvent
from PyQt5.QtCore import Qt, pyqtSignal
from basalt_node import BasaltTree, LayoutSettings
from ui_node import UINode


class BasaltCanvas(QGraphicsView):
    node_selected = pyqtSignal(str)
    node_changed = pyqtSignal(str)
    link_clicked = pyqtSignal(str)
    add_child_requested = pyqtSignal(str)
    add_parent_requested = pyqtSignal(str)
    delete_node_requested = pyqtSignal(str)

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

    def select_node(self, node_id: str | None):
        if self.selected_id == node_id: return
        old_id = self.selected_id
        self.selected_id = node_id

        self.scene.setFocusItem(None) # now we change focus from any widget to make focusOutEvent work and our description was saved

        if old_id and old_id in self.ui_nodes:
            self.ui_nodes[old_id].set_selected(False)
        if node_id and node_id in self.ui_nodes:
            self.ui_nodes[node_id].set_selected(True)

        if node_id:
            self.node_selected.emit(node_id)

    def redraw(self):
        self.scene.setFocusItem(None)
        for ui_node in self.ui_nodes.values():
            try:
                w = ui_node.widget
                if w is not None:
                    w.title_edit.blockSignals(True)
                    if w.note_edit is not None:
                        w.note_edit.blockSignals(True)
            except RuntimeError:
                pass

        self.scene.clear()
        self.ui_nodes.clear()
        if not self.tree or not self.tree.nodes: return

        visible_ids = set()
        def collect_visible(nid, visited=None):
            if visited is None: visited = set()
            if nid in visited or nid not in self.tree.nodes: return
            visited.add(nid)
            visible_ids.add(nid)
            if nid not in self.collapsed_nodes:
                for cid in self.tree.nodes[nid].children:
                    collect_visible(cid, visited)

        if self.tree.root_id:
            collect_visible(self.tree.root_id)

        # Draw links (accounting for multiple parents)
        drawn_links = set()
        for nid in visible_ids:
            node = self.tree.nodes[nid]
            for cid in node.children:
                if cid in visible_ids:
                    key = tuple(sorted((nid, cid)))
                    if key not in drawn_links:
                        self._draw_link(node, self.tree.nodes[cid])
                        drawn_links.add(key)

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

    # ── NEW: LMB on empty space = panning ─────────
    def _hit_node(self, event: QMouseEvent) -> bool:
        """Returns True if the click hit any node."""
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())
        while item:
            if isinstance(item, UINode) or isinstance(item, QGraphicsProxyWidget):
                return True
            item = item.parentItem()
        return False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if not self._hit_node(event):
                # Click on empty space: clear selection and enable panning
                if self.selected_id:
                    self.select_node(None)
                self._panning = True
                self._last_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
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
        if event.button() in (Qt.LeftButton, Qt.MiddleButton, Qt.RightButton):
            if self._panning:
                self._panning = False
                self.setCursor(Qt.ArrowCursor)
                event.accept()
                return
        super().mouseReleaseEvent(event)