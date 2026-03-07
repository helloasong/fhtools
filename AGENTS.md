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
