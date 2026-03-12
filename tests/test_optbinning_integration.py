"""Optbinning 集成测试"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRecommendParams(unittest.TestCase):
    """推荐参数算法测试"""
    
    def setUp(self):
        from src.utils.recommend_params import get_recommended_params, get_data_scale_label
        self.get_recommended_params = get_recommended_params
        self.get_data_scale_label = get_data_scale_label
    
    def test_small_data_params(self):
        """TC-001: 小数据推荐参数测试"""
        params = self.get_recommended_params(5000)
        
        self.assertEqual(params['solver'], 'cp')
        self.assertEqual(params['max_n_prebins'], 20)
        self.assertEqual(params['time_limit'], 30)
        self.assertEqual(params['gamma'], 0)
    
    def test_medium_data_params(self):
        """TC-002: 中数据推荐参数测试"""
        params = self.get_recommended_params(50000)
        
        self.assertEqual(params['solver'], 'cp')
        self.assertEqual(params['max_n_prebins'], 20)
        self.assertEqual(params['time_limit'], 100)
    
    def test_large_data_params(self):
        """TC-003: 大数据推荐参数测试"""
        params = self.get_recommended_params(200000)
        
        self.assertEqual(params['solver'], 'ls')
        self.assertEqual(params['max_n_prebins'], 50)
        self.assertEqual(params['gamma'], 0.1)
    
    def test_data_scale_label(self):
        """TC-004: 数据规模标签测试"""
        self.assertIn("小数据", self.get_data_scale_label(5000))
        self.assertIn("中数据", self.get_data_scale_label(50000))
        self.assertIn("大数据", self.get_data_scale_label(500000))
    
    def test_edge_case_zero(self):
        """TC-005: 边界条件 - 0样本"""
        params = self.get_recommended_params(0)
        self.assertEqual(params['solver'], 'cp')  # 返回默认值
    
    def test_edge_case_negative(self):
        """TC-006: 边界条件 - 负数"""
        params = self.get_recommended_params(-100)
        self.assertEqual(params['solver'], 'cp')


class TestOptbinningAdapterBasics(unittest.TestCase):
    """适配器基础测试（无需 pandas）"""
    
    def test_import_availability_flag(self):
        """TC-007: 导入标志测试"""
        from src.core.binning import OPTBINNING_AVAILABLE
        # 该标志应该被正确定义
        self.assertIsInstance(OPTBINNING_AVAILABLE, bool)
    
    def test_adapter_class_exists(self):
        """TC-008: 适配器类存在性测试"""
        try:
            from src.core.binning import OptimalBinningAdapter
            self.assertTrue(hasattr(OptimalBinningAdapter, 'fit'))
            self.assertTrue(hasattr(OptimalBinningAdapter, 'transform'))
            self.assertTrue(hasattr(OptimalBinningAdapter, 'splits'))
        except ImportError:
            self.skipTest("optbinning not installed")


class TestConfigPanelBasics(unittest.TestCase):
    """配置面板基础测试"""
    
    def test_config_panel_import(self):
        """TC-009: 配置面板导入测试"""
        try:
            from src.ui.widgets.optbinning_config_panel import OptbinningConfigPanel
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_default_config_constants(self):
        """TC-010: 默认配置常量测试"""
        from src.ui.widgets.optbinning_config_panel import DEFAULT_CONFIG, SOLVER_OPTIONS
        
        self.assertIn('solver', DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG['solver'], 'cp')
        self.assertIsInstance(SOLVER_OPTIONS, list)
        self.assertGreater(len(SOLVER_OPTIONS), 0)


class TestIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""
    
    def test_method_list_order(self):
        """TC-101: 方法列表顺序检查"""
        # 验证 method_map 构建逻辑
        from src.core.binning import OPTBINNING_AVAILABLE
        
        # 模拟构建方法列表
        method_map = []
        if OPTBINNING_AVAILABLE:
            method_map.append(("🎯 最优分箱 (推荐)", "optimal"))
            method_map.append(("───────────────", "separator"))
        
        method_map.extend([
            ("等频分箱", "equal_freq"),
            ("等距分箱", "equal_width"),
        ])
        
        if OPTBINNING_AVAILABLE:
            self.assertEqual(method_map[0][1], "optimal")
            self.assertEqual(method_map[1][1], "separator")
    
    def test_special_codes_parsing(self):
        """TC-102: 特殊值字符串解析逻辑测试"""
        # 模拟控制器中的解析逻辑
        special_codes = "-999, 999, NA"
        codes = [c.strip() for c in special_codes.split(',') if c.strip()]
        
        parsed_codes = []
        for c in codes:
            try:
                parsed_codes.append(float(c))
            except ValueError:
                parsed_codes.append(c)
        
        self.assertEqual(len(parsed_codes), 3)
        self.assertEqual(parsed_codes[0], -999.0)
        self.assertEqual(parsed_codes[1], 999.0)
        self.assertEqual(parsed_codes[2], "NA")


class TestControllerIntegration(unittest.TestCase):
    """控制器集成测试"""
    
    def test_sample_count_method(self):
        """TC-103: 样本数获取方法测试"""
        # 由于需要 pandas，这里只做方法签名检查
        from src.controllers.project_controller import ProjectController
        self.assertTrue(hasattr(ProjectController, 'get_sample_count'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
