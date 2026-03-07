# 风控数据分箱工具技术架构文档

## 1. 系统概述
本项目旨在开发一个基于 **Python** 和 **PyQt6** 的原生桌面端风控数据分箱工具。系统采用**MVC (Model-View-Controller)** 变体架构，结合**模块化、层次化**设计，确保高性能、高交互性和易维护性。

## 2. 架构设计

### 2.1 整体架构图
```mermaid
graph TD
    UI[View Layer (PyQt6 Widgets)] --> Controller[Controller/Service Layer]
    Controller --> Core[Core Engine Layer (Binning Algorithms)]
    Controller --> Data[Data Access Layer (Persistence)]
    Core --> Utils[Utility Layer (Stats, Metrics)]
    Data --> FileSystem[File System (Pickle/CSV)]
    
    subgraph UI Layer
        MainWindow
        EDAWidget
        BinningWidget
        Plots(PyQtGraph/Matplotlib)
    end
```

### 2.2 模块划分

| 模块 | 路径 | 职责描述 |
| :--- | :--- | :--- |
| **UI 层 (View)** | `src/ui/` | 负责界面展示、用户交互和绘图。 |
| | `src/ui/main_window.py` | 主窗口框架 (MainWindow)。 |
| | `src/ui/views/` | 各功能视图（ImportView, EDAView, BinningView）。 |
| | `src/ui/widgets/` | 自定义组件（如 DraggablePlot, DataGrid）。 |
| | `src/ui/dialogs/` | 弹窗（如项目设置、导出配置）。 |
| **Controller 层** | `src/controllers/` | 处理 UI 事件，协调 Model 和 View。 |
| | `src/controllers/main_controller.py` | 全局控制器。 |
| | `src/controllers/project_controller.py` | 项目/数据流控制。 |
| **Core 层 (Model)** | `src/core/` | 核心算法实现，**纯函数或无状态类**。 |
| | `src/core/binning/` | 分箱算法包 (Strategy Pattern)。 |
| | `src/core/metrics.py` | WOE, IV, KS, Lift 等指标计算。 |
| **Data 层** | `src/data/` | 数据持久化与状态管理。 |
| | `src/data/repository.py` | 数据存取接口。 |
| | `src/data/models.py` | 数据模型 (Project, Dataset, BinningResult)。 |
| **Utils 层** | `src/utils/` | 通用工具。 |
| | `src/utils/workers.py` | 异步任务 (QThread) 封装。 |

## 3. 核心类设计

### 3.1 分箱引擎 (Core)
采用**策略模式**，保持与原设计一致，不依赖任何 UI 库。

```python
class BaseBinner(ABC):
    @abstractmethod
    def fit(self, x, y=None, **kwargs): ...
    @abstractmethod
    def transform(self, x): ...
```

### 3.2 数据模型 (Model)
```python
@dataclass
class ProjectState:
    """项目状态，用于序列化保存"""
    raw_data_path: str
    target_col: str
    feature_cols: List[str]
    # 键为 feature_name，值为该特征的分箱配置和结果
    binning_results: Dict[str, BinningResult]
    last_modified: datetime
```

### 3.3 UI 交互设计 (View)
*   **交互式分箱图**：使用 `pyqtgraph` 实现。
    *   **直方图**：显示数据分布。
    *   **切点线 (InfiniteLine)**：可拖拽 (`movable=True`)，拖动结束触发信号 `sigPositionChangeFinished`。
    *   **右键菜单**：在图上右键添加/删除切点。

### 3.4 异步处理 (Concurrency)
所有耗时操作（文件加载、自动分箱计算）必须在 `QThread` 中执行。

```python
class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def run(self):
        try:
            result = do_heavy_computation()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

## 4. 数据持久化方案
*   **项目文件 (.fht)**：本质是 pickle 序列化的 `ProjectState` 对象。
*   **原始数据**：建议在项目文件夹下另存一份 `data.parquet` (高效) 或 `data.csv`。

## 5. 开发规范
1.  **UI与逻辑分离**：Widget 只负责显示和发信号，Controller 负责逻辑。
2.  **PyQt6 信号槽**：充分利用 Signal/Slot 机制解耦。
3.  **类型提示**：严格使用 Type Hints。
4.  **异常捕获**：UI 层必须有全局异常捕获机制，避免 crash。

## 6. 开发计划 (调整后)
1.  **Phase 1 (Core)**: 核心分箱算法与指标计算 (已完成部分)。
2.  **Phase 2 (Data/Controller)**: 数据模型与项目管理逻辑。
3.  **Phase 3 (UI - Framework)**: PyQt6 主窗口搭建，数据导入与表格展示。
4.  **Phase 4 (UI - EDA/Binning)**: 实现 EDA 图表和**交互式分箱图** (PyQtGraph)。
5.  **Phase 5 (Integration)**: 串联全流程，实现持久化与导出。

## 7. 新特性补充
- 分箱算法：新增 Best-KS 分箱（最大化 KS），卡方分箱采用预分桶 + 相邻合并以保障性能。
- 导出：支持 Excel、Python 与 SQL 规则导出；规则与缺失策略一致。
- 缺失值策略：在配置与计算中支持 `separate`、`ignore`、`merge` 三种策略，并贯穿导出。
- 交互增强：分箱图为双轴图（样本数柱状、坏率折线），支持拖拽切点与悬停提示。
- 异步与快照：所有重型任务通过 QThread 异步执行；退出前提示保存快照。
