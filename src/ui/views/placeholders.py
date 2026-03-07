from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)

class EDAView(QWidget):
    def __init__(self, controller):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("EDA View - Coming Soon"))

class BinningView(QWidget):
    def __init__(self, controller):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Binning View - Coming Soon"))
