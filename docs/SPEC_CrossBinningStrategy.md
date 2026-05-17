# FHBinningTool - 组合策略分析技术设计文档 (SPEC)

> **版本**: v1.0  
> **日期**: 2026-05-17  
> **作者**: AI Assistant  
> **状态**: 待评审  
> **依赖 PRD**: `docs/PRD_CrossBinningStrategy.md`

---

## 1. 设计目标

1. **最小侵入性**: 作为独立模块接入，不破坏现有 MVC 架构和数据流，复用已有分箱结果
2. **计算高效**: 基于 pandas groupby 向量化操作，避免逐行迭代
3. **UI 一致性**: 对话框风格完全遵循现有 qt-material + 自定义 QSS 体系
4. **可扩展性**: 核心算法与 UI 解耦，便于后续支持联合最优分箱（OptBinning2D）

---

## 2. 总体架构

### 2.1 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              UI Layer (PyQt6)                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      CombinedView                                │   │
│  │  ┌─────────────────┐  ┌─────────────────────────────────────┐  │   │
│  │  │ Left Panel      │  │ Right Panel (Analysis)              │  │   │
│  │  │ [批量分箱]       │  │ ...                                 │  │   │
│  │  │ [🔀组合策略] ←───┼──┼─────────────────────────────────────│  │   │
│  │  │ [变量列表]       │  │                                     │  │   │
│  │  └─────────────────┘  └─────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              CrossBinningDialog (QDialog)                        │   │
│  │  ┌──────────────────────────┬─────────────────────────────────┐ │   │
│  │  │ LeftPanel                │ RightPanel                      │ │   │
│  │  │ ┌────────────────────┐   │ ┌─────────────────────────────┐ │ │   │
│  │  │ │ VariableSelector   │   │ │ HeatmapWidget (2D only)     │ │ │   │
│  │  │ │ (QListWidget)      │   │ │ (pyqtgraph / matplotlib)    │ │ │   │
│  │  │ └────────────────────┘   │ └─────────────────────────────┘ │ │   │
│  │  │ ┌────────────────────┐   │ ┌─────────────────────────────┐ │ │   │
│  │  │ │ FilterParamsPanel  │   │ │ RuleResultTable             │ │ │   │
│  │  │ │ (QWidget)          │   │ │ (QTableWidget)              │ │ │   │
│  │  │ └────────────────────┘   │ └─────────────────────────────┘ │ │   │
│  │  │ ┌────────────────────┐   │ ┌─────────────────────────────┐ │ │   │
│  │  │ │ VariablePreview    │   │ │ StatusBar                   │ │ │   │
│  │  │ │ (QLabel)           │   │ │ (统计信息)                   │ │ │   │
│  │  │ └────────────────────┘   │ └─────────────────────────────┘ │ │   │
│  │  └──────────────────────────┴─────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Controller Layer                                 │
│                         ProjectController                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  [new] run_cross_binning(features, filters) -> CrossBinningResult│   │
│  │  [new] get_binned_features() -> List[str]                        │   │
│  │  [existing] state.binning_configs -> Dict[str, BinningConfig]    │   │
│  │  [existing] state.binning_results -> Dict[str, BinningMetrics]   │   │
│  │  [existing] get_filtered_data_for_feature(feature) -> DataFrame  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Core Layer                                      │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  CrossBinningAnalyzer   │  │  Binning Algorithms (existing)      │  │
│  │  (src/core/cross_binning│  │  (src/core/binning)                 │  │
│  │                         │  │                                     │  │
│  │  analyze(df, features,  │  │  [reused] splits from configs       │  │
│  │           configs,      │  │  [reused] MetricsCalculator         │  │
│  │           target_col,   │  │                                     │  │
│  │           filters)      │  │                                     │  │
│  │  -> CrossBinningResult  │  │                                     │  │
│  └─────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 新增/修改文件清单

| 路径 | 类型 | 职责 |
|------|------|------|
| `src/core/cross_binning.py` | 新增 | 组合策略核心算法（笛卡尔积、筛选、统计计算） |
| `src/ui/dialogs/cross_binning_dialog.py` | 新增 | 组合策略分析主对话框 |
| `src/ui/widgets/cross_binning_heatmap.py` | 新增 | 二维热力图组件（PyQtGraph 实现） |
| `src/ui/widgets/cross_binning_params.py` | 新增 | 筛选参数配置面板 |
| `src/controllers/project_controller.py` | 修改 | 新增 `run_cross_binning()`、`get_binned_features()` |
| `src/ui/views/combined_view.py` | 修改 | 左侧增加"组合策略分析"入口按钮 |
| `style.qss` | 修改 | 新增组合策略相关样式 |

---

## 3. 数据模型设计

### 3.1 新增数据类

**文件**: `src/core/cross_binning.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import pandas as pd


@dataclass
class CrossBinningFilters:
    """组合策略筛选参数"""
    min_sample_rate: float = 0.01          # 最小样本占比 (默认1%)
    bad_rate_mode: str = "relative"         # relative | absolute
    bad_rate_high_multiplier: float = 2.0   # 高于整体坏账率的倍数
    bad_rate_low_multiplier: float = 0.5    # 低于整体坏账率的倍数
    min_lift: float = 1.5                   # 最小 Lift
    sort_by: str = "bad_rate_desc"          # bad_rate_desc | lift_desc | sample_desc
    max_combinations: int = 5000            # 最大组合数限制


@dataclass
class CrossBinningRule:
    """单条组合策略规则"""
    rule_id: str                           # 规则编号 (Rule-001)
    risk_level: str                        # high | medium-high | normal | low
    conditions: List[Dict]                 # 条件列表 [{var, bin_label, range}, ...]
    condition_str: str                     # 可读的条件字符串
    sample_count: int                      # 样本数
    sample_rate: float                     # 样本占比
    bad_count: int                         # 坏样本数
    bad_rate: float                        # 坏账率
    overall_bad_rate: float                # 整体坏账率
    lift: float                            # Lift
    woe: float                             # WOE
    iv: float                              # 该组合的 IV 贡献


@dataclass
class CrossBinningResult:
    """组合策略分析结果"""
    overall_bad_rate: float                # 整体坏账率
    total_combinations: int                # 笛卡尔积总组合数
    filtered_combinations: int             # 筛选后剩余组合数
    rules: List[CrossBinningRule]          # 规则列表
    feature_names: List[str]               # 参与的变量名
    feature_bin_counts: Dict[str, int]     # 各变量箱数
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame 便于展示和导出"""
        ...


@dataclass
class CrossBinningHeatmapData:
    """二维热力图数据（仅2变量时使用）"""
    feature_x: str                         # X轴变量名
    feature_y: str                         # Y轴变量名
    x_labels: List[str]                    # X轴箱标签
    y_labels: List[str]                    # Y轴箱标签
    bad_rate_matrix: pd.DataFrame          # 坏账率矩阵 (y_labels × x_labels)
    sample_count_matrix: pd.DataFrame      # 样本数矩阵
    lift_matrix: pd.DataFrame              # Lift 矩阵
```

### 3.2 与现有模型的关系

```
ProjectState (existing)
├── binning_configs: Dict[str, BinningConfig]  ──┐
│   └── splits: List[float]  ←── 用于映射箱标签   │
├── binning_results: Dict[str, BinningMetrics] ──┤
│   └── summary_table: DataFrame                 │
├── target_col: str                             ─┤
└── feature_filter_settings: Dict[str, ...]     ─┘
                                                 │
                                                 ▼
CrossBinningAnalyzer.analyze()
├── 读取 splits → pd.cut() 映射箱标签
├── 应用各变量的有效过滤规则
├── groupby(箱标签) 计算统计量
└── 筛选 → CrossBinningResult
```

---

## 4. 核心算法设计

### 4.1 主类：CrossBinningAnalyzer

**文件**: `src/core/cross_binning.py`

```python
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from src.data.models import ProjectState, BinningConfig
from src.core.cross_binning import (
    CrossBinningFilters, CrossBinningResult, 
    CrossBinningRule, CrossBinningHeatmapData
)


class CrossBinningAnalyzer:
    """组合策略分析器
    
    基于已有单变量分箱结果，通过笛卡尔积交叉组合挖掘多变量联合策略规则。
    所有计算均为 pandas 向量化操作。
    """
    
    @staticmethod
    def analyze(
        df: pd.DataFrame,
        target_col: str,
        features: List[str],
        configs: Dict[str, BinningConfig],
        filters: CrossBinningFilters,
        filtered_data_map: Optional[Dict[str, pd.DataFrame]] = None
    ) -> CrossBinningResult:
        """执行组合策略分析
        
        Args:
            df: 原始数据（用于获取目标变量和变量列）
            target_col: 目标变量列名
            features: 选择的变量名列表（2~N个）
            configs: 各变量的分箱配置 {feature: BinningConfig}
            filters: 筛选参数
            filtered_data_map: 各变量过滤后的数据子集 {feature: filtered_df}
                               为 None 时自动从 df 提取（不过滤）
        
        Returns:
            CrossBinningResult 分析结果
        """
        # Step 1: 参数校验
        CrossBinningAnalyzer._validate_inputs(
            df, target_col, features, configs, filters
        )
        
        # Step 2: 获取各变量过滤后的数据（统一索引以便交叉）
        # 策略：取所有变量过滤后数据的索引交集，确保每个样本在所有选中变量上都是有效的
        working_df = CrossBinningAnalyzer._build_working_df(
            df, features, configs, target_col, filtered_data_map
        )
        
        # Step 3: 计算整体坏账率
        overall_bad_rate = working_df[target_col].mean()
        
        # Step 4: 对每个变量做箱标签映射
        bin_cols = []
        for feat in features:
            cfg = configs[feat]
            bin_col = f"__bin_{feat}"
            # 使用 pd.cut 映射，注意处理缺失值策略
            working_df[bin_col] = CrossBinningAnalyzer._apply_binning(
                working_df[feat], cfg
            )
            bin_cols.append(bin_col)
        
        # Step 5: 按箱标签 groupby 计算统计量
        grouped = working_df.groupby(bin_cols)[target_col].agg([
            'count', 'sum'
        ])
        grouped.columns = ['total', 'bad']
        grouped['good'] = grouped['total'] - grouped['bad']
        grouped['bad_rate'] = grouped['bad'] / grouped['total']
        grouped['total_pct'] = grouped['total'] / len(working_df)
        grouped['lift'] = grouped['bad_rate'] / overall_bad_rate
        
        # Step 6: WOE 计算（带平滑）
        total_bad = working_df[target_col].sum()
        total_good = len(working_df) - total_bad
        eps = 1e-10
        grouped['bad_dist'] = grouped['bad'] / total_bad
        grouped['good_dist'] = grouped['good'] / total_good
        grouped['woe'] = np.log((grouped['good_dist'] + eps) / (grouped['bad_dist'] + eps))
        grouped['iv'] = (grouped['good_dist'] - grouped['bad_dist']) * grouped['woe']
        
        # Step 7: 应用筛选条件
        mask = CrossBinningAnalyzer._apply_filters(
            grouped, overall_bad_rate, filters
        )
        filtered = grouped[mask].copy()
        
        # Step 8: 排序
        filtered = CrossBinningAnalyzer._sort_results(filtered, filters.sort_by)
        
        # Step 9: 构建规则对象
        rules = CrossBinningAnalyzer._build_rules(
            filtered, features, overall_bad_rate
        )
        
        return CrossBinningResult(
            overall_bad_rate=overall_bad_rate,
            total_combinations=len(grouped),
            filtered_combinations=len(filtered),
            rules=rules,
            feature_names=features,
            feature_bin_counts={f: len(configs[f].splits) - 1 for f in features}
        )
    
    @staticmethod
    def build_heatmap_data(
        df: pd.DataFrame,
        target_col: str,
        feature_x: str,
        feature_y: str,
        config_x: BinningConfig,
        config_y: BinningConfig,
        filtered_data_map: Optional[Dict[str, pd.DataFrame]] = None
    ) -> CrossBinningHeatmapData:
        """构建二维热力图数据"""
        ...
    
    # ============= 私有方法 =============
    
    @staticmethod
    def _validate_inputs(df, target_col, features, configs, filters):
        """校验输入参数"""
        if len(features) < 2:
            raise ValueError("至少需要选择2个变量")
        if len(features) > 5:
            raise ValueError("最多支持5个变量同时交叉")
        
        # 计算笛卡尔积组合数
        total_bins = 1
        for feat in features:
            if feat not in configs:
                raise ValueError(f"变量 '{feat}' 未进行分箱")
            n_bins = len(configs[feat].splits) - 1
            total_bins *= n_bins
        
        if total_bins > filters.max_combinations:
            raise ValueError(
                f"笛卡尔积组合数 {total_bins} 超过上限 {filters.max_combinations}，"
                f"建议减少变量数或合并部分变量的箱"
            )
    
    @staticmethod
    def _build_working_df(df, features, configs, target_col, filtered_data_map):
        """构建工作数据集（取各变量过滤后数据的交集）"""
        # 基础列：目标变量 + 所有选中特征
        cols = [target_col] + features
        working = df[cols].copy()
        
        if filtered_data_map:
            # 取所有过滤后数据的索引交集
            valid_indices = set(working.index)
            for feat in features:
                if feat in filtered_data_map:
                    valid_indices &= set(filtered_data_map[feat].index)
            working = working.loc[list(valid_indices)]
        
        # 删除目标变量为缺失的行
        working = working.dropna(subset=[target_col])
        
        return working
    
    @staticmethod
    def _apply_binning(series: pd.Series, cfg: BinningConfig) -> pd.Series:
        """应用分箱配置，返回箱标签"""
        from src.core.binning.base import BaseBinner
        
        binner = BaseBinner.__new__(BaseBinner)
        binner._splits = cfg.splits
        
        # 使用 _apply_splits 映射（包含缺失值处理）
        result = binner._apply_splits(series, cfg.splits)
        
        # 处理缺失值策略
        if cfg.missing_strategy == 'separate' and series.isna().any():
            # Missing 已作为单独类别，无需处理
            pass
        elif cfg.missing_strategy == 'ignore':
            # 缺失值在本次分析中不参与（已在 _build_working_df 中 dropna 处理）
            pass
        elif cfg.missing_strategy == 'merge' and series.isna().any():
            # 将 Missing 合并到最近箱（需要基于 bad_rate 判断，这里简化处理）
            # 实际实现中可复用 MetricsCalculator 的 merge 逻辑
            pass
        
        return result
    
    @staticmethod
    def _apply_filters(grouped, overall_bad_rate, filters):
        """应用筛选条件，返回布尔掩码"""
        mask = (
            (grouped['total_pct'] >= filters.min_sample_rate) &
            (
                (grouped['bad_rate'] >= overall_bad_rate * filters.bad_rate_high_multiplier) |
                (grouped['bad_rate'] <= overall_bad_rate * filters.bad_rate_low_multiplier)
            ) &
            (grouped['lift'].abs() >= filters.min_lift)
        )
        return mask
    
    @staticmethod
    def _sort_results(grouped, sort_by):
        """按指定方式排序"""
        if sort_by == 'bad_rate_desc':
            return grouped.sort_values('bad_rate', ascending=False)
        elif sort_by == 'lift_desc':
            return grouped.sort_values('lift', ascending=False)
        elif sort_by == 'sample_desc':
            return grouped.sort_values('total', ascending=False)
        return grouped
    
    @staticmethod
    def _build_rules(grouped, features, overall_bad_rate) -> List[CrossBinningRule]:
        """从 groupby 结果构建规则列表"""
        rules = []
        bin_col_names = [f"__bin_{f}" for f in features]
        
        for idx, (group_key, row) in enumerate(grouped.iterrows()):
            # 解析组合条件
            conditions = []
            condition_parts = []
            
            # group_key 可能是单个值或元组（取决于变量数量）
            if len(features) == 1:
                group_keys = [group_key]
            else:
                group_keys = group_key
            
            for feat, bin_label in zip(features, group_keys):
                # 将 pd.Interval 转换为可读字符串
                if isinstance(bin_label, pd.Interval):
                    left = bin_label.left if np.isfinite(bin_label.left) else '-∞'
                    right = bin_label.right if np.isfinite(bin_label.right) else '+∞'
                    label_str = f"[{left}, {right})"
                    condition_parts.append(f"{feat}∈{label_str}")
                else:
                    label_str = str(bin_label)
                    condition_parts.append(f"{feat}={label_str}")
                
                conditions.append({
                    'variable': feat,
                    'bin_label': label_str,
                    'interval': bin_label if isinstance(bin_label, pd.Interval) else None
                })
            
            # 风险等级判定
            bad_rate = row['bad_rate']
            lift = row['lift']
            if bad_rate >= overall_bad_rate * 3.0:
                risk_level = 'extreme-high'
            elif bad_rate >= overall_bad_rate * 2.0:
                risk_level = 'high'
            elif bad_rate <= overall_bad_rate * 0.5:
                risk_level = 'low'
            else:
                risk_level = 'normal'
            
            rule = CrossBinningRule(
                rule_id=f"Rule-{idx+1:03d}",
                risk_level=risk_level,
                conditions=conditions,
                condition_str=' ∧ '.join(condition_parts),
                sample_count=int(row['total']),
                sample_rate=row['total_pct'],
                bad_count=int(row['bad']),
                bad_rate=bad_rate,
                overall_bad_rate=overall_bad_rate,
                lift=lift,
                woe=row['woe'],
                iv=row['iv']
            )
            rules.append(rule)
        
        return rules
```

### 4.2 算法复杂度分析

| 步骤 | 操作 | 复杂度 | 说明 |
|------|------|--------|------|
| 箱标签映射 | `pd.cut` × N变量 | O(N × n) | n为样本数，向量化 |
| Groupby 聚合 | `df.groupby(bin_cols).agg` | O(n × log n) | pandas 内部优化 |
| 筛选 | 布尔掩码 | O(m) | m为组合数 |
| **总体** | — | **O(n × log n)** | 主要耗时在 groupby，与样本数线性相关 |

---

## 5. UI 组件详细设计

### 5.1 组件层级

```
CrossBinningDialog (QDialog)
├── main_splitter (QSplitter)
│   ├── left_panel (QWidget)
│   │   ├── variable_group (QGroupBox)
│   │   │   └── variable_list (QListWidget with checkboxes)
│   │   ├── params_group (QGroupBox)
│   │   │   └── CrossBinningParamsPanel
│   │   ├── preview_label (QLabel)
│   │   └── analyze_btn (QPushButton)
│   │
│   └── right_panel (QWidget)
│       ├── heatmap_container (QWidget)  [2变量时显示]
│       │   └── CrossBinningHeatmap (pyqtgraph)
│       ├── result_table (QTableWidget)
│       └── status_bar (QLabel)
│
├── top_toolbar (QHBoxLayout)
│   ├── title_label (QLabel)
│   ├── export_btn (QPushButton)
│   └── close_btn (QPushButton)
```

### 5.2 CrossBinningDialog

**文件**: `src/ui/dialogs/cross_binning_dialog.py`

```python
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict

from src.controllers.project_controller import ProjectController
from src.core.cross_binning import (
    CrossBinningAnalyzer, CrossBinningFilters,
    CrossBinningResult, CrossBinningHeatmapData
)
from src.ui.widgets.cross_binning_params import CrossBinningParamsPanel
from src.ui.widgets.cross_binning_heatmap import CrossBinningHeatmap


class CrossBinningWorker(QThread):
    """组合策略分析工作线程"""
    
    finished = pyqtSignal(object)  # CrossBinningResult
    error = pyqtSignal(str)
    
    def __init__(self, controller, features, filters):
        super().__init__()
        self.controller = controller
        self.features = features
        self.filters = filters
    
    def run(self):
        try:
            df = self.controller.df
            target_col = self.controller.state.target_col
            configs = {
                f: self.controller.state.binning_configs[f] 
                for f in self.features
            }
            
            # 获取各变量过滤后的数据
            filtered_map = {}
            for feat in self.features:
                filtered_map[feat] = self.controller.get_filtered_data_for_feature(feat)
            
            result = CrossBinningAnalyzer.analyze(
                df=df,
                target_col=target_col,
                features=self.features,
                configs=configs,
                filters=self.filters,
                filtered_data_map=filtered_map
            )
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CrossBinningDialog(QDialog):
    """组合策略分析对话框
    
    最大化显示，支持二维热力图（仅2变量）和规则列表。
    """
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.worker = None
        self.current_result = None
        
        self.setWindowTitle("🔀 组合策略分析")
        self.setMinimumSize(1000, 700)
        self.showMaximized()
        
        self.init_ui()
        self.load_variables()
    
    def init_ui(self):
        """初始化 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.title_label = QLabel("<b>组合策略分析</b>")
        self.title_label.setStyleSheet("font-size: 16px;")
        
        self.export_btn = QPushButton("📥 导出规则")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.on_export)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        
        toolbar.addWidget(self.title_label)
        toolbar.addStretch()
        toolbar.addWidget(self.export_btn)
        toolbar.addWidget(self.close_btn)
        layout.addLayout(toolbar)
        
        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板
        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
    
    def _build_left_panel(self) -> QWidget:
        """构建左侧面板：变量选择 + 参数配置"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 变量选择组
        var_group = QGroupBox("选择变量（勾选已分箱变量）")
        var_layout = QVBoxLayout(var_group)
        
        self.variable_list = QListWidget()
        self.variable_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        # 使用复选框模式
        self.variable_list.itemChanged.connect(self.on_variable_selection_changed)
        var_layout.addWidget(self.variable_list)
        
        layout.addWidget(var_group)
        
        # 参数配置组
        self.params_panel = CrossBinningParamsPanel()
        layout.addWidget(self.params_panel)
        
        # 预览信息
        self.preview_label = QLabel("请选择至少2个已分箱变量")
        self.preview_label.setStyleSheet("color: #666; padding: 8px;")
        layout.addWidget(self.preview_label)
        
        # 分析按钮
        self.analyze_btn = QPushButton("▶️ 开始分析")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white; 
                border-radius: 6px; padding: 10px;
                font-weight: bold; font-size: 14px;
            }
            QPushButton:disabled { background: #BDBDBD; }
        """)
        self.analyze_btn.clicked.connect(self.on_analyze)
        layout.addWidget(self.analyze_btn)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定模式
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        return panel
    
    def _build_right_panel(self) -> QWidget:
        """构建右侧面板：热力图 + 结果表格"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 热力图容器（仅2变量时显示）
        self.heatmap_container = QWidget()
        heatmap_layout = QVBoxLayout(self.heatmap_container)
        self.heatmap_widget = CrossBinningHeatmap()
        heatmap_layout.addWidget(self.heatmap_widget)
        self.heatmap_container.setVisible(False)
        layout.addWidget(self.heatmap_container)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(11)
        self.result_table.setHorizontalHeaderLabels([
            "规则编号", "风险等级", "组合条件", "样本数", "占比",
            "坏样本数", "坏账率", "整体坏账率", "Lift", "WOE", "操作"
        ])
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        layout.addWidget(self.result_table)
        
        # 状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self.status_bar)
        
        return panel
    
    def load_variables(self):
        """加载变量列表，区分已分箱和未分箱"""
        state = self.controller.state
        if not state or not state.feature_cols:
            return
        
        binned_features = set(state.binning_configs.keys())
        
        for feat in state.feature_cols:
            item = QListWidgetItem()
            is_binned = feat in binned_features
            
            if is_binned:
                n_bins = len(state.binning_configs[feat].splits) - 1
                item.setText(f"{feat}  ({n_bins}箱)")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, True)
            else:
                item.setText(f"{feat}  (未分箱)")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                item.setForeground(Qt.GlobalColor.gray)
                item.setData(Qt.ItemDataRole.UserRole, False)
            
            self.variable_list.addItem(item)
    
    def on_variable_selection_changed(self, item: QListWidgetItem):
        """变量选择变化时更新预览"""
        checked = []
        for i in range(self.variable_list.count()):
            item = self.variable_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                feat = item.text().split("  ")[0]
                checked.append(feat)
        
        # 更新预览信息
        if len(checked) >= 2:
            state = self.controller.state
            bin_counts = [len(state.binning_configs[f].splits) - 1 for f in checked]
            total_combo = 1
            for c in bin_counts:
                total_combo *= c
            
            preview = " × ".join([f"{f}({c}箱)" for f, c in zip(checked, bin_counts)])
            self.preview_label.setText(
                f"已选: {preview}\n"
                f"笛卡尔积组合数: {total_combo}"
            )
            self.analyze_btn.setEnabled(total_combo <= 5000)
            if total_combo > 5000:
                self.preview_label.setText(
                    self.preview_label.text() + "\n⚠️ 组合数超过5000上限"
                )
        else:
            self.preview_label.setText(f"已选 {len(checked)} 个变量，还需选择 {2-len(checked)} 个")
            self.analyze_btn.setEnabled(False)
    
    def on_analyze(self):
        """执行分析"""
        # 收集选中的变量
        features = []
        for i in range(self.variable_list.count()):
            item = self.variable_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                feat = item.text().split("  ")[0]
                features.append(feat)
        
        if len(features) < 2:
            QMessageBox.warning(self, "提示", "请至少选择2个变量")
            return
        
        # 获取筛选参数
        filters = self.params_panel.get_filters()
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")
        
        # 启动工作线程
        self.worker = CrossBinningWorker(self.controller, features, filters)
        self.worker.finished.connect(self.on_analyze_finished)
        self.worker.error.connect(self.on_analyze_error)
        self.worker.start()
    
    def on_analyze_finished(self, result: CrossBinningResult):
        """分析完成回调"""
        self.current_result = result
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("▶️ 开始分析")
        self.export_btn.setEnabled(True)
        
        # 更新状态栏
        self.status_bar.setText(
            f"整体坏账率: {result.overall_bad_rate:.2%} | "
            f"总组合: {result.total_combinations} | "
            f"命中规则: {result.filtered_combinations}"
        )
        
        # 2变量时显示热力图
        if len(result.feature_names) == 2:
            self._show_heatmap(result)
        else:
            self.heatmap_container.setVisible(False)
        
        # 填充表格
        self._fill_result_table(result)
    
    def on_analyze_error(self, error_msg: str):
        """分析错误回调"""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("▶️ 开始分析")
        QMessageBox.critical(self, "分析失败", error_msg)
    
    def _fill_result_table(self, result: CrossBinningResult):
        """填充结果表格"""
        self.result_table.setRowCount(len(result.rules))
        
        risk_icons = {
            'extreme-high': '🔴 极高',
            'high': '🟠 高',
            'normal': '⚪ 正常',
            'low': '🟢 低'
        }
        
        for i, rule in enumerate(result.rules):
            values = [
                rule.rule_id,
                risk_icons.get(rule.risk_level, rule.risk_level),
                rule.condition_str,
                str(rule.sample_count),
                f"{rule.sample_rate:.2%}",
                str(rule.bad_count),
                f"{rule.bad_rate:.2%}",
                f"{rule.overall_bad_rate:.2%}",
                f"{rule.lift:.2f}",
                f"{rule.woe:.4f}",
                "[复制]"
            ]
            for j, v in enumerate(values):
                self.result_table.setItem(i, j, QTableWidgetItem(v))
        
        self.result_table.resizeColumnsToContents()
    
    def _show_heatmap(self, result: CrossBinningResult):
        """显示二维热力图"""
        # TODO: 通过 CrossBinningAnalyzer.build_heatmap_data 获取数据
        # self.heatmap_widget.set_data(heatmap_data)
        self.heatmap_container.setVisible(True)
    
    def on_export(self):
        """导出规则"""
        if not self.current_result:
            return
        # TODO: 弹出导出对话框，支持 Excel / 文本 / JSON
        pass
```

### 5.3 CrossBinningParamsPanel

**文件**: `src/ui/widgets/cross_binning_params.py`

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox
)
from src.core.cross_binning import CrossBinningFilters


class CrossBinningParamsPanel(QGroupBox):
    """组合策略筛选参数配置面板"""
    
    def __init__(self, parent=None):
        super().__init__("筛选条件", parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 最小样本占比
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("最小样本占比:"))
        self.min_sample_spin = QDoubleSpinBox()
        self.min_sample_spin.setRange(0.005, 0.10)
        self.min_sample_spin.setValue(0.01)
        self.min_sample_spin.setSingleStep(0.005)
        self.min_sample_spin.setDecimals(3)
        self.min_sample_spin.setSuffix(" (0.5%~10%)")
        row1.addWidget(self.min_sample_spin)
        layout.addLayout(row1)
        
        # 高风险倍数
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("高风险倍数 (≥):"))
        self.high_mult_spin = QDoubleSpinBox()
        self.high_mult_spin.setRange(1.0, 5.0)
        self.high_mult_spin.setValue(2.0)
        self.high_mult_spin.setSingleStep(0.5)
        row2.addWidget(self.high_mult_spin)
        layout.addLayout(row2)
        
        # 优质客群倍数
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("优质客群倍数 (≤):"))
        self.low_mult_spin = QDoubleSpinBox()
        self.low_mult_spin.setRange(0.1, 1.0)
        self.low_mult_spin.setValue(0.5)
        self.low_mult_spin.setSingleStep(0.1)
        row3.addWidget(self.low_mult_spin)
        layout.addLayout(row3)
        
        # 最小 Lift
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("最小 Lift:"))
        self.min_lift_spin = QDoubleSpinBox()
        self.min_lift_spin.setRange(1.0, 5.0)
        self.min_lift_spin.setValue(1.5)
        self.min_lift_spin.setSingleStep(0.5)
        row4.addWidget(self.min_lift_spin)
        layout.addLayout(row4)
        
        # 排序方式
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("排序方式:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("坏账率降序", "bad_rate_desc")
        self.sort_combo.addItem("Lift降序", "lift_desc")
        self.sort_combo.addItem("样本数降序", "sample_desc")
        row5.addWidget(self.sort_combo)
        layout.addLayout(row5)
    
    def get_filters(self) -> CrossBinningFilters:
        """获取当前配置的筛选参数"""
        return CrossBinningFilters(
            min_sample_rate=self.min_sample_spin.value(),
            bad_rate_high_multiplier=self.high_mult_spin.value(),
            bad_rate_low_multiplier=self.low_mult_spin.value(),
            min_lift=self.min_lift_spin.value(),
            sort_by=self.sort_combo.currentData()
        )
```

### 5.4 CrossBinningHeatmap

**文件**: `src/ui/widgets/cross_binning_heatmap.py`

```python
import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt


class CrossBinningHeatmap(QWidget):
    """二维决策矩阵热力图组件
    
    使用 PyQtGraph 的 ImageItem 实现，支持鼠标悬停提示。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_widget = pg.PlotWidget()
        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        
        # 颜色条
        self.color_bar = pg.ColorBarItem(
            values=(0, 1),
            colorMap=pg.colormap.get('CET-D1')  # diverging colormap
        )
        # TODO: 正确配置 color bar
    
    def set_data(self, heatmap_data):
        """设置热力图数据
        
        Args:
            heatmap_data: CrossBinningHeatmapData
        """
        # 将 bad_rate_matrix 转换为 numpy 数组
        matrix = heatmap_data.bad_rate_matrix.values
        
        # 相对于整体坏账率做归一化，以便使用 diverging colormap
        overall = matrix.mean()  # 或传入的整体坏账率
        normalized = matrix / overall - 1  # 0 表示等于整体，正数表示高于整体
        
        self.image_item.setImage(normalized)
        
        # 设置坐标轴标签
        self.plot_widget.getAxis('bottom').setTicks([
            [(i, label) for i, label in enumerate(heatmap_data.x_labels)]
        ])
        self.plot_widget.getAxis('left').setTicks([
            [(i, label) for i, label in enumerate(heatmap_data.y_labels)]
        ])
```

---

## 6. Controller 扩展

**文件**: `src/controllers/project_controller.py`（修改）

```python
# 新增方法

def get_binned_features(self) -> List[str]:
    """获取所有已分箱的变量名"""
    if not self.state:
        return []
    return list(self.state.binning_configs.keys())


def run_cross_binning(
    self, 
    features: List[str], 
    filters: 'CrossBinningFilters'
) -> 'CrossBinningResult':
    """执行组合策略分析
    
    Args:
        features: 选择的变量名列表
        filters: 筛选参数
        
    Returns:
        CrossBinningResult
    """
    from src.core.cross_binning import CrossBinningAnalyzer
    
    configs = {f: self.state.binning_configs[f] for f in features}
    
    # 获取各变量过滤后的数据
    filtered_map = {}
    for feat in features:
        filtered_map[feat] = self.get_filtered_data_for_feature(feat)
    
    return CrossBinningAnalyzer.analyze(
        df=self.df,
        target_col=self.state.target_col,
        features=features,
        configs=configs,
        filters=filters,
        filtered_data_map=filtered_map
    )
```

---

## 7. CombinedView 入口集成

**文件**: `src/ui/views/combined_view.py`（修改）

在 `init_ui()` 方法中，批量分箱按钮布局之后、变量列表之前插入入口按钮：

```python
# 在 batch_btn_layout 之后添加
cross_btn_layout = QHBoxLayout()
self.cross_binning_btn = QPushButton("🔀 组合策略分析")
self.cross_binning_btn.setToolTip("基于已有分箱结果挖掘多变量组合策略")
self.cross_binning_btn.setStyleSheet("""
    QPushButton {
        background: linear-gradient(to bottom, #FFF3E0, #FFE0B2);
        border: 1px solid #FFB74D;
        border-radius: 6px;
        padding: 6px 10px;
        color: #E65100;
        font-weight: bold;
    }
    QPushButton:hover {
        background: linear-gradient(to bottom, #FFE0B2, #FFCC80);
    }
    QPushButton:disabled {
        background: #F5F5F5;
        border-color: #E0E0E0;
        color: #9E9E9E;
    }
""")
self.cross_binning_btn.clicked.connect(self.on_cross_binning)
cross_btn_layout.addWidget(self.cross_binning_btn)
cross_btn_layout.addStretch()
left_layout.addLayout(cross_btn_layout)
```

在 `on_project_updated()` 中更新按钮状态：

```python
def on_project_updated(self, state: ProjectState):
    # ... 现有代码 ...
    
    # 更新组合策略分析按钮状态
    binned_count = len(state.binning_configs) if state else 0
    self.cross_binning_btn.setEnabled(binned_count >= 2)
    if binned_count >= 2:
        self.cross_binning_btn.setToolTip(
            f"基于 {binned_count} 个已分箱变量挖掘组合策略"
        )
    else:
        self.cross_binning_btn.setToolTip(
            f"请先对至少2个变量进行分箱 (当前: {binned_count})"
        )
```

新增事件处理方法：

```python
def on_cross_binning(self):
    """打开组合策略分析对话框"""
    if not self.controller.state or not self.controller.state.target_col:
        QMessageBox.warning(self, "提示", "未设置目标变量")
        return
    
    binned_count = len(self.controller.state.binning_configs)
    if binned_count < 2:
        QMessageBox.information(
            self, "提示", 
            f"当前只有 {binned_count} 个变量已完成分箱，\n"
            f"请先对至少2个变量进行分箱后再使用此功能。"
        )
        return
    
    from src.ui.dialogs.cross_binning_dialog import CrossBinningDialog
    dialog = CrossBinningDialog(self.controller, parent=self)
    dialog.exec()
```

---

## 8. 边界情况处理

| 场景 | 处理策略 |
|------|---------|
| 某变量分箱结果中包含全空箱 | groupby 后自然不会出现，无需特殊处理 |
| 过滤后某变量全部缺失 | `pd.cut` 返回 NaN，groupby 时进入 Missing 组 |
| 目标变量在部分样本上缺失 | `_build_working_df` 中统一 `dropna(subset=[target_col])` |
| 筛选后结果为空 | UI 显示空状态提示，建议放宽阈值 |
| 组合数恰好等于 5000 | 允许执行，但显示警告"组合数较多，分析可能需要较长时间" |
| 用户快速多次点击"分析" | 按钮置灰+进度条，防止重复提交 |
| 工作线程运行时关闭对话框 | `dialog.reject()` 前检查 `worker.isRunning()`，若运行中则 `worker.quit()` + `worker.wait()` |

---

## 9. 测试策略

### 9.1 单元测试

**文件**: `tests/test_cross_binning.py`

```python
# 测试场景
1. test_two_variable_cross          # 2变量交叉，验证结果数量和字段
2. test_three_variable_cross        # 3变量交叉
3. test_filter_by_sample_rate       # 样本占比筛选
4. test_filter_by_bad_rate          # 坏账率倍数筛选
5. test_filter_by_lift              # Lift 筛选
6. test_empty_result                # 筛选条件严格导致空结果
7. test_combination_limit           # 组合数超限拒绝
8. test_missing_strategy_inherit    # 缺失值策略继承
9. test_filter_rule_inherit         # 过滤规则继承
10. test_heatmap_data_build         # 热力图数据构建
```

### 9.2 集成测试

1. 从 CombinedView 入口打开对话框 → 选择变量 → 分析 → 结果展示
2. 2变量场景下热力图正确显示
3. 导出功能生成正确格式的文件
4. 10万样本性能测试（3变量 × 各5箱 < 5秒）

---

## 10. 验收标准

- [ ] `src/core/cross_binning.py` 核心算法通过全部单元测试
- [ ] `CrossBinningDialog` UI 布局正确，支持最大化/缩放
- [ ] 2变量场景下热力图颜色、坐标轴、悬停提示正确
- [ ] 筛选参数（样本占比、坏账率倍数、Lift）正确生效
- [ ] 规则列表排序、风险等级标注正确
- [ ] 导出功能支持 Excel / 文本 / JSON 三种格式
- [ ] 10万样本 × 3变量 × 各5箱，分析耗时 < 5秒
- [ ] 组合数 > 5,000 时正确拒绝并友好提示
- [ ] 各变量的有效过滤规则在组合分析中被正确应用
- [ ] CombinedView 入口按钮状态随已分箱变量数正确变化
- [ ] 代码遵循现有 MVC + Signal/Slot 架构，无架构破坏

---

**文档历史**:
- v1.0 (2026-05-17): 初稿
