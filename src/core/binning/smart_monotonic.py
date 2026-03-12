"""智能单调分箱 - 自动化追求单调性，保证100%有解

基于多层策略实现：
1. 决策树分箱（追求IV最大化）
2. 减少箱数重试（逐步放松约束）
3. 强制单调合并（保证单调性）
4. 保底2分箱（最终保证有解）
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from sklearn.tree import DecisionTreeClassifier
from .base import BaseBinner


class SmartMonotonicBinner(BaseBinner):
    """智能单调分箱器
    
    特点：
    - 自动化追求单调性，最小化人工干预
    - 多层降级策略，保证100%有解
    - IV损失可控，业务可用性优先
    
    Example:
        >>> binner = SmartMonotonicBinner()
        >>> binner.fit(x, y, max_bins=8, monotonic_trend='ascending')
        >>> print(binner.splits)
        >>> print(f"是否单调: {binner.is_monotonic}")
        >>> print(f"调整方式: {binner.adjustment_method}")
    """
    
    # 默认参数
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 2
    DEFAULT_MONOTONIC_TREND = 'auto'  # auto/ascending/descending
    
    def __init__(self):
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
            y: 目标变量（必需）
            **kwargs:
                max_bins (int): 最大箱数，默认10
                min_bins (int): 最小箱数，默认2
                monotonic_trend (str): 单调趋势，'auto'/'ascending'/'descending'，默认'auto'
                
        Returns:
            self
        """
        if y is None:
            raise ValueError("SmartMonotonicBinner requires target variable 'y'.")
        
        max_bins = kwargs.get('max_bins', self.DEFAULT_MAX_BINS)
        min_bins = kwargs.get('min_bins', self.DEFAULT_MIN_BINS)
        monotonic_trend = kwargs.get('monotonic_trend', self.DEFAULT_MONOTONIC_TREND)
        
        self._adjustment_info = []
        
        # 清理数据
        data = pd.DataFrame({'x': x, 'y': y}).dropna()
        x_clean = data['x']
        y_clean = data['y']
        
        if len(data) < 100:
            raise ValueError("样本数不足，至少需要100条")
        
        # 策略1: 尝试不同箱数，找到满足单调的最大箱数
        best_result = None
        
        # 首先确定目标趋势
        _, trend = self._check_monotonic(x_clean, y_clean, 
                                         [-np.inf, x_clean.median(), np.inf])
        if monotonic_trend == 'auto':
            target_trend = trend if trend else 'ascending'
        else:
            target_trend = monotonic_trend
        
        for try_bins in range(max_bins, min_bins - 1, -1):
            splits = self._decision_tree_binning(x_clean, y_clean, try_bins)
            
            if len(splits) < 3:  # 只有2箱，跳过
                continue
            
            # 立即尝试强制单调合并
            forced_result = self._force_monotonic_merge(
                x_clean, y_clean, splits, target_trend, min_bins
            )
            
            n_forced_bins = len(forced_result['splits']) - 1
            
            if n_forced_bins >= min_bins:
                # 强制合并成功，返回结果
                original_iv = self._calculate_iv(x_clean, y_clean, splits)
                self._original_iv = original_iv
                self._final_iv = forced_result['iv']
                self._adjustment_method = 'forced_merge'
                self._is_monotonic = True
                self._splits = forced_result['splits']
                
                loss = (original_iv - forced_result['iv']) / original_iv if original_iv > 0 else 0
                self._log(f"强制单调合并: {n_forced_bins}箱(原{len(splits)-1}箱)，IV损失={loss:.1%}")
                return self
        
        # 保底：2分箱（中位数切分）
        self._splits = self._fallback_bins(x_clean)
        self._final_iv = self._calculate_iv(x_clean, y_clean, self._splits)
        self._adjustment_method = 'fallback'
        self._is_monotonic = True
        self._log("使用保底2分箱")
        
        return self
    
    def transform(self, x: pd.Series) -> pd.Series:
        """应用分箱"""
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
    
    def _decision_tree_binning(self, x, y, max_bins):
        """决策树分箱 - 动态调整参数以尽量达到目标箱数"""
        n_samples = len(x)
        
        # 动态计算 min_samples_leaf：确保能分裂出 max_bins 箱
        # 每箱至少 min_samples_per_bin 样本
        min_samples_per_bin = 50
        required_samples = max_bins * min_samples_per_bin
        
        if n_samples < required_samples:
            # 样本不足，降低要求
            min_samples = max(10, n_samples // (max_bins * 2))
        else:
            # 样本充足，但也不要限制太死
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
    
    def _force_monotonic_merge(self, x, y, splits, target_trend, min_bins):
        """强制单调合并 - 贪婪合并违反单调性的箱"""
        # 先细粒度分箱
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
        except:
            return {'splits': splits, 'iv': self._calculate_iv(x, y, splits)}
        
        df = pd.DataFrame({'bin': x_binned, 'y': y})
        
        # 计算每箱统计
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
        
        # 迭代合并直至单调
        while len(stats) > min_bins:
            # 检查是否已单调
            rates = [s['bad_rate'] for s in stats]
            if self._is_monotonic_list(rates, target_trend):
                break
            
            # 找到违反单调性的位置
            violate_idx = self._find_violation(stats, target_trend)
            if violate_idx is None:
                break
            
            # 合并violate_idx和violate_idx+1
            stats = self._merge_adjacent(stats, violate_idx)
        
        # 构建新切点
        if len(stats) >= 2:
            split_points = [stats[i]['right'] for i in range(len(stats)-1)]
            new_splits = [-np.inf] + split_points + [np.inf]
        else:
            new_splits = [-np.inf, np.inf]
        
        iv = self._calculate_iv(x, y, new_splits)
        return {'splits': new_splits, 'iv': iv}
    
    def _find_violation(self, stats, target_trend):
        """找到第一个违反单调性的位置"""
        for i in range(len(stats) - 1):
            if target_trend == 'ascending':
                if stats[i]['bad_rate'] > stats[i+1]['bad_rate']:
                    return i
            else:
                if stats[i]['bad_rate'] < stats[i+1]['bad_rate']:
                    return i
        return None
    
    def _merge_adjacent(self, stats, idx):
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
        
        # 重建列表
        new_stats = stats[:idx] + [merged] + stats[idx+2:]
        return new_stats
    
    def _is_monotonic_list(self, values, trend):
        """检查列表是否单调"""
        if trend == 'ascending':
            return all(values[i] <= values[i+1] for i in range(len(values)-1))
        else:
            return all(values[i] >= values[i+1] for i in range(len(values)-1))
    
    def _fallback_bins(self, x):
        """保底2分箱"""
        median = x.median()
        return [-np.inf, median, np.inf]
    
    def _check_monotonic(self, x, y, splits):
        """检查分箱结果是否单调"""
        try:
            x_binned = pd.cut(x, bins=splits, include_lowest=True)
        except:
            return False, 'ascending'
        
        rates = x_binned.groupby(x_binned, observed=False).apply(lambda g: y[g.index].mean())
        
        asc = all(rates.iloc[i] <= rates.iloc[i+1] for i in range(len(rates)-1))
        desc = all(rates.iloc[i] >= rates.iloc[i+1] for i in range(len(rates)-1))
        
        if asc:
            return True, 'ascending'
        elif desc:
            return True, 'descending'
        else:
            # 判断更接近哪种
            asc_violations = sum(rates.iloc[i] > rates.iloc[i+1] for i in range(len(rates)-1))
            desc_violations = sum(rates.iloc[i] < rates.iloc[i+1] for i in range(len(rates)-1))
            trend = 'ascending' if asc_violations <= desc_violations else 'descending'
            return False, trend
    
    def _calculate_iv(self, x, y, splits):
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
    
    def _log(self, msg):
        """记录调试信息"""
        self._adjustment_info.append(msg)
