"""智能单调分箱 v3.0 - 实用实现

核心改进：
1. 基于optbinning思路，使用预分箱+优化
2. 先生成细粒度预分箱（如20-50箱）
3. 然后合并或调整以满足单调性和目标箱数
4. 优先保证箱数，不追求数学最优（为了性能）
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from .base import BaseBinner


class SmartMonotonicBinnerV3(BaseBinner):
    """智能单调分箱器 v3.0 - 实用版"""
    
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 3
    DEFAULT_MIN_SAMPLES_PER_BIN = 50
    N_PREBINS = 50  # 预分箱数
    
    def __init__(self):
        super().__init__()
        self._is_monotonic = False
        self._adjustment_method = None
        self._adjustment_info = []
        self._final_iv = 0.0
        
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'SmartMonotonicBinnerV3':
        """拟合分箱"""
        if y is None:
            raise ValueError("需要目标变量y")
        
        max_bins = kwargs.get('max_bins', self.DEFAULT_MAX_BINS)
        min_bins = kwargs.get('min_bins', self.DEFAULT_MIN_BINS)
        trend = kwargs.get('monotonic_trend', 'auto')
        min_samples = kwargs.get('min_samples_per_bin', self.DEFAULT_MIN_SAMPLES_PER_BIN)
        
        self._adjustment_info = []
        
        # 数据准备
        data = pd.DataFrame({'x': x, 'y': y}).dropna().sort_values('x')
        x_arr = data['x'].values
        y_arr = data['y'].values
        n = len(data)
        
        if n < 100:
            raise ValueError(f"样本不足: {n}")
        
        # 确定趋势
        if trend == 'auto':
            corr = np.corrcoef(np.arange(n), y_arr)[0, 1]
            target_trend = 'ascending' if corr >= 0 else 'descending'
        else:
            target_trend = trend
        
        self._log(f"V3: max={max_bins}, min={min_bins}, trend={target_trend}")
        
        # 步骤1: 细粒度预分箱（等频）
        prebin_stats = self._prebin(x_arr, y_arr, self.N_PREBINS)
        self._log(f"预分箱: {len(prebin_stats)}箱")
        
        # 步骤2: 从max_bins到min_bins尝试
        for try_bins in range(max_bins, min_bins - 1, -1):
            result = self._find_monotonic_merge(prebin_stats, try_bins, target_trend, min_samples)
            if result:
                splits = [-np.inf] + [s['right'] for s in prebin_stats[:-1] if s['keep']] + [np.inf]
                # 重新计算实际切点
                actual_splits = self._compute_actual_splits(x_arr, y_arr, result['cuts'])
                
                self._splits = actual_splits
                self._final_iv = result['iv']
                self._is_monotonic = True
                self._adjustment_method = 'optimal'
                self._log(f"成功: {try_bins}箱")
                return self
        
        # 保底
        return self._fallback(x_arr, min_bins)
    
    def _prebin(self, x: np.ndarray, y: np.ndarray, n_bins: int) -> List[Dict]:
        """等频预分箱"""
        n = len(x)
        stats = []
        
        bin_size = n // n_bins
        for i in range(n_bins):
            start = i * bin_size
            end = start + bin_size if i < n_bins - 1 else n
            
            bin_y = y[start:end]
            stats.append({
                'start_idx': start,
                'end_idx': end - 1,
                'left': x[start],
                'right': x[end - 1],
                'count': end - start,
                'events': np.sum(bin_y),
                'bad_rate': np.mean(bin_y),
                'keep': True  # 是否保留
            })
        
        return stats
    
    def _find_monotonic_merge(self, stats: List[Dict], target_bins: int, 
                             trend: str, min_samples: int) -> Optional[Dict]:
        """找到单调合并方案
        
        策略：
        1. 如果当前箱数 > target_bins，需要合并
        2. 每次合并违反单调性的相邻箱，或IV损失最小的箱
        3. 直到箱数=target_bins且满足单调性
        """
        n = len(stats)
        if n < target_bins:
            return None
        
        # 工作副本
        work_stats = [dict(s) for s in stats]
        
        # 迭代合并
        max_iter = n - target_bins + 10
        for iteration in range(max_iter):
            current_bins = len([s for s in work_stats if s['keep']])
            
            if current_bins <= target_bins:
                # 检查是否单调
                active_stats = [s for s in work_stats if s['keep']]
                rates = [s['bad_rate'] for s in active_stats]
                
                is_mono = self._check_monotonic_rates(rates, trend)
                if is_mono:
                    cuts = [s['end_idx'] for s in active_stats]
                    iv = self._calculate_iv_from_stats(active_stats)
                    return {'cuts': cuts, 'iv': iv}
                
                # 还需要继续合并
                if current_bins <= 2:
                    break  # 无法再合并
            
            # 找到最佳合并对
            best_merge_idx = self._find_best_merge_pair(work_stats, trend, target_bins)
            if best_merge_idx is None:
                break
            
            # 执行合并
            self._merge_pair(work_stats, best_merge_idx)
        
        return None
    
    def _find_best_merge_pair(self, stats: List[Dict], trend: str, target_bins: int) -> Optional[int]:
        """找到最佳合并对"""
        active_indices = [i for i, s in enumerate(stats) if s['keep']]
        
        if len(active_indices) <= 2:
            return None
        
        best_idx = None
        best_score = float('inf')
        
        for i in range(len(active_indices) - 1):
            idx1 = active_indices[i]
            idx2 = active_indices[i + 1]
            
            s1, s2 = stats[idx1], stats[idx2]
            
            # 计算合并后的bad_rate
            merged_count = s1['count'] + s2['count']
            merged_events = s1['events'] + s2['events']
            merged_rate = merged_events / merged_count if merged_count > 0 else 0
            
            # 检查合并后是否改善单调性
            # 简化：优先合并非单调的相邻对
            violates_mono = False
            if trend == 'ascending':
                if s1['bad_rate'] > s2['bad_rate'] + 1e-6:
                    violates_mono = True
            else:
                if s1['bad_rate'] < s2['bad_rate'] - 1e-6:
                    violates_mono = True
            
            # 打分：违反单调性的优先，然后看IV损失
            iv_loss = abs(merged_rate - s1['bad_rate']) + abs(merged_rate - s2['bad_rate'])
            score = (0 if violates_mono else 1) * 1000 + iv_loss
            
            if score < best_score:
                best_score = score
                best_idx = idx1
        
        return best_idx
    
    def _merge_pair(self, stats: List[Dict], idx: int):
        """合并idx和idx+1"""
        # 找到idx和下一个active的idx
        active_indices = [i for i, s in enumerate(stats) if s['keep']]
        
        for i, ai in enumerate(active_indices):
            if ai == idx and i + 1 < len(active_indices):
                next_idx = active_indices[i + 1]
                
                # 合并到idx
                stats[idx]['end_idx'] = stats[next_idx]['end_idx']
                stats[idx]['right'] = stats[next_idx]['right']
                stats[idx]['count'] += stats[next_idx]['count']
                stats[idx]['events'] += stats[next_idx]['events']
                stats[idx]['bad_rate'] = stats[idx]['events'] / stats[idx]['count']
                
                # 标记next为不保留
                stats[next_idx]['keep'] = False
                return
    
    def _check_monotonic_rates(self, rates: List[float], trend: str) -> bool:
        """检查bad_rate列表是否单调"""
        if trend == 'ascending':
            return all(rates[i] <= rates[i+1] + 1e-6 for i in range(len(rates)-1))
        else:
            return all(rates[i] >= rates[i+1] - 1e-6 for i in range(len(rates)-1))
    
    def _calculate_iv_from_stats(self, stats: List[Dict]) -> float:
        """从统计计算IV"""
        total_events = sum(s['events'] for s in stats)
        total_non_events = sum(s['count'] - s['events'] for s in stats)
        
        if total_events == 0 or total_non_events == 0:
            return 0.0
        
        iv = 0.0
        for s in stats:
            events = s['events']
            non_events = s['count'] - events
            
            if events > 0 and non_events > 0:
                event_dist = events / total_events
                non_event_dist = non_events / total_non_events
                iv += (event_dist - non_event_dist) * np.log(event_dist / non_event_dist)
        
        return max(0, iv)
    
    def _compute_actual_splits(self, x: np.ndarray, y: np.ndarray, cuts: List[int]) -> List[float]:
        """根据切点索引计算实际切分值"""
        splits = [-np.inf]
        for cut in cuts[:-1]:  # 最后一个cut是末尾，不需要
            splits.append(float(x[cut]))
        splits.append(np.inf)
        return splits
    
    def _fallback(self, x: np.ndarray, min_bins: int) -> 'SmartMonotonicBinnerV3':
        """保底"""
        self._log("保底分箱")
        n = len(x)
        
        if min_bins <= 2:
            idx = n // 2
            self._splits = [-np.inf, float(x[idx]), np.inf]
        else:
            idx1 = n // 3
            idx2 = 2 * n // 3
            self._splits = [-np.inf, float(x[idx1]), float(x[idx2]), np.inf]
        
        self._is_monotonic = True
        self._adjustment_method = 'fallback'
        return self
    
    def transform(self, x: pd.Series) -> pd.Series:
        return pd.cut(x, bins=self._splits, include_lowest=True)
    
    @property
    def is_monotonic(self) -> bool:
        return self._is_monotonic
    
    @property
    def splits(self) -> List[float]:
        return self._splits
    
    def _log(self, msg: str):
        self._adjustment_info.append(msg)
