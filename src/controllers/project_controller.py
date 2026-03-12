import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from src.data.models import ProjectState, VariableStats, BinningConfig
from src.data.repository import ProjectRepository
from src.core.binning.unsupervised import EqualFrequencyBinner, EqualWidthBinner, ManualBinner
from src.core.binning.supervised import DecisionTreeBinner, ChiMergeBinner
from src.core.binning.supervised import BestKSBinner
from src.core.binning.smart_monotonic import SmartMonotonicBinner
from src.core.binning.optbinning_adapter import OptimalBinningAdapter, OPTBINNING_AVAILABLE, InfeasibleBinningError
from src.core.metrics import MetricsCalculator, BinningMetrics
from src.services.export_service import export_excel, export_python
from src.utils.formatting import snap_value_to_precision

class ProjectController(QObject):
    """
    核心控制器：管理项目生命周期、数据流和核心业务逻辑。
    继承 QObject 以支持 PyQt 信号机制。
    """
    
    # 定义信号，用于通知 UI 更新
    data_loaded = pyqtSignal(pd.DataFrame)       # 数据加载完成
    project_updated = pyqtSignal(ProjectState)   # 项目状态更新
    binning_finished = pyqtSignal(str, object)   # 分箱计算完成 (feature_name, BinningMetrics)
    error_occurred = pyqtSignal(str)             # 发生错误
    
    # 批量分箱信号
    batch_binning_progress = pyqtSignal(int, int, str)  # 当前进度, 总数, 当前变量名
    batch_binning_finished = pyqtSignal(list, list)     # 成功变量列表, 失败变量列表
    batch_binning_item_finished = pyqtSignal(str, object, bool, str)  # 变量名, 指标, 是否成功, 错误信息

    def __init__(self):
        super().__init__()
        self.repository = ProjectRepository()
        self.state: Optional[ProjectState] = None
        self.df: Optional[pd.DataFrame] = None
        self.dirty: bool = False
        
        # 算法工厂
        self.binners = {
            'equal_freq': EqualFrequencyBinner,
            'equal_width': EqualWidthBinner,
            'manual': ManualBinner,
            'decision_tree': DecisionTreeBinner,
            'chi_merge': ChiMergeBinner,
            'best_ks': BestKSBinner,
            'smart_monotonic': SmartMonotonicBinner,  # 智能单调分箱
        }
        
        # 条件添加 Optbinning（如果已安装）
        if OPTBINNING_AVAILABLE:
            self.binners['optimal'] = OptimalBinningAdapter

    def create_new_project(self, name: str, file_path: str):
        """创建新项目并加载数据"""
        try:
            self.state = self.repository.create_project(name, file_path)
            self.df = self.repository.load_data(self.state)
            
            # 自动识别列类型
            self._auto_detect_columns()
            
            self.data_loaded.emit(self.df)
            self.project_updated.emit(self.state)
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to create project: {str(e)}")

    def load_project(self, file_path: str):
        """加载已有项目"""
        try:
            self.state = self.repository.load_project(file_path)
            self.df = self.repository.load_data(self.state)
            self.data_loaded.emit(self.df)
            self.project_updated.emit(self.state)
        except Exception as e:
            self.error_occurred.emit(f"Failed to load project: {str(e)}")

    def save_project(self, file_path: str):
        """保存当前项目状态"""
        if self.state:
            try:
                self.repository.save_project(self.state, file_path)
            except Exception as e:
                self.error_occurred.emit(f"Failed to save project: {str(e)}")

    def _auto_detect_columns(self):
        """自动识别数值型和类别型变量"""
        if self.df is None:
            return
            
        # 简单逻辑：数值类型且 unique > 10 视为连续变量
        numerics = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 默认假设最后一列是 target，如果它是数值型且只有0/1
        potential_target = self.df.columns[-1]
        if self.df[potential_target].nunique() == 2:
            self.state.target_col = potential_target
            if potential_target in numerics:
                numerics.remove(potential_target)
        
        self.state.feature_cols = numerics
        
        # 计算 EDA 统计信息 (初步)
        self.calculate_eda()

    # ===== 目标变量设置与映射 =====
    def set_target_column(self, col: str):
        if self.df is None or col not in self.df.columns:
            self.error_occurred.emit("目标变量设置失败：列不存在")
            return
        self.state.target_col = col
        self.project_updated.emit(self.state)

    def apply_target_mapping(self, source_col: str, operator: str, value_expr: str, new_col: str = "target"):
        if self.df is None or source_col not in self.df.columns:
            self.error_occurred.emit("目标映射失败：列不存在")
            return
        s = self.df[source_col]

        def parse_values(expr: str):
            items = [x.strip() for x in expr.split(',') if x.strip()]
            # 尝试转数字
            vals = []
            for it in items:
                try:
                    vals.append(float(it))
                except Exception:
                    vals.append(it)
            return vals

        cond = None
        if operator in ["==", "!=", ">=", "<=", ">", "<"]:
            try:
                v = float(value_expr)
            except Exception:
                v = value_expr
            if operator == "==":
                cond = (s == v)
            elif operator == "!=":
                cond = (s != v)
            elif operator == ">=":
                cond = (pd.to_numeric(s, errors='coerce') >= float(v))
            elif operator == "<=":
                cond = (pd.to_numeric(s, errors='coerce') <= float(v))
            elif operator == ">":
                cond = (pd.to_numeric(s, errors='coerce') > float(v))
            elif operator == "<":
                cond = (pd.to_numeric(s, errors='coerce') < float(v))
        elif operator.lower() in ["in", "not in"]:
            vals = parse_values(value_expr)
            cond_base = s.isin(vals)
            cond = cond_base if operator.lower() == "in" else (~cond_base)
        else:
            self.error_occurred.emit("不支持的运算符")
            return

        self.df[new_col] = cond.fillna(False).astype(int)
        self.state.target_col = new_col
        self.state.target_mapping = {"source": source_col, "op": operator, "expr": value_expr, "target_col": new_col}
        # 重新计算 EDA 并通知界面
        self.calculate_eda()
        self.project_updated.emit(self.state)

    def calculate_eda(self):
        """计算所有特征的基础统计信息"""
        if self.df is None or not self.state.feature_cols:
            return
            
        for col in self.state.feature_cols:
            series = self.df[col]
            stats = VariableStats(
                name=col,
                dtype=str(series.dtype),
                n_samples=len(series),
                n_missing=series.isna().sum(),
                missing_pct=series.isna().mean(),
                n_unique=series.nunique(),
                min_val=float(series.min()) if pd.api.types.is_numeric_dtype(series) else None,
                max_val=float(series.max()) if pd.api.types.is_numeric_dtype(series) else None,
                mean_val=float(series.mean()) if pd.api.types.is_numeric_dtype(series) else None,
                std_val=float(series.std()) if pd.api.types.is_numeric_dtype(series) else None
            )
            self.state.variable_stats[col] = stats

    def run_binning(self, feature: str, method: str = 'equal_freq', emit_error: bool = True, **kwargs):
        """
        对指定特征执行分箱计算。
        
        Args:
            feature: 特征列名
            method: 分箱方法
            emit_error: 是否在发生错误时发射 error_occurred 信号（工作线程中应设为 False 避免重复弹窗）
            **kwargs: 算法参数 (n_bins, splits 等)
        """
        if self.df is None or self.state.target_col is None:
            if emit_error:
                self.error_occurred.emit("Data or Target not set.")
            return

        try:
            x = self.df[feature]
            y = self.df[self.state.target_col]

            existing_cfg = self.state.binning_configs.get(feature)
            merged_params = dict((existing_cfg.params if existing_cfg else {}) or {})
            merged_params.update(kwargs)
            merged_params.pop("boundary_unit", None)
            if existing_cfg is None:
                merged_params["boundary_precision_mode"] = "auto"
                merged_params["boundary_precision_digits"] = 0

            # 1. 初始化分箱器
            binner_class = self.binners.get(method)
            if not binner_class:
                raise ValueError(f"Unknown binning method: {method}")
                
            binner = binner_class()
            
            # 2. 计算切点 (Fit)
            # 有监督算法需要 y，无监督不需要但传入也无妨
            if method == 'chi_merge' and 'initial_bins' not in merged_params:
                merged_params['initial_bins'] = 64
            
            # Optbinning 特殊处理：处理 special_codes 字符串转列表
            if method == 'optimal' and 'special_codes' in merged_params:
                special_codes = merged_params['special_codes']
                if isinstance(special_codes, str):
                    # 将逗号分隔的字符串转为列表
                    codes = [c.strip() for c in special_codes.split(',') if c.strip()]
                    # 尝试转为数值
                    parsed_codes = []
                    for c in codes:
                        try:
                            parsed_codes.append(float(c))
                        except ValueError:
                            parsed_codes.append(c)
                    merged_params['special_codes'] = parsed_codes if parsed_codes else None
            
            binner.fit(x, y, **merged_params)
            splits = binner.splits

            precision_mode = (merged_params.get("boundary_precision_mode") or "auto")
            try:
                precision_digits = int(merged_params.get("boundary_precision_digits", 0))
            except Exception:
                precision_digits = 0
            if str(precision_mode).strip().lower() != "auto":
                finite = [
                    snap_value_to_precision(
                        s,
                        precision_mode=str(precision_mode),
                        precision_digits=precision_digits,
                    )
                    for s in splits
                    if np.isfinite(s)
                ]
                finite = sorted(set(float(v) for v in finite))
                splits = [-np.inf] + finite + [np.inf]
                if len(splits) < 2:
                    splits = [-np.inf, np.inf]
            
            # 3. 转换数据 (Transform)
            x_binned = binner._apply_splits(x, splits)
            
            # 4. 计算指标 (Metrics)
            cfg = existing_cfg or BinningConfig(method=method, params=merged_params, splits=splits)
            ms = cfg.missing_strategy if cfg else 'separate'
            merge_label = cfg.missing_merge_label if cfg else None
            metrics = MetricsCalculator.calculate(x_binned, y, missing_strategy=ms, missing_merge_label=merge_label)
            
            # 5. 更新状态
            config = BinningConfig(
                method=method,
                params=merged_params,
                splits=splits,
                is_confirmed=(existing_cfg.is_confirmed if existing_cfg else False),
                missing_strategy=(existing_cfg.missing_strategy if existing_cfg else "separate"),
                missing_merge_label=(existing_cfg.missing_merge_label if existing_cfg else None),
            )
            self.state.binning_configs[feature] = config
            self.state.binning_results[feature] = metrics
            self.dirty = True
            
            # 6. 通知 UI
            self.binning_finished.emit(feature, metrics)
            
        except InfeasibleBinningError as e:
            # 最优分箱约束冲突，提供友好的错误提示
            if emit_error:
                self.error_occurred.emit(f"【分箱无解】{feature}\n\n{str(e)}")
            raise  # 重新抛出，让调用者处理
        except Exception as e:
            error_msg = str(e)
            # 检查是否是无解相关的错误
            if any(keyword in error_msg.lower() for keyword in ['infeasible', 'no solution', 'mpsolver']):
                if emit_error:
                    self.error_occurred.emit(
                        f"【分箱无解】{feature}\n\n"
                        f"当前约束条件下无可行解。请尝试以下调整：\n"
                        f"1. 将『单调性』改为『自动』或关闭\n"
                        f"2. 增加『预分箱数』（如 50-100）\n" 
                        f"3. 更换求解器（MIP → CP）\n"
                        f"4. 放宽『最小占比』约束\n"
                        f"5. 使用无监督分箱方法（如等频、等宽）"
                    )
            else:
                if emit_error:
                    self.error_occurred.emit(f"Binning failed for {feature}: {error_msg}")
            raise  # 重新抛出，让调用者处理

    def update_splits(self, feature: str, new_splits: List[float]):
        """用户手动调整切点后，重新计算指标"""
        # 使用 ManualBinner 重新计算
        self.run_binning(feature, method='manual', splits=new_splits)

    # ===== 导出与快照 =====
    def get_binning_summary_df(self) -> pd.DataFrame:
        """聚合所有特征的分箱结果为统一的汇总表"""
        rows = []
        for feature, metrics in self.state.binning_results.items():
            df = metrics.summary_table.reset_index().copy()
            df["feature"] = feature
            rows.append(df)
        if not rows:
            return pd.DataFrame()
        return pd.concat(rows, ignore_index=True)

    def export_excel_report(self, dir_path: str) -> str:
        if not self.state:
            raise RuntimeError("No project state to export")
        return export_excel(self.state, dir_path)

    def export_python_rules(self, dir_path: str) -> str:
        if not self.state:
            raise RuntimeError("No project state to export")
        return export_python(self.state, dir_path)

    def export_sql_rules(self, dir_path: str) -> str:
        from src.services.export_service import export_sql
        if not self.state:
            raise RuntimeError("No project state to export")
        return export_sql(self.state, dir_path)

    def save_snapshot(self) -> str:
        if not self.state:
            raise RuntimeError("No project state")
        path = self.repository.save_snapshot(self.state)
        self.dirty = False
        return path

    def get_sample_count(self) -> int:
        """获取当前数据样本数"""
        if self.df is not None:
            return len(self.df)
        return 0

    def run_batch_binning(self, features: List[str], method: str = 'optimal', **kwargs):
        """
        批量分箱
        
        Args:
            features: 特征列表
            method: 分箱方法
            **kwargs: 分箱参数
        """
        success_features = []
        failed_features = []
        
        for i, feature in enumerate(features):
            self.batch_binning_progress.emit(i + 1, len(features), feature)
            
            try:
                self.run_binning(feature, method=method, **kwargs)
                metrics = self.state.binning_results.get(feature)
                success_features.append(feature)
                self.batch_binning_item_finished.emit(feature, metrics, True, "")
            except Exception as e:
                failed_features.append((feature, str(e)))
                self.batch_binning_item_finished.emit(feature, None, False, str(e))
                self.error_occurred.emit(f"{feature} 分箱失败: {str(e)}")
        
        self.batch_binning_finished.emit(success_features, failed_features)
