import unittest
import pandas as pd
import numpy as np
from src.core.binning.unsupervised import EqualFrequencyBinner, EqualWidthBinner, ManualBinner
from src.core.binning.supervised import DecisionTreeBinner, ChiMergeBinner
from src.core.metrics import MetricsCalculator

class TestBinning(unittest.TestCase):

    def setUp(self):
        # 构造测试数据
        np.random.seed(42)
        self.n_samples = 100
        self.x = pd.Series(np.random.normal(0, 1, self.n_samples))
        # 构造 target，使其与 x 有一定关系
        self.y = pd.Series((self.x > 0).astype(int))
        
        # 构造含有缺失值的数据
        self.x_nan = self.x.copy()
        self.x_nan.iloc[0:10] = np.nan

    def test_equal_frequency(self):
        binner = EqualFrequencyBinner()
        binner.fit(self.x, n_bins=5)
        splits = binner.splits
        
        # 验证切点数量 (5箱 => 6个切点: -inf, q1, q2, q3, q4, inf)
        self.assertEqual(len(splits), 6)
        self.assertEqual(splits[0], -np.inf)
        self.assertEqual(splits[-1], np.inf)
        
        # 验证转换结果
        x_bin = binner.transform(self.x)
        # 每个箱的样本数应该大致相等 (100 / 5 = 20)
        counts = x_bin.value_counts()
        self.assertTrue(all(c >= 18 and c <= 22 for c in counts))

    def test_equal_width(self):
        binner = EqualWidthBinner()
        binner.fit(self.x, n_bins=5)
        splits = binner.splits
        
        self.assertEqual(len(splits), 6)
        
        # 验证切点间距是否相等 (中间部分)
        diffs = np.diff(splits[1:-1])
        self.assertTrue(np.allclose(diffs, diffs[0]))

    def test_manual_binning(self):
        binner = ManualBinner()
        # 手动指定 [-1, 1]
        binner.fit(self.x, splits=[-1, 1])
        splits = binner.splits
        
        # 应该自动扩展为 [-inf, -1, 1, inf]
        self.assertEqual(splits, [-np.inf, -1.0, 1.0, np.inf])

    def test_decision_tree(self):
        binner = DecisionTreeBinner()
        binner.fit(self.x, self.y, max_leaf_nodes=3)
        splits = binner.splits
        
        # 决策树应该能找到 0 附近的切点
        has_split_near_zero = any(abs(s) < 0.5 for s in splits if np.isfinite(s))
        self.assertTrue(has_split_near_zero)

    def test_chimerge(self):
        binner = ChiMergeBinner()
        # 使用较少的数据测试 ChiMerge，因为它比较慢
        x_small = self.x[:50]
        y_small = self.y[:50]
        
        binner.fit(x_small, y_small, max_bins=3)
        splits = binner.splits
        
        # 验证切点是否合理
        self.assertGreaterEqual(len(splits), 2)
        self.assertEqual(splits[0], -np.inf)

    def test_metrics(self):
        # 简单构造一个完全区分的数据
        # bin1: all good (y=0) -> bad_rate=0 -> woe = +inf (或者很大)
        # bin2: all bad (y=1) -> bad_rate=1 -> woe = -inf (或者很小)
        x_bin = pd.Series([1, 1, 1, 1, 1, 2, 2, 2, 2, 2])
        y = pd.Series([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        
        metrics = MetricsCalculator.calculate(x_bin, y)
        
        summary = metrics.summary_table
        self.assertEqual(len(summary), 2)
        
        # 验证 IV 值应该是很大的（因为完全区分）
        self.assertGreater(metrics.iv, 1.0)
        
        # 验证单调性 (0 -> 1，Bad Rate 递增)
        self.assertTrue(metrics.is_monotonic)

    def test_nan_handling(self):
        # 测试等频分箱对 NaN 的处理（忽略 NaN 进行计算）
        binner = EqualFrequencyBinner()
        binner.fit(self.x_nan, n_bins=5)
        # 应该不报错，且能算出切点
        self.assertEqual(len(binner.splits), 6)

if __name__ == '__main__':
    unittest.main()
