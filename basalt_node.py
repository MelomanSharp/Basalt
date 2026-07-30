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
class Review:
    due: str = field(default_factory=lambda: date.today().isoformat())
    interval: int = 0
    ease: float = 2.5
    repetitions: int = 0

    def schedule(self, grade: int) -> None:
        """Update an SM-2-inspired schedule after a 0..5 self-assessment."""
        grade = max(0, min(5, int(grade)))
        today = date.today()
        if grade < 3:
            self.repetitions = 0
            self.interval = 1
        else:
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval = 1
            elif self.repetitions == 2:
                self.interval = 6
            else:
                self.interval = max(1, round(self.interval * self.ease))
        self.ease = max(1.3, self.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)))
        self.due = (today + timedelta(days=self.interval)).isoformat()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Review":
        data = data or {}
        return cls(
            due=str(data.get("due") or date.today().isoformat()),
            interval=int(data.get("interval", 0)),
            ease=float(data.get("ease", 2.5)),
            repetitions=int(data.get("repetitions", 0)),
        )


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
        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title", "Новый узел")),
            note=str(data.get("note", "")),
            parent_id=data.get("parent_id"),
            children=list(data.get("children", [])),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            review=Review.from_dict(data.get("review")),
        )


@dataclass
class BasaltTree:
    id: str = field(default_factory=new_id)
    title: str = "Новое дерево"
    root_id: str | None = None
    nodes: dict[str, BasaltNode] = field(default_factory=dict)

    def create_root(self, title: str = "Главная идея") -> BasaltNode:
        node = BasaltNode(title=title, x=80, y=80)
        self.nodes[node.id] = node
        self.root_id = node.id
        return node

    def add_child(self, parent_id: str, title: str = "Новый узел") -> BasaltNode:
        parent = self.nodes[parent_id]
        index = len(parent.children)
        node = BasaltNode(
            title=title,
            parent_id=parent_id,
            x=parent.x + 260,
            y=parent.y + index * 110,
        )
        self.nodes[node.id] = node
        parent.children.append(node.id)
        return node

    def add_parent(self, child_id: str, title: str = "Новый родитель") -> BasaltNode:
        child = self.nodes[child_id]
        parent = BasaltNode(title=title, x=child.x - 260, y=child.y)
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
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            parent.children = [item for item in parent.children if item != node_id]
        
        doomed: list[str] = []
        def visit(item_id: str) -> None:
            doomed.append(item_id)
            for child_id in self.nodes[item_id].children:
                if child_id in self.nodes:
                    visit(child_id)
        visit(node_id)
        
        for item_id in doomed:
            self.nodes.pop(item_id, None)
        if self.root_id == node_id:
            self.root_id = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "root_id": self.root_id,
                "nodes": [node.to_dict() for node in self.nodes.values()]}

    def to_json(self, indent=4) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasaltTree":
        tree = cls(id=str(data.get("id") or new_id()), title=str(data.get("title", "Без названия")),
                   root_id=data.get("root_id"))
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = raw_nodes.values()
        tree.nodes = {node.id: node for node in (BasaltNode.from_dict(raw) for raw in raw_nodes)}
        
        for node in tree.nodes.values():
            node.children = [child for child in node.children if child in tree.nodes]
        for node in tree.nodes.values():
            if node.parent_id in tree.nodes and node.id not in tree.nodes[node.parent_id].children:
                tree.nodes[node.parent_id].children.append(node.id)
        if tree.root_id not in tree.nodes:
            roots = [node.id for node in tree.nodes.values() if not node.parent_id]
            tree.root_id = roots[0] if roots else None
        return tree
        
    @classmethod
    def from_json(cls, json_str: str) -> "BasaltTree":
        return cls.from_dict(json.loads(json_str))