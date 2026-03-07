import pandas as pd
import numpy as np
from typing import List, Optional, Union
from sklearn.tree import DecisionTreeClassifier
from scipy import stats
from .base import BaseBinner

class DecisionTreeBinner(BaseBinner):
    """
    决策树分箱 (Decision Tree Binning)。
    利用 CART 决策树算法，以目标变量为监督信息，寻找最优的切分点。
    这种方法能最大化箱与箱之间的区分度 (Gini 或 Entropy)。
    """

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'DecisionTreeBinner':
        """
        Args:
            x (pd.Series): 特征数据。
            y (pd.Series): 目标变量（必需）。
            **kwargs:
                max_leaf_nodes (int): 最大叶子节点数（即最大箱数），默认 5。
                min_samples_leaf (float): 叶子节点最小样本占比，默认 0.05。
        """
        if y is None:
            raise ValueError("DecisionTreeBinner requires target variable 'y'.")

        # 1. 准备数据
        data = pd.DataFrame({'feature': x, 'target': y}).dropna()
        X_train = data[['feature']]
        y_train = data['target']

        # 2. 获取参数
        max_leaf_nodes = kwargs.get('max_leaf_nodes', 5)
        min_samples_leaf = kwargs.get('min_samples_leaf', 0.05)
        
        # 如果 min_samples_leaf 是小数，转换为样本数
        if isinstance(min_samples_leaf, float):
            min_samples_leaf = int(len(data) * min_samples_leaf)

        # 3. 训练决策树
        dt = DecisionTreeClassifier(
            criterion='entropy',  # 使用信息熵 (Information Gain)
            max_leaf_nodes=max_leaf_nodes,
            min_samples_leaf=min_samples_leaf,
            random_state=42
        )
        dt.fit(X_train, y_train)

        # 4. 提取切点 (Thresholds)
        # tree_.threshold 包含所有节点的切点，非叶子节点的 threshold != -2
        thresholds = dt.tree_.threshold[dt.tree_.threshold != -2]
        
        # 5. 整理切点
        splits = sorted(list(set(thresholds)))
        
        # 扩展首尾
        if not splits: # 树可能没分裂（例如数据太少或纯度太高）
             self._splits = [-np.inf, np.inf]
        else:
             self._splits = [-np.inf] + splits + [np.inf]
             
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)


class ChiMergeBinner(BaseBinner):
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'ChiMergeBinner':
        if y is None:
            raise ValueError("ChiMergeBinner requires target variable 'y'.")
        max_bins = kwargs.get('max_bins', 5)
        initial_bins = kwargs.get('initial_bins', 64)

        df = pd.DataFrame({'x': x, 'y': y}).dropna()

        try:
            cats = pd.qcut(df['x'], q=initial_bins, duplicates='drop')
        except Exception:
            cats = pd.cut(df['x'], bins=initial_bins)

        gb = df.groupby(cats, observed=False)['y'].agg(['count', 'sum'])
        gb.rename(columns={'count': 'total', 'sum': 'bad'}, inplace=True)
        gb['good'] = gb['total'] - gb['bad']

        intervals = []
        rows = gb.reset_index().sort_values('x')
        for _, r in rows.iterrows():
            iv = r['x']
            intervals.append({'min': float(iv.left), 'max': float(iv.right), 'good': int(r['good']), 'bad': int(r['bad'])})

        while len(intervals) > max_bins:
            chi_values = []
            for i in range(len(intervals) - 1):
                obs = np.array([[intervals[i]['good'], intervals[i]['bad']],
                                [intervals[i+1]['good'], intervals[i+1]['bad']]])
                try:
                    chi2, _, _, _ = stats.chi2_contingency(obs)
                except Exception:
                    chi2 = 0.0
                chi_values.append(chi2)
            min_idx = int(np.argmin(chi_values))
            intervals[min_idx]['max'] = intervals[min_idx + 1]['max']
            intervals[min_idx]['good'] += intervals[min_idx + 1]['good']
            intervals[min_idx]['bad'] += intervals[min_idx + 1]['bad']
            intervals.pop(min_idx + 1)

        splits = [i['max'] for i in intervals[:-1]]
        self._splits = sorted(list(set([-np.inf] + splits + [np.inf])))
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)


class BestKSBinner(BaseBinner):
    """
    Best-KS 分箱：在候选切点中选择使 KS 最大化的切分，
    通过贪心递归或迭代选择，约束最大箱数与最小样本量。
    实现思路：
    1) 先对连续特征按等频/等距预分桶 (initial_bins)。
    2) 计算每个桶的好/坏计数与累计分布；
    3) 在候选边界上评估 KS，迭代选择最高 KS 的边界作为切点，直到达到 max_bins-1 或无显著提升。
    """

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'BestKSBinner':
        if y is None:
            raise ValueError("BestKSBinner requires target variable 'y'.")
        max_bins = kwargs.get('max_bins', 5)
        initial_bins = kwargs.get('initial_bins', 64)
        min_samples_bin = kwargs.get('min_samples_bin', 0)

        df = pd.DataFrame({'x': x, 'y': y}).dropna()
        n = len(df)
        min_samples_abs = int(min_samples_bin * n) if 0 < min_samples_bin < 1 else int(min_samples_bin)

        try:
            cats = pd.qcut(df['x'], q=initial_bins, duplicates='drop')
        except Exception:
            cats = pd.cut(df['x'], bins=initial_bins)

        gb = df.groupby(cats, observed=False)['y'].agg(['count', 'sum']).reset_index()
        gb.rename(columns={'count': 'total', 'sum': 'bad'}, inplace=True)
        gb['good'] = gb['total'] - gb['bad']

        # 计算每桶的累计分布
        gb = gb.sort_values('x')
        gb['cum_bad'] = gb['bad'].cumsum()
        gb['cum_good'] = gb['good'].cumsum()
        total_bad = gb['bad'].sum()
        total_good = gb['good'].sum()
        gb['cdf_bad'] = gb['cum_bad'] / max(total_bad, 1)
        gb['cdf_good'] = gb['cum_good'] / max(total_good, 1)
        gb['ks'] = (gb['cdf_bad'] - gb['cdf_good']).abs()

        # 候选边界为每个桶的右边界（不含最后一个）
        candidates = gb[:-1].copy()
        candidates['boundary'] = candidates['x'].apply(lambda iv: iv.right)

        # 贪心选择：每次挑选最高 KS 的边界，避免过近边界导致空箱
        chosen = []
        used = set()
        while len(chosen) < max_bins - 1 and not candidates.empty:
            c = candidates.sort_values('ks', ascending=False).iloc[0]
            boundary = float(c['boundary'])
            # 样本量约束：粗略检查分割两侧样本是否满足最小值
            left_count = gb[candidates.index[0]:candidates.index[0]+1]['cum_bad'].iloc[0] + gb[candidates.index[0]:candidates.index[0]+1]['cum_good'].iloc[0]
            right_count = n - (gb.loc[candidates.index[0], 'cum_bad'] + gb.loc[candidates.index[0], 'cum_good'])
            if (min_samples_abs and (left_count < min_samples_abs or right_count < min_samples_abs)):
                candidates = candidates.iloc[1:]
                continue
            if boundary in used:
                candidates = candidates.iloc[1:]
                continue
            chosen.append(boundary)
            used.add(boundary)
            candidates = candidates.iloc[1:]

        splits = sorted(chosen)
        self._splits = sorted(list(set([-np.inf] + splits + [np.inf])))
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)
