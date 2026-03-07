import pandas as pd
import numpy as np
from typing import List, Optional
from .base import BaseBinner

class EqualFrequencyBinner(BaseBinner):
    """
    等频分箱 (Equal Frequency Binning)。
    将数据划分为 n_bins 个箱，使得每个箱中的样本数量大致相同。
    """

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'EqualFrequencyBinner':
        """
        计算等频分箱的切点。

        Args:
            x (pd.Series): 待分箱的特征数据。
            y (pd.Series, optional): 目标变量（不使用，仅为了接口兼容）。
            **kwargs:
                n_bins (int): 期望的箱数，默认为 10。

        Returns:
            EqualFrequencyBinner: 自身实例。
        """
        n_bins = kwargs.get('n_bins', 10)
        
        # 1. 处理缺失值，只对非空值进行切分计算
        x_clean = x.dropna()
        
        if len(x_clean) == 0:
            self._splits = [-np.inf, np.inf]
            return self

        # 2. 使用 qcut 计算分位点
        # retbins=True 返回 (bins, splits)
        # duplicates='drop' 处理大量重复值导致的切点重复问题
        try:
            _, splits = pd.qcut(x_clean, q=n_bins, retbins=True, duplicates='drop')
            splits = list(splits)
        except ValueError:
            # 如果数据极度倾斜，qcut 可能失败，回退到最大最小值
            splits = [x_clean.min(), x_clean.max()]

        # 3. 扩展首尾切点为 -inf 和 +inf，确保覆盖所有可能的新数据
        splits[0] = -np.inf
        splits[-1] = np.inf
        
        self._splits = sorted(list(set(splits)))
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)


class EqualWidthBinner(BaseBinner):
    """
    等距分箱 (Equal Width Binning)。
    将数据划分为 n_bins 个箱，使得每个箱的区间宽度（Max - Min）相同。
    """

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'EqualWidthBinner':
        """
        计算等距分箱的切点。

        Args:
            x (pd.Series): 待分箱的特征数据。
            y (pd.Series, optional): 目标变量（不使用）。
            **kwargs:
                n_bins (int): 期望的箱数，默认为 10。
        """
        n_bins = kwargs.get('n_bins', 10)
        x_clean = x.dropna()

        if len(x_clean) == 0:
            self._splits = [-np.inf, np.inf]
            return self

        # 1. 使用 cut 计算等距切点
        _, splits = pd.cut(x_clean, bins=n_bins, retbins=True)
        splits = list(splits)

        # 2. 扩展首尾
        splits[0] = -np.inf
        splits[-1] = np.inf

        self._splits = sorted(list(set(splits)))
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)


class ManualBinner(BaseBinner):
    """
    手动分箱 (Manual Binning)。
    使用用户指定的切点列表进行分箱。
    """

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'ManualBinner':
        """
        设置手动切点。

        Args:
            x (pd.Series): 特征数据（用于校验范围，可选）。
            y (pd.Series, optional): 目标变量。
            **kwargs:
                splits (List[float]): 必需参数。用户指定的切点列表。
                                      例如 [20, 30, 40] 将产生 (-inf, 20], (20, 30], (30, 40], (40, inf)。
        """
        custom_splits = kwargs.get('splits')
        if not custom_splits:
            raise ValueError("ManualBinner requires 'splits' parameter in kwargs.")

        # 确保包含 -inf 和 inf
        splits = sorted(list(set(custom_splits)))
        if splits[0] != -np.inf:
            splits.insert(0, -np.inf)
        if splits[-1] != np.inf:
            splits.append(np.inf)
            
        self._splits = splits
        return self

    def transform(self, x: pd.Series) -> pd.Series:
        return self._apply_splits(x, self._splits)
