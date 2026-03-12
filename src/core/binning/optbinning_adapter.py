"""Optbinning 适配器模块

将 OptimalBinning 包装为符合 BaseBinner 接口的适配器。
optbinning 是可选依赖，未安装时类仍然可定义但方法会抛出 ImportError。
"""
from typing import List, Optional, Dict, Any
import logging
import pandas as pd
import numpy as np

from .base import BaseBinner

logger = logging.getLogger(__name__)


class InfeasibleBinningError(RuntimeError):
    """最优分箱约束冲突导致无可行解的错误。
    
    当 optbinning 求解器返回 INFEASIBLE 状态时抛出，
    提示用户调整约束条件。
    """
    pass

# 可选依赖处理
try:
    from optbinning import OptimalBinning
    OPTBINNING_AVAILABLE = True
except ImportError:
    OPTBINNING_AVAILABLE = False
    logger.warning("optbinning not installed, OptimalBinningAdapter unavailable")
    # 定义占位符类，避免类型检查错误
    OptimalBinning = None


class OptimalBinningAdapter(BaseBinner):
    """Optbinning 适配器
    
    将 OptimalBinning 包装为符合 BaseBinner 接口的适配器，
    支持 cp、mip、ls 等多种求解器和多种散度度量。
    
    Attributes:
        _optb: 底层的 OptimalBinning 实例
        _is_fitted: 是否已拟合
        _status: 求解状态
        _info: 求解信息字典
    
    Example:
        >>> adapter = OptimalBinningAdapter()
        >>> adapter.fit(x, y, solver='cp', max_n_bins=5)
        >>> bins = adapter.transform(x)
        >>> print(adapter.splits)
        >>> print(adapter.status)
    """
    
    # 默认参数值
    DEFAULT_SOLVER = 'cp'
    DEFAULT_DIVERGENCE = 'iv'
    DEFAULT_MONOTONIC_TREND = 'auto'
    DEFAULT_MAX_N_BINS = 10
    DEFAULT_MIN_N_BINS = 2
    DEFAULT_MAX_N_PREBINS = 20
    DEFAULT_MIN_PREBIN_SIZE = 0.05
    DEFAULT_TIME_LIMIT = 100
    
    def __init__(self):
        """初始化适配器。"""
        super().__init__()
        self._optb: Optional[Any] = None
        self._is_fitted: bool = False
        self._status: str = 'NOT_FITTED'
        self._info: Dict[str, Any] = {}
        self._dtype: str = 'numerical'
        self._cat_cutoff: Optional[float] = None
        
    def _detect_dtype(self, x: pd.Series) -> str:
        """自动检测变量类型。
        
        Args:
            x: 特征数据 (pd.Series)
            
        Returns:
            'numerical' 或 'categorical'
        """
        if pd.api.types.is_numeric_dtype(x):
            return 'numerical'
        else:
            return 'categorical'
    
    def _validate_params(self, kwargs: Dict[str, Any], dtype: str = 'numerical') -> Dict[str, Any]:
        """验证并整理参数。
        
        Args:
            kwargs: 用户传入的参数
            dtype: 变量类型，'numerical' 或 'categorical'
            
        Returns:
            整理后的参数字典
            
        Raises:
            ValueError: 参数值无效
        """
        params = {
            'solver': kwargs.get('solver', self.DEFAULT_SOLVER),
            'divergence': kwargs.get('divergence', self.DEFAULT_DIVERGENCE),
            'monotonic_trend': kwargs.get('monotonic_trend', self.DEFAULT_MONOTONIC_TREND),
            'max_n_bins': kwargs.get('max_n_bins', self.DEFAULT_MAX_N_BINS),
            'min_n_bins': kwargs.get('min_n_bins', self.DEFAULT_MIN_N_BINS),
            'max_n_prebins': kwargs.get('max_n_prebins', self.DEFAULT_MAX_N_PREBINS),
            'min_prebin_size': kwargs.get('min_prebin_size', self.DEFAULT_MIN_PREBIN_SIZE),
            'special_codes': kwargs.get('special_codes', None),
            'time_limit': kwargs.get('time_limit', self.DEFAULT_TIME_LIMIT),
            'dtype': dtype,
            'cat_cutoff': kwargs.get('cat_cutoff', None),
            # 新增参数
            'prebinning_method': kwargs.get('prebinning_method', 'cart'),
            'min_bin_size': kwargs.get('min_bin_size', None),
            'max_bin_size': kwargs.get('max_bin_size', None),
            'min_bin_n_event': kwargs.get('min_bin_n_event', None),
            'max_bin_n_event': kwargs.get('max_bin_n_event', None),
            'min_bin_n_nonevent': kwargs.get('min_bin_n_nonevent', None),
            'max_bin_n_nonevent': kwargs.get('max_bin_n_nonevent', None),
            'min_event_rate_diff': kwargs.get('min_event_rate_diff', 0.0),
            'max_pvalue': kwargs.get('max_pvalue', None),
            'max_pvalue_policy': kwargs.get('max_pvalue_policy', 'consecutive'),
            'split_digits': kwargs.get('split_digits', None),
            'gamma': kwargs.get('gamma', 0.0),
        }
        
        # 验证 solver
        # 注意：LS 求解器在 optbinning 0.21.0 中有 bug，暂时禁用
        valid_solvers = ['cp', 'mip']  # 'ls' 暂时禁用
        if params['solver'] not in valid_solvers:
            raise ValueError(f"solver must be one of {valid_solvers}, got {params['solver']}. "
                           f"Note: 'ls' solver is temporarily disabled due to a bug in optbinning 0.21.0")
        
        # 验证 divergence
        valid_divergences = ['iv', 'js', 'hellinger', 'triangular']
        if params['divergence'] not in valid_divergences:
            raise ValueError(
                f"divergence must be one of {valid_divergences}, got {params['divergence']}"
            )
        
        # 验证数值参数
        if not isinstance(params['max_n_bins'], int) or params['max_n_bins'] < 2:
            raise ValueError(f"max_n_bins must be an integer >= 2, got {params['max_n_bins']}")
        
        if not isinstance(params['min_n_bins'], int) or params['min_n_bins'] < 2:
            raise ValueError(f"min_n_bins must be an integer >= 2, got {params['min_n_bins']}")
        
        if params['min_n_bins'] > params['max_n_bins']:
            raise ValueError(
                f"min_n_bins ({params['min_n_bins']}) cannot be greater than "
                f"max_n_bins ({params['max_n_bins']})"
            )
        
        # 分类型变量不需要验证这些参数
        if dtype == 'numerical':
            if not isinstance(params['max_n_prebins'], int) or params['max_n_prebins'] < 2:
                raise ValueError(
                    f"max_n_prebins must be an integer >= 2, got {params['max_n_prebins']}"
                )
            
            if not isinstance(params['min_prebin_size'], (int, float)) or \
               not 0 < params['min_prebin_size'] <= 1:
                raise ValueError(
                    f"min_prebin_size must be a float in (0, 1], got {params['min_prebin_size']}"
                )
        
        if not isinstance(params['time_limit'], int) or params['time_limit'] < 1:
            raise ValueError(f"time_limit must be a positive integer, got {params['time_limit']}")
        
        # 验证 special_codes
        if params['special_codes'] is not None:
            if not isinstance(params['special_codes'], list):
                raise ValueError("special_codes must be a list or None")
        
        # 验证 cat_cutoff
        if params['cat_cutoff'] is not None:
            if not isinstance(params['cat_cutoff'], (int, float)) or \
               not 0 <= params['cat_cutoff'] <= 1:
                raise ValueError(
                    f"cat_cutoff must be a float in [0, 1], got {params['cat_cutoff']}"
                )
        
        return params
    
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'OptimalBinningAdapter':
        """拟合分箱。
        
        Args:
            x: 特征数据 (pd.Series)
            y: 目标变量二分类 0/1 (pd.Series, 有监督分箱必需)
            **kwargs: 可选参数
                - solver: 'cp'|'mip'|'ls', 默认 'cp'
                - divergence: 'iv'|'js'|'hellinger'|'triangular', 默认 'iv'
                - monotonic_trend: str, 默认 'auto'
                - max_n_bins: int, 默认 10
                - min_n_bins: int, 默认 2
                - max_n_prebins: int, 默认 20
                - min_prebin_size: float, 默认 0.05
                - special_codes: list, 默认 None
                - time_limit: int, 默认 100
                - dtype: 'numerical'|'categorical'|'auto', 默认 'auto'
                - cat_cutoff: float, 默认 None (分类型变量低频类别合并阈值)
        
        Returns:
            self: 支持链式调用
            
        Raises:
            ImportError: optbinning 未安装
            ValueError: 参数无效或 y 为 None（有监督分箱必需）
            RuntimeError: 拟合过程中发生错误
        """
        if not OPTBINNING_AVAILABLE:
            raise ImportError(
                "optbinning is not installed. "
                "Install it with: pip install optbinning"
            )
        
        if y is None:
            raise ValueError("OptimalBinningAdapter requires target variable 'y' for supervised binning.")
        
        # 检测或获取 dtype
        dtype = kwargs.get('dtype', 'auto')
        if dtype == 'auto':
            dtype = self._detect_dtype(x)
        
        self._dtype = dtype
        self._cat_cutoff = kwargs.get('cat_cutoff', None)
        
        # 智能检测：如果使用分类类型但数据是数值型（大量唯一值），
        # 且 cat_cutoff 会导致所有类别被合并，则自动调整
        if dtype == 'categorical' and self._cat_cutoff is not None:
            n_unique = x.nunique()
            n_samples = len(x)
            # 如果每个类别的平均占比低于 cat_cutoff，会出问题
            avg_pct_per_category = 1.0 / n_unique if n_unique > 0 else 1.0
            if avg_pct_per_category < self._cat_cutoff:
                logger.warning(
                    f"Categorical dtype with cat_cutoff={self._cat_cutoff} but "
                    f"data has {n_unique} unique values (avg pct per category: "
                    f"{avg_pct_per_category:.4%}). Disabling cat_cutoff to avoid "
                    f"'All categories moved to others bin' error."
                )
                self._cat_cutoff = None
                # 更新 kwargs 以便后续使用
                kwargs = dict(kwargs)
                kwargs['cat_cutoff'] = None
        
        # 验证并整理参数
        params = self._validate_params(kwargs, dtype)
        
        logger.info(
            f"Fitting OptimalBinning with solver={params['solver']}, "
            f"divergence={params['divergence']}, max_n_bins={params['max_n_bins']}, "
            f"monotonic_trend={params['monotonic_trend']}, dtype={dtype}"
        )
        
        # 对 peak/valley 约束给出警告提示
        if params['monotonic_trend'] in ['peak', 'valley', 'peak_heuristic', 'valley_heuristic']:
            if params['max_n_prebins'] < 20:
                logger.warning(
                    f"monotonic_trend='{params['monotonic_trend']}' may require max_n_prebins >= 20 "
                    f"to form effective change points, current={params['max_n_prebins']}"
                )
        
        try:
            # 构建 OptimalBinning 参数
            opt_params = {
                'name': x.name if x.name is not None else 'feature',
                'dtype': dtype,
                'solver': params['solver'],
                'divergence': params['divergence'],
                'monotonic_trend': params['monotonic_trend'],
                'max_n_bins': params['max_n_bins'],
                'min_n_bins': params['min_n_bins'],
                'special_codes': params['special_codes'],
                'time_limit': params['time_limit'],
                'prebinning_method': params['prebinning_method'],
                'min_event_rate_diff': params['min_event_rate_diff'],
                'max_pvalue_policy': params['max_pvalue_policy'],
                'gamma': params['gamma'],
            }
            
            # 数值型特有参数
            if dtype == 'numerical':
                opt_params['max_n_prebins'] = params['max_n_prebins']
                opt_params['min_prebin_size'] = params['min_prebin_size']
            
            # 可选约束参数（仅当不为 None 时添加）
            for key in ['min_bin_size', 'max_bin_size', 'min_bin_n_event', 
                       'max_bin_n_event', 'min_bin_n_nonevent', 'max_bin_n_nonevent',
                       'max_pvalue', 'split_digits']:
                if params[key] is not None:
                    opt_params[key] = params[key]
            
            # 分类型特有参数
            if dtype == 'categorical' and params['cat_cutoff'] is not None:
                opt_params['cat_cutoff'] = params['cat_cutoff']
            
            # 创建 OptimalBinning 实例
            self._optb = OptimalBinning(**opt_params)
            
            # 准备数据（处理缺失值）
            mask = x.notna() & y.notna()
            x_clean = x[mask]
            y_clean = y[mask]
            
            if len(x_clean) == 0:
                raise ValueError("No valid samples after removing NaN values")
            
            # 拟合
            self._optb.fit(x_clean.values, y_clean.values)
            
            # 更新状态
            self._is_fitted = True
            self._status = getattr(self._optb, 'status', 'UNKNOWN')
            
            # 检查求解状态
            if self._status == 'INFEASIBLE' or 'No solution exists' in str(getattr(self._optb, '_status', '')):
                self._is_fitted = False
                self._status = 'INFEASIBLE'
                raise InfeasibleBinningError(
                    "当前约束条件下无可行解。请尝试以下调整：\n"
                    "1. 将『单调性』改为『自动』或关闭\n"
                    "2. 增加『预分箱数』（如 50-100）\n" 
                    "3. 更换求解器（MIP → CP）\n"
                    "4. 放宽『最小占比』约束\n"
                    "5. 使用无监督分箱方法（如等频、等宽）"
                )
            
            # 检查是否只有单箱（退化解）
            if self._status in ['OPTIMAL', 'FEASIBLE']:
                try:
                    n_bins = len(self._optb.splits) - 1 if self._optb.splits else 0
                    if n_bins <= 1:
                        logger.warning(f"OptimalBinning returned only {n_bins} bin(s), possibly due to strict constraints")
                except Exception:
                    pass
            
            # 提取切点或类别
            self._update_splits()
            
            # 更新信息字典
            self._update_info(params)
            
            logger.info(f"OptimalBinning fitting completed with status: {self._status}")
            
            # 检查 peak/valley 约束是否生效
            if params['monotonic_trend'] in ['peak', 'valley', 'peak_heuristic', 'valley_heuristic']:
                self._check_monotonic_trend_applied(params['monotonic_trend'])
            
        except InfeasibleBinningError:
            raise
        except Exception as e:
            logger.error(f"OptimalBinning fitting failed: {str(e)}")
            self._status = 'ERROR'
            self._is_fitted = False
            # 检查是否是 INFEASIBLE 相关错误
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['infeasible', 'no solution', 'mpsolver']):
                raise InfeasibleBinningError(
                    "当前约束条件下无可行解。请尝试以下调整：\n"
                    "1. 将『单调性』改为『自动』或关闭\n"
                    "2. 增加『预分箱数』（如 50-100）\n" 
                    "3. 更换求解器（MIP → CP）\n"
                    "4. 放宽『最小占比』约束\n"
                    "5. 使用无监督分箱方法（如等频、等宽）"
                ) from e
            raise RuntimeError(f"OptimalBinning fitting failed: {str(e)}") from e
        
        return self
    
    def _update_splits(self) -> None:
        """从 OptimalBinning 实例提取并更新切点或类别。"""
        if self._optb is None:
            self._splits = []
            return
        
        # 获取切点或类别
        try:
            opt_splits = list(self._optb.splits)
        except (AttributeError, TypeError):
            opt_splits = []
        
        # 根据类型处理
        if self._dtype == 'categorical':
            # 分类型变量：直接返回类别列表
            self._splits = opt_splits if opt_splits else []
        else:
            # 数值型变量：确保包含 -inf 和 +inf
            if opt_splits:
                # 移除可能已经存在的 inf 值
                finite_splits = [s for s in opt_splits if np.isfinite(s)]
                self._splits = sorted(list(set([-np.inf] + finite_splits + [np.inf])))
            else:
                self._splits = [-np.inf, np.inf]
    
    def _update_info(self, params: Dict[str, Any]) -> None:
        """更新求解信息字典。
        
        Args:
            params: 使用的参数
        """
        self._info = {
            'solver': params['solver'],
            'divergence': params['divergence'],
            'monotonic_trend': params['monotonic_trend'],
            'max_n_bins': params['max_n_bins'],
            'min_n_bins': params['min_n_bins'],
            'special_codes': params['special_codes'],
            'time_limit': params['time_limit'],
            'dtype': self._dtype,
            'status': self._status,
            'n_bins': len(self._splits) - 1 if self._dtype == 'numerical' and len(self._splits) > 1 else len(self._splits),
            'splits': self._splits.copy(),
        }
        
        # 数值型特有参数
        if self._dtype == 'numerical':
            self._info['max_n_prebins'] = params['max_n_prebins']
            self._info['min_prebin_size'] = params['min_prebin_size']
        
        # 分类型特有参数
        if self._dtype == 'categorical':
            self._info['cat_cutoff'] = params['cat_cutoff']
        
        # 尝试获取更多求解信息
        if self._optb is not None:
            try:
                # 尝试获取 optbinning 提供的额外信息
                if hasattr(self._optb, 'splits_optimal'):
                    self._info['splits_optimal'] = self._optb.splits_optimal
                if hasattr(self._optb, 'iv'):
                    self._info['iv'] = float(self._optb.iv)
                if hasattr(self._optb, 'gini'):
                    self._info['gini'] = float(self._optb.gini)
                if hasattr(self._optb, 'quality_score'):
                    self._info['quality_score'] = float(self._optb.quality_score)
            except Exception:
                pass
    
    def _check_monotonic_trend_applied(self, expected_trend: str) -> None:
        """检查单调性约束是否实际生效。
        
        对于 peak/valley 约束，如果数据本身的分布无法满足约束，
        求解器可能会退化为单调递增/递减。此方法检测这种情况并给出警告。
        
        Args:
            expected_trend: 期望的单调性趋势 ('peak', 'valley', 'peak_heuristic', 'valley_heuristic')
        """
        if self._optb is None or not hasattr(self._optb, 'binning_table'):
            return
        
        try:
            # 获取各箱的坏样本率
            bt = self._optb.binning_table
            event_rates = list(bt.event_rate)
            
            if len(event_rates) < 3:
                logger.warning(
                    f"monotonic_trend='{expected_trend}' requires at least 3 bins, "
                    f"but got {len(event_rates)}. Constraint may not be effective."
                )
                return
            
            # 检测实际趋势
            increasing = decreasing = 0
            for i in range(len(event_rates) - 1):
                if event_rates[i+1] > event_rates[i]:
                    increasing += 1
                elif event_rates[i+1] < event_rates[i]:
                    decreasing += 1
            
            # 判断实际趋势
            actual_trend = None
            if increasing > 0 and decreasing == 0:
                actual_trend = 'ascending'
            elif decreasing > 0 and increasing == 0:
                actual_trend = 'descending'
            elif increasing > 0 and decreasing > 0:
                # 检查是否是 peak 或 valley
                max_idx = event_rates.index(max(event_rates))
                min_idx = event_rates.index(min(event_rates))
                if max_idx not in [0, len(event_rates)-1]:
                    actual_trend = 'peak'
                elif min_idx not in [0, len(event_rates)-1]:
                    actual_trend = 'valley'
            
            # 检查是否符合预期
            expected_base = expected_trend.replace('_heuristic', '')
            if actual_trend and actual_trend != expected_base:
                logger.warning(
                    f"monotonic_trend='{expected_trend}' requested but actual trend is '{actual_trend}'. "
                    f"The constraint could not be satisfied with current data distribution. "
                    f"Consider increasing max_n_prebins or using '{expected_trend}_heuristic'."
                )
                # 将警告信息保存到 _info 中供 UI 显示
                self._info['trend_warning'] = (
                    f"期望趋势 '{expected_trend}' 未生效，实际趋势为 '{actual_trend}'。"
                    f"建议：增加预分箱数或改用 '{expected_trend}_heuristic'"
                )
        except Exception as e:
            logger.debug(f"Could not check monotonic trend: {e}")
    
    def transform(self, x: pd.Series) -> pd.Series:
        """将原始数据映射到对应的箱。
        
        Args:
            x: 待转换的特征数据 (pd.Series)
            
        Returns:
            pd.Series: 分箱后的区间标签
            
        Raises:
            RuntimeError: 尚未拟合
            ValueError: 转换过程中发生错误
        """
        if not OPTBINNING_AVAILABLE:
            raise ImportError(
                "optbinning is not installed. "
                "Install it with: pip install optbinning"
            )
        
        if not self._is_fitted or self._optb is None:
            raise RuntimeError("OptimalBinningAdapter must be fitted before transform")
        
        try:
            # 使用 optbinning 的 transform 方法
            result = self._optb.transform(x.values)
            
            # 转换为 pandas Series，保持索引
            return pd.Series(result, index=x.index, name=x.name)
            
        except Exception as e:
            logger.error(f"Transform failed: {str(e)}")
            # 降级：使用切点进行分箱
            logger.warning("Falling back to splits-based binning")
            return self._apply_splits(x, self._splits)
    
    @property
    def dtype(self) -> str:
        """获取变量类型。
        
        Returns:
            str: 'numerical' 或 'categorical'
        """
        return self._dtype
    
    @property
    def cat_cutoff(self) -> Optional[float]:
        """获取分类型变量的低频类别合并阈值。
        
        Returns:
            float: cat_cutoff 值，数值型变量返回 None
        """
        return self._cat_cutoff if self._dtype == 'categorical' else None
    
    @property
    def splits(self) -> List:
        """获取切点或类别列表。
        
        Returns:
            数值型: 切点列表 [-inf, ..., +inf]
            分类型: 类别列表
            
        Example:
            >>> adapter.fit(x, y)
            >>> adapter.splits
            [-inf, 25.0, 50.0, +inf]  # 数值型
            >>> adapter.splits
            ['A', 'B', 'C']  # 分类型
        """
        if self._dtype == 'categorical':
            # 分类型变量：返回类别列表
            if self._optb is not None:
                try:
                    return list(self._optb.splits) if self._optb.splits else []
                except (AttributeError, TypeError):
                    pass
            return self._splits.copy() if self._splits else []
        else:
            # 数值型变量：返回切点列表
            return self._splits.copy()
    
    @property
    def status(self) -> str:
        """获取求解状态。
        
        Returns:
            str: 求解状态，可能的值包括:
                - 'NOT_FITTED': 尚未拟合
                - 'OPTIMAL': 最优解
                - 'FEASIBLE': 可行解
                - 'INFEASIBLE': 无可行解
                - 'ERROR': 求解出错
                - 其他 optbinning 返回的状态
        """
        return self._status
    
    def get_info(self) -> Dict[str, Any]:
        """获取求解信息字典。
        
        Returns:
            Dict[str, Any]: 包含求解参数、状态、结果等信息的字典
            
        Example:
            >>> adapter = OptimalBinningAdapter()
            >>> adapter.fit(x, y, solver='cp')
            >>> info = adapter.get_info()
            >>> print(f"Status: {info['status']}")
            >>> print(f"Bins: {info['n_bins']}")
            >>> print(f"IV: {info.get('iv', 'N/A')}")
        """
        return self._info.copy()
    
    def get_binning_table(self) -> Optional[pd.DataFrame]:
        """获取分箱详细表格（如果 optbinning 可用）。
        
        Returns:
            pd.DataFrame: 分箱统计表，包含每箱的计数、占比、WOE、IV 等信息
            None: 如果尚未拟合或 optbinning 不可用
        """
        if not OPTBINNING_AVAILABLE or not self._is_fitted or self._optb is None:
            return None
        
        try:
            binning_table = self._optb.binning_table
            # 构建 DataFrame
            df = pd.DataFrame({
                'Bin': binning_table.bin,
                'Count': binning_table.n_records,
                'Count (%)': binning_table.n_records / binning_table.n_records.sum() * 100,
                'Non-event': binning_table.n_non_events,
                'Event': binning_table.n_events,
                'Event rate': binning_table.event_rate,
                'WoE': binning_table.woe,
                'IV': binning_table.iv,
            })
            return df
        except Exception as e:
            logger.warning(f"Failed to get binning table: {str(e)}")
            return None
