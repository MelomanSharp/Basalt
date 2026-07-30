"""Domain model and persistence helpers for Basalt."""

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

def new_id() -> str:
    return uuid4().hex

@dataclass
class LayoutSettings:
    """Настройки отображения и выравнивания дерева"""
    h_spacing: int = 40      # Горизонтальный отступ между узлами
    v_spacing: int = 60      # Вертикальный отступ между уровнями
    node_width: int = 260    # Ширина узла
    node_height: int = 140   # Высота узла
    text_align: str = "left" # Выравнивание текста: left, center, right

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "LayoutSettings":
        if not data: return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Review:
    due: str = field(default_factory=lambda: date.today().isoformat())
    interval: int = 0
    ease: float = 2.5
    repetitions: int = 0

    def schedule(self, grade: int) -> None:
        grade = max(0, min(5, int(grade)))
        today = date.today()
        if grade < 3:
            self.repetitions = 0
            self.interval = 1
        else:
            self.repetitions += 1
            if self.repetitions == 1: self.interval = 1
            elif self.repetitions == 2: self.interval = 6
            else: self.interval = max(1, round(self.interval * self.ease))
        self.ease = max(1.3, self.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)))
        self.due = (today + timedelta(days=self.interval)).isoformat()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Review":
        data = data or {}
        return cls(due=str(data.get("due") or date.today().isoformat()),
                   interval=int(data.get("interval", 0)),
                   ease=float(data.get("ease", 2.5)),
                   repetitions=int(data.get("repetitions", 0)))

@dataclass
class BasaltNode:
    id: str = field(default_factory=new_id)
    title: str = "Новый узел"
    note: str = ""
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    review: Review = field(default_factory=Review)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["review"] = asdict(self.review)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasaltNode":
        return cls(id=str(data.get("id") or new_id()), title=str(data.get("title", "Новый узел")),
                   note=str(data.get("note", "")), parent_id=data.get("parent_id"),
                   children=list(data.get("children", [])), x=float(data.get("x", 0)),
                   y=float(data.get("y", 0)), review=Review.from_dict(data.get("review")))

@dataclass
class BasaltTree:
    id: str = field(default_factory=new_id)
    title: str = "Новое дерево"
    root_id: str | None = None
    nodes: dict[str, BasaltNode] = field(default_factory=dict)

    def create_root(self, title: str = "Главная идея") -> BasaltNode:
        node = BasaltNode(title=title, x=400, y=50)
        self.nodes[node.id] = node
        self.root_id = node.id
        return node

    def add_child(self, parent_id: str, title: str = "Новый узел") -> BasaltNode:
        parent = self.nodes[parent_id]
        # Просто добавляем, координаты потом выровняются алгоритмом
        node = BasaltNode(title=title, parent_id=parent_id, x=parent.x, y=parent.y + 160)
        self.nodes[node.id] = node
        parent.children.append(node.id)
        return node

    def add_parent(self, child_id: str, title: str = "Новый родитель") -> BasaltNode:
        child = self.nodes[child_id]
        parent = BasaltNode(title=title, x=child.x, y=child.y - 160)
        old_parent = child.parent_id
        parent.children.append(child.id)
        parent.parent_id = old_parent
        self.nodes[parent.id] = parent
        child.parent_id = parent.id
        if old_parent and old_parent in self.nodes:
            siblings = self.nodes[old_parent].children
            siblings[siblings.index(child.id)] = parent.id
        else:
            self.root_id = parent.id
        return parent

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes: return
        node = self.nodes[node_id]
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].children = [i for i in self.nodes[node.parent_id].children if i != node_id]
        doomed = []
        def visit(iid):
            doomed.append(iid)
            for cid in self.nodes[iid].children: visit(cid)
        visit(node_id)
        for iid in doomed: self.nodes.pop(iid, None)
        if self.root_id == node_id: self.root_id = None

    def layout_tree(self, settings: LayoutSettings):
        """Идеальный алгоритм выравнивания без наложений (Reingold-Tilford style)"""
        if not self.root_id: return
        
        w = settings.node_width
        h = settings.node_height
        h_gap = settings.h_spacing
        v_gap = settings.v_spacing

        # 1. Считаем точную ширину каждого поддерева
        widths = {}
        def calc_width(nid):
            node = self.nodes[nid]
            if not node.children:
                widths[nid] = w
                return w
            # Ширина детей + отступы между ними
            children_width = sum(calc_width(c) for c in node.children) + h_gap * (len(node.children) - 1)
            widths[nid] = max(w, children_width)
            return widths[nid]

        calc_width(self.root_id)

        # 2. Расставляем координаты
        def assign_pos(nid, x, y):
            node = self.nodes[nid]
            node_w = widths[nid]
            # Центрируем сам узел в пределах его поддерева
            node.x = x + (node_w - w) / 2
            node.y = y

            if node.children:
                total_children_w = sum(widths[c] for c in node.children) + h_gap * (len(node.children) - 1)
                # Начинаем рисовать детей так, чтобы они были центрированы под родителем
                curr_x = x + (node_w - total_children_w) / 2
                for c in node.children:
                    assign_pos(c, curr_x, y + h + v_gap)
                    curr_x += widths[c] + h_gap

        assign_pos(self.root_id, 0, 0)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "root_id": self.root_id,
                "nodes": [n.to_dict() for n in self.nodes.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasaltTree":
        tree = cls(id=str(data.get("id") or new_id()), title=str(data.get("title", "Без названия")), root_id=data.get("root_id"))
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict): raw_nodes = raw_nodes.values()
        tree.nodes = {n.id: n for n in (BasaltNode.from_dict(r) for r in raw_nodes)}
        for n in tree.nodes.values():
            n.children = [c for c in n.children if c in tree.nodes]
            if n.parent_id in tree.nodes and n.id not in tree.nodes[n.parent_id].children:
                tree.nodes[n.parent_id].children.append(n.id)
        if tree.root_id not in tree.nodes:
            roots = [n.id for n in tree.nodes.values() if not n.parent_id]
            tree.root_id = roots[0] if roots else None
        return tree

@dataclass
class BasaltProject:
    trees: dict[str, BasaltTree] = field(default_factory=dict)
    settings: LayoutSettings = field(default_factory=LayoutSettings)

    def add_tree(self, title: str = "Новое дерево") -> BasaltTree:
        tree = BasaltTree(title=title)
        tree.create_root(title)
        self.trees[tree.id] = tree
        return tree

    def find_tree_by_title(self, title: str) -> BasaltTree | None:
        for tree in self.trees.values():
            if tree.title.strip().lower() == title.strip().lower():
                return tree
        return None

    def get_all_due_nodes(self) -> list[BasaltNode]:
        today = date.today().isoformat()
        due = []
        for tree in self.trees.values():
            due.extend([n for n in tree.nodes.values() if n.review.due <= today])
        return due

    def to_json(self) -> str:
        return json.dumps({
            "trees": [t.to_dict() for t in self.trees.values()],
            "settings": self.settings.to_dict()
        }, indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "BasaltProject":
        data = json.loads(json_str)
        proj = cls()
        proj.settings = LayoutSettings.from_dict(data.get("settings"))
        for t_data in data.get("trees", []):
            tree = BasaltTree.from_dict(t_data)
            proj.trees[tree.id] = tree
        return proj