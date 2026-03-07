from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import List, Optional, Union

class BaseBinner(ABC):
    """
    分箱算法的抽象基类 (Abstract Base Class)。
    
    所有具体的分箱策略（如等频、等距、卡方等）都必须继承此类，
    并实现 fit, transform 和 splits 接口。
    """

    def __init__(self):
        self._splits: List[float] = []

    @abstractmethod
    def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'BaseBinner':
        """
        根据输入数据计算分箱切点。

        Args:
            x (pd.Series): 待分箱的特征数据（连续型）。
            y (pd.Series, optional): 目标变量数据（仅有监督分箱算法需要）。
            **kwargs: 其他算法特定的参数（如 n_bins, min_samples 等）。

        Returns:
            BaseBinner: 返回自身实例，支持链式调用。
        """
        pass

    @abstractmethod
    def transform(self, x: pd.Series) -> pd.Series:
        """
        将原始数据映射到对应的箱。

        Args:
            x (pd.Series): 待转换的特征数据。

        Returns:
            pd.Series: 分箱后的类别数据（Categorical）或区间字符串。
        """
        pass

    @property
    def splits(self) -> List[float]:
        """
        获取计算得到的分箱切点列表。
        
        Returns:
            List[float]: 切点列表，通常包含 -inf 和 +inf。
        """
        return self._splits

    def _apply_splits(self, x: pd.Series, splits: List[float]) -> pd.Series:
        """
        通用工具方法：根据给定的切点对数据进行分箱。

        Args:
            x (pd.Series): 原始数据。
            splits (List[float]): 切点列表。

        Returns:
            pd.Series: 分箱后的结果。
        """
        # 确保 splits 单调递增且不重复
        unique_splits = sorted(list(set(splits)))
        
        # 使用 pd.cut 进行分箱
        # include_lowest=True 保证左闭右开区间能包含最小值
        # labels=False 返回箱的索引，方便后续处理；如果需要区间标签，可设为 None
        return pd.cut(x, bins=unique_splits, include_lowest=True)
