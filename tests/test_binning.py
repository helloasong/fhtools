import unittest
import pandas as pd
import numpy as np
from src.core.binning.unsupervised import EqualFrequencyBinner, EqualWidthBinner, ManualBinner
from src.core.binning.supervised import DecisionTreeBinner, ChiMergeBinner
from src.core.binning.optbinning_adapter import OptimalBinningAdapter, OPTBINNING_AVAILABLE
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



class TestOptimalBinningAdapter(unittest.TestCase):
    """OptimalBinningAdapter 单元测试"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        self.n_samples = 100
        self.x = pd.Series(np.random.normal(0, 1, self.n_samples), name='test_feature')
        # 构造与 x 相关的目标变量
        self.y = pd.Series((self.x > 0).astype(int))

    def test_import_availability_flag(self):
        """测试导入标志是否正确设置"""
        # OPTBINNING_AVAILABLE 应该是布尔值
        self.assertIsInstance(OPTBINNING_AVAILABLE, bool)

    def test_initialization(self):
        """测试初始化状态"""
        adapter = OptimalBinningAdapter()
        self.assertEqual(adapter.status, 'NOT_FITTED')
        self.assertEqual(adapter.splits, [])
        self.assertEqual(adapter.get_info(), {})

    def test_parameter_validation_solver(self):
        """测试 solver 参数验证"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        adapter = OptimalBinningAdapter()
        # 无效的 solver
        with self.assertRaises(ValueError) as context:
            adapter.fit(self.x, self.y, solver='invalid_solver')
        self.assertIn('solver', str(context.exception))
        
        # 有效的 solver 不应抛出错误
        for solver in ['cp', 'mip', 'ls']:
            adapter = OptimalBinningAdapter()
            try:
                adapter.fit(self.x, self.y, solver=solver, time_limit=10)
            except Exception as e:
                # 只接受 ImportError 或求解相关错误，不接受参数验证错误
                if 'solver' in str(e).lower():
                    self.fail(f"Valid solver {solver} raised error: {e}")

    def test_parameter_validation_divergence(self):
        """测试 divergence 参数验证"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        adapter = OptimalBinningAdapter()
        # 无效的 divergence
        with self.assertRaises(ValueError) as context:
            adapter.fit(self.x, self.y, divergence='invalid')
        self.assertIn('divergence', str(context.exception))
        
        # 有效的 divergence 不应抛出错误
        for div in ['iv', 'js', 'hellinger', 'triangular']:
            adapter = OptimalBinningAdapter()
            try:
                adapter.fit(self.x, self.y, divergence=div, time_limit=10)
            except Exception as e:
                if 'divergence' in str(e).lower():
                    self.fail(f"Valid divergence {div} raised error: {e}")

    def test_parameter_validation_bins(self):
        """测试 bins 相关参数验证"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        adapter = OptimalBinningAdapter()
        
        # max_n_bins 太小
        with self.assertRaises(ValueError):
            adapter.fit(self.x, self.y, max_n_bins=1)
        
        # min_n_bins 太小
        adapter = OptimalBinningAdapter()
        with self.assertRaises(ValueError):
            adapter.fit(self.x, self.y, min_n_bins=1)
        
        # min_n_bins > max_n_bins
        adapter = OptimalBinningAdapter()
        with self.assertRaises(ValueError) as context:
            adapter.fit(self.x, self.y, min_n_bins=5, max_n_bins=3)
        self.assertIn('min_n_bins', str(context.exception))

    def test_parameter_validation_prebin_size(self):
        """测试 min_prebin_size 参数验证"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        adapter = OptimalBinningAdapter()
        
        # 无效的范围
        with self.assertRaises(ValueError):
            adapter.fit(self.x, self.y, min_prebin_size=0)
        
        with self.assertRaises(ValueError):
            adapter.fit(self.x, self.y, min_prebin_size=1.5)

    def test_missing_y(self):
        """测试缺少 y 时的错误"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        adapter = OptimalBinningAdapter()
        with self.assertRaises(ValueError) as context:
            adapter.fit(self.x, None)
        self.assertIn('target variable', str(context.exception))

    def test_transform_before_fit(self):
        """测试未拟合时调用 transform"""
        if not OPTBINNING_AVAILABLE:
            # 如果 optbinning 未安装，应该抛出 ImportError
            adapter = OptimalBinningAdapter()
            with self.assertRaises(ImportError):
                adapter.transform(self.x)
            return
        
        adapter = OptimalBinningAdapter()
        with self.assertRaises(RuntimeError) as context:
            adapter.transform(self.x)
        self.assertIn('fitted', str(context.exception).lower())

    def test_special_codes_parameter(self):
        """测试 special_codes 参数"""
        if not OPTBINNING_AVAILABLE:
            self.skipTest("optbinning not installed")
        
        # 有效的 special_codes
        adapter = OptimalBinningAdapter()
        try:
            adapter.fit(self.x, self.y, special_codes=[-999, -1], time_limit=10)
        except Exception as e:
            if 'special_codes' in str(e).lower():
                self.fail(f"Valid special_codes raised error: {e}")
        
        # 无效的 special_codes 类型
        adapter = OptimalBinningAdapter()
        with self.assertRaises(ValueError):
            adapter.fit(self.x, self.y, special_codes="invalid")

    @unittest.skipUnless(OPTBINNING_AVAILABLE, "optbinning not installed")
    def test_fit_transform_integration(self):
        """测试完整的拟合和转换流程（需要 optbinning 安装）"""
        adapter = OptimalBinningAdapter()
        adapter.fit(self.x, self.y, max_n_bins=5, time_limit=10)
        
        # 检查状态
        self.assertIn(adapter.status, ['OPTIMAL', 'FEASIBLE', 'UNKNOWN'])
        
        # 检查切点
        splits = adapter.splits
        self.assertGreaterEqual(len(splits), 2)
        self.assertEqual(splits[0], -np.inf)
        self.assertEqual(splits[-1], np.inf)
        
        # 转换数据
        result = adapter.transform(self.x)
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), len(self.x))
        
        # 检查分箱数量
        n_bins = len(result.unique())
        self.assertLessEqual(n_bins, 5)
        
        # 检查 get_info
        info = adapter.get_info()
        self.assertIn('solver', info)
        self.assertIn('status', info)
        self.assertIn('n_bins', info)

    @unittest.skipUnless(OPTBINNING_AVAILABLE, "optbinning not installed")
    def test_get_binning_table(self):
        """测试获取分箱表（需要 optbinning 安装）"""
        adapter = OptimalBinningAdapter()
        
        # 未拟合时返回 None
        self.assertIsNone(adapter.get_binning_table())
        
        # 拟合后应返回 DataFrame
        adapter.fit(self.x, self.y, time_limit=10)
        table = adapter.get_binning_table()
        if table is not None:
            self.assertIsInstance(table, pd.DataFrame)
            self.assertIn('Bin', table.columns)

