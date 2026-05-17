from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum
import pandas as pd
from src.core.metrics import BinningMetrics


class FilterMode(str, Enum):
    """指标过滤模式"""
    GLOBAL = "global"
    CUSTOM = "custom"
    DISABLED = "disabled"


@dataclass
class FilterCondition:
    """原子条件节点 (叶子节点)

    表示一个最基本的判断，如 `age > 18`

    Attributes:
        variable: 变量名（数据集中的列名）
        operator: 操作符
        value: 比较值，类型取决于 operator
        negate: 是否取反 (NOT)
    """
    variable: str
    operator: str
    value: Optional[Union[str, float, int, List]] = None
    negate: bool = False


@dataclass
class FilterLogicNode:
    """逻辑组合节点 (分支节点)

    表示 AND/OR 逻辑组合，可嵌套任意深度。

    Attributes:
        operator: 'AND' 或 'OR'
        children: 子节点列表，元素可以是 FilterCondition 或 FilterLogicNode
    """
    operator: str = "AND"
    children: List[Union['FilterLogicNode', FilterCondition]] = field(default_factory=list)


FilterNode = Union[FilterLogicNode, FilterCondition]


@dataclass
class FilterRule:
    """完整的过滤规则

    Attributes:
        name: 规则名称，用于展示
        enabled: 是否启用（禁用后等效于不存在）
        root: 规则树根节点
        created_at: 创建时间 ISO 字符串
        updated_at: 更新时间 ISO 字符串
    """
    name: Optional[str] = None
    enabled: bool = True
    root: Optional[FilterNode] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class FeatureFilterSetting:
    """单个指标的过滤设置

    每个指标在 ProjectState 中对应一个此对象，
    明确记录该指标使用全局规则、自定义规则、还是不过滤。

    Attributes:
        mode: 过滤模式
        rule: 自定义规则（仅在 mode=CUSTOM 时有效）
    """
    mode: FilterMode = FilterMode.GLOBAL
    rule: Optional[FilterRule] = None

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

    # [新增] 数据过滤规则
    global_filter_rule: Optional[FilterRule] = None
    feature_filter_settings: Dict[str, FeatureFilterSetting] = field(default_factory=dict)

    def update_timestamp(self):
        self.last_modified = datetime.now()
