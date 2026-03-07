from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd
from src.core.metrics import BinningMetrics

@dataclass
class BinningConfig:
    """单个变量的分箱配置"""
    method: str  # 'equal_freq', 'equal_width', 'chi_merge', 'decision_tree', 'manual'
    params: Dict[str, Any] = field(default_factory=dict)
    splits: List[float] = field(default_factory=list)
    is_confirmed: bool = False  # 用户是否确认了该分箱结果
    missing_strategy: str = "separate"  # 'ignore' | 'separate' | 'merge'
    missing_merge_label: Optional[str] = None

@dataclass
class VariableStats:
    """变量的基础统计信息 (EDA)"""
    name: str
    dtype: str
    n_samples: int
    n_missing: int
    missing_pct: float
    n_unique: int
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    quantiles: Dict[str, float] = field(default_factory=dict)
    skew: Optional[float] = None
    kurt: Optional[float] = None

@dataclass
class ProjectState:
    """
    项目状态模型，用于序列化保存 (.fht 文件)
    """
    # 项目元数据
    project_name: str
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    project_dir: str = ""
    
    # 数据路径 (只存路径，不存原始大数据，避免项目文件过大)
    # 但如果是 Snapshot，可能需要考虑数据的版本一致性
    raw_data_path: str = ""
    
    # 变量配置
    target_col: Optional[str] = None
    feature_cols: List[str] = field(default_factory=list)
    target_mapping: Dict[str, Any] = field(default_factory=dict)
    
    # EDA 缓存
    variable_stats: Dict[str, VariableStats] = field(default_factory=dict)
    
    # 分箱结果缓存 {feature_name: (config, result_metrics)}
    binning_configs: Dict[str, BinningConfig] = field(default_factory=dict)
    binning_results: Dict[str, BinningMetrics] = field(default_factory=dict)

    def update_timestamp(self):
        self.last_modified = datetime.now()
