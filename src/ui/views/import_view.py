from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QLineEdit, QProgressBar, QMessageBox, QTableView, QMenu, QDialog, QFormLayout, QComboBox
)
from src.controllers.project_controller import ProjectController
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
import pandas as pd
from src.utils.workers import Worker

class ImportView(QWidget):
    """
    数据导入视图：
    1. 创建新项目/加载旧项目
    2. 选择数据文件
    3. 预览数据
    """
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 顶部操作区
        top_panel = QHBoxLayout()
        
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("项目名称（例如：信用评分_v1）")
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择数据文件（.csv, .xlsx）...")
        self.path_input.setReadOnly(True)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        
        create_btn = QPushButton("创建项目并导入数据")
        create_btn.clicked.connect(self.create_project)
        
        # load_btn = QPushButton("Load Existing Project") # TODO

        top_panel.addWidget(QLabel("项目名称："))
        top_panel.addWidget(self.project_name_input)
        top_panel.addWidget(QLabel("数据文件："))
        top_panel.addWidget(self.path_input)
        top_panel.addWidget(browse_btn)
        top_panel.addWidget(create_btn)
        
        layout.addLayout(top_panel)
        
        # 目标变量提示 Banner
        self.target_banner = QLabel("")
        self.target_banner.setStyleSheet("padding:6px; background:#E9F6EC; border:1px solid #CBE6D1; border-radius:8px; color:#2E7D32;")
        layout.addWidget(self.target_banner)

        # 2. 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 3. 数据预览区
        self.table_preview = QTableView()
        self.table_preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_preview.customContextMenuRequested.connect(self.on_table_context_menu)
        self.file_info = QLabel("")
        layout.addWidget(self.file_info)
        layout.addWidget(self.table_preview)

    def setup_connections(self):
        # 连接控制器的信号
        self.controller.data_loaded.connect(self.on_data_loaded)
        self.controller.error_occurred.connect(self.on_error)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "数据文件 (*.csv *.xlsx *.parquet)"
        )
        if file_path:
            self.path_input.setText(file_path)

    def create_project(self):
        name = self.project_name_input.text().strip()
        path = self.path_input.text().strip()
        
        if not name or not path:
            QMessageBox.warning(self, "提示", "请输入项目名称并选择数据文件")
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate mode
        # 保持引用，避免线程对象在运行中被销毁
        self.worker = Worker(self.controller.create_new_project, name, path)
        self.worker.finished.connect(lambda _: self.progress_bar.setVisible(False))
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(lambda _: self.file_info.setText(self._shape_text()))
        # 完成后释放引用
        self.worker.finished.connect(self._clear_worker)
        self.worker.error.connect(self._clear_worker)
        self.worker.start()

    def on_data_loaded(self, df: pd.DataFrame):
        """数据显示到表格中"""
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "成功", f"数据导入成功！维度：{df.shape}")
        # 设置模型（首行插入列名行）
        self.table_preview.setModel(DataFrameModel(df))
        header = self.table_preview.horizontalHeader()
        try:
            from PyQt6.QtWidgets import QHeaderView
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        except Exception:
            pass
        self.file_info.setText(self._shape_text())
        # 更新目标变量提示
        if self.controller.state and self.controller.state.target_col:
            self.target_banner.setText(f"目标变量：{self.controller.state.target_col}")
        else:
            self.target_banner.setText("未设置目标变量：请右键列名进行设置或映射")

    def on_error(self, msg: str):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", msg)

    def _shape_text(self) -> str:
        if self.controller.df is None:
            return ""
        return f"文件：{self.controller.state.raw_data_path} | 维度：{self.controller.df.shape}"

    def _clear_worker(self, *args, **kwargs):
        try:
            if hasattr(self, 'worker') and self.worker is not None:
                if self.worker.isRunning():
                    self.worker.quit()
                    self.worker.wait()
        finally:
            self.worker = None

    def on_table_context_menu(self, pos):
        # 仅首行（列名行）响应右键
        index = self.table_preview.indexAt(pos)
        if not index.isValid() or index.row() != 0:
            return
        col_name = str(self.controller.df.columns[index.column()]) if self.controller and self.controller.df is not None else ""
        menu = QMenu(self)
        act_set_target = menu.addAction(f"设为目标变量（{col_name}）")
        act_map_target = menu.addAction("设置目标映射...")
        act = menu.exec(self.table_preview.viewport().mapToGlobal(pos))
        if act == act_set_target:
            self.controller.set_target_column(col_name)
            QMessageBox.information(self, "提示", f"已将 {col_name} 设为目标变量")
            self.target_banner.setText(f"目标变量：{col_name}")
        elif act == act_map_target:
            dlg = TargetMappingDialog(self, col_name)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                op, expr = dlg.get_mapping()
                self.controller.apply_target_mapping(col_name, op, expr, new_col="target")
                QMessageBox.information(self, "提示", f"已将 {col_name} 映射为二值目标 (target)")
                self.target_banner.setText("目标变量：target")

class TargetMappingDialog(QDialog):
    def __init__(self, parent, col_name: str):
        super().__init__(parent)
        self.setWindowTitle("设置目标映射")
        lay = QFormLayout(self)
        self.op = QComboBox(self)
        self.op.addItems(["==", "!=", ">=", "<=", ">", "<", "in", "not in"])
        self.expr = QLineEdit(self)
        self.expr.setPlaceholderText("输入值或列表，如：1 或 0,1 或 A,B")
        btns = QHBoxLayout()
        ok = QPushButton("确定"); cancel = QPushButton("取消")
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel)
        lay.addRow(QLabel(f"源列：{col_name}"))
        lay.addRow("运算符", self.op)
        lay.addRow("比较值", self.expr)
        lay.addRow(btns)

    def get_mapping(self):
        return self.op.currentText(), self.expr.text().strip()

    def _clear_worker(self, *args, **kwargs):
        try:
            if hasattr(self, 'worker') and self.worker is not None:
                # 确保线程结束
                if self.worker.isRunning():
                    self.worker.quit()
                    self.worker.wait()
        finally:
            self.worker = None
class BodyModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self.df = df.head(200)

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return self.df.shape[1]

    def data(self, index, role=None):
        if role is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.df.iat[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=0):
        if role != 0:
            return None
        if orientation == 1:
            return str(self.df.columns[section])
        return str(section)

class HeaderModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self.columns = list(df.columns)

    def rowCount(self, parent=QModelIndex()):
        return 1

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def data(self, index, role=None):
        if role is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.columns[index.column()])
        if role == Qt.ItemDataRole.BackgroundRole:
            from PyQt6.QtGui import QBrush, QColor
            return QBrush(QColor(240, 245, 255))
        if role == Qt.ItemDataRole.FontRole:
            from PyQt6.QtGui import QFont
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.ItemDataRole.ForegroundRole:
            from PyQt6.QtGui import QBrush, QColor
            return QBrush(QColor(30, 30, 30))
        return None

    def headerData(self, section, orientation, role=0):
        if role != 0:
            return None
        if orientation == 1:
            return str(self.columns[section])
        return str(section)

class DataFrameModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        header_row = pd.DataFrame([df.columns], columns=df.columns)
        self.df = pd.concat([header_row, df.head(200)], ignore_index=True)

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return self.df.shape[1]

    def data(self, index, role=None):
        if role is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.df.iat[index.row(), index.column()])
        # 首行为列名行样式
        if role == Qt.ItemDataRole.BackgroundRole and index.row() == 0:
            from PyQt6.QtGui import QBrush, QColor
            return QBrush(QColor(240, 245, 255))
        if role == Qt.ItemDataRole.FontRole and index.row() == 0:
            from PyQt6.QtGui import QFont
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.ItemDataRole.ForegroundRole and index.row() == 0:
            from PyQt6.QtGui import QBrush, QColor
            return QBrush(QColor(30, 30, 30))
        return None

    def headerData(self, section, orientation, role=0):
        if role != 0:
            return None
        if orientation == 1:
            return str(self.df.columns[section])
        return str(section)

