from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt
from datetime import datetime
import os

from src.controllers.project_controller import ProjectController
from src.utils.workers import Worker


class ExportView(QWidget):
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 导出目录
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select export directory...")
        self.dir_input.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("Export Dir:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)

        # 按钮区
        btn_row = QHBoxLayout()
        self.export_excel_btn = QPushButton("Export Excel Report")
        self.export_py_btn = QPushButton("Export Python Rules")
        self.export_sql_btn = QPushButton("Export SQL Rules")
        self.export_config_btn = QPushButton("Export Optbinning Config (JSON)")
        self.export_excel_btn.clicked.connect(self.export_excel)
        self.export_py_btn.clicked.connect(self.export_python)
        self.export_sql_btn.clicked.connect(self.export_sql)
        self.export_config_btn.clicked.connect(self.export_optbinning_config)
        btn_row.addWidget(self.export_excel_btn)
        btn_row.addWidget(self.export_py_btn)
        btn_row.addWidget(self.export_sql_btn)
        btn_row.addWidget(self.export_config_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

    def browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if dir_path:
            self.dir_input.setText(dir_path)

    def _start_worker(self, fn, *args, success_msg: str):
        if not self.dir_input.text().strip():
            QMessageBox.warning(self, "Warning", "Please select export directory.")
            return
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Info", "Export task is running, please wait...")
            return
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.worker = Worker(fn, *args)
        self.worker.finished.connect(lambda out_path: self._on_success(success_msg, out_path))
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(lambda _: self._stop_progress())
        self.worker.error.connect(lambda _: self._stop_progress())
        self.worker.finished.connect(self._clear_worker)
        self.worker.error.connect(self._clear_worker)
        self.worker.start()

    def _on_success(self, msg: str, out_path: str):
        QMessageBox.information(self, "Success", f"{msg}\n\nSaved to: {out_path}")

    def _on_error(self, err: str):
        QMessageBox.critical(self, "Error", err)

    def _stop_progress(self):
        self.progress.setVisible(False)
        self.progress.setRange(0, 100)

    def _clear_worker(self, *args, **kwargs):
        try:
            if hasattr(self, 'worker') and self.worker is not None:
                if self.worker.isRunning():
                    self.worker.quit()
                    self.worker.wait()
        finally:
            self.worker = None

    def export_excel(self):
        self._start_worker(self.controller.export_excel_report, self.dir_input.text(), success_msg="Excel report exported.")

    def export_python(self):
        self._start_worker(self.controller.export_python_rules, self.dir_input.text(), success_msg="Python rules exported.")

    def export_sql(self):
        self._start_worker(self.controller.export_sql_rules, self.dir_input.text(), success_msg="SQL rules exported.")

    def export_optbinning_config(self):
        """导出 Optbinning JSON 配置"""
        if not self.dir_input.text().strip():
            QMessageBox.warning(self, "Warning", "Please select export directory.")
            return
        
        # 检查是否有分箱结果
        if not hasattr(self.controller, 'state') or not self.controller.state:
            QMessageBox.warning(self, "Warning", "No project state available.")
            return
        
        if not self.controller.state.binning_results:
            QMessageBox.warning(self, "Warning", "No binning results to export.")
            return
        
        from src.services.export_optbinning_config import export_optbinning_config
        
        try:
            output_path = os.path.join(
                self.dir_input.text(),
                f"optbinning_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            export_optbinning_config(self.controller.state, output_path)
            
            QMessageBox.information(
                self, "Success",
                f"Optbinning config exported.\n\nSaved to: {output_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export config: {str(e)}")
