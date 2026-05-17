# FHBinningTool - 数据过滤引擎技术设计文档 (SPEC)

> **版本**: v1.0  
> **日期**: 2026-05-17  
> **作者**: AI Assistant  
> **状态**: 待评审  
> **依赖 PRD**: `docs/PRD_DataFilterEngine.md`

---

## 1. 设计目标

1. **最小侵入性**: 过滤引擎作为独立模块接入，不破坏现有 MVC 架构和数据流
2. **向后兼容**: 旧项目文件无感知加载，新功能完全可选
3. **性能可控**: 过滤在分箱前应用，基于 pandas 向量化操作，不引入显著性能损耗
4. **UI 一致性**: 编辑器风格完全遵循现有 qt-material + 自定义 QSS 体系

---

## 2. 总体架构

### 2.1 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              UI Layer (PyQt6)                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  ImportView     │  │  CombinedView   │  │  FilterRuleDialog       │  │
│  │  (全局规则入口)  │  │  (指标规则入口)  │  │  (规则编辑器弹窗)        │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘  │
│           │                    │                        │               │
│           └────────────────────┼────────────────────────┘               │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              FilterRuleEditor (QWidget)                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │   │
│  │  │ ModeSwitch  │ │ RuleTree    │ │ FilterPreviewPanel      │   │   │
│  │  │ (三态切换)   │ │ (规则树)     │ │ (效果预览)              │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Controller Layer                                 │
│                         ProjectController                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  + get_effective_filter_rule(feature: str) -> Optional[FilterRule]│  │
│  │  + apply_filter_to_feature(feature: str) -> pd.DataFrame          │  │
│  │  + get_filter_preview(rule: FilterRule) -> FilterPreviewResult    │  │
│  │  + save_feature_filter_setting(feature, setting)                  │  │
│  │  + save_global_filter_rule(rule)                                  │  │
│  │  [modified] run_binning(feature, method, **kwargs)                │  │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Core Layer                                      │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  FilterEngine           │  │  Binning Algorithms (existing)      │  │
│  │  (src/core/filtering)   │  │  (src/core/binning)                 │  │
│  │                         │  │                                     │  │
│  │  apply(df, rule)        │  │  [modified] fit(x, y, **kwargs)     │  │
│  │  preview(df, rule)      │  │  x,y now from filtered df           │  │
│  │  validate(rule, df)     │  │                                     │  │
│  └─────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Layer                                        │
│                         ProjectState (dataclass)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  global_filter_rule: Optional[FilterRule]                        │   │
│  │  feature_filter_settings: Dict[str, FeatureFilterSetting]        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                         ProjectRepository (pickle)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 新增文件清单

| 路径 | 类型 | 职责 |
|------|------|------|
| `src/core/filtering/__init__.py` | 新增 | 模块导出 |
| `src/core/filtering/engine.py` | 新增 | 过滤规则执行引擎 |
| `src/core/filtering/validation.py` | 新增 | 规则合法性校验 |
| `src/data/models.py` | 修改 | 扩展 FilterRule 相关数据结构 |
| `src/ui/widgets/filter_rule_editor.py` | 新增 | 过滤规则编辑器主组件 |
| `src/ui/widgets/filter_condition_row.py` | 新增 | 单条件行（显示/编辑两种模式） |
| `src/ui/widgets/filter_logic_group_widget.py` | 新增 | 逻辑组容器（AND/OR 嵌套） |
| `src/ui/widgets/filter_mode_switch.py` | 新增 | 三态模式切换按钮组 |
| `src/ui/widgets/filter_preview_panel.py` | 新增 | 效果预览面板 |
| `src/ui/dialogs/filter_rule_dialog.py` | 新增 | 规则配置对话框 |
| `src/controllers/project_controller.py` | 修改 | 集成过滤逻辑 |
| `src/ui/views/import_view.py` | 修改 | 全局规则配置入口 |
| `src/ui/views/combined_view.py` | 修改 | 指标级规则配置入口 + 列表标识 |
| `style.qss` | 修改 | 过滤编辑器样式 |

---

## 3. 数据模型详细设计

### 3.1 类图

```
┌──────────────────────┐
│    <<enum>>          │
│    FilterMode        │
├──────────────────────┤
│ GLOBAL = "global"    │
│ CUSTOM = "custom"    │
│ DISABLED = "disabled"│
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│ FeatureFilterSetting │
├──────────────────────┤
│ mode: FilterMode     │
│ rule: FilterRule|None│
└──────────────────────┘
           │
┌──────────▼───────────┐         ┌──────────────────────┐
│     FilterRule       │         │   FilterCondition    │
├──────────────────────┤         ├──────────────────────┤
│ name: str|None       │◄────────│ variable: str        │
│ enabled: bool        │  root   │ operator: str        │
│ root: Node|None      │         │ value: Any           │
│ created_at: str|None │         │ negate: bool         │
│ updated_at: str|None │         └──────────────────────┘
└──────────┬───────────┘                    ▲
           │                                │
           └────────────────────────────────┘
                          root
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│  FilterLogicNode     │      │   FilterCondition    │
├──────────────────────┤      └──────────────────────┘
│ operator: str        │
│ children: List[Node] │
└──────────────────────┘

Node = FilterLogicNode | FilterCondition
```

### 3.2 类型定义

**文件**: `src/data/models.py`

```python
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict, Any
from enum import Enum


class FilterMode(str, Enum):
    """指标过滤模式"""
    GLOBAL = "global"      # 使用全局规则
    CUSTOM = "custom"      # 使用自定义规则
    DISABLED = "disabled"  # 不应用任何过滤


@dataclass
class FilterCondition:
    """原子条件节点 (叶子节点)
    
    表示一个最基本的判断，如 `age > 18`
    
    Attributes:
        variable: 变量名（数据集中的列名）
        operator: 操作符，见 SUPPORTED_OPERATORS
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
    operator: str  # 'AND' | 'OR'
    children: List[Union['FilterLogicNode', FilterCondition]] = field(default_factory=list)


# 类型别名：规则树的任意节点
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


# ========== ProjectState 扩展 ==========

@dataclass
class ProjectState:
    """项目状态（已有类，此处仅展示新增字段）"""
    # ... 现有字段保持不变 ...
    
    # [新增] 全局过滤规则
    global_filter_rule: Optional[FilterRule] = None
    
    # [新增] 各指标的过滤设置（key 为指标名）
    feature_filter_settings: Dict[str, FeatureFilterSetting] = field(default_factory=dict)
```

### 3.3 常量定义

**文件**: `src/core/filtering/constants.py`（或合并到 `__init__.py`）

```python
# 支持的操作符
SUPPORTED_OPERATORS = [
    '==', '!=', 
    '>', '>=', '<', '<=',
    'in', 'not in',
    'between',
    'like',
    'is null', 'is not null',
]

# 按数据类型推荐的操作符
OPERATORS_BY_TYPE = {
    'numeric': ['>', '>=', '<', '<=', '==', '!=', 'between', 'in', 'not in', 'is null', 'is not null'],
    'string': ['==', '!=', 'in', 'not in', 'like', 'is null', 'is not null'],
    'datetime': ['>', '>=', '<', '<=', '==', '!=', 'between', 'is null', 'is not null'],
    'boolean': ['==', '!=', 'is null', 'is not null'],
}

# 逻辑操作符
LOGIC_OPERATORS = ['AND', 'OR']

# 最大嵌套深度（防止过深嵌套导致性能/栈溢出问题）
MAX_NESTING_DEPTH = 10
```

---

## 4. 过滤执行引擎设计

### 4.1 核心类：FilterEngine

**文件**: `src/core/filtering/engine.py`

```python
from typing import Optional
import pandas as pd
import numpy as np
from src.data.models import FilterRule, FilterCondition, FilterLogicNode, FilterMode


class FilterEngine:
    """过滤规则执行引擎
    
    负责将 FilterRule 转换为 pandas boolean mask 并应用到 DataFrame。
    所有操作均为向量化，不逐行迭代。
    """
    
    @staticmethod
    def apply(df: pd.DataFrame, rule: Optional[FilterRule]) -> pd.DataFrame:
        """对 DataFrame 应用过滤规则
        
        Args:
            df: 原始数据
            rule: 过滤规则，为 None 或 disabled 时返回原数据
            
        Returns:
            过滤后的 DataFrame 子集
        """
        if rule is None or not rule.enabled or rule.root is None:
            return df
        
        mask = FilterEngine._eval_node(df, rule.root)
        return df[mask].copy()
    
    @staticmethod
    def preview(df: pd.DataFrame, rule: Optional[FilterRule]) -> 'FilterPreviewResult':
        """计算过滤规则的预览统计信息
        
        Args:
            df: 原始数据
            rule: 过滤规则
            
        Returns:
            FilterPreviewResult 包含过滤前后样本数等信息
        """
        total = len(df)
        
        if rule is None or not rule.enabled or rule.root is None:
            return FilterPreviewResult(
                total_samples=total,
                filtered_samples=total,
                removed_samples=0,
                removal_ratio=0.0
            )
        
        mask = FilterEngine._eval_node(df, rule.root)
        filtered = mask.sum()
        removed = total - filtered
        
        return FilterPreviewResult(
            total_samples=total,
            filtered_samples=int(filtered),
            removed_samples=int(removed),
            removal_ratio=removed / total if total > 0 else 0.0
        )
    
    # ============= 私有递归求值方法 =============
    
    @staticmethod
    def _eval_node(df: pd.DataFrame, node: FilterNode) -> pd.Series:
        """递归计算规则节点的布尔掩码 Series"""
        if isinstance(node, FilterCondition):
            mask = FilterEngine._eval_condition(df, node)
        elif isinstance(node, FilterLogicNode):
            mask = FilterEngine._eval_logic(df, node)
        else:
            raise TypeError(f"Unknown filter node type: {type(node)}")
        
        return mask
    
    @staticmethod
    def _eval_condition(df: pd.DataFrame, cond: FilterCondition) -> pd.Series:
        """计算原子条件的布尔掩码"""
        col = df[cond.variable]
        op = cond.operator
        val = cond.value
        
        # 根据操作符计算基础掩码
        if op == '==':
            mask = col == val
        elif op == '!=':
            mask = col != val
        elif op == '>':
            mask = col > val
        elif op == '>=':
            mask = col >= val
        elif op == '<':
            mask = col < val
        elif op == '<=':
            mask = col <= val
        elif op == 'in':
            mask = col.isin(val if isinstance(val, list) else [val])
        elif op == 'not in':
            mask = ~col.isin(val if isinstance(val, list) else [val])
        elif op == 'between':
            if isinstance(val, (list, tuple)) and len(val) == 2:
                mask = (col >= val[0]) & (col <= val[1])
            else:
                raise ValueError(f"'between' requires a list/tuple of 2 values, got {val}")
        elif op == 'like':
            mask = col.astype(str).str.contains(str(val).replace('%', '.*'), regex=True, na=False)
        elif op == 'is null':
            mask = col.isna()
        elif op == 'is not null':
            mask = col.notna()
        else:
            raise ValueError(f"Unsupported operator: {op}")
        
        # 处理缺失值：比较操作符的结果中，NaN 会得到 False，符合预期
        # 如需特殊处理 NaN，可在此统一填充
        
        # 应用 NOT 取反
        if cond.negate:
            mask = ~mask
        
        return mask
    
    @staticmethod
    def _eval_logic(df: pd.DataFrame, node: FilterLogicNode) -> pd.Series:
        """计算逻辑组合节点的布尔掩码"""
        if not node.children:
            # 空逻辑组：AND 返回全 True，OR 返回全 False
            if node.operator == 'AND':
                return pd.Series(True, index=df.index)
            else:
                return pd.Series(False, index=df.index)
        
        masks = [FilterEngine._eval_node(df, child) for child in node.children]
        
        if node.operator == 'AND':
            result = masks[0]
            for m in masks[1:]:
                result = result & m
            return result
        elif node.operator == 'OR':
            result = masks[0]
            for m in masks[1:]:
                result = result | m
            return result
        else:
            raise ValueError(f"Unknown logic operator: {node.operator}")


@dataclass
class FilterPreviewResult:
    """过滤预览结果"""
    total_samples: int
    filtered_samples: int
    removed_samples: int
    removal_ratio: float
```

### 4.2 规则校验：FilterValidator

**文件**: `src/core/filtering/validation.py`

```python
from typing import List, Optional, Set
import pandas as pd
from src.data.models import FilterRule, FilterCondition, FilterLogicNode, FilterNode
from src.core.filtering.constants import SUPPORTED_OPERATORS, MAX_NESTING_DEPTH


class FilterValidationError(Exception):
    """规则校验错误"""
    pass


class FilterValidator:
    """过滤规则合法性校验器
    
    在保存/执行规则前进行完整性校验，避免运行时错误。
    """
    
    @staticmethod
    def validate(rule: FilterRule, df: Optional[pd.DataFrame] = None) -> List[str]:
        """校验规则合法性
        
        Args:
            rule: 待校验的过滤规则
            df: 可选的数据集，用于校验变量名是否存在
            
        Returns:
            错误信息列表，为空表示校验通过
        """
        errors = []
        
        if rule is None or not rule.enabled or rule.root is None:
            return errors  # 空规则无需校验
        
        seen_vars: Set[str] = set()
        FilterValidator._validate_node(rule.root, df, errors, seen_vars, depth=0)
        
        return errors
    
    @staticmethod
    def _validate_node(
        node: FilterNode,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str],
        depth: int
    ) -> None:
        """递归校验节点"""
        if depth > MAX_NESTING_DEPTH:
            errors.append(f"规则嵌套深度超过最大限制 {MAX_NESTING_DEPTH}")
            return
        
        if isinstance(node, FilterCondition):
            FilterValidator._validate_condition(node, df, errors, seen_vars)
        elif isinstance(node, FilterLogicNode):
            FilterValidator._validate_logic(node, df, errors, seen_vars, depth)
    
    @staticmethod
    def _validate_condition(
        cond: FilterCondition,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str]
    ) -> None:
        """校验原子条件"""
        # 校验变量名
        if not cond.variable or not cond.variable.strip():
            errors.append("条件变量名不能为空")
            return
        
        if df is not None and cond.variable not in df.columns:
            errors.append(f"变量 '{cond.variable}' 不存在于数据集中")
            return
        
        seen_vars.add(cond.variable)
        
        # 校验操作符
        if cond.operator not in SUPPORTED_OPERATORS:
            errors.append(f"不支持的操作符: '{cond.operator}'")
            return
        
        # 校验值（is null / is not null 不需要值）
        if cond.operator in ('is null', 'is not null'):
            return
        
        if cond.value is None:
            errors.append(f"操作符 '{cond.operator}' 需要提供比较值")
            return
        
        # 校验 between 需要两个值
        if cond.operator == 'between':
            if not isinstance(cond.value, (list, tuple)) or len(cond.value) != 2:
                errors.append("'between' 操作符需要提供包含两个值的列表")
    
    @staticmethod
    def _validate_logic(
        node: FilterLogicNode,
        df: Optional[pd.DataFrame],
        errors: List[str],
        seen_vars: Set[str],
        depth: int
    ) -> None:
        """校验逻辑节点"""
        if node.operator not in ('AND', 'OR'):
            errors.append(f"未知的逻辑操作符: '{node.operator}'")
        
        if not node.children:
            errors.append(f"{node.operator} 逻辑组不能为空")
        
        for child in node.children:
            FilterValidator._validate_node(child, df, errors, seen_vars, depth + 1)
```

---

## 5. UI 组件详细设计

### 5.1 组件层级

```
FilterRuleDialog (QDialog)
└── FilterRuleEditor (QWidget)
    ├── Header (QWidget)
    │   ├── title_label (QLabel)
    │   └── mode_switch (FilterModeSwitch)  [仅指标级显示]
    ├── Body (QScrollArea)
    │   └── rule_tree_container (QWidget)
    │       └── root_widget (FilterLogicGroupWidget | FilterConditionRow)
    │           ├── [LogicGroup] FilterLogicGroupWidget
    │           │   ├── operator_combo (QComboBox: AND/OR)
    │           │   ├── children_layout (QVBoxLayout)
    │           │   │   ├── FilterConditionRow (显示模式)
    │           │   │   ├── FilterConditionRow (编辑模式)
    │           │   │   └── FilterLogicGroupWidget (嵌套)
    │           │   └── action_buttons (添加条件/添加组/取消分组)
    │           └── [Condition] FilterConditionRow
    │               ├── negate_toggle (QCheckBox: NOT)
    │               ├── variable_combo (QComboBox)
    │               ├── operator_combo (QComboBox)
    │               ├── value_input (动态输入组件)
    │               └── action_buttons (确认/取消/删除)
    ├── PreviewPanel (FilterPreviewPanel) [可选显示]
    │   ├── total_label (QLabel)
    │   ├── filtered_label (QLabel)
    │   └── removed_label (QLabel)
    └── Footer (QWidget)
        ├── test_button (QPushButton)
        └── save_button (QPushButton)
```

### 5.2 FilterModeSwitch — 三态模式切换

**文件**: `src/ui/widgets/filter_mode_switch.py`

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal
from src.data.models import FilterMode


class FilterModeSwitch(QWidget):
    """指标过滤模式三态切换组件
    
    三个互斥按钮组成的切换器，类似 QButtonGroup 但视觉更直观。
    当前选中项高亮显示，未选中项为普通样式。
    
    Signals:
        mode_changed(FilterMode): 用户切换模式时发射
    """
    mode_changed = pyqtSignal(object)  # FilterMode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = FilterMode.GLOBAL
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_global = QPushButton("🌐 使用全局规则")
        self.btn_custom = QPushButton("⚙️ 使用自定义规则")
        self.btn_disabled = QPushButton("🚫 不应用过滤")
        
        self.btn_global.setCheckable(True)
        self.btn_custom.setCheckable(True)
        self.btn_disabled.setCheckable(True)
        
        self.btn_global.clicked.connect(lambda: self._on_clicked(FilterMode.GLOBAL))
        self.btn_custom.clicked.connect(lambda: self._on_clicked(FilterMode.CUSTOM))
        self.btn_disabled.clicked.connect(lambda: self._on_clicked(FilterMode.DISABLED))
        
        layout.addWidget(self.btn_global)
        layout.addWidget(self.btn_custom)
        layout.addWidget(self.btn_disabled)
        layout.addStretch()
        
        self._update_style()
    
    def set_mode(self, mode: FilterMode):
        """设置当前模式（不发射信号）"""
        self._current_mode = mode
        self._update_style()
    
    def get_mode(self) -> FilterMode:
        return self._current_mode
    
    def _on_clicked(self, mode: FilterMode):
        if self._current_mode != mode:
            self._current_mode = mode
            self._update_style()
            self.mode_changed.emit(mode)
    
    def _update_style(self):
        """更新按钮样式以反映当前选中状态"""
        buttons = {
            FilterMode.GLOBAL: self.btn_global,
            FilterMode.CUSTOM: self.btn_custom,
            FilterMode.DISABLED: self.btn_disabled,
        }
        for mode, btn in buttons.items():
            btn.setChecked(mode == self._current_mode)
            # 样式通过 QSS 控制，此处仅标记 checked 状态
```

**QSS 样式**（添加到 `style.qss`）：
```css
FilterModeSwitch QPushButton {
    background: linear-gradient(to bottom, #F4F7FB, #E8EEF6);
    border: 1px solid #C9D6EA;
    border-radius: 8px;
    padding: 6px 14px;
    color: #666;
    font-size: 12px;
}

FilterModeSwitch QPushButton:hover {
    background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
    color: #333;
}

FilterModeSwitch QPushButton:checked {
    background: #4A90D9;
    color: white;
    border-color: #3A7BC8;
}
```

### 5.3 FilterConditionRow — 条件行（显示+编辑双模式）

**文件**: `src/ui/widgets/filter_condition_row.py`

```python
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton,
    QCheckBox, QLabel, QStackedWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from src.data.models import FilterCondition
from src.core.filtering.constants import OPERATORS_BY_TYPE


class FilterConditionRow(QWidget):
    """单条件行编辑器
    
    支持两种模式：
    - 显示模式：以可读文本展示条件，提供编辑/删除按钮
    - 编辑模式：以内联表单展示，提供变量/操作符/值的输入控件
    
    Signals:
        condition_saved(FilterCondition): 用户确认保存条件时发射
        condition_deleted(): 用户删除条件时发射
        edit_canceled(): 用户取消编辑时发射
    """
    condition_saved = pyqtSignal(object)  # FilterCondition
    condition_deleted = pyqtSignal()
    edit_canceled = pyqtSignal()
    
    def __init__(
        self,
        columns: list[str],
        column_types: Optional[dict[str, str]] = None,
        condition: Optional[FilterCondition] = None,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.column_types = column_types or {}
        self.condition = condition
        self._is_editing = condition is None  # 新建时直接进入编辑模式
        self._setup_ui()
    
    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(8)
        
        # 双模式切换容器
        self.stack = QStackedWidget()
        
        # 模式1: 显示
        self.display_widget = self._build_display_widget()
        self.stack.addWidget(self.display_widget)
        
        # 模式2: 编辑
        self.edit_widget = self._build_edit_widget()
        self.stack.addWidget(self.edit_widget)
        
        self.main_layout.addWidget(self.stack)
        self._refresh_mode()
    
    def _build_display_widget(self) -> QWidget:
        """构建显示模式 UI"""
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_display = QLabel()
        self.lbl_display.setStyleSheet("color: #333; font-size: 13px;")
        
        self.btn_edit = QPushButton("✏️")
        self.btn_edit.setToolTip("编辑条件")
        self.btn_edit.setFixedSize(28, 28)
        self.btn_edit.clicked.connect(self._enter_edit_mode)
        
        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setToolTip("删除条件")
        self.btn_delete.setFixedSize(28, 28)
        self.btn_delete.clicked.connect(self.condition_deleted.emit)
        
        layout.addWidget(self.lbl_display)
        layout.addStretch()
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)
        
        return w
    
    def _build_edit_widget(self) -> QWidget:
        """构建编辑模式 UI"""
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # NOT 取反开关
        self.chk_negate = QCheckBox("NOT")
        self.chk_negate.setToolTip("取反此条件")
        
        # 变量下拉框
        self.cmb_variable = QComboBox()
        self.cmb_variable.setEditable(True)
        self.cmb_variable.setMinimumWidth(120)
        self.cmb_variable.addItems(self.columns)
        self.cmb_variable.currentTextChanged.connect(self._on_variable_changed)
        
        # 操作符下拉框
        self.cmb_operator = QComboBox()
        self.cmb_operator.setMinimumWidth(100)
        self.cmb_operator.currentTextChanged.connect(self._on_operator_changed)
        
        # 值输入区域（动态切换）
        self.value_stack = QStackedWidget()
        
        # 值输入模式1: 单行文本
        self.edit_single = QLineEdit()
        self.edit_single.setPlaceholderText("输入值...")
        self.value_stack.addWidget(self.edit_single)
        
        # 值输入模式2: 多值（逗号分隔）
        self.edit_multi = QLineEdit()
        self.edit_multi.setPlaceholderText("多个值用逗号分隔...")
        self.value_stack.addWidget(self.edit_multi)
        
        # 值输入模式3: 区间 [min, max]
        self.range_widget = QWidget()
        range_layout = QHBoxLayout(self.range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_range_min = QLineEdit()
        self.edit_range_min.setPlaceholderText("最小值")
        self.edit_range_max = QLineEdit()
        self.edit_range_max.setPlaceholderText("最大值")
        range_layout.addWidget(self.edit_range_min)
        range_layout.addWidget(QLabel("~"))
        range_layout.addWidget(self.edit_range_max)
        self.value_stack.addWidget(self.range_widget)
        
        # 值输入模式4: 无需输入（is null / is not null）
        self.lbl_no_value = QLabel("(无需输入值)")
        self.lbl_no_value.setStyleSheet("color: #999; font-style: italic;")
        self.value_stack.addWidget(self.lbl_no_value)
        
        # 操作按钮
        self.btn_confirm = QPushButton("✓")
        self.btn_confirm.setToolTip("确认 (Enter)")
        self.btn_confirm.setFixedSize(28, 28)
        self.btn_confirm.clicked.connect(self._save_condition)
        
        self.btn_cancel = QPushButton("✗")
        self.btn_cancel.setToolTip("取消 (Esc)")
        self.btn_cancel.setFixedSize(28, 28)
        self.btn_cancel.clicked.connect(self._cancel_edit)
        
        layout.addWidget(self.chk_negate)
        layout.addWidget(self.cmb_variable)
        layout.addWidget(self.cmb_operator)
        layout.addWidget(self.value_stack, 1)
        layout.addWidget(self.btn_confirm)
        layout.addWidget(self.btn_cancel)
        
        return w
    
    def _enter_edit_mode(self):
        self._is_editing = True
        self._load_condition_to_edit()
        self._refresh_mode()
    
    def _save_condition(self):
        """从编辑控件读取数据，构建 FilterCondition 并发射"""
        cond = self._build_condition_from_ui()
        self.condition = cond
        self._is_editing = False
        self._refresh_display_text()
        self._refresh_mode()
        self.condition_saved.emit(cond)
    
    def _cancel_edit(self):
        if self.condition is None:
            # 新建时取消 = 删除
            self.condition_deleted.emit()
        else:
            self._is_editing = False
            self._refresh_mode()
            self.edit_canceled.emit()
    
    def _build_condition_from_ui(self) -> FilterCondition:
        """从 UI 控件构建 FilterCondition"""
        variable = self.cmb_variable.currentText().strip()
        operator = self.cmb_operator.currentText()
        negate = self.chk_negate.isChecked()
        
        # 根据操作符和当前值输入模式读取 value
        value = self._get_value_from_ui(operator)
        
        return FilterCondition(
            variable=variable,
            operator=operator,
            value=value,
            negate=negate
        )
    
    def _get_value_from_ui(self, operator: str):
        """根据当前值输入状态返回对应的值"""
        if operator in ('is null', 'is not null'):
            return None
        
        idx = self.value_stack.currentIndex()
        if operator == 'between':
            min_val = self.edit_range_min.text().strip()
            max_val = self.edit_range_max.text().strip()
            return [min_val, max_val]
        elif operator in ('in', 'not in'):
            text = self.edit_multi.text().strip()
            return [v.strip() for v in text.split(',') if v.strip()]
        else:
            text = self.edit_single.text().strip()
            # 尝试转换为数值
            try:
                return float(text)
            except ValueError:
                return text
    
    def _on_variable_changed(self, text: str):
        """变量改变时，更新可用的操作符列表"""
        # 根据变量类型推断可用操作符
        col_type = self.column_types.get(text, 'string')
        ops = OPERATORS_BY_TYPE.get(col_type, OPERATORS_BY_TYPE['string'])
        
        current_op = self.cmb_operator.currentText()
        self.cmb_operator.clear()
        self.cmb_operator.addItems(ops)
        
        # 尽量保持原选择
        idx = self.cmb_operator.findText(current_op)
        if idx >= 0:
            self.cmb_operator.setCurrentIndex(idx)
    
    def _on_operator_changed(self, text: str):
        """操作符改变时，切换值输入模式"""
        if text in ('is null', 'is not null'):
            self.value_stack.setCurrentIndex(3)  # 无需输入
        elif text == 'between':
            self.value_stack.setCurrentIndex(2)  # 区间输入
        elif text in ('in', 'not in'):
            self.value_stack.setCurrentIndex(1)  # 多值输入
        else:
            self.value_stack.setCurrentIndex(0)  # 单行输入
    
    def _refresh_mode(self):
        self.stack.setCurrentIndex(1 if self._is_editing else 0)
    
    def _refresh_display_text(self):
        """更新显示文本"""
        if self.condition:
            text = self._format_condition(self.condition)
            self.lbl_display.setText(text)
    
    def _format_condition(self, cond: FilterCondition) -> str:
        """将条件格式化为可读文本"""
        prefix = "NOT " if cond.negate else ""
        if cond.operator in ('is null', 'is not null'):
            return f"{prefix}{cond.variable} {cond.operator}"
        return f"{prefix}{cond.variable} {cond.operator} {cond.value}"
    
    def _load_condition_to_edit(self):
        """将现有条件加载到编辑控件"""
        if not self.condition:
            return
        self.cmb_variable.setCurrentText(self.condition.variable)
        self.cmb_operator.setCurrentText(self.condition.operator)
        self.chk_negate.setChecked(self.condition.negate)
        # TODO: 根据 condition.value 回填对应的输入控件
    
    def keyPressEvent(self, event):
        if self._is_editing:
            if event.key() == Qt.Key.Key_Return:
                self._save_condition()
            elif event.key() == Qt.Key.Key_Escape:
                self._cancel_edit()
        super().keyPressEvent(event)
```

### 5.4 FilterLogicGroupWidget — 逻辑组容器

**文件**: `src/ui/widgets/filter_logic_group_widget.py`

```python
from typing import List, Union, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import pyqtSignal
from src.data.models import FilterLogicNode, FilterCondition


class FilterLogicGroupWidget(QWidget):
    """逻辑组容器组件 (AND/OR)
    
    可嵌套包含其他 FilterLogicGroupWidget 或 FilterConditionRow。
    提供添加子条件/子组、删除自身、切换操作符等功能。
    
    Signals:
        structure_changed(): 内部结构变化时发射（用于父级重新收集规则树）
    """
    structure_changed = pyqtSignal()
    
    def __init__(
        self,
        columns: list[str],
        node: Optional[FilterLogicNode] = None,
        is_root: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.node = node or FilterLogicNode(operator='AND')
        self.is_root = is_root
        self.child_widgets: List[QWidget] = []
        self._setup_ui()
    
    def _setup_ui(self):
        self.setProperty("logicGroup", "true")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 头部：操作符选择 + 取反 + 删除（非根节点）
        header = QHBoxLayout()
        
        self.cmb_operator = QComboBox()
        self.cmb_operator.addItems(['AND', 'OR'])
        self.cmb_operator.setCurrentText(self.node.operator)
        self.cmb_operator.setFixedWidth(70)
        self.cmb_operator.currentTextChanged.connect(self._on_operator_changed)
        
        header.addWidget(QLabel("逻辑:"))
        header.addWidget(self.cmb_operator)
        header.addStretch()
        
        if not self.is_root:
            self.btn_ungroup = QPushButton("取消分组")
            self.btn_ungroup.setToolTip("将子条件提升到父级")
            self.btn_ungroup.clicked.connect(self._on_ungroup)
            header.addWidget(self.btn_ungroup)
            
            self.btn_delete_group = QPushButton("🗑️")
            self.btn_delete_group.setToolTip("删除此逻辑组")
            self.btn_delete_group.setFixedSize(28, 28)
            self.btn_delete_group.clicked.connect(self._on_delete_group)
            header.addWidget(self.btn_delete_group)
        
        layout.addLayout(header)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E3E6EA;")
        layout.addWidget(line)
        
        # 子节点容器
        self.children_container = QWidget()
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.setSpacing(6)
        self.children_layout.setContentsMargins(12, 0, 0, 0)  # 左侧缩进
        layout.addWidget(self.children_container)
        
        # 操作按钮栏
        actions = QHBoxLayout()
        
        self.btn_add_condition = QPushButton("+ 添加条件")
        self.btn_add_condition.clicked.connect(self._add_new_condition)
        
        self.btn_add_and_group = QPushButton("+ 添加AND组")
        self.btn_add_and_group.clicked.connect(lambda: self._add_new_group('AND'))
        
        self.btn_add_or_group = QPushButton("+ 添加OR组")
        self.btn_add_or_group.clicked.connect(lambda: self._add_new_group('OR'))
        
        actions.addWidget(self.btn_add_condition)
        actions.addWidget(self.btn_add_and_group)
        actions.addWidget(self.btn_add_or_group)
        actions.addStretch()
        
        layout.addLayout(actions)
        
        # 如果初始化时传入了 node.children，递归构建
        self._build_from_node(self.node)
    
    def _build_from_node(self, node: FilterLogicNode):
        """从现有 FilterLogicNode 递归构建 UI"""
        for child in node.children:
            if isinstance(child, FilterLogicNode):
                self._add_group_widget(child)
            else:
                self._add_condition_widget(child)
    
    def _add_new_condition(self):
        """添加一个新的空条件行（编辑模式）"""
        row = FilterConditionRow(columns=self.columns, parent=self)
        row.condition_saved.connect(self._on_child_changed)
        row.condition_deleted.connect(lambda: self._remove_child(row))
        row.edit_canceled.connect(self._on_child_changed)
        self.child_widgets.append(row)
        self.children_layout.addWidget(row)
        self.structure_changed.emit()
    
    def _add_condition_widget(self, condition: FilterCondition):
        """从现有条件添加条件行（显示模式）"""
        row = FilterConditionRow(
            columns=self.columns,
            condition=condition,
            parent=self
        )
        row.condition_saved.connect(self._on_child_changed)
        row.condition_deleted.connect(lambda: self._remove_child(row))
        row.edit_canceled.connect(self._on_child_changed)
        self.child_widgets.append(row)
        self.children_layout.addWidget(row)
    
    def _add_new_group(self, operator: str):
        """添加一个新的空逻辑组"""
        node = FilterLogicNode(operator=operator)
        self._add_group_widget(node)
        self.structure_changed.emit()
    
    def _add_group_widget(self, node: FilterLogicNode):
        """从现有节点添加逻辑组"""
        group = FilterLogicGroupWidget(
            columns=self.columns,
            node=node,
            is_root=False,
            parent=self
        )
        group.structure_changed.connect(self._on_child_changed)
        self.child_widgets.append(group)
        self.children_layout.addWidget(group)
    
    def _remove_child(self, widget: QWidget):
        """移除子组件"""
        if widget in self.child_widgets:
            self.child_widgets.remove(widget)
        widget.deleteLater()
        self.structure_changed.emit()
    
    def _on_operator_changed(self, text: str):
        self.node.operator = text
        self.structure_changed.emit()
    
    def _on_ungroup(self):
        """取消分组：将子条件提升到父级"""
        # 此操作由父级处理，发射信号告知父级
        self.structure_changed.emit()
        # TODO: 实际实现需要父级支持
    
    def _on_delete_group(self):
        """删除此逻辑组"""
        self.deleteLater()
        self.structure_changed.emit()
    
    def _on_child_changed(self):
        self.structure_changed.emit()
    
    def to_logic_node(self) -> FilterLogicNode:
        """将当前 UI 状态转换为 FilterLogicNode"""
        children = []
        for widget in self.child_widgets:
            if isinstance(widget, FilterConditionRow):
                if widget.condition:
                    children.append(widget.condition)
            elif isinstance(widget, FilterLogicGroupWidget):
                children.append(widget.to_logic_node())
        
        return FilterLogicNode(
            operator=self.cmb_operator.currentText(),
            children=children
        )
```

### 5.5 FilterRuleEditor — 编辑器主组件

**文件**: `src/ui/widgets/filter_rule_editor.py`

```python
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from src.data.models import FilterRule, FilterMode, FeatureFilterSetting
from src.ui.widgets.filter_mode_switch import FilterModeSwitch
from src.ui.widgets.filter_logic_group_widget import FilterLogicGroupWidget
from src.ui.widgets.filter_preview_panel import FilterPreviewPanel


class FilterRuleEditor(QWidget):
    """过滤规则编辑器主组件
    
    整合模式切换、规则树编辑、效果预览于一体。
    支持两种使用场景：
    - 全局规则编辑（无 mode_switch，直接编辑规则树）
    - 指标级规则编辑（有 mode_switch，三态切换）
    
    Signals:
        rule_changed(FilterRule|None): 规则内容变化时发射
        mode_changed(FilterMode): 模式切换时发射（仅指标级）
    """
    rule_changed = pyqtSignal(object)
    mode_changed = pyqtSignal(object)
    
    def __init__(
        self,
        columns: list[str],
        setting: Optional[FeatureFilterSetting] = None,
        global_rule: Optional[FilterRule] = None,
        is_global_editor: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.global_rule = global_rule
        self.is_global_editor = is_global_editor
        
        # 内部状态
        self._setting = setting or FeatureFilterSetting()
        self._current_rule = self._resolve_initial_rule()
        
        self._setup_ui()
        self._refresh_ui_by_mode()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # ===== 头部 =====
        header = QHBoxLayout()
        
        title = "全局过滤规则" if self.is_global_editor else f"指标过滤规则"
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        header.addWidget(self.lbl_title)
        
        if not self.is_global_editor:
            self.mode_switch = FilterModeSwitch()
            self.mode_switch.set_mode(self._setting.mode)
            self.mode_switch.mode_changed.connect(self._on_mode_changed)
            header.addWidget(self.mode_switch)
        
        header.addStretch()
        layout.addLayout(header)
        
        # ===== 规则树编辑区 =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.tree_container = QWidget()
        self.tree_layout = QVBoxLayout(self.tree_container)
        self.tree_layout.setContentsMargins(0, 0, 0, 0)
        
        # 根级逻辑组
        self.root_group = FilterLogicGroupWidget(
            columns=self.columns,
            is_root=True,
            parent=self.tree_container
        )
        self.root_group.structure_changed.connect(self._on_tree_changed)
        self.tree_layout.addWidget(self.root_group)
        self.tree_layout.addStretch()
        
        self.scroll.setWidget(self.tree_container)
        layout.addWidget(self.scroll, 1)
        
        # ===== 全局规则预览（仅指标级，且模式为 GLOBAL 时显示） =====
        self.global_preview = QLabel()
        self.global_preview.setStyleSheet("color: #666; font-size: 12px; padding: 8px; background: #F8FAFD; border-radius: 6px;")
        self.global_preview.setWordWrap(True)
        layout.addWidget(self.global_preview)
        
        # ===== 禁用提示（模式为 DISABLED 时显示） =====
        self.disabled_notice = QLabel("🚫 该指标不参与任何数据过滤，将使用全部样本进行分箱。")
        self.disabled_notice.setStyleSheet("color: #999; font-size: 12px; padding: 12px; background: #FFF3F3; border-radius: 6px;")
        layout.addWidget(self.disabled_notice)
        
        # ===== 效果预览面板 =====
        self.preview_panel = FilterPreviewPanel()
        layout.addWidget(self.preview_panel)
        
        # ===== 底部按钮 =====
        footer = QHBoxLayout()
        footer.addStretch()
        
        self.btn_test = QPushButton("🧪 测试规则")
        self.btn_test.setToolTip("预览当前规则的过滤效果")
        self.btn_test.clicked.connect(self._on_test_rule)
        footer.addWidget(self.btn_test)
        
        self.btn_save = QPushButton("✓ 保存规则")
        self.btn_save.setStyleSheet("background: #4CAF50; color: white; padding: 8px 20px; border-radius: 8px;")
        self.btn_save.clicked.connect(self._on_save_rule)
        footer.addWidget(self.btn_save)
        
        layout.addLayout(footer)
    
    def _resolve_initial_rule(self) -> Optional[FilterRule]:
        """根据当前 setting 和场景确定初始规则"""
        if self.is_global_editor:
            return self.global_rule
        
        if self._setting.mode == FilterMode.CUSTOM:
            return self._setting.rule
        return None
    
    def _on_mode_changed(self, mode: FilterMode):
        self._setting.mode = mode
        self.mode_changed.emit(mode)
        self._refresh_ui_by_mode()
    
    def _refresh_ui_by_mode(self):
        """根据当前模式刷新 UI 各区域的可见性"""
        if self.is_global_editor:
            # 全局编辑器：始终显示规则树
            self.root_group.setVisible(True)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(False)
            return
        
        mode = self._setting.mode
        
        if mode == FilterMode.GLOBAL:
            self.root_group.setVisible(False)
            self.global_preview.setVisible(True)
            self.disabled_notice.setVisible(False)
            self.btn_test.setVisible(True)
            self.btn_save.setVisible(False)
            self._update_global_preview()
            
        elif mode == FilterMode.CUSTOM:
            self.root_group.setVisible(True)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(False)
            self.btn_test.setVisible(True)
            self.btn_save.setVisible(True)
            
        elif mode == FilterMode.DISABLED:
            self.root_group.setVisible(False)
            self.global_preview.setVisible(False)
            self.disabled_notice.setVisible(True)
            self.btn_test.setVisible(False)
            self.btn_save.setVisible(True)  # 保存 DISABLED 状态
    
    def _update_global_preview(self):
        """更新全局规则预览文本"""
        if self.global_rule and self.global_rule.root:
            text = f"🌐 当前使用全局规则:\n{self._format_rule_summary(self.global_rule)}"
        else:
            text = "🌐 当前使用全局规则:\n（全局规则未配置，不过滤任何数据）"
        self.global_preview.setText(text)
    
    def _format_rule_summary(self, rule: FilterRule) -> str:
        """格式化规则摘要（用于预览显示）"""
        # TODO: 实现递归格式化
        return "规则内容摘要..."
    
    def _on_tree_changed(self):
        """规则树结构变化"""
        self._current_rule = self.get_current_rule()
        self.rule_changed.emit(self._current_rule)
    
    def _on_test_rule(self):
        """测试当前规则"""
        rule = self.get_current_rule()
        # 通过信号通知外部（Controller）执行预览计算
        # 外部计算完成后调用 set_preview_result()
        self.rule_changed.emit(rule)
    
    def _on_save_rule(self):
        """保存规则"""
        rule = self.get_current_rule()
        # 校验...
        self.rule_changed.emit(rule)
    
    def get_current_rule(self) -> Optional[FilterRule]:
        """获取当前编辑器中的规则（从 UI 构建）"""
        if self.is_global_editor:
            root = self.root_group.to_logic_node()
            return FilterRule(root=root) if root.children else None
        
        if self._setting.mode == FilterMode.DISABLED:
            return None  # DISABLED 模式不生成规则
        
        if self._setting.mode == FilterMode.GLOBAL:
            return self.global_rule
        
        # CUSTOM 模式
        root = self.root_group.to_logic_node()
        return FilterRule(root=root) if root.children else None
    
    def set_preview_result(self, result: 'FilterPreviewResult'):
        """设置预览结果（由外部调用）"""
        self.preview_panel.set_result(result)
    
    def load_setting(self, setting: FeatureFilterSetting, global_rule: Optional[FilterRule] = None):
        """加载指标设置"""
        self._setting = setting
        self.global_rule = global_rule or self.global_rule
        
        if not self.is_global_editor and self.mode_switch:
            self.mode_switch.set_mode(setting.mode)
        
        # 加载自定义规则到 UI
        if setting.rule and setting.rule.root:
            # TODO: 将 rule.root 加载到 root_group
            pass
        
        self._refresh_ui_by_mode()
```

### 5.6 FilterPreviewPanel — 效果预览

**文件**: `src/ui/widgets/filter_preview_panel.py`

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from src.core.filtering.engine import FilterPreviewResult


class FilterPreviewPanel(QWidget):
    """过滤效果预览面板
    
    展示过滤前后样本数对比。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setProperty("card", "true")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(16, 12, 16, 12)
        
        self.lbl_total = QLabel("过滤前: -")
        self.lbl_total.setStyleSheet("font-size: 13px; color: #333;")
        
        self.lbl_filtered = QLabel("过滤后: -")
        self.lbl_filtered.setStyleSheet("font-size: 13px; color: #4CAF50; font-weight: bold;")
        
        self.lbl_removed = QLabel("已过滤: -")
        self.lbl_removed.setStyleSheet("font-size: 13px; color: #E53935;")
        
        self.lbl_ratio = QLabel("比例: -")
        self.lbl_ratio.setStyleSheet("font-size: 13px; color: #666;")
        
        layout.addWidget(self.lbl_total)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_filtered)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_removed)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.lbl_ratio)
        layout.addStretch()
    
    def set_result(self, result: FilterPreviewResult):
        self.lbl_total.setText(f"过滤前: {result.total_samples:,}")
        self.lbl_filtered.setText(f"过滤后: {result.filtered_samples:,}")
        self.lbl_removed.setText(f"已过滤: {result.removed_samples:,}")
        self.lbl_ratio.setText(f"比例: {result.removal_ratio:.2%}")
```

### 5.7 FilterRuleDialog — 对话框

**文件**: `src/ui/dialogs/filter_rule_dialog.py`

```python
from typing import Optional
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal
from src.data.models import FilterRule, FeatureFilterSetting, FilterMode
from src.ui.widgets.filter_rule_editor import FilterRuleEditor


class FilterRuleDialog(QDialog):
    """过滤规则配置对话框
    
    用于在 ImportView 和 CombinedView 中弹出编辑过滤规则。
    
    Signals:
        rule_saved(FeatureFilterSetting): 用户保存时发射
    """
    rule_saved = pyqtSignal(object)  # FeatureFilterSetting
    
    def __init__(
        self,
        columns: list[str],
        setting: Optional[FeatureFilterSetting] = None,
        global_rule: Optional[FilterRule] = None,
        feature_name: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.columns = columns
        self.feature_name = feature_name
        self.setWindowTitle(f"过滤规则 - {feature_name or '全局'}")
        self.setMinimumSize(700, 500)
        self._setup_ui()
        
        # 加载数据
        self.editor.load_setting(setting or FeatureFilterSetting(), global_rule)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 编辑器
        self.editor = FilterRuleEditor(
            columns=self.columns,
            is_global_editor=(self.feature_name is None)
        )
        layout.addWidget(self.editor, 1)
        
        # 底部按钮
        footer = QHBoxLayout()
        footer.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)
        
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("background: #4CAF50; color: white; padding: 8px 24px; border-radius: 8px;")
        btn_save.clicked.connect(self._on_save)
        footer.addWidget(btn_save)
        
        layout.addLayout(footer)
    
    def _on_save(self):
        """保存并关闭"""
        rule = self.editor.get_current_rule()
        mode = FilterMode.GLOBAL if self.feature_name is None else self.editor._setting.mode
        
        setting = FeatureFilterSetting(mode=mode, rule=rule)
        self.rule_saved.emit(setting)
        self.accept()
```

---

## 6. 控制器集成设计

### 6.1 ProjectController 修改

**文件**: `src/controllers/project_controller.py`

```python
# ===== 新增导入 =====
from src.core.filtering.engine import FilterEngine, FilterPreviewResult
from src.core.filtering.validation import FilterValidator
from src.data.models import FilterRule, FeatureFilterSetting, FilterMode

# ===== 类内新增方法 =====

def get_effective_filter_rule(self, feature: str) -> Optional[FilterRule]:
    """获取指定指标生效的过滤规则
    
    根据指标级设置和全局规则，返回最终生效的 FilterRule。
    
    Args:
        feature: 指标名称
        
    Returns:
        生效的过滤规则，如果无过滤则返回 None
    """
    if not self.state:
        return None
    
    # 获取指标设置
    setting = self.state.feature_filter_settings.get(feature)
    
    if setting:
        if setting.mode == FilterMode.DISABLED:
            return None
        elif setting.mode == FilterMode.CUSTOM:
            return setting.rule if (setting.rule and setting.rule.enabled) else None
        # mode == GLOBAL，继续走全局逻辑
    
    # 使用全局规则
    if self.state.global_filter_rule and self.state.global_filter_rule.enabled:
        return self.state.global_filter_rule
    
    return None


def get_filtered_data_for_feature(self, feature: str) -> pd.DataFrame:
    """获取指定指标过滤后的数据子集
    
    Args:
        feature: 指标名称
        
    Returns:
        过滤后的 DataFrame（未过滤则返回原 df 的 copy）
    """
    if self.df is None:
        raise ValueError("数据未加载")
    
    rule = self.get_effective_filter_rule(feature)
    return FilterEngine.apply(self.df, rule)


def get_filter_preview(self, rule: Optional[FilterRule]) -> FilterPreviewResult:
    """获取过滤规则的预览统计信息
    
    Args:
        rule: 过滤规则
        
    Returns:
        预览结果对象
    """
    if self.df is None:
        return FilterPreviewResult(0, 0, 0, 0.0)
    
    return FilterEngine.preview(self.df, rule)


def validate_filter_rule(self, rule: FilterRule) -> list[str]:
    """校验过滤规则
    
    Args:
        rule: 待校验的规则
        
    Returns:
        错误信息列表，空列表表示校验通过
    """
    return FilterValidator.validate(rule, self.df)


def save_global_filter_rule(self, rule: Optional[FilterRule]) -> None:
    """保存全局过滤规则
    
    Args:
        rule: 全局规则，None 表示清除全局规则
    """
    if not self.state:
        raise ValueError("项目未加载")
    
    self.state.global_filter_rule = rule
    self._mark_dirty()
    self.project_updated.emit(self.state)


def save_feature_filter_setting(self, feature: str, setting: FeatureFilterSetting) -> None:
    """保存指标的过滤设置
    
    Args:
        feature: 指标名称
        setting: 过滤设置
    """
    if not self.state:
        raise ValueError("项目未加载")
    
    self.state.feature_filter_settings[feature] = setting
    self._mark_dirty()
    self.project_updated.emit(self.state)


# ===== 修改现有方法 =====

def run_binning(self, feature: str, method: str, **kwargs):
    """执行分箱（修改版）
    
    在原有逻辑基础上，在取 x,y 之前应用过滤规则。
    """
    if self.df is None or self.state is None:
        self.error_occurred.emit("数据未加载")
        return
    
    # === [新增] 应用过滤规则 ===
    filtered_df = self.get_filtered_data_for_feature(feature)
    
    if filtered_df.empty:
        self.error_occurred.emit(f"指标 '{feature}' 过滤后数据为空，无法进行分箱")
        return
    
    # 从过滤后的数据取 x, y
    x = filtered_df[feature]
    y = filtered_df[self.state.target_col] if self.state.target_col else None
    
    # ... 原有分箱逻辑继续 ...
    # binner.fit(x, y, **kwargs)
    # 但注意：原有逻辑可能直接从 self.df 取数据，需要确认修改点
```

### 6.2 时序图：打开指标规则编辑器

```
用户点击 CombinedView 中的"配置过滤规则"按钮
    │
    ▼
CombinedView._open_filter_dialog(feature_name)
    │
    ├─► 获取数据列名: self.controller.state.feature_cols + [target_col]
    │
    ├─► 获取当前设置: setting = controller.state.feature_filter_settings.get(feature)
    │
    ├─► 获取全局规则: global_rule = controller.state.global_filter_rule
    │
    ▼
FilterRuleDialog(columns, setting, global_rule, feature_name)
    │
    ├─► 初始化 FilterRuleEditor
    │       ├─► mode_switch.set_mode(setting.mode)
    │       ├─► 加载 setting.rule 到 root_group
    │       └─► _refresh_ui_by_mode()
    │
    ▼
[用户交互：切换模式 / 编辑规则 / 测试规则]
    │
    ├─ 点击"测试规则"
    │   ├─► editor.get_current_rule()
    │   ├─► dialog 调用 controller.get_filter_preview(rule)
    │   ├─► FilterEngine.preview(df, rule)
    │   └─► editor.set_preview_result(result)
    │
    ├─ 切换模式（GLOBAL → CUSTOM）
    │   └─► _refresh_ui_by_mode() 显示编辑器
    │
    └─ 添加条件、编辑条件、删除条件
        └─► root_group 内部更新，structure_changed 信号
    │
    ▼
用户点击"保存"
    │
    ├─► dialog._on_save()
    ├─► editor.get_current_rule() → FilterRule
    ├─► 构建 FeatureFilterSetting(mode, rule)
    ├─► dialog.rule_saved.emit(setting)
    ├─► CombinedView 接收信号
    ├─► controller.save_feature_filter_setting(feature, setting)
    ├─► state 更新 + _mark_dirty()
    ├─► project_updated.emit(state)
    └─► dialog.accept()
    │
    ▼
CombinedView 刷新指标列表图标（显示该指标使用自定义规则）
```

### 6.3 时序图：执行分箱（含过滤）

```
用户点击"运行分箱"
    │
    ▼
CombinedView.run_binning(feature, method, **kwargs)
    │
    ├─► 组装参数 kwargs
    │
    ▼
SingleBinningWorker(controller, feature, method, kwargs)
    │
    ▼ (在 Worker 线程中)
controller.run_binning(feature, method, emit_error=False, **kwargs)
    │
    ├─► [新增] filtered_df = self.get_filtered_data_for_feature(feature)
    │
    ├─► x = filtered_df[feature]
    ├─► y = filtered_df[target_col]
    │
    ├─► binner = self.binners[method]()
    ├─► binner.fit(x, y, **merged_params)
    │
    ├─► metrics = MetricsCalculator.calculate(...)
    │
    ├─► [新增] 在 BinningConfig 中记录过滤规则信息
    │   cfg = BinningConfig(
    │       method=method,
    │       params=merged_params,
    │       splits=splits,
    │       # [新增字段]
    │       filter_rule_summary=self._summarize_filter_rule(feature)
    │   )
    │
    ├─► state.binning_configs[feature] = cfg
    ├─► state.binning_results[feature] = metrics
    │
    └─► binning_finished.emit(feature, metrics)
    │
    ▼
CombinedView.on_binning_finished(feature, metrics)
    └─► render_binning(metrics, cfg)
        └─► 在分箱明细表中展示过滤规则摘要（如有）
```

---

## 7. 与现有 UI 的集成点

### 7.1 ImportView 集成（全局规则入口）

**文件**: `src/ui/views/import_view.py`

在数据预览表格下方增加全局过滤规则配置区域：

```python
# 在 ImportView.init_ui() 中添加
self.filter_section = self._build_filter_section()
main_layout.addWidget(self.filter_section)

def _build_filter_section(self):
    section = QWidget()
    layout = QHBoxLayout(section)
    
    self.lbl_filter_status = QLabel("🌐 全局过滤规则: 未配置")
    layout.addWidget(self.lbl_filter_status)
    
    self.btn_config_filter = QPushButton("配置全局过滤规则")
    self.btn_config_filter.clicked.connect(self._open_global_filter_dialog)
    layout.addWidget(self.btn_config_filter)
    
    layout.addStretch()
    return section

def _open_global_filter_dialog(self):
    """打开全局规则编辑对话框"""
    dialog = FilterRuleDialog(
        columns=self._get_all_columns(),
        setting=None,  # 全局规则不传 setting
        global_rule=self.controller.state.global_filter_rule if self.controller.state else None,
        feature_name=None,  # None 表示全局规则
        parent=self
    )
    dialog.rule_saved.connect(self._on_global_filter_saved)
    dialog.exec()

def _on_global_filter_saved(self, setting):
    """全局规则保存回调"""
    # setting 中 mode 应为 GLOBAL，rule 为实际规则
    self.controller.save_global_filter_rule(setting.rule)
    self._update_filter_status()

def _update_filter_status(self):
    """更新全局规则状态显示"""
    if self.controller.state and self.controller.state.global_filter_rule:
        rule = self.controller.state.global_filter_rule
        self.lbl_filter_status.setText(f"🌐 全局过滤规则: {'已启用' if rule.enabled else '已禁用'}")
    else:
        self.lbl_filter_status.setText("🌐 全局过滤规则: 未配置")
```

### 7.2 CombinedView 集成（指标级规则入口）

**文件**: `src/ui/views/combined_view.py`

在变量列表区域增加过滤规则配置入口：

```python
# 在 CombinedView.init_ui() 中，变量列表上方或下方添加
filter_toolbar = QHBoxLayout()

self.btn_feature_filter = QPushButton("⚙️ 配置过滤规则")
self.btn_feature_filter.setToolTip("为当前选中的指标配置数据过滤规则")
self.btn_feature_filter.clicked.connect(self._open_feature_filter_dialog)
filter_toolbar.addWidget(self.btn_feature_filter)

# 在 feature_list 的 currentRowChanged 信号处理中更新按钮状态

def _open_feature_filter_dialog(self):
    """打开当前选中指标的规则编辑对话框"""
    feature = self._get_current_feature()
    if not feature:
        return
    
    setting = self.controller.state.feature_filter_settings.get(feature) if self.controller.state else None
    global_rule = self.controller.state.global_filter_rule if self.controller.state else None
    
    dialog = FilterRuleDialog(
        columns=self._get_all_columns(),
        setting=setting,
        global_rule=global_rule,
        feature_name=feature,
        parent=self
    )
    dialog.rule_saved.connect(lambda s: self._on_feature_filter_saved(feature, s))
    dialog.exec()

def _on_feature_filter_saved(self, feature: str, setting: FeatureFilterSetting):
    """指标规则保存回调"""
    self.controller.save_feature_filter_setting(feature, setting)
    self._update_feature_list_icons()

def _update_feature_list_icons(self):
    """更新变量列表中的过滤状态图标"""
    for i in range(self.feature_list.count()):
        item = self.feature_list.item(i)
        feature = item.text()
        
        setting = self.controller.state.feature_filter_settings.get(feature)
        if setting:
            if setting.mode == FilterMode.CUSTOM:
                item.setText(f"⚙️ {feature}")
                item.setToolTip(f"{feature}\n使用自定义过滤规则")
            elif setting.mode == FilterMode.DISABLED:
                item.setText(f"🚫 {feature}")
                item.setToolTip(f"{feature}\n不参与任何数据过滤")
            else:
                item.setText(feature)
                item.setToolTip(feature)
        else:
            item.setText(feature)
            item.setToolTip(feature)
```

---

## 8. 样式规范（QSS）

在 `style.qss` 末尾追加：

```css
/* ========== 过滤规则编辑器 ========== */

FilterRuleEditor {
    background: transparent;
}

/* 逻辑组容器 */
[logicGroup="true"] {
    background: #F8FAFD;
    border: 1px solid #E3E6EA;
    border-radius: 10px;
}

/* 条件行 */
FilterConditionRow {
    background: #FFFFFF;
    border: 1px solid #D7DEE8;
    border-radius: 8px;
}

FilterConditionRow:hover {
    border-color: #B0C4DE;
    background: #FAFBFD;
}

/* 模式切换按钮组 */
FilterModeSwitch QPushButton {
    background: linear-gradient(to bottom, #F4F7FB, #E8EEF6);
    border: 1px solid #C9D6EA;
    border-radius: 8px;
    padding: 6px 14px;
    color: #666;
    font-size: 12px;
}

FilterModeSwitch QPushButton:hover {
    background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
    color: #333;
}

FilterModeSwitch QPushButton:checked {
    background: #4A90D9;
    color: white;
    border-color: #3A7BC8;
}

/* 预览面板 */
FilterPreviewPanel {
    background: linear-gradient(to bottom, #FFFFFF, #F4F7FB);
    border: 1px solid #E3E6EA;
    border-radius: 10px;
}

/* 输入框在过滤编辑器中的样式 */
FilterConditionRow QComboBox,
FilterConditionRow QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D7DEE8;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}

FilterConditionRow QComboBox:focus,
FilterConditionRow QLineEdit:focus {
    border-color: #4A90D9;
}

/* 操作按钮 */
FilterLogicGroupWidget QPushButton {
    background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
    border: 1px solid #C9D6EA;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}

FilterLogicGroupWidget QPushButton:hover {
    background: linear-gradient(to bottom, #D9E4F5, #C9D6EA);
}
```

---

## 9. 错误处理与边界情况

| 场景 | 处理策略 | 负责模块 |
|------|---------|---------|
| 规则引用不存在的列 | `FilterValidator` 校验时返回错误，UI 显示红色提示 | validation.py + UI |
| 规则值类型与列类型不匹配 | 尝试自动转换，失败时校验报错 | validation.py |
| 过滤后数据为空 | `run_binning` 中提前拦截，弹出友好提示，不执行分箱 | controller.py |
| 过滤后某箱样本数 < min_samples | 正常传入分箱算法，由算法自身处理 | 现有算法 |
| 逻辑组为空 | AND 返回全 True，OR 返回全 False，校验时警告 | engine.py |
| 规则嵌套深度 > MAX_NESTING_DEPTH | 校验拒绝保存 | validation.py |
| 旧项目文件无过滤字段 | 加载时使用默认值（None / empty dict） | models.py |
| 全局规则编辑时引用指标级变量 | 允许，全局规则可使用任意列 | engine.py |
| 多值输入格式错误（如 `in` 操作符） | 按逗号分割，去除空白，空值校验报错 | condition_row.py |
| 用户快速连续点击"测试规则" | UI 层防抖，或取消上次未完成的 Worker | preview_panel.py |

---

## 10. 测试策略

### 10.1 单元测试

**文件**: `tests/test_filter_engine.py`

| 测试用例 | 描述 |
|---------|------|
| `test_apply_empty_rule` | 空规则不过滤 |
| `test_apply_single_condition_eq` | `==` 操作符 |
| `test_apply_single_condition_gt` | `>` 操作符 |
| `test_apply_single_condition_in` | `in` 操作符（多值） |
| `test_apply_single_condition_between` | `between` 操作符（区间） |
| `test_apply_single_condition_null` | `is null` 操作符 |
| `test_apply_negate_condition` | NOT 取反 |
| `test_apply_and_logic` | AND 逻辑组合 |
| `test_apply_or_logic` | OR 逻辑组合 |
| `test_apply_nested_logic` | 嵌套 AND/OR |
| `test_apply_complex_rule` | 复杂嵌套规则 |
| `test_preview_calculation` | 预览统计计算正确性 |

**文件**: `tests/test_filter_validation.py`

| 测试用例 | 描述 |
|---------|------|
| `test_validate_empty_variable` | 空变量名校验失败 |
| `test_validate_invalid_column` | 列不存在校验失败 |
| `test_validate_unsupported_operator` | 不支持的操作符 |
| `test_validate_missing_value` | 需要值但值为空 |
| `test_validate_between_wrong_value_count` | between 需要两个值 |
| `test_validate_max_nesting_depth` | 超过最大嵌套深度 |
| `test_validate_valid_rule` | 合法规则校验通过 |

### 10.2 集成测试

**文件**: `tests/test_filter_integration.py`

| 测试用例 | 描述 |
|---------|------|
| `test_global_filter_applied_in_binning` | 全局规则在分箱时正确应用 |
| `test_custom_filter_overrides_global` | 自定义规则覆盖全局规则 |
| `test_disabled_feature_skips_filter` | DISABLED 模式跳过所有过滤 |
| `test_filter_persistence_in_fht` | 过滤规则随项目正确保存/加载 |
| `test_old_project_backward_compat` | 旧项目文件加载不报错 |
| `test_filter_ui_dialog_flow` | UI 对话框完整操作流程 |

---

## 11. 实现计划（分阶段）

### Phase 1: 核心引擎（1-2 天）
- [ ] 新建 `src/core/filtering/` 模块
- [ ] 实现 `FilterEngine.apply()` 和 `preview()`
- [ ] 实现 `FilterValidator`
- [ ] 扩展 `src/data/models.py` 数据模型
- [ ] 编写引擎单元测试

### Phase 2: UI 组件（2-3 天）
- [ ] 实现 `FilterModeSwitch`
- [ ] 实现 `FilterConditionRow`（显示+编辑双模式）
- [ ] 实现 `FilterLogicGroupWidget`
- [ ] 实现 `FilterPreviewPanel`
- [ ] 实现 `FilterRuleEditor`（整合以上组件）
- [ ] 实现 `FilterRuleDialog`
- [ ] 编写 QSS 样式

### Phase 3: 控制器集成（1 天）
- [ ] `ProjectController` 新增过滤相关方法
- [ ] 修改 `run_binning()` 应用过滤逻辑
- [ ] `BinningConfig` 扩展过滤规则摘要字段

### Phase 4: 页面集成（1 天）
- [ ] `ImportView` 增加全局规则入口
- [ ] `CombinedView` 增加指标级规则入口
- [ ] 变量列表图标标识过滤状态

### Phase 5: 测试与打磨（1-2 天）
- [ ] 集成测试
- [ ] 边界情况测试
- [ ] 旧项目兼容性测试
- [ ] UI 交互细节打磨

**预估总工期**: 6-9 天

---

## 12. 验收检查清单

- [ ] 数据模型扩展正确，pickle 序列化兼容
- [ ] `FilterEngine` 所有操作符单元测试通过
- [ ] `FilterValidator` 边界校验完整
- [ ] 全局规则在 ImportView 可配置
- [ ] 指标级规则在 CombinedView 可配置
- [ ] 三态切换（GLOBAL/CUSTOM/DISABLED）UI 正常
- [ ] 自定义规则正确覆盖全局规则
- [ ] DISABLED 模式正确跳过所有过滤
- [ ] 分箱计算使用过滤后的数据
- [ ] 过滤效果预览统计正确
- [ ] 旧项目文件无感知加载
- [ ] UI 风格与现有项目一致
- [ ] 所有新增代码有类型注解
- [ ] 所有公共方法有 docstring
