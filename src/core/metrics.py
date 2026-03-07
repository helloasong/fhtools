import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

@dataclass
class BinningMetrics:
    """
    分箱指标结果类。
    """
    woe: pd.Series
    iv: float
    summary_table: pd.DataFrame
    is_monotonic: bool

class MetricsCalculator:
    """
    分箱指标计算器。
    负责计算 Count, Percent, Bad Rate, WOE, IV, Lift 等指标。
    """

    @staticmethod
    def calculate(x_binned: pd.Series, y: pd.Series, target_value: int = 1, missing_strategy: str = "separate", missing_merge_label: Optional[str] = None) -> BinningMetrics:
        """
        计算分箱的各项指标。

        Args:
            x_binned (pd.Series): 分箱后的特征数据（Categorical 或 bin index）。
            y (pd.Series): 目标变量（0/1）。
            target_value (int): 坏样本的目标值，默认为 1。

        Returns:
            BinningMetrics: 包含 WOE, IV, 汇总表的对象。
        """
        # 1. 构造基础统计表
        df = pd.DataFrame({'bin': x_binned, 'target': y})

        if missing_strategy == 'ignore':
            df = df[~df['bin'].isna()]
        elif missing_strategy == 'separate':
            df['bin'] = df['bin'].astype('object')
            df.loc[df['bin'].isna(), 'bin'] = 'Missing'
        elif missing_strategy == 'merge':
            pass
        
        # 统计每个箱的总样本数、坏样本数
        summary = df.groupby('bin', observed=False)['target'].agg(['count', 'sum']).rename(columns={'count': 'total', 'sum': 'bad'})
        summary['good'] = summary['total'] - summary['bad']
        
        # 2. 计算全局统计量
        total_bad = summary['bad'].sum()
        total_good = summary['good'].sum()
        
        # 防止除零错误，加一个极小值 epsilon
        epsilon = 1e-10
        
        # 3. 计算比率指标
        summary['total_pct'] = summary['total'] / summary['total'].sum()
        summary['bad_rate'] = summary['bad'] / summary['total']
        summary['bad_dist'] = summary['bad'] / total_bad  # 坏样本占比 (Distribution Bad)
        summary['good_dist'] = summary['good'] / total_good # 好样本占比 (Distribution Good)
        
        # 4. 计算 WOE 和 IV
        # WOE = ln(Dist_Good / Dist_Bad)  (注意：通常风控中定义 WOE = ln(Good% / Bad%) 或 ln(Bad% / Good%)，需统一符号)
        # 这里采用标准定义: WOE = ln(Dist_Bad / Dist_Good) * 100 ? 或者 ln(Dist_Good / Dist_Bad)
        # 常用：WOE_i = ln( (Good_i / Total_Good) / (Bad_i / Total_Bad) )
        # IV_i = ( (Good_i / Total_Good) - (Bad_i / Total_Bad) ) * WOE_i
        
        # 修正：为了保证 WOE 与 Bad Rate 负相关（Bad Rate 越高，分数越低），通常定义 WOE = ln(Good_dist / Bad_dist)
        summary['woe'] = np.log((summary['good_dist'] + epsilon) / (summary['bad_dist'] + epsilon))
        summary['iv'] = (summary['good_dist'] - summary['bad_dist']) * summary['woe']
        
        # 5. 计算 Lift
        # Lift = Bad_Rate_i / Total_Bad_Rate
        total_bad_rate = total_bad / (total_bad + total_good)
        summary['lift'] = summary['bad_rate'] / total_bad_rate
        
        # 6. 检查单调性 (基于 Bad Rate)
        # 忽略空箱与缺失箱，并按区间中心排序以避免字符串与 Interval 比较异常
        tmp = summary.reset_index()
        def _order_key(b):
            if isinstance(b, pd.Interval):
                return (float(b.left) + float(b.right)) / 2.0
            # 将缺失或其他字符串放到末尾，不参与单调性判断
            return np.inf
        mask_valid = (tmp['total'] > 0) & (~tmp['bin'].astype(str).eq('Missing'))
        bad_rates_series = tmp.loc[mask_valid, ['bin', 'bad_rate']].copy()
        bad_rates_series['order_key'] = bad_rates_series['bin'].apply(_order_key)
        bad_rates_sorted = bad_rates_series.sort_values('order_key')['bad_rate'].values
        is_increasing = np.all(np.diff(bad_rates_sorted) >= 0) if bad_rates_sorted.size > 1 else True
        is_decreasing = np.all(np.diff(bad_rates_sorted) <= 0) if bad_rates_sorted.size > 1 else True
        is_monotonic = is_increasing or is_decreasing
        
        # 7. 整理返回结果
        # 如果是 merge 策略，且存在缺失，需要将缺失并入指定标签，再重算
        if missing_strategy == 'merge' and df['bin'].isna().any():
            overall_bad_rate = df['target'].mean()
            target_label = missing_merge_label
            if target_label is None:
                diffs = (summary['bad_rate'] - overall_bad_rate).abs()
                target_label = diffs.idxmin()
            df['bin'] = df['bin'].astype('object')
            df.loc[df['bin'].isna(), 'bin'] = target_label
            summary = df.groupby('bin', observed=False)['target'].agg(['count', 'sum']).rename(columns={'count': 'total', 'sum': 'bad'})
            summary['good'] = summary['total'] - summary['bad']
            summary['total_pct'] = summary['total'] / summary['total'].sum()
            summary['bad_rate'] = summary['bad'] / summary['total']
            summary['bad_dist'] = summary['bad'] / summary['bad'].sum()
            summary['good_dist'] = summary['good'] / summary['good'].sum()
            summary['woe'] = np.log((summary['good_dist'] + epsilon) / (summary['bad_dist'] + epsilon))
            summary['iv'] = (summary['good_dist'] - summary['bad_dist']) * summary['woe']
            total_bad_rate = summary['bad'].sum() / summary['total'].sum()
            summary['lift'] = summary['bad_rate'] / total_bad_rate
            tmp = summary.reset_index()
            mask_valid = (tmp['total'] > 0) & (~tmp['bin'].astype(str).eq('Missing'))
            bad_rates_series = tmp.loc[mask_valid, ['bin', 'bad_rate']].copy()
            bad_rates_series['order_key'] = bad_rates_series['bin'].apply(_order_key)
            bad_rates_sorted = bad_rates_series.sort_values('order_key')['bad_rate'].values
            is_increasing = np.all(np.diff(bad_rates_sorted) >= 0) if bad_rates_sorted.size > 1 else True
            is_decreasing = np.all(np.diff(bad_rates_sorted) <= 0) if bad_rates_sorted.size > 1 else True
            is_monotonic = is_increasing or is_decreasing

        total_iv = summary['iv'].sum()
        
        return BinningMetrics(
            woe=summary['woe'],
            iv=total_iv,
            summary_table=summary,
            is_monotonic=is_monotonic
        )
