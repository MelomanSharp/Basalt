"""Domain model and persistence helpers for Basalt."""

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import uuid4
from i18n import tr

def new_id() -> str:
    return uuid4().hex

@dataclass
class LayoutSettings:
    """Display and tree layout settings"""
    h_spacing: int = 40
    v_spacing: int = 60
    node_width: int = 260
    node_height: int = 140
    text_align: str = "left"
    max_parents: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "LayoutSettings":
        if not data: return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TreeLearningConfig:
    """Learning settings for a single tree."""
    enabled: bool = True
    mode: str = "random"

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TreeLearningConfig":
        return cls(enabled=data.get("enabled", True), mode=data.get("mode", "random"))


@dataclass
class LearningCardSettings:
    """Learning card appearance settings."""
    font_family: str = "Segoe UI"
    font_size: int = 12
    card_width: int = 600
    card_height: int = 450
    window_position: str = "center"
    show_children_notes: bool = False

    def to_dict(self) -> dict: return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LearningCardSettings":
        if not data: return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LearningSettings:
    """Background learning mode settings."""
    interval_minutes: int = 1
    interval_seconds: int = 0
    random_order_trees: bool = True
    tree_configs: dict[str, TreeLearningConfig] = field(default_factory=dict)
    card_settings: LearningCardSettings = field(default_factory=LearningCardSettings)

    def get_interval_ms(self) -> int:
        return (self.interval_minutes * 60 + self.interval_seconds) * 1000

    def get_tree_config(self, tree_id: str) -> TreeLearningConfig:
        if tree_id not in self.tree_configs:
            self.tree_configs[tree_id] = TreeLearningConfig()
        return self.tree_configs[tree_id]

    def to_dict(self) -> dict:
        return {
            "interval_minutes": self.interval_minutes,
            "interval_seconds": self.interval_seconds,
            "random_order_trees": self.random_order_trees,
            "tree_configs": {k: v.to_dict() for k, v in self.tree_configs.items()},
            "card_settings": self.card_settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningSettings":
        ls = cls()
        ls.interval_minutes = data.get("interval_minutes", 1)
        ls.interval_seconds = data.get("interval_seconds", 0)
        ls.random_order_trees = data.get("random_order_trees", True)
        for k, v in data.get("tree_configs", {}).items():
            ls.tree_configs[k] = TreeLearningConfig.from_dict(v)
        if "card_settings" in data:
            ls.card_settings = LearningCardSettings.from_dict(data["card_settings"])
        return ls


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
        return cls(
            due=str(data.get("due") or date.today().isoformat()),
            interval=int(data.get("interval", 0)),
            ease=float(data.get("ease", 2.5)),
            repetitions=int(data.get("repetitions", 0)),
        )


@dataclass
class BasaltNode:
    id: str = field(default_factory=new_id)
    # Fallback to translation if created programmatically without title
    title: str = field(default_factory=lambda: tr("default_node_title"))
    note: str = ""
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    review: Review = field(default_factory=Review)

    @property
    def parent_id(self) -> str | None:
        return self.parents[0] if self.parents else None

    @parent_id.setter
    def parent_id(self, value: str | None):
        self.parents = [value] if value else []

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["review"] = asdict(self.review)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasaltNode":
        parents = data.get("parents")
        if parents is None and "parent_id" in data:
            parents = [data["parent_id"]] if data["parent_id"] else []
        if parents is None:
            parents = []
        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title", tr("default_node_title"))),
            note=str(data.get("note", "")),
            parents=list(parents),
            children=list(data.get("children", [])),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            review=Review.from_dict(data.get("review")),
        )


@dataclass
class BasaltTree:
    id: str = field(default_factory=new_id)
    title: str = field(default_factory=lambda: tr("default_tree_title"))
    root_id: str | None = None
    nodes: dict[str, BasaltNode] = field(default_factory=dict)

    def create_root(self, title: str | None = None) -> BasaltNode:
        if title is None: title = tr("default_root_title")
        node = BasaltNode(title=title, x=400, y=50)
        self.nodes[node.id] = node
        self.root_id = node.id
        return node

    def add_child(self, parent_id: str, title: str | None = None) -> BasaltNode:
        if title is None: title = tr("default_new_child")
        parent = self.nodes[parent_id]
        node = BasaltNode(title=title, parents=[parent_id], x=parent.x, y=parent.y + 160)
        self.nodes[node.id] = node
        parent.children.append(node.id)
        return node

    def add_parent(self, child_id: str, title: str | None = None) -> BasaltNode:
        if title is None: title = tr("default_new_parent")
        child = self.nodes[child_id]
        parent = BasaltNode(title=title, x=child.x, y=child.y - 160)
        old_parents = child.parents.copy()
        parent.children.append(child.id)
        parent.parents = old_parents
        self.nodes[parent.id] = parent
        child.parents = [parent.id]
        for old_p in old_parents:
            if old_p and old_p in self.nodes:
                sibs = self.nodes[old_p].children
                if child.id in sibs:
                    sibs[sibs.index(child.id)] = parent.id
        if not parent.parents:
            self.root_id = parent.id
        return parent

    def reparent_node(self, node_id: str, new_parent_id: str) -> bool:
        if node_id not in self.nodes or new_parent_id not in self.nodes:
            return False
        if node_id == new_parent_id:
            return False

        def is_descendant(ancestor_id, candidate_id, visited=None):
            if visited is None: visited = set()
            if candidate_id in visited: return False
            visited.add(candidate_id)
            if ancestor_id == candidate_id: return True
            for c in self.nodes[candidate_id].children:
                if is_descendant(ancestor_id, c, visited):
                    return True
            return False

        if is_descendant(node_id, new_parent_id):
            return False

        node = self.nodes[node_id]
        for pid in list(node.parents):
            if pid in self.nodes and node_id in self.nodes[pid].children:
                self.nodes[pid].children.remove(node_id)

        new_parent = self.nodes[new_parent_id]
        if node_id not in new_parent.children:
            new_parent.children.append(node_id)
        node.parents = [new_parent_id]

        if self.root_id == node_id:
            for nid, n in self.nodes.items():
                if not n.parents:
                    self.root_id = nid
                    break
        return True

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes: return
        node = self.nodes[node_id]
        for pid in list(node.parents):
            if pid in self.nodes and node_id in self.nodes[pid].children:
                self.nodes[pid].children.remove(node_id)

        doomed = []
        def visit(iid):
            doomed.append(iid)
            for cid in self.nodes[iid].children: visit(cid)
        visit(node_id)
        for iid in doomed: self.nodes.pop(iid, None)

        if self.root_id == node_id:
            self._find_new_root()

    def remove_node_only(self, node_id: str) -> None:
        if node_id not in self.nodes: return
        node = self.nodes[node_id]
        parents = node.parents
        children = node.children

        for child_id in children:
            child = self.nodes.get(child_id)
            if not child: continue
            if node_id in child.parents:
                child.parents.remove(node_id)
            for pid in parents:
                if pid not in child.parents:
                    child.parents.append(pid)
                if pid in self.nodes and child_id not in self.nodes[pid].children:
                    self.nodes[pid].children.append(child_id)

        for pid in parents:
            if pid in self.nodes and node_id in self.nodes[pid].children:
                self.nodes[pid].children.remove(node_id)

        self.nodes.pop(node_id, None)
        if self.root_id == node_id:
            self._find_new_root()

    def _find_new_root(self):
        for nid, n in self.nodes.items():
            if not n.parents:
                self.root_id = nid
                return
        self.root_id = None

    def layout_tree(self, settings: LayoutSettings):
        if not self.root_id: return

        w = settings.node_width
        h = settings.node_height
        h_gap = settings.h_spacing
        v_gap = settings.v_spacing

        widths = {}
        def calc_width(nid, visited=None):
            if visited is None: visited = set()
            if nid in visited: return 0
            visited.add(nid)
            node = self.nodes[nid]
            if not node.children:
                widths[nid] = w
                return w
            children_width = sum(calc_width(c, visited) for c in node.children) + h_gap * (len(node.children) - 1)
            widths[nid] = max(w, children_width)
            return widths[nid]

        calc_width(self.root_id)

        def assign_pos(nid, x, y, visited=None):
            if visited is None: visited = set()
            if nid in visited: return
            visited.add(nid)
            node = self.nodes[nid]
            node_w = widths.get(nid, w)
            node.x = x + (node_w - w) / 2
            node.y = y

            if node.children:
                total_children_w = sum(widths.get(c, w) for c in node.children) + h_gap * (len(node.children) - 1)
                curr_x = x + (node_w - total_children_w) / 2
                for c in node.children:
                    assign_pos(c, curr_x, y + h + v_gap, visited)
                    curr_x += widths.get(c, w) + h_gap

        assign_pos(self.root_id, 0, 0)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "root_id": self.root_id,
                "nodes": [n.to_dict() for n in self.nodes.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasaltTree":
        tree = cls(id=str(data.get("id") or new_id()),
                   title=str(data.get("title", tr("default_tree_title"))),
                   root_id=data.get("root_id"))
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict): raw_nodes = raw_nodes.values()
        tree.nodes = {n.id: n for n in (BasaltNode.from_dict(r) for r in raw_nodes)}
        for n in tree.nodes.values():
            n.children = [c for c in n.children if c in tree.nodes]
            n.parents = [p for p in n.parents if p in tree.nodes]
            for p in n.parents:
                if n.id not in tree.nodes[p].children:
                    tree.nodes[p].children.append(n.id)
        if tree.root_id not in tree.nodes:
            roots = [n.id for n in tree.nodes.values() if not n.parents]
            tree.root_id = roots[0] if roots else None
        return tree


@dataclass
class BasaltProject:
    trees: dict[str, BasaltTree] = field(default_factory=dict)
    settings: LayoutSettings = field(default_factory=LayoutSettings)
    learning: LearningSettings = field(default_factory=LearningSettings)

    def add_tree(self, title: str | None = None) -> BasaltTree:
        if title is None: title = tr("default_tree_title")
        tree = BasaltTree(title=title)
        tree.create_root()
        self.trees[tree.id] = tree
        return tree

    def remove_tree(self, tree_id: str) -> None:
        self.trees.pop(tree_id, None)
        self.learning.tree_configs.pop(tree_id, None)

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

    def get_due_nodes_for_learning(self) -> list[tuple["BasaltTree", "BasaltNode"]]:
        import random
        today = date.today().isoformat()
        tree_nodes: list[tuple["BasaltTree", list["BasaltNode"]]] = []

        for tree in self.trees.values():
            config = self.learning.get_tree_config(tree.id)
            if not config.enabled:
                continue

            nodes = [n for n in tree.nodes.values() if n.review.due <= today]
            if not nodes:
                continue

            if config.mode == "sequential":
                ordered = []
                visited = set()

                def dfs(nid):
                    if nid in visited or nid not in tree.nodes: return
                    visited.add(nid)
                    n = tree.nodes[nid]
                    if n.review.due <= today:
                        ordered.append(n)
                    for c in n.children:
                        dfs(c)

                if tree.root_id:
                    dfs(tree.root_id)
                nodes = ordered
            else:
                random.shuffle(nodes)

            tree_nodes.append((tree, nodes))

        if self.learning.random_order_trees:
            random.shuffle(tree_nodes)

        result = []
        for tree, tn in tree_nodes:
            for n in tn:
                result.append((tree, n))
        return result

    def to_json(self) -> str:
        return json.dumps({
            "trees": [t.to_dict() for t in self.trees.values()],
            "settings": self.settings.to_dict(),
            "learning": self.learning.to_dict(),
        }, indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "BasaltProject":
        data = json.loads(json_str)
        proj = cls()
        proj.settings = LayoutSettings.from_dict(data.get("settings"))
        proj.learning = LearningSettings.from_dict(data.get("learning", {}))
        for t_data in data.get("trees", []):
            tree = BasaltTree.from_dict(t_data)
            proj.trees[tree.id] = tree
        return proj