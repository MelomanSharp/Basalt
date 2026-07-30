"""Settings dialog for Basalt layout and appearance."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpinBox, QComboBox, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from basalt_node import LayoutSettings

class SettingsDialog(QDialog):
    def __init__(self, settings: LayoutSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки отображения")
        self.setFixedSize(400, 350)
        self.settings = settings
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Размеры узлов
        size_group = QGroupBox("Размеры узлов")
        size_layout = QFormLayout()
        
        self.spin_width = QSpinBox()
        self.spin_width.setRange(150, 500)
        self.spin_width.setValue(self.settings.node_width)
        self.spin_width.setSuffix(" px")
        size_layout.addRow("Ширина:", self.spin_width)
        
        self.spin_height = QSpinBox()
        self.spin_height.setRange(80, 300)
        self.spin_height.setValue(self.settings.node_height)
        self.spin_height.setSuffix(" px")
        size_layout.addRow("Высота:", self.spin_height)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Отступы
        spacing_group = QGroupBox("Отступы")
        spacing_layout = QFormLayout()
        
        self.spin_h_gap = QSpinBox()
        self.spin_h_gap.setRange(10, 200)
        self.spin_h_gap.setValue(self.settings.h_spacing)
        self.spin_h_gap.setSuffix(" px")
        spacing_layout.addRow("По горизонтали:", self.spin_h_gap)
        
        self.spin_v_gap = QSpinBox()
        self.spin_v_gap.setRange(20, 200)
        self.spin_v_gap.setValue(self.settings.v_spacing)
        self.spin_v_gap.setSuffix(" px")
        spacing_layout.addRow("По вертикали:", self.spin_v_gap)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        # Текст
        text_group = QGroupBox("Текст")
        text_layout = QFormLayout()
        
        self.combo_align = QComboBox()
        self.combo_align.addItems(["Слева", "По центру", "Справа"])
        align_map = {"left": 0, "center": 1, "right": 2}
        self.combo_align.setCurrentIndex(align_map.get(self.settings.text_align, 0))
        text_layout.addRow("Выравнивание:", self.combo_align)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Применить")
        btn_save.setFont(QFont("Segoe UI", 10, QFont.Bold))
        btn_save.setStyleSheet("background-color: #3772d6; color: white; padding: 8px;")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_settings(self) -> LayoutSettings:
        align_map = {0: "left", 1: "center", 2: "right"}
        return LayoutSettings(
            node_width=self.spin_width.value(),
            node_height=self.spin_height.value(),
            h_spacing=self.spin_h_gap.value(),
            v_spacing=self.spin_v_gap.value(),
            text_align=align_map[self.combo_align.currentIndex()]
        )