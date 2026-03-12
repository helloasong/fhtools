# FHBinningTool - AI Coding Agent Guide

## Project Overview

**FHBinningTool** (风控数据分箱工具 / Risk Control Binning Tool) is a desktop application for risk control data analysis and scorecard development. It provides an interactive GUI for data binning (分箱), variable analysis, and export of binning rules for production use.

**Language:** Python 3.9+  
**GUI Framework:** PyQt6 with qt-material styling  
**Primary Use Case:** Risk control data analysts performing variable analysis, WOE encoding, and model variable selection for credit scoring.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.9+ |
| GUI Framework | PyQt6 |
| Styling | qt-material (themes), custom QSS (style.qss) |
| Data Processing | pandas, numpy, scipy |
| Machine Learning | scikit-learn (Decision Tree for binning) |
| Visualization | PyQtGraph (interactive plots), matplotlib, seaborn |
| Excel I/O | openpyxl |
| Packaging | PyInstaller |

## Project Structure

```
.
├── src/                          # Source code
│   ├── controllers/              # MVC Controller layer
│   │   └── project_controller.py # Main controller managing project lifecycle
│   ├── core/                     # Core algorithm layer (Model)
│   │   ├── binning/              # Binning algorithms (Strategy Pattern)
│   │   │   ├── base.py           # Abstract base class BaseBinner
│   │   │   ├── unsupervised.py   # EqualFreq, EqualWidth, Manual binner
│   │   │   └── supervised.py     # DecisionTree, ChiMerge, Best-KS binner
│   │   └── metrics.py            # WOE, IV, KS, Lift calculation
│   ├── data/                     # Data persistence layer
│   │   ├── models.py             # ProjectState, BinningConfig, VariableStats
│   │   └── repository.py         # ProjectRepository for .fht files
│   ├── services/                 # Business services
│   │   └── export_service.py     # Export to Excel/Python/SQL
│   ├── ui/                       # View layer (PyQt6)
│   │   ├── main_window.py        # MainWindow with navigation
│   │   ├── views/                # Page views (Import, Combined, Export)
│   │   ├── widgets/              # Reusable widgets
│   │   └── dialogs/              # Dialogs
│   └── utils/                    # Utilities
│       ├── formatting.py         # Number/bin formatting
│       └── workers.py            # QThread wrapper for async tasks
├── tests/                        # Unit and integration tests
├── scripts/                      # Build scripts
│   ├── build_mac.sh              # macOS build script
│   ├── package_dmg.sh            # DMG packaging
│   └── diagnose_mac_app.sh       # Diagnose script
├── projects/                     # Default project storage directory
├── config.json                   # App configuration
├── style.qss                     # Custom Qt stylesheet
├── FHBinningTool.spec            # PyInstaller spec
├── requirements.txt              # Python dependencies
└── run.py                        # Entry point
```

## Architecture

### MVC Pattern with Variations

```
UI Layer (PyQt6 Widgets)
    ↕ (Signals/Slots)
Controller Layer (ProjectController)
    ↕
Core Engine Layer (Binning Algorithms)
    ↕
Data Access Layer (Repository)
    ↕
File System (.fht pickle files)
```

### Key Design Patterns

1. **Strategy Pattern**: All binning algorithms inherit from `BaseBinner` and implement `fit()` and `transform()` methods.
2. **Signal/Slot Pattern**: PyQt6 signals for decoupled UI updates (`data_loaded`, `binning_finished`, `error_occurred`).
3. **Repository Pattern**: `ProjectRepository` handles persistence of `ProjectState` objects.

## Key Configuration Files

### config.json
```json
{
  "theme": "light_blue.xml",      // qt-material theme
  "initial_bins": 64,              // Default pre-binning buckets
  "default_max_bins": 5,           // Default target bin count
  "export_dir": "exports",         // Default export directory
  "missing_strategy": "separate",  // Default: separate|ignore|merge
  "qss": "style.qss"               // Custom stylesheet path
}
```

### FHBinningTool.spec
PyInstaller spec for building macOS .app bundle:
- Entry: `src/ui/main_window.py`
- Architecture: arm64
- Bundle ID: `com.fhtools.fhbinningtool`

## Build and Run Commands

### Development Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Run Application
```bash
# Method 1 (Recommended)
python -m src.ui.main_window

# Method 2
python run.py

# Method 3 (for IDE direct run)
PYTHONPATH=. python src/ui/main_window.py
```

### Build for macOS
```bash
# Use build script
bash scripts/build_mac.sh

# Or use PyInstaller directly
pyinstaller FHBinningTool.spec

# Output: dist/FHBinningTool.app
```

## Testing

### Run Tests
```bash
# Run all tests
python -m unittest discover tests/

# Run specific test
python -m unittest tests.test_binning
python -m unittest tests.test_integration
```

### Test Structure
- `test_binning.py`: Unit tests for binning algorithms and metrics
- `test_formatting.py`: Tests for number/bin formatting utilities
- `test_integration.py`: End-to-end integration tests
- `mock_data.xlsx`: Test data with 20k rows, 30 features

## Binning Algorithms

All algorithms are in `src/core/binning/`:

| Algorithm | Class | Type | Description |
|-----------|-------|------|-------------|
| Equal Frequency | `EqualFrequencyBinner` | Unsupervised | Equal sample count per bin |
| Equal Width | `EqualWidthBinner` | Unsupervised | Equal value range per bin |
| Decision Tree | `DecisionTreeBinner` | Supervised | Uses sklearn DecisionTreeClassifier |
| ChiMerge | `ChiMergeBinner` | Supervised | Chi-square based merging (pre-binning + merge) |
| Best-KS | `BestKSBinner` | Supervised | Greedy KS maximization |
| Manual | `ManualBinner` | Manual | User-specified cutpoints |
| Smart Monotonic | `SmartMonotonicBinner` | Supervised | **智能单调分箱** - 自动追求单调性，多层降级策略保证100%有解 (见下方详细说明) |

### SmartMonotonicBinner 详细说明

**文件位置**: `src/core/binning/smart_monotonic.py`  
**测试文件**: `tests/test_smart_monotonic.py` (23个测试用例)  
**对比测试**: `tests/test_binning_comparison.py` (全面对比6种策略)

**🏆 全面对比测试结论** (2026-03-12)

在10种数据场景下对比6种分箱策略的结果：

| 排名 | 策略 | 综合得分 | 单调率 | 成功率 | 平均IV损失 |
|-----|------|---------|-------|-------|-----------|
| 🥇 1 | **SmartMonotonic** | **81.76** | **60%** | **100%** | **6.71%** |
| 🥈 2 | DecisionTree | 74.87 | 40% | 100% | 3.90% |
| 🥉 3 | EqualFrequency | 73.87 | 50% | 100% | 30.25% |
| 4 | EqualWidth | 72.73 | 50% | 100% | 36.13% |
| 5 | BestKS | 62.31 | 30% | 100% | 40.52% |
| 6 | ChiMerge | 60.98 | 30% | 100% | 5.11% |

**核心优势**:
- ✅ **综合排名第1**，领先第二名9.2%
- ✅ **单调率最高** (60%)，第二名仅40%
- ✅ **100%有解率**，无需人工干预
- ✅ **IV损失可控** (6.71%)，远低于等频/等宽

**测试文档**:
- 测试计划: `docs/PLAN_BinningComparisonTest.md`
- 优化记录: `docs/OPTIMIZATION_RECORD_BinningComparison.md`

**核心特点**:
- 自动化追求单调性，无需人工调整参数
- 多层降级策略，保证100%有解（即使退化为2箱）
- IV损失可控，优先保留更高箱数
- 支持多种调整方法：merge（合并）、pava（平滑）、none（仅检查）

**参数列表**:

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `max_bins` | int | 10 | 最大箱数（UI上"箱数"控制） |
| `min_bins` | int | **3** | 最小箱数（默认3，避免2分箱业务价值过低） |
| `monotonic_trend` | str | 'auto' | 单调趋势：'auto'/'ascending'/'descending' |
| `adjustment_method` | str | 'auto' | 调整方法：'auto'/'merge'/'pava'/'none' |
| `iv_tolerance` | float | 0.1 | IV损失容忍度（0-1），默认10% |
| `min_samples_per_bin` | int | 50 | 每箱最小样本数 |

**调整方法说明**:

| 方法 | 描述 | 适用场景 |
|-----|------|---------|
| `auto` | 智能选择：优先merge，IV损失大则用pava | **推荐默认** |
| `merge` | 合并相邻违反单调性的箱 | 箱数可能减少，IV损失可控 |
| `pava` | PAVA平滑算法，保持箱数不变 | 需要保持箱数时使用 |
| `none` | 仅检查单调性，不调整 | 用于分析原始结果 |

**算法策略**（按优先级）:
1. **决策树分箱**: 使用CART生成初始切分，追求IV最大化
2. **调整方法选择**:
   - `merge`: 贪婪合并违反单调性的相邻箱
   - `pava`: 平滑bad rate使其单调，保持边界不变
3. **保底3分箱**: 33%/67%分位数切分（默认最少3箱，避免2分箱业务价值过低）

**关键修复记录** (2026-03-12):
```
问题: 5箱需求实际只返回2箱
原因: 决策树5箱不单调时继续尝试更少箱数，2箱总是单调导致直接返回
修复: 每次决策树分箱后立即强制单调合并，成功则返回不再尝试更少箱数

修复效果:
- feature_01: 2箱 → 3箱
- feature_02: 2箱 → 5箱 (达目标)
- feature_03: 2箱 → 5箱 (达目标)
- feature_04: 2箱 → 4箱  
- feature_05: 2箱 → 3箱
```

**使用示例**:
```python
from src.core.binning.smart_monotonic import SmartMonotonicBinner

binner = SmartMonotonicBinner()
binner.fit(x, y, 
    max_bins=8,
    monotonic_trend='ascending',  # 强制递增
    adjustment_method='pava',     # 使用PAVA平滑
    iv_tolerance=0.05             # 只接受5% IV损失
)

print(f"分箱边界: {binner.splits}")
print(f"实际箱数: {len(binner.splits)-1}")
print(f"是否单调: {binner.is_monotonic}")
print(f"调整方法: {binner.adjustment_method}")  # 'none', 'merge', 'pava', 'fallback'
print(f"IV损失: {binner.iv_loss:.1%}")
print(f"调整信息: {binner.adjustment_info}")
```

### Algorithm Interface
```python
class BaseBinner(ABC):
    @abstractmethod
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'BaseBinner': ...
    
    @abstractmethod
    def transform(self, x: pd.Series) -> pd.Series: ...
    
    @property
    def splits(self) -> List[float]: ...  # Cutpoints including -inf, +inf
```

## Data Persistence

### Project Files (.fht)
- Format: Python pickle of `ProjectState` dataclass
- Location: `projects/{project_name}_{timestamp}/project.fht`
- Contains: Project metadata, column configs, binning results (not raw data)

### Snapshots
- Auto-prompt on exit if `dirty=True`
- Saved to `projects/{project}/snapshots/snapshot_{timestamp}.fht`

### Raw Data
- Backed up to project directory on import
- Supported formats: CSV, Excel (.xls/.xlsx), Parquet

## Key Metrics

Calculated in `src/core/metrics.py`:
- **WOE** (Weight of Evidence): ln(Good_dist / Bad_dist)
- **IV** (Information Value): Sum of (Good_dist - Bad_dist) * WOE
- **Bad Rate**: Bad_count / Total_count per bin
- **Lift**: Bin_bad_rate / Overall_bad_rate
- **Monotonicity**: Check if Bad Rate is monotonic across bins

## Missing Value Strategies

Three strategies supported across all algorithms:
- `separate`: Missing values form their own bin
- `ignore`: Exclude missing from calculations
- `merge`: Merge missing to bin with closest bad rate

## Export Formats

1. **Excel** (`binning_report.xlsx`): Summary sheet + per-feature sheets
2. **Python** (`scorecard_transform.py`): `transform(df)` function with WOE mapping
3. **SQL** (`scorecard_rules.sql`): CASE WHEN rules with WOE values

## Code Style Guidelines

1. **Type Hints**: Mandatory for function signatures
2. **Docstrings**: Google-style docstrings in Chinese
3. **Naming**: 
   - Classes: PascalCase
   - Functions/Variables: snake_case
   - Constants: UPPER_SNAKE_CASE
4. **UI/Logic Separation**: Widgets emit signals, Controllers handle logic
5. **Async Operations**: Heavy operations (file load, binning) use `Worker` QThread

## Common Development Tasks

### Add New Binning Algorithm
1. Create class in `src/core/binning/` inheriting `BaseBinner`
2. Implement `fit()` and `transform()` methods
3. Register in `ProjectController.binners` dict
4. Add unit test in `tests/test_binning.py`

### Add New Export Format
1. Add function in `src/services/export_service.py`
2. Add button handler in `ExportView`
3. Call through `ProjectController`

### Modify UI Theme
1. Edit `config.json` theme value (qt-material themes)
2. Or modify `style.qss` for custom styles

## Security Considerations

- Project files use Python pickle - only load trusted .fht files
- No network operations - purely offline desktop app
- No sensitive credential storage

## Troubleshooting

### App Won't Start
- Check Python version >= 3.9
- Verify virtual environment activated
- Run `pip install -r requirements.txt`

### Build Issues (macOS)
- Ensure PyQt6 installed in venv
- Check architecture matches (arm64 vs x86_64)
- Use `scripts/diagnose_mac_app.sh` for debugging

### Import Errors
- Set `PYTHONPATH=. ` or use `python -m` syntax
- Verify `src/__init__.py` exists

## ⚠️ 重要：Git 操作规范

**除非用户明确要求，否则不要自动执行 `git push`**

正确的Git提交流程:
```bash
# 1. 添加更改到暂存区
git add -A

# 2. 提交到本地仓库
git commit -m "描述信息"

# 3. 推送到远程仓库 - 必须等待用户明确确认后才执行
git push origin main  # ❌ 不要自动执行此步骤
```

**规则**:
- ✅ 可以自动执行 `git add` 和 `git commit`
- ❌ **永远不要**在没有用户明确许可的情况下执行 `git push`
- 推送前必须询问用户: "是否推送到GitHub？"
