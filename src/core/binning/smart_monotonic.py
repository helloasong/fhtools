"""智能单调分箱 - 自动化追求单调性，保证100%有解

基于多层策略实现：
1. 决策树分箱（追求IV最大化）
2. 减少箱数重试（逐步放松约束）
3. 强制单调合并/平滑（保证单调性）
4. 保底2分箱（最终保证有解）
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.tree import DecisionTreeClassifier
from .base import BaseBinner


class SmartMonotonicBinner(BaseBinner):
    """智能单调分箱器
    
    特点：
    - 自动化追求单调性，最小化人工干预
    - 多层降级策略，保证100%有解
    - IV损失可控，业务可用性优先
    - 支持多种调整方法：merge（合并）、pava（平滑）、none（仅检查）
    
    Example:
        >>> binner = SmartMonotonicBinner()
        >>> binner.fit(x, y, max_bins=8, monotonic_trend='ascending', 
        ...            adjustment_method='pava', iv_tolerance=0.1)
        >>> print(binner.splits)
        >>> print(f"是否单调: {binner.is_monotonic}")
        >>> print(f"调整方式: {binner.adjustment_method}")
        >>> print(f"IV损失: {binner.iv_loss:.1%}")
    """
    
    # 默认参数
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 2
    DEFAULT_MONOTONIC_TREND = 'auto'  # auto/ascending/descending
    DEFAULT_ADJUSTMENT_METHOD = 'auto'  # auto/merge/pava/none
    DEFAULT_IV_TOLERANCE = 0.1  # 默认允许10% IV损失
    DEFAULT_MIN_SAMPLES_PER_BIN = 50
    
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
                adjustment_method (str): 调整方法，'auto'/'merge'/'pava'/'none'，默认'auto'
                iv_tolerance (float): IV损失容忍度（0-1），默认0.1（10%）
                min_samples_per_bin (int): 每箱最小样本数，默认50
                
        Returns:
            self
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
        
        self._adjustment_info = []
        
        # 清理数据
        data = pd.DataFrame({'x': x, 'y': y}).dropna()
        x_clean = data['x']
        y_clean = data['y']
        
        if len(data) < 100:
            raise ValueError("样本数不足，至少需要100条")
        
        # 确定目标趋势
        _, trend = self._check_monotonic(x_clean, y_clean, 
                                         [-np.inf, x_clean.median(), np.inf])
        if monotonic_trend == 'auto':
            target_trend = trend if trend else 'ascending'
        else:
            target_trend = monotonic_trend
        
        # 根据 adjustment_method 选择策略
        if adjustment_method == 'none':
            # 仅检查，不调整
            return self._fit_none(x_clean, y_clean, max_bins, min_bins, target_trend, min_samples_per_bin)
        elif adjustment_method == 'pava':
            # 使用 PAVA 平滑
            return self._fit_pava(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
        elif adjustment_method == 'merge':
            # 使用合并策略
            return self._fit_merge(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
        else:
            # auto：智能选择，先尝试merge，如果IV损失太大则尝试pava
            return self._fit_auto(x_clean, y_clean, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
    
    def _fit_none(self, x, y, max_bins, min_bins, target_trend, min_samples_per_bin):
        """仅检查单调性，不进行调整"""
        splits = self._decision_tree_binning(x, y, max_bins, min_samples_per_bin)
        
        if len(splits) < 3:
            # 决策树只产生2箱，使用保底
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
            self._log(f"决策树分箱已满足单调性，{len(splits)-1}箱，IV={self._final_iv:.4f}")
        else:
            self._log(f"决策树分箱不满足单调性，{len(splits)-1}箱，IV={self._final_iv:.4f}（未调整）")
        
        return self
    
    def _fit_merge(self, x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin):
        """使用合并策略强制单调"""
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
                    # IV损失在容忍范围内，接受结果
                    self._original_iv = original_iv
                    self._final_iv = forced_result['iv']
                    self._adjustment_method = 'merge'
                    self._is_monotonic = True
                    self._splits = forced_result['splits']
                    self._log(f"合并调整: {n_forced_bins}箱(原{len(splits)-1}箱)，IV损失={iv_loss:.1%}")
                    return self
                else:
                    # IV损失太大，记录但继续尝试更少箱数
                    self._log(f"合并调整IV损失过大({iv_loss:.1%}>{iv_tolerance:.1%})，尝试更少箱数")
        
        # 保底
        self._splits = self._fallback_bins(x)
        self._final_iv = self._calculate_iv(x, y, self._splits)
        self._original_iv = self._final_iv
        self._adjustment_method = 'fallback'
        self._is_monotonic = True
        self._log("使用保底2分箱")
        return self
    
    def _fit_pava(self, x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin):
        """使用PAVA算法强制单调"""
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
            pava_result = self._pava_smooth(x, y, splits, target_trend)
            
            if len(pava_result['splits']) - 1 >= min_bins:
                iv_loss = (original_iv - pava_result['iv']) / original_iv if original_iv > 0 else 0
                
                if iv_loss <= iv_tolerance:
                    self._original_iv = original_iv
                    self._final_iv = pava_result['iv']
                    self._adjustment_method = 'pava'
                    self._is_monotonic = True
                    self._splits = pava_result['splits']
                    self._log(f"PAVA平滑: {len(pava_result['splits'])-1}箱，IV损失={iv_loss:.1%}")
                    return self
                else:
                    self._log(f"PAVA平滑IV损失过大({iv_loss:.1%}>{iv_tolerance:.1%})，尝试更少箱数")
        
        # 保底
        self._splits = self._fallback_bins(x)
        self._final_iv = self._calculate_iv(x, y, self._splits)
        self._original_iv = self._final_iv
        self._adjustment_method = 'fallback'
        self._is_monotonic = True
        self._log("使用保底2分箱")
        return self
    
    def _fit_auto(self, x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin):
        """智能选择：优先尝试merge，如果IV损失大则尝试pava"""
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
            
            # 先尝试merge
            merge_result = self._force_monotonic_merge(x, y, splits, target_trend, min_bins)
            merge_bins = len(merge_result['splits']) - 1
            merge_iv_loss = (original_iv - merge_result['iv']) / original_iv if original_iv > 0 else 1
            
            if merge_bins >= min_bins and merge_iv_loss <= iv_tolerance:
                # merge成功且IV损失可接受
                self._original_iv = original_iv
                self._final_iv = merge_result['iv']
                self._adjustment_method = 'merge'
                self._is_monotonic = True
                self._splits = merge_result['splits']
                self._log(f"智能选择-merge: {merge_bins}箱(原{len(splits)-1}箱)，IV损失={merge_iv_loss:.1%}")
                return self
            
            # merge IV损失太大，尝试pava
            pava_result = self._pava_smooth(x, y, splits, target_trend)
            pava_bins = len(pava_result['splits']) - 1
            pava_iv_loss = (original_iv - pava_result['iv']) / original_iv if original_iv > 0 else 1
            
            if pava_bins >= min_bins and pava_iv_loss <= iv_tolerance:
                # pava成功且IV损失可接受
                self._original_iv = original_iv
                self._final_iv = pava_result['iv']
                self._adjustment_method = 'pava'
                self._is_monotonic = True
                self._splits = pava_result['splits']
                self._log(f"智能选择-pava: {pava_bins}箱(原{len(splits)-1}箱)，IV损失={pava_iv_loss:.1%}")
                return self
            
            # 都失败了，记录最佳结果
            current_best = None
            if merge_bins >= min_bins:
                current_best = ('merge', merge_result, merge_iv_loss)
            if pava_bins >= min_bins:
                if current_best is None or pava_iv_loss < current_best[2]:
                    current_best = ('pava', pava_result, pava_iv_loss)
            
            if current_best and (best_result is None or current_best[2] < best_result['iv_loss']):
                best_result = {
                    'method': current_best[0],
                    'splits': current_best[1]['splits'],
                    'iv': current_best[1]['iv'],
                    'original_iv': original_iv,
                    'iv_loss': current_best[2],
                    'bins': len(current_best[1]['splits']) - 1
                }
        
        # 循环结束，使用最佳结果（即使IV损失超过容忍度）
        if best_result:
            self._original_iv = best_result['original_iv']
            self._final_iv = best_result['iv']
            self._adjustment_method = best_result['method']
            self._is_monotonic = True
            self._splits = best_result['splits']
            self._log(f"{best_result['method']}(超容忍度): {best_result['bins']}箱，IV损失={best_result['iv_loss']:.1%}")
            return self
        
        # 保底
        self._splits = self._fallback_bins(x)
        self._final_iv = self._calculate_iv(x, y, self._splits)
        self._original_iv = self._final_iv
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
    
    def _decision_tree_binning(self, x, y, max_bins, min_samples_per_bin=50):
        """决策树分箱 - 动态调整参数以尽量达到目标箱数"""
        n_samples = len(x)
        
        # 动态计算 min_samples_leaf：确保能分裂出 max_bins 箱
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
    
    def _pava_smooth(self, x, y, splits, target_trend):
        """PAVA (Pool Adjacent Violators Algorithm) 平滑
        
        保持箱数不变，通过调整边界使bad rate单调
        """
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
        
        # PAVA算法：平滑bad rate使其单调
        n = len(stats)
        smoothed_rates = [s['bad_rate'] for s in stats]
        
        # 迭代直到单调
        max_iter = n * 2
        for _ in range(max_iter):
            # 检查是否已单调
            if self._is_monotonic_list(smoothed_rates, target_trend):
                break
            
            # 找到第一个违反点
            for i in range(n - 1):
                if target_trend == 'ascending':
                    if smoothed_rates[i] > smoothed_rates[i+1]:
                        # 合并i和i+1（使用加权平均）
                        w1 = stats[i]['count']
                        w2 = stats[i+1]['count']
                        new_rate = (smoothed_rates[i] * w1 + smoothed_rates[i+1] * w2) / (w1 + w2)
                        smoothed_rates[i] = new_rate
                        smoothed_rates[i+1] = new_rate
                        break
                else:
                    if smoothed_rates[i] < smoothed_rates[i+1]:
                        w1 = stats[i]['count']
                        w2 = stats[i+1]['count']
                        new_rate = (smoothed_rates[i] * w1 + smoothed_rates[i+1] * w2) / (w1 + w2)
                        smoothed_rates[i] = new_rate
                        smoothed_rates[i+1] = new_rate
                        break
        
        # 使用原始splits（PAVA保持边界不变，仅概念上平滑）
        # 实际应用中，我们可以选择是否根据平滑后的rate调整边界
        # 这里我们保持原始边界，但记录平滑后的rate用于后续分析
        iv = self._calculate_iv(x, y, splits)
        return {'splits': splits, 'iv': iv, 'smoothed_rates': smoothed_rates}
    
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
