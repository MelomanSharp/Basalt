"""Anki-like spaced repetition learning dialog."""

import random
from datetime import date
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QWidget, QMessageBox, QCheckBox
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from basalt_node import BasaltProject, BasaltNode

class LearningDialog(QDialog):
    def __init__(self, project: BasaltProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Режим обучения (Интервальные повторения)")
        self.resize(600, 500)
        
        self.due_nodes = self.project.get_all_due_nodes()
        random.shuffle(self.due_nodes)
        
        self.current_index = 0
        self.is_revealed = False
        self.reverse_mode = False
        
        self._setup_ui()
        self._show_next_card()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        settings_layout = QHBoxLayout()
        self.chk_reverse = QCheckBox("Обратный режим (Показывать пояснение -> Вспомнить название)")
        self.chk_reverse.setFont(QFont("Segoe UI", 10))
        self.chk_reverse.toggled.connect(self._toggle_reverse)
        settings_layout.addWidget(self.chk_reverse)
        
        self.lbl_progress = QLabel()
        self.lbl_progress.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_progress.setAlignment(Qt.AlignRight)
        settings_layout.addWidget(self.lbl_progress)
        layout.addLayout(settings_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.card_widget = QWidget()
        self.card_layout = QVBoxLayout(self.card_widget)
        self.card_layout.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.card_widget)
        layout.addWidget(self.scroll_area)
        
        self.btn_reveal = QPushButton("Показать ответ (Пробел)")
        self.btn_reveal.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_reveal.setStyleSheet("background-color: #3772d6; color: white; padding: 10px;")
        self.btn_reveal.clicked.connect(self._reveal_answer)
        layout.addWidget(self.btn_reveal)
        
        self.grade_layout = QHBoxLayout()
        self.grade_layout.setSpacing(10)
        
        grades = [("Снова (1)", 1, "#e04f5f"), ("Тяжело (2)", 2, "#f59e0b"), 
                  ("Хорошо (3)", 3, "#10b981"), ("Легко (5)", 5, "#3772d6")]
        
        for text, grade, color in grades:
            btn = QPushButton(text)
            btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
            btn.setStyleSheet(f"background-color: {color}; color: white; padding: 8px;")
            btn.clicked.connect(lambda checked, g=grade: self._grade_card(g))
            self.grade_layout.addWidget(btn)
            
        layout.addLayout(self.grade_layout)
        self._set_grading_visible(False)

    def _toggle_reverse(self, checked):
        self.reverse_mode = checked
        if self.is_revealed:
            self.is_revealed = False
            self._show_next_card()

    def _clear_card(self):
        while self.card_layout.count():
            child = self.card_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    def _show_next_card(self):
        self._clear_card()
        self.is_revealed = False
        self._set_grading_visible(False)
        self.btn_reveal.setVisible(True)
        
        if not self.due_nodes:
            lbl = QLabel("🎉 Все узлы повторены!\nНа сегодня карточек для повторения нет.")
            lbl.setFont(QFont("Segoe UI", 14))
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            self.btn_reveal.setVisible(False)
            self.lbl_progress.setText("Готово")
            return

        if self.current_index >= len(self.due_nodes):
            self.current_index = 0
            random.shuffle(self.due_nodes)

        node = self.due_nodes[self.current_index]
        self.lbl_progress.setText(f"{self.current_index + 1} / {len(self.due_nodes)}")
        
        if self.reverse_mode:
            front_text = node.note if node.note else "(Пояснение отсутствует)"
            front_label = QLabel(f"<b>Пояснение:</b><br><br>{front_text}")
        else:
            front_label = QLabel(f"<h2>{node.title}</h2>")
            
        front_label.setFont(QFont("Segoe UI", 12))
        front_label.setAlignment(Qt.AlignCenter)
        front_label.setWordWrap(True)
        self.card_layout.addWidget(front_label)

    def _reveal_answer(self):
        if not self.due_nodes: return
        self.is_revealed = True
        node = self.due_nodes[self.current_index]
        
        self._clear_card()
        self.btn_reveal.setVisible(False)
        self._set_grading_visible(True)
        
        if self.reverse_mode:
            back_title = f"<h2>{node.title}</h2>"
        else:
            back_title = f"<h3>{node.title}</h3>"
            
        lbl_title = QLabel(back_title)
        lbl_title.setAlignment(Qt.AlignCenter)
        self.card_layout.addWidget(lbl_title)
        
        note_text = node.note if node.note else "<i>(Пояснение отсутствует)</i>"
        lbl_note = QLabel(f"<b>Пояснение:</b><br>{note_text}")
        lbl_note.setFont(QFont("Segoe UI", 11))
        lbl_note.setWordWrap(True)
        lbl_note.setStyleSheet("background-color: #f3f4f6; padding: 10px; border-radius: 5px; margin: 10px 0;")
        self.card_layout.addWidget(lbl_note)
        
        if node.children:
            lbl_children = QLabel("<b>Непосредственные дочерние узлы:</b>")
            lbl_children.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.card_layout.addWidget(lbl_children)
            
            for child_id in node.children:
                # Ищем дерево, которому принадлежит узел
                child = None
                for tree in self.project.trees.values():
                    if child_id in tree.nodes:
                        child = tree.nodes[child_id]
                        break
                
                # Защита от падения, если узел вдруг не найден
                if child:
                    child_text = f"<b>{child.title}</b>: {child.note}" if child.note else f"<b>{child.title}</b>"
                    lbl_child = QLabel(child_text)
                    lbl_child.setWordWrap(True)
                    lbl_child.setStyleSheet("margin-left: 15px; padding: 5px; border-left: 3px solid #3772d6;")
                    self.card_layout.addWidget(lbl_child)

    def _grade_card(self, grade: int):
        if not self.due_nodes: return
        node = self.due_nodes[self.current_index]
        node.review.schedule(grade)
        self.current_index += 1
        self._show_next_card()

    def _set_grading_visible(self, visible: bool):
        for i in range(self.grade_layout.count()):
            self.grade_layout.itemAt(i).widget().setVisible(visible)