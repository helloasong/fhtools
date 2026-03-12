"""分箱算法模块

提供多种分箱算法的实现，包括无监督分箱和有监督分箱。
"""
from .base import BaseBinner
from .unsupervised import EqualFrequencyBinner, EqualWidthBinner, ManualBinner
from .supervised import DecisionTreeBinner, ChiMergeBinner, BestKSBinner

# 可选依赖：optbinning
from .optbinning_adapter import (
    OptimalBinningAdapter,
    OPTBINNING_AVAILABLE,
)

__all__ = [
    # 基类
    'BaseBinner',
    # 无监督分箱
    'EqualFrequencyBinner',
    'EqualWidthBinner',
    'ManualBinner',
    # 有监督分箱
    'DecisionTreeBinner',
    'ChiMergeBinner',
    'BestKSBinner',
    # 可选依赖
    'OptimalBinningAdapter',
    'OPTBINNING_AVAILABLE',
]
