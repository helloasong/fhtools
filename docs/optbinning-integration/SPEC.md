# Optbinning 集成技术规范

> 版本: v1.0  
> 日期: 2026-03-11

---

## 1. 接口规范

### 1.1 适配器接口

```python
# src/core/binning/optbinning_adapter.py

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from .base import BaseBinner

class OptimalBinningAdapter(BaseBinner):
    """
    Optbinning 适配器，将 OptimalBinning 包装为符合 BaseBinner 接口
    """
    
    def __init__(self):
        super().__init__()
        self._optb = None
        self._is_fitted = False
        
    def fit(
        self, 
        x: pd.Series, 
        y: Optional[pd.Series] = None, 
        **kwargs
    ) -> 'OptimalBinningAdapter':
        """
        拟合最优分箱
        
        Args:
            x: 特征数据
            y: 目标变量（二分类 0/1）
            **kwargs: 分箱参数
                - solver: 'cp' | 'mip' | 'ls', default='cp'
                - divergence: 'iv' | 'js' | 'hellinger' | 'triangular', default='iv'
                - monotonic_trend: str, default='auto'
                - max_n_bins: int, default=10
                - min_n_bins: int, default=2
                - max_n_prebins: int, default=20
                - min_prebin_size: float, default=0.05
                - special_codes: list, default=None
                - time_limit: int, default=100
        
        Returns:
            self
        """
        pass
    
    def transform(self, x: pd.Series) -> pd.Series:
        """
        将数据转换为分箱标签
        
        Args:
            x: 待转换数据
            
        Returns:
            分箱后的区间标签
        """
        pass
    
    @property
    def splits(self) -> List[float]:
        """获取切点列表"""
        pass
    
    @property
    def status(self) -> str:
        """获取求解状态"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取求解信息（时间、迭代次数等）"""
        pass
```

### 1.2 推荐参数接口

```python
# src/utils/recommend_params.py

from typing import Dict, Any

def get_recommended_params(n_samples: int) -> Dict[str, Any]:
    """
    根据样本量推荐分箱参数
    
    Args:
        n_samples: 样本数量
        
    Returns:
        推荐参数字典
        {
            'solver': str,
            'max_n_prebins': int,
            'min_prebin_size': float,
            'max_n_bins': int,
            'min_n_bins': int,
            'min_bin_size': float,
            'time_limit': int,
            'gamma': float
        }
    """
    pass

def get_data_scale_label(n_samples: int) -> str:
    """获取数据规模标签"""
    pass
```

### 1.3 配置面板接口

```python
# src/ui/widgets/optbinning_config_panel.py

from PyQt6.QtWidgets import QWidget
from typing import Dict, Any

class OptbinningConfigPanel(QWidget):
    """Optbinning 配置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        """初始化 UI 组件"""
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        pass
    
    def set_config(self, config: Dict[str, Any]):
        """
        设置配置
        
        Args:
            config: 配置字典
        """
        pass
    
    def apply_recommended_params(self, n_samples: int):
        """
        应用推荐参数
        
        Args:
            n_samples: 样本数量
        """
        pass
    
    def reset_to_defaults(self):
        """重置为默认值"""
        pass
```

---

## 2. 参数规范

### 2.1 Optbinning 核心参数

| 参数名 | 类型 | 默认值 | 范围 | 说明 |
|--------|------|--------|------|------|
| solver | str | 'cp' | 'cp'/'mip'/'ls' | 求解器类型 |
| divergence | str | 'iv' | 'iv'/'js'/'hellinger'/'triangular' | 优化目标 |
| monotonic_trend | str | 'auto' | 见下方 | 单调性约束 |
| max_n_bins | int | 10 | [2, 100] | 最大箱数 |
| min_n_bins | int | 2 | [2, max_n_bins] | 最小箱数 |
| max_n_prebins | int | 20 | [5, 200] | 预分箱数 |
| min_prebin_size | float | 0.05 | (0, 1] | 预分箱最小占比 |
| min_bin_size | float | None | (0, 1] | 每箱最小占比 |
| max_pvalue | float | None | (0, 1] | 最大p-value |
| gamma | float | 0 | [0, 1] | 正则化系数 |
| special_codes | list | None | - | 特殊值列表 |
| time_limit | int | 100 | [10, 600] | 求解时间限制(秒) |

### 2.2 单调性趋势选项

```python
MONOTONIC_TREND_OPTIONS = [
    ('auto', '自动检测'),
    ('auto_heuristic', '启发式自动'),
    ('ascending', '递增'),
    ('descending', '递减'),
    ('concave', '凹形'),
    ('convex', '凸形'),
    ('peak', '单峰'),
    ('valley', '单谷'),
]
```

### 2.3 求解器选项

```python
SOLVER_OPTIONS = [
    ('cp', 'CP (约束编程) - 推荐'),
    ('mip', 'MIP (混合整数规划) - 精确但慢'),
    ('ls', 'LS (LocalSolver) - 大数据'),
]
```

### 2.4 优化目标选项

```python
DIVERGENCE_OPTIONS = [
    ('iv', 'IV (信息值) - 风控常用'),
    ('js', 'JS (Jensen-Shannon)'),
    ('hellinger', 'Hellinger 散度'),
    ('triangular', '三角判别 - 最快'),
]
```

---

## 3. 推荐参数规则

### 3.1 小数据 (< 10,000)

```python
{
    'solver': 'cp',
    'max_n_prebins': 20,
    'min_prebin_size': 0.05,
    'max_n_bins': 5,
    'min_n_bins': 2,
    'min_bin_size': 0.05,
    'time_limit': 30,
    'gamma': 0
}
```

### 3.2 中数据 (10,000 - 100,000)

```python
{
    'solver': 'cp',
    'max_n_prebins': 20,
    'min_prebin_size': 0.05,
    'max_n_bins': 5,
    'min_n_bins': 2,
    'min_bin_size': 0.05,
    'time_limit': 100,
    'gamma': 0
}
```

### 3.3 大数据 (> 100,000)

```python
{
    'solver': 'ls',
    'max_n_prebins': 50,
    'min_prebin_size': 0.02,
    'max_n_bins': 10,
    'min_n_bins': 2,
    'min_bin_size': 0.02,
    'time_limit': 60,
    'gamma': 0.1
}
```

---

## 4. 错误处理规范

### 4.1 异常类型

```python
class OptbinningNotInstalledError(Exception):
    """optbinning 未安装"""
    pass

class BinningSolveError(Exception):
    """求解失败"""
    pass

class BinningTimeoutError(Exception):
    """求解超时"""
    pass
```

### 4.2 错误处理策略

| 错误场景 | 处理策略 | 用户提示 |
|----------|----------|----------|
| optbinning 未安装 | 隐藏"最优分箱"选项 | 不提示 |
| 求解超时 | 返回当前最优解 | "求解超时，返回当前最优可行解" |
| 无解 | 降级到决策树 | "无法满足约束，已降级到决策树分箱" |
| 参数错误 | 抛出异常 | 显示具体错误信息 |

---

## 5. UI 规范

### 5.1 配置面板布局

```
┌─────────────────────────────────────────────────────────┐
│  分箱方法: [🎯 最优分箱 ▼]  [⚡恢复推荐] [运行] [保存]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ 基础配置        │  │ 特殊值处理                 │  │
│  │                 │  │                            │  │
│  │  求解器: [▼]    │  │  特殊值: [-999, 999]       │  │
│  │  优化目标: [▼]  │  │  [?] 需要单独处理的标记值  │  │
│  │  单调性: [▼]    │  │                            │  │
│  │                 │  │                            │  │
│  │  箱数范围:      │  │                            │  │
│  │  [2] - [10]     │  │                            │  │
│  │                 │  │                            │  │
│  │  求解限制:      │  │                            │  │
│  │  [100] 秒       │  │                            │  │
│  │                 │  │                            │  │
│  └─────────────────┘  └─────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Tooltip 规范

```python
# 简短提示 (原生 Tooltip)
TOOLTIP_SHORT = "每箱最小样本占比，推荐: 大数据2%，中小数据5%"

# 详细提示 (富文本，Phase 2)
TOOLTIP_RICH = """
<h4>📘 最小箱大小 (min_bin_size)</h4>
<p>每箱最小样本占比，防止过拟合。</p>
<ul>
    <li>大数据(&gt;10万): 0.02 (2%)</li>
    <li>中小数据: 0.05 (5%)</li>
</ul>
"""
```

### 5.3 确认对话框

```
┌────────────────────────────────────────────┐
│  ⚡ 恢复推荐参数                            │
├────────────────────────────────────────────┤
│  当前数据规模: 50,000 样本 (中数据)          │
│                                             │
│  即将应用的推荐值:                          │
│  ┌─────────────────┬─────────────────┐     │
│  │ 参数            │ 推荐值          │     │
│  ├─────────────────┼─────────────────┤     │
│  │ 求解器          │ CP              │     │
│  │ 预分箱数        │ 20              │     │
│  │ 最小箱大小      │ 5%              │     │
│  │ 求解时间限制    │ 100秒           │     │
│  │ 正则化系数      │ 0               │     │
│  └─────────────────┴─────────────────┘     │
│                                             │
│  ⚠️ 此操作将覆盖当前所有参数设置            │
│                                             │
│           [取消]    [应用推荐值]            │
└────────────────────────────────────────────┘
```

---

## 6. 测试规范

### 6.1 单元测试要求

- 适配器: 覆盖率 > 80%
- 推荐参数: 所有分支覆盖
- 配置面板: 主要交互覆盖

### 6.2 集成测试要求

- 完整流程: 导入 → 配置 → 运行 → 结果
- 边界条件: 空数据、单一值、全缺失
- 异常情况: 未安装、超时、无解

### 6.3 性能测试要求

| 数据规模 | 时间要求 | 内存要求 |
|----------|----------|----------|
| 1,000 | < 1s | < 100MB |
| 10,000 | < 3s | < 200MB |
| 100,000 | < 10s | < 500MB |

---

## 7. 代码规范

### 7.1 导入规范

```python
# 标准库
from typing import List, Optional, Dict, Any

# 第三方库
try:
    from optbinning import OptimalBinning
    OPTBINNING_AVAILABLE = True
except ImportError:
    OPTBINNING_AVAILABLE = False
import pandas as pd
import numpy as np

# 项目内部
from src.core.binning.base import BaseBinner
```

### 7.2 命名规范

- 类名: `OptimalBinningAdapter` (PascalCase)
- 函数: `get_recommended_params` (snake_case)
- 常量: `DEFAULT_SOLVER = 'cp'` (UPPER_SNAKE)
- 私有: `_optb`, `_is_fitted` (前导下划线)

### 7.3 文档规范

```python
def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'OptimalBinningAdapter':
    """
    拟合最优分箱
    
    Args:
        x: 特征数据，数值型 Series
        y: 目标变量，二分类 0/1
        **kwargs: 分箱参数，详见 SPEC.md
        
    Returns:
        self，支持链式调用
        
    Raises:
        ValueError: 参数错误
        BinningSolveError: 求解失败
        
    Example:
        >>> adapter = OptimalBinningAdapter()
        >>> adapter.fit(x, y, solver='cp', max_n_bins=5)
    """
```

---

## 8. 依赖管理

### 8.1 可选依赖声明

```txt
# requirements.txt
# 核心依赖（已有）
pandas>=1.5.0
numpy>=1.23.0
PyQt6>=6.4.0

# 可选依赖
optbinning>=0.19.0; extra == 'optimal'
ortools>=9.8; extra == 'optimal'
```

### 8.2 运行时检测

```python
def check_optbinning_available() -> bool:
    """检查 optbinning 是否可用"""
    try:
        import optbinning
        return True
    except ImportError:
        return False
```

---

## 9. 日志规范

```python
import logging

logger = logging.getLogger(__name__)

# 信息日志
logger.info(f"Optbinning fit started: solver={solver}, n_samples={len(x)}")

# 警告日志
logger.warning(f"Solver timeout after {time_limit}s, returning best feasible solution")

# 错误日志
logger.error(f"Binning solve failed: {e}")
```

---

## 10. 版本兼容性

- Python: 3.9+
- optbinning: 0.19.0+
- pandas: 1.5.0+
- PyQt6: 6.4.0+

---

**规范制定**: Kimi  
**最后更新**: 2026-03-11
