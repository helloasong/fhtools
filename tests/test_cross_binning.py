"""
组合策略分析模块单元测试
"""

import unittest
import pandas as pd
import numpy as np

from src.core.cross_binning import (
    CrossBinningAnalyzer,
    CrossBinningFilters,
    CrossBinningResult,
    CrossBinningRule,
    CrossBinningHeatmapData,
)
from src.data.models import BinningConfig


class TestCrossBinningAnalyzer(unittest.TestCase):
    """测试组合策略分析器核心逻辑"""

    def setUp(self):
        """构造测试数据"""
        np.random.seed(42)
        self.n = 10000
        self.df = pd.DataFrame({
            'age': np.concatenate([
                np.random.randint(18, 30, self.n // 4),
                np.random.randint(30, 45, self.n // 4),
                np.random.randint(45, 60, self.n // 4),
                np.random.randint(60, 80, self.n // 4),
            ]),
            'income': np.concatenate([
                np.random.randint(2000, 5000, self.n // 4),
                np.random.randint(5000, 10000, self.n // 4),
                np.random.randint(10000, 15000, self.n // 4),
                np.random.randint(15000, 30000, self.n // 4),
            ]),
        })
        # 构造目标变量：年龄小+收入低 = 高违约率
        p = (
            ((self.df['age'] < 30) & (self.df['income'] < 5000)).astype(float) * 0.5 +
            ((self.df['age'] < 30) & (self.df['income'] >= 5000)).astype(float) * 0.15 +
            ((self.df['age'] >= 30) & (self.df['income'] < 5000)).astype(float) * 0.20 +
            ((self.df['age'] >= 30) & (self.df['income'] >= 5000)).astype(float) * 0.05
        )
        self.df['target'] = np.random.binomial(1, p)

        self.age_cfg = BinningConfig(
            method='equal_freq',
            splits=[-np.inf, 30, 45, 60, np.inf]
        )
        self.income_cfg = BinningConfig(
            method='equal_freq',
            splits=[-np.inf, 5000, 10000, 15000, np.inf]
        )
        self.configs = {'age': self.age_cfg, 'income': self.income_cfg}

    def test_two_variable_cross_basic(self):
        """TC-001: 两变量交叉基础功能"""
        filters = CrossBinningFilters(
            min_sample_rate=0.01,
            bad_rate_high_multiplier=1.5,
            bad_rate_low_multiplier=0.5,
            min_lift=1.0,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        self.assertIsInstance(result, CrossBinningResult)
        self.assertEqual(result.total_combinations, 16)  # 4×4
        self.assertEqual(result.feature_bin_counts, {'age': 4, 'income': 4})
        self.assertGreater(len(result.rules), 0)

    def test_three_variable_cross(self):
        """TC-002: 三变量交叉"""
        self.df['score'] = np.random.randint(300, 950, self.n)
        score_cfg = BinningConfig(
            method='equal_freq',
            splits=[-np.inf, 500, 700, np.inf]
        )
        configs3 = {**self.configs, 'score': score_cfg}

        filters = CrossBinningFilters(
            min_sample_rate=0.005,
            bad_rate_high_multiplier=1.2,
            bad_rate_low_multiplier=0.8,
            min_lift=1.0,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income', 'score'],
            configs=configs3,
            filters=filters,
        )

        self.assertEqual(result.total_combinations, 48)  # 4×4×3
        self.assertEqual(len(result.feature_names), 3)

    def test_filter_by_sample_rate(self):
        """TC-003: 样本占比筛选"""
        filters = CrossBinningFilters(
            min_sample_rate=0.30,  # 非常严格，只保留大样本组合
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.5,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        for rule in result.rules:
            self.assertGreaterEqual(rule.sample_rate, 0.30)

    def test_filter_by_bad_rate(self):
        """TC-004: 坏账率倍数筛选"""
        overall_bad_rate = self.df['target'].mean()

        filters = CrossBinningFilters(
            min_sample_rate=0.01,
            bad_rate_high_multiplier=2.0,
            bad_rate_low_multiplier=0.5,
            min_lift=1.0,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        for rule in result.rules:
            br = rule.bad_rate
            self.assertTrue(
                br >= overall_bad_rate * 2.0 or br <= overall_bad_rate * 0.5,
                f"规则 {rule.rule_id} 坏账率 {br:.2%} 不符合筛选条件"
            )

    def test_filter_by_lift(self):
        """TC-005: Lift 筛选"""
        filters = CrossBinningFilters(
            min_sample_rate=0.01,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=2.0,  # 只保留 Lift >= 2 的规则
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        for rule in result.rules:
            # 新逻辑：高风险 lift >= min_lift，优质客群 lift <= 1/min_lift
            self.assertTrue(
                rule.lift >= 2.0 or rule.lift <= 0.5,
                f"rule lift={rule.lift} 不满足 lift>=2.0 或 lift<=0.5"
            )

    def test_empty_result(self):
        """TC-006: 筛选条件严格导致空结果"""
        filters = CrossBinningFilters(
            min_sample_rate=0.90,  # 几乎不可能满足
            bad_rate_high_multiplier=10.0,
            bad_rate_low_multiplier=0.01,
            min_lift=10.0,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        self.assertEqual(result.filtered_combinations, 0)
        self.assertEqual(len(result.rules), 0)

    def test_combination_limit(self):
        """TC-007: 组合数超限拒绝"""
        # 构造一个会产生大量组合的场景
        for i in range(10):
            self.df[f'var_{i}'] = np.random.randint(0, 10, self.n)

        configs_many = {
            f'var_{i}': BinningConfig(
                method='equal_freq',
                splits=[-np.inf, 3, 6, 9, np.inf]
            )
            for i in range(10)
        }

        filters = CrossBinningFilters(max_combinations=100)

        with self.assertRaises(ValueError) as ctx:
            CrossBinningAnalyzer.analyze(
                df=self.df,
                target_col='target',
                features=[f'var_{i}' for i in range(6)],  # 6个变量，先触发数量限制
                configs={k: v for k, v in list(configs_many.items())[:6]},
                filters=filters,
            )

        self.assertIn("最多支持", str(ctx.exception))

    def test_single_variable_rejected(self):
        """TC-008: 单变量被拒绝"""
        filters = CrossBinningFilters()

        with self.assertRaises(ValueError) as ctx:
            CrossBinningAnalyzer.analyze(
                df=self.df,
                target_col='target',
                features=['age'],
                configs=self.configs,
                filters=filters,
            )

        self.assertIn("至少", str(ctx.exception))

    def test_unbinned_variable_rejected(self):
        """TC-009: 未分箱变量被拒绝"""
        filters = CrossBinningFilters()

        with self.assertRaises(ValueError) as ctx:
            CrossBinningAnalyzer.analyze(
                df=self.df,
                target_col='target',
                features=['age', 'not_binned'],
                configs=self.configs,
                filters=filters,
            )

        self.assertIn("未进行分箱", str(ctx.exception))

    def test_risk_level_classification(self):
        """TC-010: 风险等级自动标注"""
        overall_bad_rate = self.df['target'].mean()

        filters = CrossBinningFilters(
            min_sample_rate=0.005,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.1,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        for rule in result.rules:
            if rule.bad_rate >= overall_bad_rate * 3.0:
                self.assertEqual(rule.risk_level, 'extreme-high')
            elif rule.bad_rate >= overall_bad_rate * 2.0:
                self.assertEqual(rule.risk_level, 'high')
            elif rule.bad_rate <= overall_bad_rate * 0.5:
                self.assertEqual(rule.risk_level, 'low')

    def test_sort_by_options(self):
        """TC-011: 排序方式测试"""
        filters = CrossBinningFilters(
            min_sample_rate=0.005,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.1,
            sort_by='lift_desc',
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        if len(result.rules) >= 2:
            for i in range(len(result.rules) - 1):
                self.assertGreaterEqual(
                    result.rules[i].lift,
                    result.rules[i + 1].lift
                )

    def test_to_dataframe(self):
        """TC-012: 结果转 DataFrame"""
        filters = CrossBinningFilters(
            min_sample_rate=0.005,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.1,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        df = result.to_dataframe()
        self.assertIsInstance(df, pd.DataFrame)
        if not df.empty:
            self.assertIn('规则编号', df.columns)
            self.assertIn('组合条件', df.columns)
            self.assertIn('坏账率', df.columns)

    def test_heatmap_data_build(self):
        """TC-013: 热力图数据构建"""
        heatmap = CrossBinningAnalyzer.build_heatmap_data(
            df=self.df,
            target_col='target',
            feature_x='age',
            feature_y='income',
            config_x=self.age_cfg,
            config_y=self.income_cfg,
        )

        self.assertIsInstance(heatmap, CrossBinningHeatmapData)
        self.assertEqual(heatmap.feature_x, 'age')
        self.assertEqual(heatmap.feature_y, 'income')
        self.assertEqual(heatmap.bad_rate_matrix.shape, (4, 4))
        self.assertEqual(len(heatmap.x_labels), 4)
        self.assertEqual(len(heatmap.y_labels), 4)

    def test_missing_target_handling(self):
        """TC-014: 目标变量缺失值处理"""
        df_missing = self.df.copy()
        df_missing.loc[0:100, 'target'] = np.nan

        filters = CrossBinningFilters(
            min_sample_rate=0.01,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.1,
        )

        # 不应报错，缺失值会被自动过滤
        result = CrossBinningAnalyzer.analyze(
            df=df_missing,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
        )

        self.assertIsInstance(result, CrossBinningResult)

    def test_filtered_data_map(self):
        """TC-015: 过滤规则继承"""
        # 模拟过滤后的数据（只保留 age >= 30 的样本）
        filtered_df = self.df[self.df['age'] >= 30].copy()
        filtered_map = {'age': filtered_df, 'income': filtered_df}

        filters = CrossBinningFilters(
            min_sample_rate=0.01,
            bad_rate_high_multiplier=1.0,
            bad_rate_low_multiplier=1.0,
            min_lift=0.1,
        )

        result = CrossBinningAnalyzer.analyze(
            df=self.df,
            target_col='target',
            features=['age', 'income'],
            configs=self.configs,
            filters=filters,
            filtered_data_map=filtered_map,
        )

        # 过滤后的样本应少于原始样本
        total_samples = sum(r.sample_count for r in result.rules)
        self.assertLess(total_samples, len(self.df))


class TestCrossBinningFilters(unittest.TestCase):
    """测试筛选参数默认值"""

    def test_default_values(self):
        """TC-016: 默认参数值"""
        f = CrossBinningFilters()
        self.assertEqual(f.min_sample_rate, 0.005)
        self.assertEqual(f.bad_rate_high_multiplier, 2.0)
        self.assertEqual(f.bad_rate_low_multiplier, 0.5)
        self.assertEqual(f.min_lift, 1.0)
        self.assertEqual(f.sort_by, 'bad_rate_desc')
        self.assertEqual(f.max_combinations, 5000)
        self.assertEqual(f.show_all, False)


if __name__ == '__main__':
    unittest.main()
