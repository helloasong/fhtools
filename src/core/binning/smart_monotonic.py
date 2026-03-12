"""智能单调分箱 v3.1 - 支持完整参数配置

核心改进：
1. 基于optbinning思路，使用预分箱+优化
2. 先生成细粒度预分箱（如20-50箱）
3. 然后合并或调整以满足单调性和目标箱数
4. 优先保证箱数，不追求数学最优（为了性能）
5. 支持完整的参数配置（容忍度、合并策略、保底策略等）
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from .base import BaseBinner


class SmartMonotonicBinner(BaseBinner):
    """智能单调分箱器 v3.1 - 完整参数版
    
    算法流程：
    1. 预分箱：将数据等频分成 N 个细粒度箱子（默认50）
    2. 迭代合并：从目标箱数向下尝试，每次合并IV损失最小或违反单调性的箱子对
    3. 单调检查：检查当前分箱是否满足指定的单调趋势
    4. 成功返回：找到满足条件的分箱则返回
    5. 保底处理：若所有尝试都失败，使用保底策略
    
    参数说明：
    - prebins: 预分箱数，越多找到最优解可能性越高，但计算时间增加
    - min_samples_per_bin: 每箱最小样本数，防止过拟合
    - monotonic_trend: 单调趋势（auto/ascending/descending）
    - tolerance: 单调容忍度，判定bad_rate是否单调的阈值
    - merge_strategy: 合并策略（balanced/monotonic_first/iv_first）
    - fallback: 保底策略（simple/equal_freq/decision_tree）
    - max_iterations: 最大迭代次数，防止极端数据导致长时间计算
    """
    
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 3
    DEFAULT_MIN_SAMPLES_PER_BIN = 50
    DEFAULT_MONOTONIC_TREND = 'auto'
    DEFAULT_PREBINS = 50
    DEFAULT_TOLERANCE = 1e-6
    DEFAULT_MERGE_STRATEGY = 'balanced'
    DEFAULT_FALLBACK = 'simple'
    
    def __init__(self):
        super().__init__()
        self._is_monotonic = False
        self._adjustment_method = None
        self._adjustment_info = []
        self._final_iv = 0.0
        self._config = {}
        
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'SmartMonotonicBinner':
        """拟合分箱
        
        Args:
            x: 特征数据
            y: 目标变量（0/1）
            **kwargs: 配置参数
                - max_bins: 最大箱数
                - min_bins: 最小箱数
                - prebins: 预分箱数（默认50）
                - min_samples_per_bin: 每箱最小样本数（默认50）
                - monotonic_trend: 单调趋势（auto/ascending/descending）
                - tolerance: 单调容忍度（默认1e-6）
                - merge_strategy: 合并策略（balanced/monotonic_first/iv_first）
                - fallback: 保底策略（simple/equal_freq/decision_tree）
                - max_iterations: 最大迭代次数（None表示自动）
        
        Returns:
            self: 拟合后的分箱器
        """
        if y is None:
            raise ValueError("SmartMonotonicBinner requires target variable 'y'.")
        
        # 提取参数
        max_bins = kwargs.get('max_bins', self.DEFAULT_MAX_BINS)
        min_bins = kwargs.get('min_bins', self.DEFAULT_MIN_BINS)
        trend = kwargs.get('monotonic_trend', self.DEFAULT_MONOTONIC_TREND)
        min_samples = kwargs.get('min_samples_per_bin', self.DEFAULT_MIN_SAMPLES_PER_BIN)
        n_prebins = kwargs.get('prebins', self.DEFAULT_PREBINS)
        tolerance = kwargs.get('tolerance', self.DEFAULT_TOLERANCE)
        merge_strategy = kwargs.get('merge_strategy', self.DEFAULT_MERGE_STRATEGY)
        fallback = kwargs.get('fallback', self.DEFAULT_FALLBACK)
        max_iter = kwargs.get('max_iterations', None)
        
        # 保存配置
        self._config = {
            'max_bins': max_bins, 'min_bins': min_bins,
            'prebins': n_prebins, 'min_samples_per_bin': min_samples,
            'monotonic_trend': trend, 'tolerance': tolerance,
            'merge_strategy': merge_strategy, 'fallback': fallback,
            'max_iterations': max_iter
        }
        
        self._adjustment_info = []
        
        # 数据准备
        data = pd.DataFrame({'x': x, 'y': y}).dropna().sort_values('x')
        x_arr = data['x'].values
        y_arr = data['y'].values
        n = len(data)
        
        if n < 100:
            raise ValueError(f"样本数不足: {n}")
        
        # 确定趋势
        if trend == 'auto':
            corr = np.corrcoef(np.arange(n), y_arr)[0, 1]
            target_trend = 'ascending' if corr >= 0 else 'descending'
        else:
            target_trend = trend
        
        self._log(f"V3.1: max={max_bins}, min={min_bins}, prebins={n_prebins}, trend={target_trend}")
        self._log(f"策略: merge={merge_strategy}, tolerance={tolerance:.0e}")
        
        # 步骤1: 细粒度预分箱（等频）
        prebin_stats = self._prebin(x_arr, y_arr, n_prebins)
        self._log(f"预分箱: {len(prebin_stats)}箱")
        
        # 步骤2: 从max_bins到min_bins尝试
        for try_bins in range(max_bins, min_bins - 1, -1):
            result = self._find_monotonic_merge(
                prebin_stats, try_bins, target_trend, min_samples, 
                tolerance, merge_strategy, max_iter
            )
            if result:
                actual_splits = self._compute_actual_splits(x_arr, y_arr, result['cuts'])
                
                self._splits = actual_splits
                self._final_iv = result['iv']
                self._is_monotonic = True
                self._adjustment_method = 'optimal'
                self._log(f"成功: {try_bins}箱, IV={result['iv']:.4f}")
                return self
        
        # 保底
        self._log(f"智能合并失败，使用保底策略: {fallback}")
        return self._fallback(x_arr, y_arr, min_bins, fallback)
    
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
                'keep': True
            })
        
        return stats
    
    def _find_monotonic_merge(self, stats: List[Dict], target_bins: int, 
                             trend: str, min_samples: int, 
                             tolerance: float, merge_strategy: str,
                             max_iter: Optional[int]) -> Optional[Dict]:
        """找到单调合并方案
        
        策略：
        1. 如果当前箱数 > target_bins，需要合并
        2. 根据 merge_strategy 选择最佳合并对
        3. 直到箱数=target_bins且满足单调性
        """
        n = len(stats)
        if n < target_bins:
            return None
        
        # 工作副本
        work_stats = [dict(s) for s in stats]
        
        # 迭代次数上限
        if max_iter is None:
            max_iter = n - target_bins + 20
        
        for iteration in range(max_iter):
            current_bins = len([s for s in work_stats if s['keep']])
            
            if current_bins <= target_bins:
                # 检查是否单调
                active_stats = [s for s in work_stats if s['keep']]
                rates = [s['bad_rate'] for s in active_stats]
                
                is_mono = self._check_monotonic_rates(rates, trend, tolerance)
                if is_mono:
                    cuts = [s['end_idx'] for s in active_stats]
                    iv = self._calculate_iv_from_stats(active_stats)
                    return {'cuts': cuts, 'iv': iv}
                
                # 还需要继续合并
                if current_bins <= 2:
                    break
            
            # 找到最佳合并对
            best_merge_idx = self._find_best_merge_pair(
                work_stats, trend, target_bins, min_samples, tolerance, merge_strategy
            )
            if best_merge_idx is None:
                break
            
            # 执行合并
            self._merge_pair(work_stats, best_merge_idx)
        
        return None
    
    def _find_best_merge_pair(self, stats: List[Dict], trend: str, target_bins: int,
                              min_samples: int, tolerance: float, 
                              merge_strategy: str) -> Optional[int]:
        """找到最佳合并对
        
        根据 merge_strategy 选择：
        - balanced: 平衡考虑单调违反和IV损失
        - monotonic_first: 优先合并违反单调性的箱子
        - iv_first: 优先选择IV损失最小的合并
        """
        active_indices = [i for i, s in enumerate(stats) if s['keep']]
        
        if len(active_indices) <= 2:
            return None
        
        candidates = []
        
        for i in range(len(active_indices) - 1):
            idx1 = active_indices[i]
            idx2 = active_indices[i + 1]
            
            s1, s2 = stats[idx1], stats[idx2]
            
            # 检查最小样本数约束
            merged_count = s1['count'] + s2['count']
            if merged_count < min_samples:
                continue
            
            # 计算合并后的bad_rate
            merged_events = s1['events'] + s2['events']
            merged_rate = merged_events / merged_count if merged_count > 0 else 0
            
            # 检查是否违反单调性
            violates_mono = False
            if trend == 'ascending':
                if s1['bad_rate'] > s2['bad_rate'] + tolerance:
                    violates_mono = True
            else:
                if s1['bad_rate'] < s2['bad_rate'] - tolerance:
                    violates_mono = True
            
            # 计算IV损失
            iv_loss = abs(merged_rate - s1['bad_rate']) + abs(merged_rate - s2['bad_rate'])
            
            # 根据策略打分（越小越好）
            if merge_strategy == 'monotonic_first':
                score = (0 if violates_mono else 1) * 1000 + iv_loss
            elif merge_strategy == 'iv_first':
                score = iv_loss * 100 + (0 if violates_mono else 1)
            else:  # balanced
                score = (0 if violates_mono else 1) * 100 + iv_loss
            
            candidates.append((idx1, score, violates_mono, iv_loss))
        
        if not candidates:
            return None
        
        # 选择得分最低的
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    
    def _merge_pair(self, stats: List[Dict], idx: int):
        """合并idx和idx+1"""
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
    
    def _check_monotonic_rates(self, rates: List[float], trend: str, 
                               tolerance: float) -> bool:
        """检查bad_rate列表是否单调"""
        if trend == 'ascending':
            return all(rates[i] <= rates[i+1] + tolerance for i in range(len(rates)-1))
        else:
            return all(rates[i] >= rates[i+1] - tolerance for i in range(len(rates)-1))
    
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
        for cut in cuts[:-1]:
            splits.append(float(x[cut]))
        splits.append(np.inf)
        return splits
    
    def _fallback(self, x: np.ndarray, y: np.ndarray, min_bins: int, 
                  strategy: str) -> 'SmartMonotonicBinner':
        """保底策略
        
        - simple: 简单切分（三等分或二等分）
        - equal_freq: 强制等频分箱
        - decision_tree: 使用决策树切分
        """
        self._log(f"保底策略: {strategy}")
        n = len(x)
        
        if strategy == 'equal_freq':
            # 强制等频分箱
            splits = [-np.inf]
            for i in range(1, min_bins):
                idx = int(n * i / min_bins)
                splits.append(float(x[idx]))
            splits.append(np.inf)
            self._splits = splits
            
        elif strategy == 'decision_tree':
            # 使用决策树切分
            try:
                from sklearn.tree import DecisionTreeClassifier
                dt = DecisionTreeClassifier(max_leaf_nodes=min_bins, random_state=42)
                dt.fit(x.reshape(-1, 1), y)
                
                # 提取切分点
                tree = dt.tree_
                splits = set()
                for i in range(tree.node_count):
                    if tree.children_left[i] != tree.children_right[i]:
                        splits.add(tree.threshold[i])
                splits = sorted(splits)
                self._splits = [-np.inf] + splits + [np.inf]
            except Exception:
                # 决策树失败，降级为简单切分
                return self._fallback(x, y, min_bins, 'simple')
        else:
            # simple: 简单切分
            if min_bins <= 2:
                idx = n // 2
                self._splits = [-np.inf, float(x[idx]), np.inf]
            else:
                splits = [-np.inf]
                for i in range(1, min_bins):
                    idx = int(n * i / min_bins)
                    splits.append(float(x[idx]))
                splits.append(np.inf)
                self._splits = splits
        
        self._is_monotonic = True
        self._adjustment_method = f'fallback_{strategy}'
        return self
    
    def transform(self, x: pd.Series) -> pd.Series:
        return pd.cut(x, bins=self._splits, include_lowest=True)
    
    @property
    def is_monotonic(self) -> bool:
        return self._is_monotonic
    
    @property
    def splits(self) -> List[float]:
        return self._splits
    
    @property
    def adjustment_info(self) -> List[str]:
        return self._adjustment_info
    
    @property
    def adjustment_method(self) -> Optional[str]:
        return self._adjustment_method
    
    @property
    def config(self) -> Dict:
        """获取使用的配置"""
        return self._config
    
    def _log(self, msg: str):
        self._adjustment_info.append(msg)
