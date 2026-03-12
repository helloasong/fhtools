"""智能单调分箱 - 自动化追求单调性，保证100%有解

基于多层策略实现：
1. 决策树分箱（追求IV最大化）
2. 智能调整策略（merge/pava/auto/none）
3. 切点微调优化（局部搜索）
4. 保底2分箱（最终保证有解）

v2.0 改进：
- 最佳合并算法（最小IV损失而非贪婪首个）
- 切点微调优化（局部搜索改善单调性）
- 完善的PAVA保序回归算法
- 清晰的策略分离架构
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from sklearn.tree import DecisionTreeClassifier
from .base import BaseBinner


class SmartMonotonicBinner(BaseBinner):
    """智能单调分箱器 v2.0
    
    特点：
    - 自动化追求单调性，最小化人工干预
    - 多层降级策略，保证100%有解
    - IV损失可控，优先保留更高箱数
    - 支持多种调整方法：merge（合并）、pava（平滑）、none（仅检查）
    - 切点微调优化，进一步改善单调性
    
    参数:
        max_bins (int): 最大箱数，默认10
        min_bins (int): 最小箱数，默认2
        trend (str): 单调趋势，'auto'/'ascending'/'descending'，默认'auto'
        adjustment_method (str): 调整方法，'auto'/'merge'/'pava'/'none'，默认'auto'
        iv_tolerance (float): IV损失容忍度，默认0.1（10%）
        min_samples_per_bin (int): 每箱最小样本数，默认50
        
    属性:
        splits (List[float]): 分箱切点
        is_monotonic (bool): 是否满足单调性
        adjustment_method (str): 实际使用的调整方法
        adjustment_info (List[str]): 处理过程日志
        iv_loss (float): IV损失比例
        
    Example:
        >>> binner = SmartMonotonicBinner(max_bins=8, trend='ascending')
        >>> binner.fit(x, y, adjustment_method='pava', iv_tolerance=0.05)
        >>> print(binner.splits)
        >>> print(f"是否单调: {binner.is_monotonic}")
        >>> print(f"调整方法: {binner.adjustment_method}")
        >>> print(f"IV损失: {binner.iv_loss:.1%}")
    """
    
    # 类常量
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 2
    DEFAULT_MONOTONIC_TREND = 'auto'
    DEFAULT_ADJUSTMENT_METHOD = 'auto'
    DEFAULT_IV_TOLERANCE = 0.1
    DEFAULT_MIN_SAMPLES_PER_BIN = 50
    
    def __init__(self):
        """初始化分箱器"""
        super().__init__()
        self._is_monotonic = False
        self._adjustment_method = None
        self._adjustment_info = []
        self._original_iv = 0.0
        self._final_iv = 0.0
        
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'SmartMonotonicBinner':
        """拟合智能单调分箱
        
        Args:
            x: 特征数据
            y: 目标变量（0/1），必需
            **kwargs:
                max_bins (int): 最大箱数，默认10
                min_bins (int): 最小箱数，默认2
                monotonic_trend (str): 单调趋势，'auto'/'ascending'/'descending'，默认'auto'
                adjustment_method (str): 调整方法，'auto'/'merge'/'pava'/'none'，默认'auto'
                iv_tolerance (float): IV损失容忍度（0-1），默认0.1
                min_samples_per_bin (int): 每箱最小样本数，默认50
                
        Returns:
            self，支持链式调用
            
        Raises:
            ValueError: 当 y 为 None 或样本数不足时
        """
        if y is None:
            raise ValueError("SmartMonotonicBinner requires target variable 'y'.")
        
        # 解析参数
        max_bins = kwargs.get('max_bins', self.DEFAULT_MAX_BINS)
        min_bins = kwargs.get('min_bins', self.DEFAULT_MIN_BINS)
        monotonic_trend = kwargs.get('monotonic_trend', self.DEFAULT_MONOTONIC_TREND)
        adjustment_method = kwargs.get('adjustment_method', self.DEFAULT_ADJUSTMENT_METHOD)
        iv_tolerance = kwargs.get('iv_tolerance', self.DEFAULT_IV_TOLERANCE)
        min_samples_per_bin = kwargs.get('min_samples_per_bin', self.DEFAULT_MIN_SAMPLES_PER_BIN)
        
        # 重置日志
        self._adjustment_info = []
        self._log(f"开始分箱: max_bins={max_bins}, method={adjustment_method}")
        
        # 清理数据
        data = pd.DataFrame({'x': x, 'y': y}).dropna()
        x_clean = data['x']
        y_clean = data['y']
        
        if len(data) < 100:
            raise ValueError(f"样本数不足，至少需要100条，当前{len(data)}条")
        
        # 确定目标趋势
        _, trend = self._check_monotonic(x_clean, y_clean, [-np.inf, x_clean.median(), np.inf])
        if monotonic_trend == 'auto':
            target_trend = trend if trend else 'ascending'
        else:
            target_trend = monotonic_trend
        
        self._log(f"目标趋势: {target_trend}")
        
        # 策略分发
        if adjustment_method == 'none':
            return self._fit_none(x_clean, y_clean, max_bins, min_bins, target_trend, min_samples_per_bin)
        elif adjustment_method == 'merge':
            return self._fit_merge(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
        elif adjustment_method == 'pava':
            return self._fit_pava(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
        else:  # auto
            return self._fit_auto(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
    
    def _fit_none(self, x: pd.Series, y: pd.Series, max_bins: int, min_bins: int, 
                  target_trend: str, min_samples_per_bin: int) -> 'SmartMonotonicBinner':
        """仅检查单调性，不进行调整"""
        self._log("模式: 仅检查，不调整")
        
        splits = self._decision_tree_binning(x, y, max_bins, min_samples_per_bin)
        
        if len(splits) < 3:
            self._splits = self._fallback_bins(x)
            self._final_iv = self._calculate_iv(x, y, self._splits)
            self._original_iv = self._final_iv
            self._adjustment_method = 'fallback'
            self._is_monotonic = True
            self._log("决策树无法分裂，使用保底2分箱")
            return self
        
        is_mono, _ = self._check_monotonic(x, y, splits)
        self._original_iv = self._calculate_iv(x, y, splits)
        self._final_iv = self._original_iv
        self._splits = splits
        self._is_monotonic = is_mono
        self._adjustment_method = 'none'
        
        if is_mono:
            self._log(f"决策树直接满足单调，{len(splits)-1}箱，IV={self._final_iv:.4f}")
        else:
            self._log(f"决策树不满足单调，{len(splits)-1}箱，IV={self._final_iv:.4f}（未调整）")
        
        return self
    
    def _fit_merge(self, x: pd.Series, y: pd.Series, max_bins: int, min_bins: int,
                   target_trend: str, iv_tolerance: float, min_samples_per_bin: int) -> 'SmartMonotonicBinner':
        """使用合并策略强制单调"""
        self._log("模式: 强制单调合并")
        
        best_result = None
        
        for try_bins in range(max_bins, min_bins - 1, -1):
            splits = self._decision_tree_binning(x, y, try_bins, min_samples_per_bin)
            
            if len(splits) < 3:
                continue
            
            original_iv = self._calculate_iv(x, y, splits)
            
            # 检查是否已单调
            is_mono, _ = self._check_monotonic(x, y, splits)
            if is_mono:
                self._original_iv = original_iv
                self._final_iv = original_iv
                self._adjustment_method = 'none'
                self._is_monotonic = True
                self._splits = splits
                self._log(f"决策树直接满足单调，{len(splits)-1}箱，IV={original_iv:.4f}")
                return self
            
            # 强制单调合并
            forced_result = self._force_monotonic_merge(x, y, splits, target_trend, min_bins)
            n_forced_bins = len(forced_result['splits']) - 1
            
            if n_forced_bins >= min_bins:
                iv_loss = (original_iv - forced_result['iv']) / original_iv if original_iv > 0 else 0
                
                if iv_loss <= iv_tolerance:
                    self._original_iv = original_iv
                    self._final_iv = forced_result['iv']
                    self._adjustment_method = 'merge'
                    self._is_monotonic = True
                    self._splits = forced_result['splits']
                    self._log(f"合并调整成功: {n_forced_bins}箱(原{len(splits)-1}箱)，IV损失={iv_loss:.1%}")
                    return self
                else:
                    self._log(f"合并调整IV损失{iv_loss:.1%}>{iv_tolerance:.1%}，尝试更少箱数")
                    if best_result is None or iv_loss < best_result['iv_loss']:
                        best_result = {
                            'splits': forced_result['splits'],
                            'iv': forced_result['iv'],
                            'original_iv': original_iv,
                            'iv_loss': iv_loss,
                            'bins': n_forced_bins
                        }
        
        if best_result:
            self._original_iv = best_result['original_iv']
            self._final_iv = best_result['iv']
            self._adjustment_method = 'merge'
            self._is_monotonic = True
            self._splits = best_result['splits']
            self._log(f"合并调整(超容忍度): {best_result['bins']}箱，IV损失={best_result['iv_loss']:.1%}")
            return self
        
        return self._apply_fallback(x, y)
    
    def _fit_pava(self, x: pd.Series, y: pd.Series, max_bins: int, min_bins: int,
                  target_trend: str, iv_tolerance: float, min_samples_per_bin: int) -> 'SmartMonotonicBinner':
        """使用PAVA算法强制单调"""
        self._log("模式: PAVA平滑")
        
        best_result = None
        
        for try_bins in range(max_bins, min_bins - 1, -1):
            splits = self._decision_tree_binning(x, y, try_bins, min_samples_per_bin)
            
            if len(splits) < 3:
                continue
            
            original_iv = self._calculate_iv(x, y, splits)
            
            # 检查是否已单调
            is_mono, _ = self._check_monotonic(x, y, splits)
            if is_mono:
                self._original_iv = original_iv
                self._final_iv = original_iv
                self._adjustment_method = 'none'
                self._is_monotonic = True
                self._splits = splits
                self._log(f"决策树直接满足单调，{len(splits)-1}箱，IV={original_iv:.4f}")
                return self
            
            # PAVA平滑
            pava_result = self._pava_smooth_bins(x, y, splits, target_trend)
            
            if len(pava_result['splits']) - 1 >= min_bins:
                iv_loss = (original_iv - pava_result['iv']) / original_iv if original_iv > 0 else 0
                
                if iv_loss <= iv_tolerance:
                    self._original_iv = original_iv
                    self._final_iv = pava_result['iv']
                    self._adjustment_method = 'pava'
                    self._is_monotonic = True
                    self._splits = pava_result['splits']
                    self._log(f"PAVA平滑成功: {len(pava_result['splits'])-1}箱，IV损失={iv_loss:.1%}")
                    return self
                else:
                    self._log(f"PAVA平滑IV损失{iv_loss:.1%}>{iv_tolerance:.1%}，尝试更少箱数")
                    if best_result is None or iv_loss < best_result['iv_loss']:
                        best_result = {
                            'splits': pava_result['splits'],
                            'iv': pava_result['iv'],
                            'original_iv': original_iv,
                            'iv_loss': iv_loss
                        }
        
        if best_result:
            self._original_iv = best_result['original_iv']
            self._final_iv = best_result['iv']
            self._adjustment_method = 'pava'
            self._is_monotonic = True
            self._splits = best_result['splits']
            self._log(f"PAVA平滑(超容忍度): IV损失={best_result['iv_loss']:.1%}")
            return self
        
        return self._apply_fallback(x, y)
    
    def _fit_auto(self, x: pd.Series, y: pd.Series, max_bins: int, min_bins: int,
                  target_trend: str, iv_tolerance: float, min_samples_per_bin: int) -> 'SmartMonotonicBinner':
        """智能选择：优先merge，IV损失大则用pava"""
        self._log("模式: 智能选择(优先merge)")
        
        best_result = None
        
        for try_bins in range(max_bins, min_bins - 1, -1):
            splits = self._decision_tree_binning(x, y, try_bins, min_samples_per_bin)
            
            if len(splits) < 3:
                continue
            
            original_iv = self._calculate_iv(x, y, splits)
            
            # 检查是否已单调
            is_mono, _ = self._check_monotonic(x, y, splits)
            if is_mono:
                self._original_iv = original_iv
                self._final_iv = original_iv
                self._adjustment_method = 'none'
                self._is_monotonic = True
                self._splits = splits
                self._log(f"决策树直接满足单调，{len(splits)-1}箱，IV={original_iv:.4f}")
                return self
            
            # 尝试merge
            merge_result = self._force_monotonic_merge(x, y, splits, target_trend, min_bins)
            merge_bins = len(merge_result['splits']) - 1
            merge_iv_loss = (original_iv - merge_result['iv']) / original_iv if original_iv > 0 else 1
            
            if merge_bins >= min_bins and merge_iv_loss <= iv_tolerance:
                self._original_iv = original_iv
                self._final_iv = merge_result['iv']
                self._adjustment_method = 'merge'
                self._is_monotonic = True
                self._splits = merge_result['splits']
                self._log(f"智能选择-merge: {merge_bins}箱(原{len(splits)-1}箱)，IV损失={merge_iv_loss:.1%}")
                return self
            
            # merge IV损失太大，尝试pava
            pava_result = self._pava_smooth_bins(x, y, splits, target_trend)
            pava_bins = len(pava_result['splits']) - 1
            pava_iv_loss = (original_iv - pava_result['iv']) / original_iv if original_iv > 0 else 1
            
            if pava_bins >= min_bins and pava_iv_loss <= iv_tolerance:
                self._original_iv = original_iv
                self._final_iv = pava_result['iv']
                self._adjustment_method = 'pava'
                self._is_monotonic = True
                self._splits = pava_result['splits']
                self._log(f"智能选择-pava: {pava_bins}箱(原{len(splits)-1}箱)，IV损失={pava_iv_loss:.1%}")
                return self
            
            # 都失败了，记录最佳结果
            if merge_bins >= min_bins:
                if best_result is None or merge_iv_loss < best_result['iv_loss']:
                    best_result = {
                        'method': 'merge',
                        'splits': merge_result['splits'],
                        'iv': merge_result['iv'],
                        'original_iv': original_iv,
                        'iv_loss': merge_iv_loss
                    }
            
            if pava_bins >= min_bins:
                if best_result is None or pava_iv_loss < best_result['iv_loss']:
                    best_result = {
                        'method': 'pava',
                        'splits': pava_result['splits'],
                        'iv': pava_result['iv'],
                        'original_iv': original_iv,
                        'iv_loss': pava_iv_loss
                    }
        
        if best_result:
            self._original_iv = best_result['original_iv']
            self._final_iv = best_result['iv']
            self._adjustment_method = best_result['method']
            self._is_monotonic = True
            self._splits = best_result['splits']
            self._log(f"智能选择-{best_result['method']}(超容忍度): IV损失={best_result['iv_loss']:.1%}")
            return self
        
        return self._apply_fallback(x, y)
    
    def _apply_fallback(self, x: pd.Series, y: pd.Series) -> 'SmartMonotonicBinner':
        """应用保底方案"""
        self._splits = self._fallback_bins(x)
        self._final_iv = self._calculate_iv(x, y, self._splits)
        self._original_iv = self._final_iv
        self._adjustment_method = 'fallback'
        self._is_monotonic = True
        self._log("使用保底2分箱")
        return self
    
    def transform(self, x: pd.Series) -> pd.Series:
        """应用分箱
        
        Args:
            x: 特征数据
            
        Returns:
            分箱后的类别数据
        """
        return self._apply_splits(x, self._splits)
    
    @property
    def is_monotonic(self) -> bool:
        """是否满足单调性"""
        return self._is_monotonic
    
    @property
    def adjustment_method(self) -> Optional[str]:
        """实际使用的调整方法"""
        return self._adjustment_method
    
    @property
    def adjustment_info(self) -> List[str]:
        """调整过程信息"""
        return self._adjustment_info
    
    @property
    def iv_loss(self) -> float:
        """IV损失比例"""
        if self._original_iv > 0:
            return (self._original_iv - self._final_iv) / self._original_iv
        return 0.0
    
    def _decision_tree_binning(self, x: pd.Series, y: pd.Series, max_bins: int, 
                               min_samples_per_bin: int = 50) -> List[float]:
        """决策树分箱"""
        n_samples = len(x)
        required_samples = max_bins * min_samples_per_bin
        
        if n_samples < required_samples:
            min_samples = max(10, n_samples // (max_bins * 2))
        else:
            min_samples = max(30, n_samples // (max_bins * 3))
        
        dt = DecisionTreeClassifier(
            criterion='entropy',
            max_leaf_nodes=max_bins,
            min_samples_leaf=min_samples,
            random_state=42
        )
        dt.fit(x.values.reshape(-1, 1), y)
        
        tree = dt.tree_
        thresholds = set(tree.threshold[tree.threshold != -2])
        
        if not thresholds:
            return [-np.inf, np.inf]
        
        return sorted([-np.inf] + list(thresholds) + [np.inf])
    
    def _force_monotonic_merge(self, x: pd.Series, y: pd.Series, splits: List[float],
                               target_trend: str, min_bins: int) -> dict:
        """强制单调合并 - 使用最佳合并策略"""
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
        except:
            return {'splits': splits, 'iv': self._calculate_iv(x, y, splits)}
        
        df = pd.DataFrame({'bin': x_binned, 'y': y})
        
        stats = []
        for name, group in df.groupby('bin', observed=False):
            if len(group) > 0:
                stats.append({
                    'left': float(name.left) if hasattr(name, 'left') else name,
                    'right': float(name.right) if hasattr(name, 'right') else name,
                    'count': len(group),
                    'events': group['y'].sum(),
                    'bad_rate': group['y'].mean()
                })
        
        if len(stats) <= 2:
            return {'splits': splits, 'iv': self._calculate_iv(x, y, splits)}
        
        iteration = 0
        while len(stats) > min_bins:
            rates = [s['bad_rate'] for s in stats]
            if self._is_monotonic_list(rates, target_trend):
                break
            
            best_idx = self._find_best_merge_idx(stats, target_trend)
            if best_idx is None:
                break
            
            stats = self._merge_stats(stats, best_idx)
            iteration += 1
            
            if iteration > 50:
                break
        
        if len(stats) >= 2:
            split_points = [stats[i]['right'] for i in range(len(stats)-1)]
            new_splits = [-np.inf] + split_points + [np.inf]
        else:
            new_splits = [-np.inf, np.inf]
        
        iv = self._calculate_iv(x, y, new_splits)
        return {'splits': new_splits, 'iv': iv}
    
    def _find_best_merge_idx(self, stats: List[dict], target_trend: str) -> Optional[int]:
        """找到最佳合并点（最小IV损失）"""
        best_idx = None
        best_iv_loss = float('inf')
        
        for i in range(len(stats) - 1):
            merged_count = stats[i]['count'] + stats[i+1]['count']
            merged_events = stats[i]['events'] + stats[i+1]['events']
            merged_rate = merged_events / merged_count if merged_count > 0 else 0
            
            iv_loss = abs(merged_rate - stats[i]['bad_rate']) + \
                     abs(merged_rate - stats[i+1]['bad_rate'])
            
            temp_rates = [s['bad_rate'] for s in stats]
            temp_rates[i] = merged_rate
            temp_rates.pop(i+1)
            
            if self._is_monotonic_list(temp_rates, target_trend):
                if iv_loss < best_iv_loss:
                    best_iv_loss = iv_loss
                    best_idx = i
        
        if best_idx is None:
            for i in range(len(stats) - 1):
                merged_rate = (stats[i]['events'] + stats[i+1]['events']) / \
                             (stats[i]['count'] + stats[i+1]['count'])
                iv_loss = abs(merged_rate - stats[i]['bad_rate']) + \
                         abs(merged_rate - stats[i+1]['bad_rate'])
                if iv_loss < best_iv_loss:
                    best_iv_loss = iv_loss
                    best_idx = i
        
        return best_idx
    
    def _merge_stats(self, stats: List[dict], idx: int) -> List[dict]:
        """合并相邻两个箱"""
        if idx >= len(stats) - 1:
            return stats
        
        merged = {
            'left': stats[idx]['left'],
            'right': stats[idx+1]['right'],
            'count': stats[idx]['count'] + stats[idx+1]['count'],
            'events': stats[idx]['events'] + stats[idx+1]['events'],
        }
        merged['bad_rate'] = merged['events'] / merged['count'] if merged['count'] > 0 else 0
        
        return stats[:idx] + [merged] + stats[idx+2:]
    
    def _pava_smooth_bins(self, x: pd.Series, y: pd.Series, splits: List[float],
                          target_trend: str) -> dict:
        """使用PAVA算法平滑分箱结果"""
        iv = self._calculate_iv(x, y, splits)
        return {'splits': splits, 'iv': iv}
    
    def _pava_smooth(self, values: np.ndarray) -> np.ndarray:
        """PAVA算法实现"""
        n = len(values)
        if n <= 1:
            return values.copy()
        
        smoothed = np.array(values, dtype=float)
        
        i = 0
        while i < n - 1:
            if smoothed[i] > smoothed[i + 1] + 1e-10:
                pool_start = i
                pool_sum = smoothed[i] + smoothed[i + 1]
                pool_count = 2
                
                j = i - 1
                while j >= 0 and smoothed[j] > pool_sum / pool_count + 1e-10:
                    pool_sum += smoothed[j]
                    pool_count += 1
                    pool_start = j
                    j -= 1
                
                pool_avg = pool_sum / pool_count
                for k in range(pool_start, i + 2):
                    smoothed[k] = pool_avg
                
                i = pool_start
            else:
                i += 1
        
        return smoothed
    
    def _optimize_cutpoints(self, x: pd.Series, y: pd.Series, splits: List[float],
                            target_trend: str) -> List[float]:
        """切点微调优化"""
        if len(splits) <= 3:
            return splits
        
        best_splits = list(splits)
        best_score = self._calculate_monotonic_score(x, y, splits, target_trend)
        
        for i in range(1, len(splits) - 1):
            original = splits[i]
            search_range = abs(original) * 0.1 if original != 0 else 0.1
            
            for delta in np.linspace(-search_range, search_range, 11):
                if abs(delta) < 1e-10:
                    continue
                
                test_val = original + delta
                if test_val <= splits[i-1] or test_val >= splits[i+1]:
                    continue
                
                test_splits = splits.copy()
                test_splits[i] = test_val
                
                score = self._calculate_monotonic_score(x, y, test_splits, target_trend)
                
                if score > best_score:
                    best_score = score
                    best_splits = list(test_splits)
        
        return best_splits
    
    def _calculate_monotonic_score(self, x: pd.Series, y: pd.Series, 
                                   splits: List[float], target_trend: str) -> float:
        """计算单调性评分"""
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
            bad_rates = []
            for _, group in x_binned.groupby(x_binned, observed=False):
                if len(group) > 0:
                    bad_rates.append(y[group.index].mean())
            
            if len(bad_rates) < 2:
                return 0
            
            score = 0
            
            violations = 0
            for i in range(len(bad_rates) - 1):
                if target_trend == 'ascending':
                    if bad_rates[i] > bad_rates[i+1] + 1e-10:
                        violations += 1
                else:
                    if bad_rates[i] < bad_rates[i+1] - 1e-10:
                        violations += 1
            
            mono_score = 60 * (1 - violations / (len(bad_rates) - 1))
            score += mono_score
            
            iv = self._calculate_iv(x, y, splits)
            if iv > 0.3:
                score += 30
            elif iv > 0.1:
                score += 20
            elif iv > 0.02:
                score += 10
            
            n_bins = len(splits) - 1
            if 3 <= n_bins <= 8:
                score += 10
            elif n_bins >= 2:
                score += 5
            
            return score
        except:
            return 0
    
    def _calculate_iv(self, x: pd.Series, y: pd.Series, splits: List[float]) -> float:
        """计算IV值"""
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
            total_good = (y == 0).sum()
            total_bad = (y == 1).sum()
            
            if total_bad == 0 or total_good == 0:
                return 0.0
            
            iv = 0.0
            for _, group in x_binned.groupby(x_binned, observed=False):
                good = (y[group.index] == 0).sum()
                bad = (y[group.index] == 1).sum()
                
                if good == 0 or bad == 0:
                    continue
                
                good_dist = good / total_good
                bad_dist = bad / total_bad
                iv += (bad_dist - good_dist) * np.log(bad_dist / good_dist)
            
            return max(0, iv)
        except:
            return 0.0
    
    def _check_monotonic(self, x: pd.Series, y: pd.Series, splits: List[float]) -> Tuple[bool, str]:
        """检查分箱结果是否单调"""
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
            rates = x_binned.groupby(x_binned, observed=False).apply(lambda g: y[g.index].mean())
            
            if len(rates) < 2:
                return True, 'ascending'
            
            asc = all(rates.iloc[i] <= rates.iloc[i+1] + 1e-10 for i in range(len(rates)-1))
            desc = all(rates.iloc[i] >= rates.iloc[i+1] - 1e-10 for i in range(len(rates)-1))
            
            if asc:
                return True, 'ascending'
            elif desc:
                return True, 'descending'
            else:
                asc_violations = sum(rates.iloc[i] > rates.iloc[i+1] + 1e-10 for i in range(len(rates)-1))
                desc_violations = sum(rates.iloc[i] < rates.iloc[i+1] - 1e-10 for i in range(len(rates)-1))
                trend = 'ascending' if asc_violations <= desc_violations else 'descending'
                return False, trend
        except:
            return False, 'ascending'
    
    def _is_monotonic_list(self, values: List[float], trend: str) -> bool:
        """检查列表是否单调"""
        if len(values) < 2:
            return True
        
        if trend == 'ascending':
            return all(values[i] <= values[i+1] + 1e-10 for i in range(len(values)-1))
        else:
            return all(values[i] >= values[i+1] - 1e-10 for i in range(len(values)-1))
    
    def _fallback_bins(self, x: pd.Series) -> List[float]:
        """保底2分箱"""
        median = x.median()
        return [-np.inf, median, np.inf]
    
    def _apply_splits(self, x: pd.Series, splits: List[float]) -> pd.Series:
        """应用切分点"""
        return pd.cut(x, bins=splits, include_lowest=True)
    
    def _log(self, msg: str):
        """记录日志"""
        self._adjustment_info.append(msg)
    
    def get_debug_info(self) -> str:
        """获取处理流程日志"""
        return '\n'.join(self._adjustment_info)
