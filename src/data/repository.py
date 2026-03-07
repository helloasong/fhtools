import pickle
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Optional
from .models import ProjectState


def get_default_project_root() -> str:
    """
    获取默认的项目根目录，支持多平台：
    - Windows: %LOCALAPPDATA%/FHBinningTool/projects 或 %USERPROFILE%/FHBinningTool/projects
    - Linux/macOS: ~/.local/share/FHBinningTool/projects 或 ~/FHBinningTool/projects
    """
    # 优先使用环境变量指定的路径（便于打包后配置）
    env_root = os.environ.get('FHBINNINGTOOL_PROJECT_ROOT')
    if env_root:
        return env_root
    
    # 检测是否在 PyInstaller 打包环境中运行
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件位置
        if sys.platform == 'win32':
            # Windows: 使用用户目录
            base_dir = Path.home() / 'FHBinningTool'
        elif sys.platform == 'linux':
            # Linux: 使用 XDG 规范
            xdg_data = os.environ.get('XDG_DATA_HOME')
            if xdg_data:
                base_dir = Path(xdg_data) / 'FHBinningTool'
            else:
                base_dir = Path.home() / '.local' / 'share' / 'FHBinningTool'
        else:
            # macOS 或其他
            base_dir = Path.home() / 'FHBinningTool'
    else:
        # 开发环境：使用当前工作目录
        base_dir = Path.cwd()
    
    return str(base_dir / 'projects')


class ProjectRepository:
    """
    负责项目文件的加载、保存和原始数据的管理。
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or get_default_project_root()
        os.makedirs(self.project_root, exist_ok=True)

    def create_project(self, name: str, raw_data_path: str) -> ProjectState:
        """
        创建新项目：
        1. 创建项目文件夹
        2. 复制原始数据到项目目录（备份）
        3. 初始化 ProjectState
        """
        # 1. 创建目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = os.path.join(self.project_root, f"{name}_{timestamp}")
        os.makedirs(project_dir, exist_ok=True)
        
        # 2. 备份数据 (支持 csv, xlsx)
        filename = os.path.basename(raw_data_path)
        backup_path = os.path.join(project_dir, filename)
        shutil.copy2(raw_data_path, backup_path)
        
        # 3. 初始化状态
        state = ProjectState(
            project_name=name,
            raw_data_path=os.path.abspath(backup_path),
            project_dir=os.path.abspath(project_dir)
        )
        
        # 初次保存
        self.save_project(state, os.path.join(project_dir, "project.fht"))
        return state

    def save_project(self, state: ProjectState, file_path: str):
        """保存项目状态到文件 (Pickle)"""
        state.update_timestamp()
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            pickle.dump(state, f)

    def load_project(self, file_path: str) -> ProjectState:
        """从文件加载项目状态"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Project file not found: {file_path}")
            
        with open(file_path, 'rb') as f:
            state = pickle.load(f)
        return state

    def save_snapshot(self, state: ProjectState) -> str:
        os.makedirs(os.path.join(state.project_dir, 'snapshots'), exist_ok=True)
        file_path = os.path.join(state.project_dir, 'snapshots', f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fht")
        self.save_project(state, file_path)
        return file_path

    def load_data(self, state: ProjectState) -> pd.DataFrame:
        """读取项目关联的原始数据"""
        path = state.raw_data_path
        if path.endswith('.csv'):
            return pd.read_csv(path)
        elif path.endswith(('.xls', '.xlsx')):
            return pd.read_excel(path)
        elif path.endswith('.parquet'):
            return pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported file format: {path}")
