# Optbinning 集成需求文档 (PRD)

> 版本: v0.1 (草案)  
> 日期: 2026-03-11  
> 状态: 待评审

---

## 1. 背景与目标

### 1.1 现状
当前 FHBinningTool 已实现 6 种分箱算法：
- 无监督：等频、等距、手动切点
- 有监督：决策树、卡方(ChiMerge)、Best-KS

### 1.2 为什么要接入 Optbinning
[optbinning](https://gnpalencia.org/optbinning/) 是 Python 生态中**最专业**的分箱库，具备以下优势：

| 能力 | 当前实现 | Optbinning |
|------|----------|------------|
| 求解器 | 贪心/启发式 | CP(约束编程)、MIP、LocalSolver |
| 单调性约束 | 无 | 完整支持 (asc/desc/concave/convex/peak/valley) |
| 统计约束 | 无 | p-value、最小箱大小、样本数等 |
| 目标优化 | 局部最优 | IV/JS/Hellinger 全局最优 |
| 分类型变量 | 不支持 | 原生支持 |
| 特殊值处理 | 基础 | 灵活的 special_codes |
| 行业认可度 | 内部工具 | 广泛应用于风控建模 |

### 1.3 目标
**将 Optbinning 作为"高级分箱引擎"接入，不改变现有 UI 架构，通过增强配置面板提供进阶能力。**

---

## 2. 功能需求

### 2.1 核心功能

#### FR-001: 新增 "最优分箱(Optbinning)" 方法并设为默认
- 在分箱方法下拉框新增选项：**"最优分箱 (Optimal)"**
- **将此选项设为默认选中项**，体现工具的专业性
- 选中后显示 Optbinning 专属配置面板
- 原有 6 种方法保留，移至下拉框下方

**下拉框选项顺序**:
```python
method_map = [
    ("🎯 最优分箱 (推荐)", "optimal"),      # ← 默认选中
    ("───────────────", "separator"),      # 分隔线
    ("等频分箱", "equal_freq"),
    ("等距分箱", "equal_width"),
    ("决策树分箱", "decision_tree"),
    ("卡方分箱", "chi_merge"),
    ("Best-KS 分箱", "best_ks"),
    ("自定义切点", "manual"),
]
```
- 使用 emoji 图标区分专业方法 vs 传统方法
- 分隔线将最优分箱与其他方法视觉隔离
- 鼠标悬停在"最优分箱"上时显示提示："基于 Optbinning 的全局最优求解"

#### FR-002: 求解器选择
- 支持 3 种求解器：
  - `cp` (约束编程, 默认) - 推荐，平衡速度和质量
  - `mip` (混合整数规划) - 精确解，大数据慢
  - `ls` (LocalSolver) - 超大规模数据
- UI: 下拉选择，默认 CP

#### FR-003: 优化目标选择
- 发散度量选项：
  - `iv` (信息值, 默认)
  - `js` (Jensen-Shannon)
  - `hellinger` (Hellinger 散度)
  - `triangular` (三角判别)

#### FR-004: 单调性趋势约束
- 支持选项：
  - `auto` (自动检测, 默认)
  - `auto_heuristic` (启发式自动，更快)
  - `ascending` (坏样本率递增)
  - `descending` (坏样本率递减)
  - `concave` (凹形)
  - `convex` (凸形)
  - `peak` (单峰，允许先增后减)
  - `valley` (单谷，允许先减后增)
- **UI 提示**: 在图表区域用图标标注当前趋势约束类型

#### FR-005: 高级约束参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_n_prebins | int | 20 | 预分箱数，决定求解精度 |
| min_prebin_size | float | 0.05 | 预分箱最小样本占比 |
| min_n_bins | int | None | 最少箱数 |
| max_n_bins | int | None | 最多箱数 |
| min_bin_size | float | None | 每箱最小样本占比 |
| max_bin_size | float | None | 每箱最大样本占比 |
| min_bin_n_nonevent | int | None | 每箱最小好样本数 |
| min_bin_n_event | int | None | 每箱最小坏样本数 |
| max_pvalue | float | None | 最大 p-value (统计显著性) |
| gamma | float | 0 | 正则化系数，减少主导箱 |
| time_limit | int | 100 | 求解时间限制(秒) |

- **UI 设计**: 这些参数折叠在"高级选项"展开面板中，避免界面臃肿

#### FR-006: 特殊值处理 (Special Codes)
- 支持用户定义特殊值列表（如 -999, 999 表示缺失标记）
- 这些值单独成箱，不参与优化过程
- UI: 输入框，逗号分隔

#### FR-007: 分类型变量支持
- 当前工具仅支持数值型，接入后可支持分类型变量分箱
- UI: 变量列表中标识类型 (🔢数值 / 🏷️分类)
- 分类型变量显示 `cat_cutoff` 参数 (低频类别合并阈值)

---

### 2.2 结果展示增强

#### FR-008: 求解状态显示
- 在分箱图区域显示求解状态：
  - 🟡 求解中...
  - 🟢 最优解 / 可行解
  - 🔴 无解 / 超时

#### FR-009: 优化信息面板
- 显示 Optbinning 提供的统计信息：
  - 求解时间
  - 迭代次数
  - 目标函数值 (IV/JS 等)
  - 约束违反情况（如有）

---

### 2.3 批量与自动化

#### FR-010: 批量最优分箱
- 支持对多个变量一键执行 Optbinning
- 复用当前配置参数
- 后台线程执行，显示进度条

#### FR-011: 智能参数推荐
- 根据数据特征自动推荐参数：
  - 样本量 < 1万: max_n_prebins=10
  - 样本量 1-10万: max_n_prebins=20 (默认)
  - 样本量 > 10万: max_n_prebins=50, solver='ls'

#### FR-012: 一键恢复推荐值
- 在配置面板顶部添加 **"⚡恢复推荐"** 按钮
- 点击后根据当前数据特征，自动重置所有参数为推荐值
- 恢复范围包括：
  - 基础配置：求解器、目标、趋势、箱数范围
  - 高级配置：预分箱数、最小箱大小、正则化等
- **防误触设计**: 恢复前弹出确认对话框，显示即将应用的推荐值列表
- **差异化推荐逻辑**:

```python
def get_recommended_params(n_samples, n_features):
    """根据数据规模生成推荐参数"""
    
    if n_samples < 10_000:
        # 小数据：追求精度
        return {
            'solver': 'cp',
            'max_n_prebins': 20,
            'min_prebin_size': 0.05,
            'max_n_bins': 5,
            'min_bin_size': 0.05,
            'time_limit': 30,
            'gamma': 0
        }
    elif n_samples < 100_000:
        # 中数据：平衡
        return {
            'solver': 'cp',
            'max_n_prebins': 20,
            'min_prebin_size': 0.05,
            'max_n_bins': 5,
            'min_bin_size': 0.05,
            'time_limit': 100,
            'gamma': 0
        }
    else:
        # 大数据：速度优先
        return {
            'solver': 'ls',
            'max_n_prebins': 50,
            'min_prebin_size': 0.02,
            'max_n_bins': 10,
            'min_bin_size': 0.02,
            'time_limit': 60,
            'gamma': 0.1  # 轻度正则化，防止过拟合
        }
```

- **UI 反馈**: 恢复成功后，在按钮旁短暂显示 "✓ 已应用推荐值" 绿色提示

---

## 3. UI/UX 设计

### 3.1 配置面板布局

当前分箱配置是横向工具栏，空间受限。建议重构为：**双栏布局**

```
┌─────────────────────────────────────────────────────────────┐
│  分箱方法: [最优分箱 (Optimal) ▼]  [⚡恢复推荐] [运行] [确认并保存] │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ 基础配置     │  │ 高级选项 (展开/折叠)                 │ │
│  │              │  │                                      │ │
│  │ 求解器: [▼]  │  │ ☑ 启用约束                           │ │
│  │ 目标:   [▼]  │  │    最小箱大小: [____] %     [?]      │ │
│  │ 趋势:   [▼]  │  │    最大 p-value: [____]     [?]      │ │
│  │ 箱数: 2-10   │  │                                      │ │
│  │              │  │ ☑ 启用正则化                         │ │
│  │ 特殊值:      │  │    Gamma: [____]            [?]      │ │
│  │ [-999,999]   │  │                                      │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

> **注**: `[?]` 表示帮助图标，鼠标悬停显示参数说明浮窗

#### 恢复推荐值按钮设计

**按钮位置**: 分箱方法下拉框右侧，运行按钮左侧

**按钮样式**:
```
[⚡恢复推荐]
- 图标: 闪电或魔法棒，表示"智能重置"
- 颜色: 蓝色/青色，区别于运行按钮(绿色)和保存按钮(灰色)
- 状态: 
  • 正常: 可点击
  • 悬停: 显示提示"根据当前数据规模重置所有参数"
  • 已应用推荐: 短暂变为 "✓ 已应用" 绿色
```

**点击后确认对话框**:
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
│  │ 求解器          │ CP (约束编程)   │     │
│  │ 预分箱数        │ 20              │     │
│  │ 最小箱大小      │ 5%              │     │
│  │ 求解时间限制    │ 100秒           │     │
│  │ ...             │ ...             │     │
│  └─────────────────┴─────────────────┘     │
│                                             │
│  ⚠️ 此操作将覆盖当前所有参数设置            │
│                                             │
│           [取消]    [应用推荐值]            │
└────────────────────────────────────────────┘
```

**智能触发时机**:
- 首次加载数据后，自动弹出提示："检测到 100,000+ 样本，建议使用大数据优化参数 [应用] [忽略]"
- 用户手动点击"恢复推荐"按钮时
- 切换目标变量后（数据规模变化）

### 3.2 参数帮助提示系统

为降低 Optbinning 学习成本，所有参数都配备悬停提示。

#### 提示展示方式

**方式一: 原生 Tooltip (推荐用于简单说明)**
- 鼠标悬停在输入框/标签上 0.5 秒后显示
- 黑色半透明背景，白色文字
- 适合 1-2 句话的简短说明

**方式二: 富文本提示框 (推荐用于复杂参数)**
- 带标题、说明文字、示例值的格式化提示
- 可显示公式、推荐值、注意事项
- 适合需要详细解释的高级参数

```
鼠标悬停在"最小箱大小"输入框
       ↓
┌────────────────────────────────────────┐
│  📘 最小箱大小 (min_bin_size)           │
├────────────────────────────────────────┤
│  每箱最小样本占比，防止过拟合。          │
│                                        │
│  📊 推荐值:                             │
│    • 大数据(>10万): 0.02 (2%)           │
│    • 中小数据: 0.05 (5%, 默认)          │
│                                        │
│  ⚠️ 注意: 设置过大可能导致无法找到      │
│    满足所有约束的解                     │
└────────────────────────────────────────┘
```

#### 完整参数提示内容表

| 参数 | 提示类型 | 提示内容 |
|------|----------|----------|
| **求解器** | 富文本 | `CP (约束编程)`: 平衡求解速度和质量，推荐用于大多数场景<br>`MIP (混合整数规划)`: 求精确最优解，大数据量较慢<br>`LS (LocalSolver)`: 适合超大规模数据(>100万) |
| **优化目标** | 富文本 | `IV (信息值)`: 风控领域最常用，最大化组间差异<br>`JS (Jensen-Shannon)`: 更平滑的散度度量<br>`Hellinger`: 对分布尾部更敏感<br>`Triangular`: 计算效率最高 |
| **单调性趋势** | 富文本 | 约束各箱的坏样本率(Bad Rate)变化趋势<br>`Auto`: 自动检测最优趋势<br>`Ascending/Descending`: 单调递增/递减<br>`Peak/Valley`: 允许单峰/单谷形态<br>`Concave/Convex`: 凹凸形态 |
| **箱数范围** | Tooltip | 最少和最多分箱数，求解器在此范围内寻找最优解 |
| **特殊值** | 富文本 | 需要单独处理的特殊标记值，如:<br>• -999, 999: 缺失值标记<br>• 0: 可能表示"无此业务"<br>多个值用逗号分隔，这些值不参与优化 |
| **求解时间限制** | Tooltip | 最大求解时间(秒)，超时返回当前最优可行解 |
| **预分箱数** | 富文本 | `max_n_prebins`: 初始预分箱数量<br>• 值越大精度越高但求解越慢<br>• 推荐: 大数据用 50，中小数据用 20<br>• 仅当 solver='ls' 时推荐 >100 |
| **最小预分箱占比** | Tooltip | 预分箱阶段的最小样本占比，默认 5% |
| **最小箱大小** | 富文本 | 最终每箱最小样本占比<br>推荐: 大数据 2%，中小数据 5%<br>过小容易过拟合，过大可能无解 |
| **最大 p-value** | 富文本 | 箱间差异的统计显著性检验<br>• 默认 None (不检验)<br>• 常用值: 0.05 或 0.01<br>• 使用 Z-test 检验相邻箱差异 |
| **正则化 Gamma** | 富文本 | 减少"主导箱"现象的惩罚系数<br>• 0: 无正则化 (默认)<br>• 0.1-0.5: 轻度正则<br>• 越大箱子越均匀，但 IV 会降低 |
| **最小 mean diff** | Tooltip | (连续目标) 相邻箱的最小均值差异 |

#### 技术实现

**基础 Tooltip 实现**:
```python
from PyQt6.QtWidgets import QLineEdit, QLabel
from PyQt6.QtCore import Qt

# 为输入框添加提示
self.min_bin_size_input = QLineEdit()
self.min_bin_size_input.setToolTip(
    "每箱最小样本占比\n"
    "推荐值: 大数据 2%，中小数据 5%\n"
    "过小容易过拟合"
)
self.min_bin_size_input.setToolTipDuration(5000)  # 显示5秒
```

**富文本提示实现** (自定义样式):
```python
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class RichTooltipLabel(QLabel):
    """带 ? 图标和富文本提示的标签"""
    
    TOOLTIP_STYLE = """
    QToolTip {
        background-color: #2c3e50;
        color: white;
        border: 1px solid #34495e;
        border-radius: 4px;
        padding: 8px;
        font-size: 12px;
        max-width: 350px;
    }
    """
    
    def __init__(self, text, tooltip_html, parent=None):
        super().__init__(f"{text} <span style='color:#3498db;'>[?]</span>", parent)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setToolTip(tooltip_html)
        self.setStyleSheet(self.TOOLTIP_STYLE)

# 使用示例
label = RichTooltipLabel(
    "最小箱大小",
    """
    <h4>📘 最小箱大小 (min_bin_size)</h4>
    <p>每箱最小样本占比，防止过拟合。</p>
    <hr>
    <p><b>📊 推荐值:</b></p>
    <ul>
        <li>大数据(&gt;10万): 0.02 (2%)</li>
        <li>中小数据: 0.05 (5%, 默认)</li>
    </ul>
    <p style='color:#e74c3c;'>⚠️ 设置过大可能导致无法找到满足所有约束的解</p>
    """
)
```

**延迟显示优化** (避免误触发):
```python
from PyQt6.QtCore import QTimer

class DelayedTooltipMixin:
    """延迟显示工具提示，避免快速滑动时频繁弹出"""
    
    def __init__(self):
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip)
        self.pending_widget = None
    
    def enterEvent(self, event):
        self.pending_widget = self
        self.tooltip_timer.start(500)  # 延迟500ms
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.tooltip_timer.stop()
        self.pending_widget = None
        super().leaveEvent(event)
    
    def show_tooltip(self):
        if self.pending_widget:
            QToolTip.showText(
                self.mapToGlobal(self.rect().center()),
                self.toolTip(),
                self
            )
```

### 3.3 图表区域增强

在现有分箱图基础上增加：
1. **单调性指示器**: 在图表右上角显示当前趋势图标 (↗️ ↘️ 📈 📉 ⛰️ 🏞️)
2. **约束状态**: 鼠标悬停显示该箱是否满足所有约束
3. **求解信息浮层**: 右下角小面板显示求解时间和目标值

### 3.4 交互流程

```
用户选择"最优分箱"
       ↓
系统检测: 是否已设置目标变量?
   ├─ 否 → 提示"请先设置目标变量"
   └─ 是 → 继续
       ↓
显示 Optbinning 配置面板 (带默认值)
       ↓
用户点击 [运行]
       ↓
启动 Worker 线程 → 显示进度条
       ↓
调用 OptimalBinning.fit()
       ↓
完成 → 更新分箱图和表格
       ↓
用户可: 调整参数重跑 / 拖拽切点微调 / 确认保存
```

---

## 4. 技术方案

### 4.1 依赖管理

```txt
# requirements.txt 新增
optbinning>=0.19.0
ortools>=9.8  # CP/SAT 求解器
```

**兼容性说明**: 
- optbinning 依赖 ortools，后者支持 macOS/Linux/Windows
- 与现有 PyQt6、pandas 等依赖无冲突

### 4.2 架构设计

新增文件：
```
src/core/binning/optbinning_adapter.py  # 适配器模式封装
src/ui/widgets/optbinning_config_panel.py  # 专用配置面板
```

修改文件：
```
src/controllers/project_controller.py   # 注册新算法
src/ui/views/combined_view.py           # 集成配置面板
```

### 4.3 适配器模式

```python
# src/core/binning/optbinning_adapter.py
from optbinning import OptimalBinning
from .base import BaseBinner

class OptimalBinningAdapter(BaseBinner):
    """
    将 OptimalBinning 包装为符合 BaseBinner 接口的适配器
    """
    def __init__(self):
        super().__init__()
        self._optb = None
        self._config = {}
    
    def fit(self, x, y=None, **kwargs):
        # 提取 optbinning 专用参数
        opt_params = {k: v for k, v in kwargs.items() 
                     if k in self._VALID_PARAMS}
        
        self._optb = OptimalBinning(**opt_params)
        self._optb.fit(x, y)
        
        # 转换为内部 splits 格式
        self._splits = self._convert_splits(self._optb.splits)
        return self
    
    def transform(self, x):
        return self._optb.transform(x, metric='bins')
```

### 4.4 性能考虑

| 场景 | 策略 |
|------|------|
| 大数据 (>10万) | 默认使用 solver='ls', time_limit=30 |
| 实时预览 | 先使用预分箱结果快速展示，后台继续优化 |
| 批量处理 | 使用线程池，避免阻塞 UI |

---

## 5. 非功能需求

### 5.1 性能指标
- 单变量分箱: < 5秒 (10万样本)
- 批量 50 变量: < 2分钟
- 内存占用: < 2GB (100万样本)

### 5.2 兼容性
- 保持现有 6 种算法不变
- Optbinning 作为可选依赖，未安装时不显示"最优分箱"选项

### 5.3 错误处理
- ortools 未安装 → 友好提示
- 求解超时 → 返回当前最优可行解
- 无解 → 提示调整约束条件

### 5.4 开发注意事项（实际开发时关注）

> 以下问题不追求完美，但需在开发时留意，避免返工。

| 问题 | 建议方案 | MVP处理 |
|------|----------|---------|
| **求解失败/超时** | 自动降级到"决策树分箱"并提示用户 | P1: 可先抛错误，后续迭代优化 |
| **切换分箱方法** | 是否记住上次配置？→ **不记，每次都恢复推荐值** | P2: 暂不实现记忆功能 |
| **大数据卡顿** | 运行按钮加 loading 状态，避免重复点击 | **P0**: 必须实现 |
| **首次使用引导** | "恢复推荐"按钮旁加小字"推荐新手使用" | P2: 可后续加 |
| **依赖未安装** | 检测到 optbinning 未安装时，隐藏"最优分箱"选项 | **P0**: 必须实现 |
| **求解器选择** | CP 作为默认，但大数据(>10万)自动推荐 LS | **P0**: 推荐算法中实现 |

**Phase 1 最小文件清单**:
```
src/core/binning/optbinning_adapter.py       # 适配器
src/ui/widgets/optbinning_config_panel.py    # 配置面板
src/ui/views/combined_view.py                # 修改：切换逻辑
src/controllers/project_controller.py        # 修改：注册新方法
src/utils/recommend_params.py                # 新增：推荐算法
```

---

## 6. 迭代计划建议

### Phase 1: 基础集成 (MVP) - 优先级: P0
- [ ] 适配器实现 (`optbinning_adapter.py`)
- [ ] 将"最优分箱"设为默认选项，下拉框排序调整
- [ ] 动态配置面板 (传统 vs Optbinning 切换)
- [ ] 基础配置面板 (求解器、目标、趋势、箱数范围)
- [ ] **一键恢复推荐值按钮** + 智能推荐算法
- [ ] 单变量运行
- [ ] 基础参数提示 (原生 Tooltip)
- 预计: 5-7 天

**Phase 1 验收标准**:
1. 打开工具 → 默认选中"最优分箱"
2. 点击"恢复推荐" → 参数自动填入（根据样本量正确推荐）
3. 点击"运行" → 出分箱结果（IV/WOE 计算正确）
4. 切换回"等频分箱" → 显示原来的配置面板，功能正常
5. optbinning 未安装 → "最优分箱"选项隐藏，其他功能正常

### Phase 2: 高级功能 - 优先级: P1
- [x] 高级约束参数面板 (可折叠)
- [x] 特殊值处理 (Special Codes)
- [x] 求解状态显示 (状态图标 + 信息面板)
- [x] 富文本参数提示系统
- [x] 图表区域增强 (单调性指示器)
- 实际: 1 天 (并行开发提高效率)

### Phase 3: 增强体验 - 优先级: P2
- [x] 分类型变量支持
- [x] 批量处理 (多变量一键分箱)
- [x] Optbinning 配置导出 (JSON)
- 实际: 1 天 (并行开发)

**总计**: 约 10-14 天

---

## 7. 需求确认记录

| 问题 | 决策 | 备注 |
|------|------|------|
| **Q1: 是否替换现有决策树分箱？** | ✅ **选项 A** - 保留现有，Optbinning 作为"高级选项" | 但设为默认选中 |
| **Q2: 高级参数的默认值策略？** | ✅ **选项 B** - 根据样本量自动推荐，允许用户覆盖 | 已实现 FR-011/FR-012 |
| **Q3: 是否支持回归分箱？** | ✅ **暂不支持** | Phase 3 再评估 |
| **Q4: 导出格式扩展？** | ✅ **支持 JSON 导出** | Phase 3 实现 |
| **Q5: UI 切换方案？** | ✅ **方案 A** - 动态面板切换 | - |
| **Q6: 参数提示系统？** | ✅ **原生 Tooltip + 富文本提示框** | Phase 1 基础提示，Phase 2 富文本 |
| **Q7: 一键恢复推荐值？** | ✅ **支持** | FR-012，已加入 Phase 1 |
| **Q8: 默认分箱策略？** | ✅ **Optbinning 作为默认** | FR-001 已更新 |

---

## 8. 附录

### 8.1 回归场景分箱说明（Phase 3 评估）

**场景定义**: 目标变量是连续值（如房价、收入、信用评分），而非二分类（0/1）。

**典型应用场景**:

#### 什么是回归场景分箱？

**场景定义**: 目标变量是连续值（如房价、收入、信用评分），而非二分类（0/1）。

**典型应用场景**:
| 场景 | 目标变量 | 分箱用途 |
|------|----------|----------|
| 房价预测 | 房价（万元） | 将收入、面积等特征分箱，降低噪声 |
| 信用评分建模 | 信用分数（300-850） | 对原始特征分箱，提取非线性关系 |
| 风险评估 | 违约损失率（LGD） | 分箱后结合其他模型 |

**与二分类分箱的核心区别**:

| 维度 | 二分类 (OptimalBinning) | 连续目标 (ContinuousOptimalBinning) |
|------|------------------------|-------------------------------------|
| **优化目标** | 最大化 IV / JS / Hellinger | 最小化 L1-norm 或最大化 monotonic trend fit |
| **核心指标** | WOE, IV, Bad Rate | Mean, Std, Sum, Min, Max |
| **单调性** | Bad Rate 单调 | Mean 单调 |
| **transform输出** | WOE / Event Rate / Bin Index | Mean / Bin Index |
| **约束** | min_event_rate_diff | min_mean_diff |

**optbinning 支持情况**:
- ✅ `ContinuousOptimalBinning` - 标准连续目标分箱
- ✅ `ContinuousOptimalPWBinning` - 分段线性/多项式拟合（更高级）

#### 如果要支持，需要做哪些事情？

**1. 目标变量类型检测**
```python
# 自动检测目标变量类型
def detect_target_type(series):
    unique_ratio = series.nunique() / len(series)
    if series.nunique() == 2:
        return 'binary'
    elif pd.api.types.is_numeric_dtype(series) and unique_ratio > 0.01:
        return 'continuous'
    else:
        return 'multiclass'  # 暂不支持
```

**2. UI 层适配**

| 组件 | 二分类显示 | 连续目标显示 |
|------|-----------|-------------|
| 分箱方法参数 | divergence: iv/js/hellinger | objective: l1/l2 (默认) |
| 单调性选项 | bad rate 趋势 | mean 趋势 |
| 表格列 | WOE, IV, Bad Rate, Lift | Mean, Std, Sum, Min, Max |
| 图表 | 柱状图 + Bad Rate 折线 | 柱状图 + Mean 折线 |
| 导出规则 | WOE 映射 | Mean 映射 |

**3. 核心算法适配**

新增适配器类：
```python
# src/core/binning/optbinning_continuous_adapter.py
from optbinning import ContinuousOptimalBinning

class ContinuousOptimalBinningAdapter(BaseBinner):
    """连续目标变量的分箱适配器"""
    
    def fit(self, x, y=None, **kwargs):
        # 参数映射
        opt_params = {
            'monotonic_trend': kwargs.get('monotonic_trend', 'auto'),
            'min_mean_diff': kwargs.get('min_mean_diff', 0),
            'max_n_bins': kwargs.get('max_n_bins'),
            # ... 其他参数
        }
        
        self._optb = ContinuousOptimalBinning(**opt_params)
        self._optb.fit(x, y)
        self._splits = self._convert_splits(self._optb.splits)
        return self
    
    def transform(self, x, metric='mean'):
        # 返回 bin 标签或 mean 值
        return self._optb.transform(x, metric=metric)
```

**4. 指标计算模块重构**

```python
# src/core/metrics.py
class MetricsCalculator:
    @staticmethod
    def calculate(x_binned, y, target_type='binary', **kwargs):
        if target_type == 'binary':
            return calculate_binary_metrics(x_binned, y)
        elif target_type == 'continuous':
            return calculate_continuous_metrics(x_binned, y)
```

连续目标的指标表头：
```
| 范围 | Count | Count% | Sum | Std | Mean | Min | Max | WoE | IV |
```

**5. 导出格式扩展**

- **Excel**: 连续目标使用不同的汇总 sheet
- **Python**: 生成 `transform(df)` 返回 mean 值而非 WOE
- **SQL**: `CASE WHEN` 返回 mean 值

**6. 工作量评估**

| 任务 | 工作量 | 说明 |
|------|--------|------|
| 目标类型检测 | 0.5天 | 简单逻辑 |
| UI 组件改造 | 2天 | 动态显示不同表格/图表 |
| 适配器实现 | 1天 | 类似 Binary 适配器 |
| 指标计算 | 1.5天 | 新增连续目标统计 |
| 导出服务 | 1天 | 三种导出格式适配 |
| 测试 | 1天 | 回归测试 |
| **总计** | **~7天** | |

#### 建议决策

| 方案 | 描述 | 适用场景 |
|------|------|----------|
| **A: 暂不支持** (推荐) | Phase 1-2 专注二分类，后续再评估 | 当前业务以风控评分卡为主 |
| **B: 简单支持** | 仅支持 ContinuousOptimalBinning，UI 简化 | 有少量回归建模需求 |
| **C: 完整支持** | 支持 ContinuousOptimalPWBinning（分段多项式） | 需要高级非线性拟合 |

**当前建议**: 选择 A，原因：
1. 当前项目定位为"风控评分卡"工具，二分类是核心场景
2. 连续目标分箱是相对小众的需求
3. 可以先完成二分类的完整集成，验证架构后再扩展

**后续扩展路径**: Phase 3 时，如果用户有需求，可以：
1. 先支持基础 `ContinuousOptimalBinning`
2. 再考虑 `ContinuousOptimalPWBinning`（支持分段线性/多项式拟合，更强大但也更复杂）

### Q4: 导出格式是否需要扩展？
- optbinning 支持 to_json / to_dict
- **建议**: 增加"导出 Optbinning 配置"选项，方便 Python 复现

---

### 8.2 Optbinning 快速参考

```python
from optbinning import OptimalBinning

# 基础用法
optb = OptimalBinning(
    dtype='numerical',           # or 'categorical'
    prebinning_method='cart',    # 'cart', 'mdlp', 'quantile', 'uniform'
    solver='cp',                 # 'cp', 'mip', 'ls'
    divergence='iv',             # 'iv', 'js', 'hellinger', 'triangular'
    max_n_prebins=20,
    min_prebin_size=0.05,
    max_n_bins=5,
    min_n_bins=2,
    monotonic_trend='auto',      # 'auto', 'ascending', 'descending', ...
    max_pvalue=0.05,
    gamma=0,
    special_codes=[-999, 999],
    time_limit=100,
)
optb.fit(x, y)

# 获取结果
table = optb.binning_table
print(table.build())

# 转换
x_woe = optb.transform(x, metric='woe')
```

### 8.3 参考链接
- 官方文档: https://gnpalencia.org/optbinning/
- GitHub: https://github.com/guillermo-naranjo/optbinning
- 论文: Naranjo, G. (2020). Optimal binning.

---

**下一步**: 评审本 PRD，确认需求和优先级后，进入 Phase 1 开发。


---

## 9. 确认项目清单

### 9.1 Phase 1 功能确认

| 序号 | 确认项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | 最优分箱设为默认选项 | ✅ | 下拉框第一项，带🎯图标 |
| 2 | 原有6种算法保留并可用 | ✅ | 分隔线下方排列 |
| 3 | 动态面板切换正常 | ✅ | 切换方法时配置面板正确显示/隐藏 |
| 4 | 求解器选择(CP/MIP/LS) | ✅ | 默认CP，大数据自动推荐LS |
| 5 | 优化目标选择(IV/JS/Hellinger) | ✅ | 默认IV |
| 6 | 单调性趋势约束 | ✅ | 默认Auto |
| 7 | 箱数范围设置(min-max) | ✅ | 默认2-10 |
| 8 | 一键恢复推荐值按钮 | ✅ | 带⚡图标，点击弹出确认对话框 |
| 9 | 推荐值根据样本量正确计算 | ✅ | <1万/1-10万/>10万三档 |
| 10 | 基础参数提示(Tooltip) | ✅ | 主要参数都有提示 |
| 11 | 运行按钮loading状态 | ✅ | 防止重复点击 |
| 12 | 单变量分箱结果正确 | ⬜ | 需完整环境测试 IV/WOE/Bad Rate |
| 13 | 依赖缺失处理 | ✅ | optbinning未安装时隐藏选项 |

### 9.2 Phase 2 功能确认

| 序号 | 确认项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | 高级约束参数面板(可折叠) | ✅ | 8个参数，可折叠动画 |
| 2 | 特殊值处理(Special Codes) | ✅ | 输入框逗号分隔 |
| 3 | 求解状态显示 | ✅ | 🟡求解中 🟢完成 🔴失败 6种状态 |
| 4 | 富文本参数提示 | ✅ | HTML格式，延迟500ms显示 |
| 5 | 单调性指示器 | ✅ | 图表右上角显示趋势图标 |

### 9.3 Phase 3 功能确认

| 序号 | 确认项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | 分类型变量支持 | ✅ | dtype='categorical', cat_cutoff参数 |
| 2 | 批量处理 | ✅ | 多选+进度条+取消功能 |
| 3 | Optbinning配置导出(JSON) | ✅ | 完整配置+WOE+IV+可复现 |

---

## 10. 测试用例列表

### 10.1 单元测试

```python
# tests/test_optbinning_adapter.py

class TestOptimalBinningAdapter:
    """适配器单元测试"""
    
    def test_fit_basic(self):
        """TC-001: 基础拟合测试"""
        # 输入: 1000样本的二分类数据
        # 期望: 正常返回切点，无异常
        pass
    
    def test_fit_with_constraints(self):
        """TC-002: 带约束拟合测试"""
        # 输入: 设置max_n_bins=5, monotonic_trend='ascending'
        # 期望: 返回5个箱，bad rate单调递增
        pass
    
    def test_transform(self):
        """TC-003: 转换测试"""
        # 输入: fit后的模型，新数据
        # 期望: 正确分箱，返回WOE或bins
        pass
    
    def test_special_codes(self):
        """TC-004: 特殊值处理测试"""
        # 输入: 包含-999的数据，special_codes=[-999]
        # 期望: -999单独成箱，不参与优化
        pass
    
    def test_solver_selection(self):
        """TC-005: 求解器选择测试"""
        # 输入: solver='cp', 'mip', 'ls'
        # 期望: 各求解器正常运行
        pass
```

### 10.2 集成测试

```python
# tests/test_optbinning_integration.py

class TestOptbinningIntegration:
    """集成测试"""
    
    def test_default_method_selection(self):
        """TC-101: 默认分箱方法检查"""
        # 步骤: 打开工具，查看分箱方法下拉框
        # 期望: 默认选中"🎯 最优分箱 (推荐)"
        pass
    
    def test_config_panel_switch(self):
        """TC-102: 配置面板切换测试"""
        # 步骤: 
        #   1. 选择"最优分箱" → 显示Optbinning配置面板
        #   2. 选择"等频分箱" → 显示传统配置面板
        # 期望: 面板切换正确，参数不丢失
        pass
    
    def test_recommend_params_button(self):
        """TC-103: 恢复推荐值按钮测试"""
        # 步骤:
        #   1. 导入50000样本数据
        #   2. 点击"⚡恢复推荐"
        #   3. 确认对话框显示推荐值
        #   4. 点击"应用"
        # 期望: 参数自动填入CP, max_n_prebins=20等
        pass
    
    def test_end_to_end_binning(self):
        """TC-104: 端到端分箱测试"""
        # 步骤:
        #   1. 导入数据，设置目标变量
        #   2. 选择某个特征
        #   3. 点击"运行"
        # 期望: 
        #   - 显示求解状态
        #   - 完成后显示分箱图和表格
        #   - IV/WOE计算正确
        pass
    
    def test_missing_dependency(self):
        """TC-105: 依赖缺失处理测试"""
        # 步骤: 在未安装optbinning的环境中打开工具
        # 期望: "最优分箱"选项隐藏，其他功能正常
        pass
```

### 10.3 UI测试

```python
# tests/test_optbinning_ui.py

class TestOptbinningUI:
    """UI自动化测试"""
    
    def test_tooltip_display(self):
        """TC-201: 参数提示显示测试"""
        # 步骤: 鼠标悬停在"最小箱大小"标签上
        # 期望: 显示Tooltip，包含说明和推荐值
        pass
    
    def test_confirm_dialog(self):
        """TC-202: 恢复推荐确认对话框测试"""
        # 步骤: 点击"⚡恢复推荐"
        # 期望: 
        #   - 弹出确认对话框
        #   - 显示当前数据规模
        #   - 显示即将应用的参数列表
        #   - 点击"取消"不应用，点击"应用"生效
        pass
    
    def test_running_state(self):
        """TC-203: 运行状态测试"""
        # 步骤: 点击"运行"按钮
        # 期望:
        #   - 按钮变为loading状态(禁用+转圈)
        #   - 求解中显示🟡图标
        #   - 完成后显示🟢图标
        pass
```

### 10.4 性能测试

```python
# tests/test_optbinning_performance.py

class TestOptbinningPerformance:
    """性能测试"""
    
    def test_small_data_performance(self):
        """TC-301: 小数据性能(<1万)"""
        # 输入: 5000样本
        # 期望: 单变量分箱<2秒
        pass
    
    def test_medium_data_performance(self):
        """TC-302: 中数据性能(1-10万)"""
        # 输入: 50000样本
        # 期望: 单变量分箱<5秒
        pass
    
    def test_large_data_performance(self):
        """TC-303: 大数据性能(>10万)"""
        # 输入: 200000样本
        # 期望: 单变量分箱<10秒(使用LS求解器)
        pass
    
    def test_memory_usage(self):
        """TC-304: 内存占用测试"""
        # 输入: 100万样本
        # 期望: 内存占用<2GB
        pass
```

---

## 11. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v0.1 | 2026-03-11 | 初始版本，完成需求定义和架构设计 | Kimi |
| v0.2 | 2026-03-11 | 增加开发注意事项、确认项目清单、测试用例 | Kimi |

---

**状态**: 🟡 需求评审完成，待开发

**下一步**: 
1. 开发团队评审 PRD
2. 确认 Phase 1 排期
3. 开始编码实现
