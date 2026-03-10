# 必须在任何其他 import 之前执行！
# 禁用 NumPy AVX2 优化，兼容云桌面/虚拟 CPU（不支持 X86_V2 指令集）
import os
os.environ['NPY_ENABLE_CPU_FEATURES'] = ''
os.environ['NPY_DISABLE_CPU_FEATURES'] = 'AVX2,AVX512F,FMA3,SSE41,SSE42'

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QStackedWidget, QApplication
)
from qt_material import apply_stylesheet


def get_base_dir() -> str:
    """
    获取应用的基础目录，支持多种运行环境：
    - PyInstaller 打包后 (_MEIPASS)
    - 开发环境 (脚本所在目录)
    - 直接运行 (当前工作目录)
    """
    # PyInstaller 打包后的临时目录
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    
    # 开发环境：使用 main_window.py 所在目录的父目录（项目根目录）
    script_dir = Path(__file__).resolve().parent
    # src/ui/ -> 项目根目录
    project_root = script_dir.parent.parent
    return str(project_root)


def load_config(base_dir: str) -> dict:
    """加载配置文件，支持多平台路径"""
    cfg_path = os.path.join(base_dir, 'config.json')
    config = {
        'theme': 'dark_teal.xml',
        'qss': 'style.qss'
    }
    
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception:
            pass
    
    return config

from src.controllers.project_controller import ProjectController
from src.ui.views.import_view import ImportView
from src.ui.views.combined_view import CombinedView
from src.ui.views.export_view import ExportView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Risk Control Binning Tool (Trae Edition)")
        self.resize(1200, 800)
        
        # 初始化控制器
        self.controller = ProjectController()
        
        self.init_ui()

    def init_ui(self):
        # 主布局：左侧导航 + 右侧内容
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 左侧导航栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.addItems(["1. 数据导入", "2. 分析与调参", "3. 导出"])
        self.nav_list.currentRowChanged.connect(self.switch_view)
        
        # 2. 右侧内容区 (StackedWidget)
        self.stack = QStackedWidget()
        
        # 初始化各个视图
        self.import_view = ImportView(self.controller)
        self.combined_view = CombinedView(self.controller)
        self.export_view = ExportView(self.controller)
        
        self.stack.addWidget(self.import_view)
        self.stack.addWidget(self.combined_view)
        self.stack.addWidget(self.export_view)
        
        # 添加到主布局
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.stack)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)

    def closeEvent(self, event):
        if self.controller and getattr(self.controller, 'dirty', False):
            from PyQt6.QtWidgets import QMessageBox
            ret = QMessageBox.question(self, "Save Changes", "Save snapshot before exit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                try:
                    self.controller.save_snapshot()
                except Exception:
                    pass
        # 优雅停止任何正在运行的后台线程（例如导入线程）
        try:
            iv = getattr(self, 'import_view', None)
            if iv is not None and hasattr(iv, 'worker') and iv.worker is not None:
                if iv.worker.isRunning():
                    iv.worker.quit()
                    iv.worker.wait()
        except Exception:
            pass
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    
    # 获取基础目录并加载配置
    base_dir = get_base_dir()
    config = load_config(base_dir)
    
    # 应用主题
    try:
        apply_stylesheet(app, theme=config.get('theme', 'dark_teal.xml'))
    except Exception:
        pass
    
    # 载入自定义 QSS
    try:
        qss_path = config.get('qss')
        if qss_path:
            qss_file = os.path.join(base_dir, qss_path)
            if os.path.exists(qss_file):
                with open(qss_file, 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
    except Exception:
        pass
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
