"""Settings dialog for Basalt layout and appearance."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QComboBox, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from basalt_node import LayoutSettings
from i18n import tr, I18n


class SettingsDialog(QDialog):
    def __init__(self, settings: LayoutSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("view_settings_title"))
        self.setFixedSize(420, 550) # Increased height to fit language selector
        self.settings = settings
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Language ────────────────────────────────────────
        lang_group = QGroupBox(tr("language"))
        lang_layout = QFormLayout()
        self.lang_combo = QComboBox()
        langs = I18n.instance().get_available_languages()
        current_lang = I18n.instance().get_language()
        for code, name in langs.items():
            self.lang_combo.addItem(name, code)
            if code == current_lang:
                self.lang_combo.setCurrentIndex(self.lang_combo.count() - 1)
        lang_layout.addRow(tr("language") + ":", self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # ── Node Sizes ────────────────────────────────────
        size_group = QGroupBox(tr("node_sizes"))
        size_layout = QFormLayout()

        self.spin_width = QSpinBox()
        self.spin_width.setRange(150, 500)
        self.spin_width.setValue(self.settings.node_width)
        self.spin_width.setSuffix(tr("px_suffix"))
        size_layout.addRow(tr("width"), self.spin_width)

        self.spin_height = QSpinBox()
        self.spin_height.setRange(80, 300)
        self.spin_height.setValue(self.settings.node_height)
        self.spin_height.setSuffix(tr("px_suffix"))
        size_layout.addRow(tr("height"), self.spin_height)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # ── Spacing ──────────────────────────────────────────
        spacing_group = QGroupBox(tr("spacing"))
        spacing_layout = QFormLayout()

        self.spin_h_gap = QSpinBox()
        self.spin_h_gap.setRange(10, 200)
        self.spin_h_gap.setValue(self.settings.h_spacing)
        self.spin_h_gap.setSuffix(tr("px_suffix"))
        spacing_layout.addRow(tr("horizontal"), self.spin_h_gap)

        self.spin_v_gap = QSpinBox()
        self.spin_v_gap.setRange(20, 200)
        self.spin_v_gap.setValue(self.settings.v_spacing)
        self.spin_v_gap.setSuffix(tr("px_suffix"))
        spacing_layout.addRow(tr("vertical"), self.spin_v_gap)

        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)

        # ── Text ────────────────────────────────────────────
        text_group = QGroupBox(tr("text_settings"))
        text_layout = QFormLayout()

        self.combo_align = QComboBox()
        self.combo_align.addItems([tr("align_left"), tr("align_center"), tr("align_right")])
        align_map = {"left": 0, "center": 1, "right": 2}
        self.combo_align.setCurrentIndex(align_map.get(self.settings.text_align, 0))
        text_layout.addRow(tr("alignment"), self.combo_align)

        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # ── Structure ──────────────
        struct_group = QGroupBox(tr("structure"))
        struct_layout = QFormLayout()

        self.spin_max_parents = QSpinBox()
        self.spin_max_parents.setRange(1, 5)
        self.spin_max_parents.setValue(self.settings.max_parents)
        self.spin_max_parents.setToolTip(tr("max_parents_tooltip"))
        struct_layout.addRow(tr("max_parents"), self.spin_max_parents)

        struct_group.setLayout(struct_layout)
        layout.addWidget(struct_group)

        # ── Buttons ───────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_save = QPushButton(tr("apply"))
        btn_save.setFont(QFont("Segoe UI", 10, QFont.Bold))
        btn_save.setStyleSheet("background-color: #3772d6; color: white; padding: 8px;")
        btn_save.clicked.connect(self.accept)

        btn_cancel = QPushButton(tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_settings(self) -> tuple[LayoutSettings, str]:
        align_map = {0: "left", 1: "center", 2: "right"}
        settings = LayoutSettings(
            node_width=self.spin_width.value(),
            node_height=self.spin_height.value(),
            h_spacing=self.spin_h_gap.value(),
            v_spacing=self.spin_v_gap.value(),
            text_align=align_map[self.combo_align.currentIndex()],
            max_parents=self.spin_max_parents.value(),
        )
        return settings, self.lang_combo.currentData()