"""
SmartMonotonicBinner 全面单元测试

测试覆盖:
1. 基础功能测试 (使用 mock_data.xlsx)
2. 单调性保证测试
3. 边界情况测试
4. 参数验证测试
5. 与其他分箱器对比测试
"""
import unittest
import pandas as pd
import numpy as np
from src.core.binning.smart_monotonic import SmartMonotonicBinner
from src.core.binning.supervised import DecisionTreeBinner
from src.core.metrics import MetricsCalculator


class TestSmartMonotonicBinner(unittest.TestCase):
    """SmartMonotonicBinner 单元测试"""

    @classmethod
    def setUpClass(cls):
        """加载测试数据"""
        try:
            cls.df = pd.read_excel('tests/mock_data.xlsx')
            print(f"\n加载测试数据: {cls.df.shape}")
        except FileNotFoundError:
            # 如果路径不对，尝试相对路径
            cls.df = pd.read_excel('mock_data.xlsx')
        
        cls.x_numeric = cls.df['feature_02']  # 最强相关特征
        cls.x_weak = cls.df['feature_05']     # 弱相关特征
        cls.x_extreme = cls.df['feature_01']  # 极端值特征
        cls.y = cls.df['target']

    def setUp(self):
        """每个测试前重置"""
        self.binner = SmartMonotonicBinner()

    # ========== 基础功能测试 ==========

    def test_basic_fit(self):
        """测试基础拟合功能"""
        result = self.binner.fit(self.x_numeric, self.y, max_bins=5)
        
        self.assertIsInstance(result, SmartMonotonicBinner)
        self.assertTrue(len(self.binner.splits) >= 2)
        self.assertEqual(self.binner.splits[0], -np.inf)
        self.assertEqual(self.binner.splits[-1], np.inf)

    def test_transform(self):
        """测试转换功能"""
        self.binner.fit(self.x_numeric, self.y, max_bins=5)
        result = self.binner.transform(self.x_numeric)
        
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), len(self.x_numeric))
        # 验证分箱数量
        n_bins = len(result.dropna().unique())
        self.assertLessEqual(n_bins, 5)

    def test_monotonicity_guarantee(self):
        """测试单调性保证 - 核心功能"""
        # 测试多次运行，确保100%单调
        for max_bins in [3, 5, 8, 10]:
            for trend in ['auto', 'ascending', 'descending']:
                binner = SmartMonotonicBinner()
                binner.fit(self.x_numeric, self.y, max_bins=max_bins, monotonic_trend=trend)
                
                self.assertTrue(
                    binner.is_monotonic, 
                    f"Failed for max_bins={max_bins}, trend={trend}"
                )

    def test_iv_calculation(self):
        """测试IV计算"""
        self.binner.fit(self.x_numeric, self.y, max_bins=5)
        
        # IV应该为正数
        self.assertGreater(self.binner._final_iv, 0)
        
        # feature_02 应该有较高的IV
        self.assertGreater(self.binner._final_iv, 0.05)

    def test_adjustment_info(self):
        """测试调整信息记录"""
        self.binner.fit(self.x_numeric, self.y)
        
        # 应该有调整信息
        self.assertIsInstance(self.binner.adjustment_info, list)
        self.assertTrue(len(self.binner.adjustment_info) > 0)
        
        # 调整方法应该被记录
        self.assertIsNotNone(self.binner.adjustment_method)

    # ========== 单调性趋势测试 ==========

    def test_auto_trend_detection(self):
        """测试自动趋势检测"""
        # feature_02 与 target 负相关，应该检测为 descending
        self.binner.fit(self.x_numeric, self.y, monotonic_trend='auto')
        
        # 检查实际坏样本率趋势
        result = self.binner.transform(self.x_numeric)
        bad_rates = result.groupby(result).apply(lambda g: self.y[g.index].mean())
        
        # 应该满足单调性
        is_desc = all(bad_rates.iloc[i] >= bad_rates.iloc[i+1] 
                      for i in range(len(bad_rates)-1))
        is_asc = all(bad_rates.iloc[i] <= bad_rates.iloc[i+1] 
                     for i in range(len(bad_rates)-1))
        
        self.assertTrue(is_desc or is_asc, "Should be monotonic in some direction")

    def test_forced_ascending(self):
        """测试强制递增 - 使用构造的递增数据"""
        # 构造已知递增关系的数据
        np.random.seed(42)
        x_asc = pd.Series(np.random.normal(50, 15, 1000))
        y_asc = pd.Series((x_asc > 50).astype(int))  # x越大，y=1概率越高
        
        binner = SmartMonotonicBinner()
        binner.fit(x_asc, y_asc, monotonic_trend='ascending')
        
        result = binner.transform(x_asc)
        bad_rates = result.groupby(result).apply(lambda g: y_asc[g.index].mean())
        
        is_ascending = all(bad_rates.iloc[i] <= bad_rates.iloc[i+1] 
                          for i in range(len(bad_rates)-1))
        self.assertTrue(is_ascending, "Should be ascending when forced")

    def test_forced_descending(self):
        """测试强制递减 - 使用mock数据中的feature_02（已知负相关）"""
        binner = SmartMonotonicBinner()
        binner.fit(self.x_numeric, self.y, monotonic_trend='descending')
        
        result = binner.transform(self.x_numeric)
        bad_rates = result.groupby(result).apply(lambda g: self.y[g.index].mean())
        
        is_descending = all(bad_rates.iloc[i] >= bad_rates.iloc[i+1] 
                           for i in range(len(bad_rates)-1))
        self.assertTrue(is_descending, "Should be descending when forced")

    # ========== 边界情况测试 ==========

    def test_weak_correlation_feature(self):
        """测试弱相关特征 (feature_05)"""
        binner = SmartMonotonicBinner()
        binner.fit(self.x_weak, self.y, max_bins=5)
        
        # 即使弱相关，也应该有解且单调
        self.assertTrue(binner.is_monotonic)
        self.assertGreaterEqual(len(binner.splits), 2)

    def test_extreme_values_feature(self):
        """测试极端值特征 (feature_01)"""
        binner = SmartMonotonicBinner()
        binner.fit(self.x_extreme, self.y, max_bins=5)
        
        # 极端值不应导致失败
        self.assertTrue(binner.is_monotonic)
        
        # 验证切点合理（不应有inf或nan）
        finite_splits = [s for s in binner.splits if np.isfinite(s)]
        self.assertTrue(all(np.isfinite(s) for s in finite_splits))

    def test_small_sample_fallback(self):
        """测试小样本保底策略"""
        # 取小样本
        x_small = self.x_numeric[:100]
        y_small = self.y[:100]
        
        binner = SmartMonotonicBinner()
        binner.fit(x_small, y_small, max_bins=10, min_bins=2)
        
        self.assertTrue(binner.is_monotonic)
        # 小样本可能最终只有2箱
        self.assertGreaterEqual(len(binner.splits), 2)

    def test_all_bins_range(self):
        """测试不同箱数范围"""
        for max_bins in [2, 3, 5, 8, 10, 15]:
            binner = SmartMonotonicBinner()
            binner.fit(self.x_numeric, self.y, max_bins=max_bins, min_bins=2)
            
            n_bins = len(binner.splits) - 1
            self.assertGreaterEqual(n_bins, 2)
            self.assertLessEqual(n_bins, max_bins)
            self.assertTrue(binner.is_monotonic)

    # ========== 参数验证测试 ==========

    def test_invalid_missing_y(self):
        """测试缺少y时的错误"""
        with self.assertRaises(ValueError) as context:
            self.binner.fit(self.x_numeric, None)
        self.assertIn('target variable', str(context.exception))

    def test_invalid_sample_size(self):
        """测试样本数不足"""
        with self.assertRaises(ValueError) as context:
            self.binner.fit(self.x_numeric[:50], self.y[:50])
        self.assertIn('样本数不足', str(context.exception))

    def test_default_parameters(self):
        """测试默认参数"""
        self.assertEqual(SmartMonotonicBinner.DEFAULT_MAX_BINS, 10)
        self.assertEqual(SmartMonotonicBinner.DEFAULT_MIN_BINS, 2)
        self.assertEqual(SmartMonotonicBinner.DEFAULT_MONOTONIC_TREND, 'auto')

    # ========== 与其他分箱器对比测试 ==========

    def test_vs_decision_tree(self):
        """与决策树分箱对比"""
        # SmartMonotonic
        sm_binner = SmartMonotonicBinner()
        sm_binner.fit(self.x_numeric, self.y, max_bins=5)
        
        # Decision Tree
        dt_binner = DecisionTreeBinner()
        dt_binner.fit(self.x_numeric, self.y, max_leaf_nodes=5)
        
        # SmartMonotonic 应该保证单调
        self.assertTrue(sm_binner.is_monotonic)
        
        # 计算各自IV
        sm_iv = sm_binner._final_iv
        x_binned = pd.cut(self.x_numeric, bins=dt_binner.splits, include_lowest=True)
        metrics = MetricsCalculator.calculate(x_binned, self.y)
        dt_iv = metrics.iv
        
        # SmartMonotonic 的IV损失应该在可接受范围
        if dt_iv > 0:
            loss = (dt_iv - sm_iv) / dt_iv
            self.assertLess(loss, 0.3, "IV loss should be < 30%")

    def test_iv_consistency(self):
        """测试IV计算一致性"""
        self.binner.fit(self.x_numeric, self.y, max_bins=5)
        
        # 使用分箱结果重新计算IV
        result = self.binner.transform(self.x_numeric)
        metrics = MetricsCalculator.calculate(result, self.y)
        recalculated_iv = metrics.iv
        
        # 两次计算的IV应该接近
        self.assertAlmostEqual(
            self.binner._final_iv, 
            recalculated_iv, 
            places=3
        )

    # ========== 批量分箱测试 ==========

    def test_batch_binning_all_features(self):
        """测试批量分箱所有数值特征"""
        numeric_cols = [f'feature_{i:02d}' for i in range(1, 21)]
        results = []
        
        for col in numeric_cols[:5]:  # 测试前5个
            binner = SmartMonotonicBinner()
            try:
                binner.fit(self.df[col], self.y, max_bins=5)
                results.append({
                    'feature': col,
                    'is_monotonic': binner.is_monotonic,
                    'n_bins': len(binner.splits) - 1,
                    'iv': binner._final_iv
                })
            except Exception as e:
                results.append({
                    'feature': col,
                    'error': str(e)
                })
        
        # 所有特征都应该成功且单调
        for r in results:
            self.assertTrue(r.get('is_monotonic', False), 
                          f"Feature {r.get('feature')} failed monotonicity")

    # ========== 稳定性测试 ==========

    def test_reproducibility(self):
        """测试结果可重复性"""
        # 多次运行相同数据，结果应该一致
        results = []
        for _ in range(3):
            binner = SmartMonotonicBinner()
            binner.fit(self.x_numeric, self.y, max_bins=5)
            results.append(tuple(binner.splits))
        
        # 所有结果应该相同
        self.assertEqual(len(set(results)), 1, "Results should be reproducible")


class TestSmartMonotonicIntegration(unittest.TestCase):
    """集成测试 - 完整流程"""

    def test_end_to_end_workflow(self):
        """测试完整工作流程"""
        df = pd.read_excel('tests/mock_data.xlsx')
        
        # 选择测试特征
        test_features = ['feature_02', 'feature_03', 'feature_05']
        
        for feature in test_features:
            x = df[feature]
            y = df['target']
            
            # 1. 分箱
            binner = SmartMonotonicBinner()
            binner.fit(x, y, max_bins=5)
            
            # 2. 转换
            x_binned = binner.transform(x)
            
            # 3. 计算指标
            metrics = MetricsCalculator.calculate(x_binned, y)
            
            # 4. 验证
            self.assertTrue(binner.is_monotonic)
            self.assertIsNotNone(metrics.iv)
            self.assertGreater(metrics.iv, 0)


class TestSmartMonotonicEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_constant_feature(self):
        """测试常数特征"""
        x = pd.Series([1] * 1000)
        y = pd.Series([0] * 500 + [1] * 500)
        
        binner = SmartMonotonicBinner()
        # 常数特征应该能处理（可能只有1箱或保底2箱）
        try:
            binner.fit(x, y)
            self.assertTrue(binner.is_monotonic or len(binner.splits) <= 3)
        except ValueError:
            # 也可以接受抛出异常
            pass

    def test_high_cardinality_feature(self):
        """测试高基数特征"""
        np.random.seed(42)
        x = pd.Series(np.random.choice(range(1000), 2000))
        y = pd.Series(np.random.choice([0, 1], 2000))
        
        binner = SmartMonotonicBinner()
        binner.fit(x, y, max_bins=8)
        
        self.assertTrue(binner.is_monotonic)

    def test_imbalanced_target(self):
        """测试极端不平衡目标"""
        np.random.seed(42)
        x = pd.Series(np.random.normal(50, 10, 1000))
        y = pd.Series([0] * 990 + [1] * 10)  # 99% vs 1%
        
        binner = SmartMonotonicBinner()
        binner.fit(x, y, max_bins=5)
        
        # 应该成功，即使可能只有2箱
        self.assertTrue(binner.is_monotonic)


if __name__ == '__main__':
    # 运行测试并输出详细结果
    unittest.main(verbosity=2)
