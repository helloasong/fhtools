import os
import shutil
import unittest
from tempfile import mkdtemp

from src.controllers.project_controller import ProjectController


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp(prefix="fhtools_it_")
        self.ctrl = ProjectController()
        # 使用已有的模拟数据
        data_path = os.path.abspath("tests/mock_data.xlsx")
        self.ctrl.create_new_project("it_project", data_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_end_to_end_flow(self):
        # 1. 选择三个特征并执行分箱
        features = self.ctrl.state.feature_cols[:3]
        methods = ["equal_freq", "decision_tree", "chi_merge"]
        for feat, method in zip(features, methods):
            if method == "equal_freq":
                self.ctrl.run_binning(
                    feat,
                    method=method,
                    n_bins=5,
                    boundary_precision_mode="decimal",
                    boundary_precision_digits=1,
                )
            elif method == "decision_tree":
                self.ctrl.run_binning(feat, method=method, max_leaf_nodes=4)
            else:
                self.ctrl.run_binning(feat, method=method, max_bins=4, initial_bins=64)

        # 2. 手动调整其中一个特征的切点
        feat0 = features[0]
        cfg0 = self.ctrl.state.binning_configs[feat0]
        self.assertEqual(cfg0.params.get("boundary_precision_mode"), "auto")
        self.assertEqual(cfg0.params.get("boundary_precision_digits"), 0)

        self.ctrl.run_binning(
            feat0,
            method="equal_freq",
            n_bins=5,
            boundary_precision_mode="decimal",
            boundary_precision_digits=1,
        )
        cfg0 = self.ctrl.state.binning_configs[feat0]
        self.assertEqual(cfg0.params.get("boundary_precision_mode"), "decimal")
        self.assertEqual(cfg0.params.get("boundary_precision_digits"), 1)

        splits = self.ctrl.state.binning_configs[feat0].splits
        # 在中间增加一个切点（如均值附近）
        if len(splits) > 2:
            mid = (splits[1] + splits[-2]) / 2 if all(map(lambda v: abs(v) != float('inf'), splits[1:-1])) else 0.0
            new_splits = [s for s in splits if abs(s) != float('inf')] + [mid]
            new_splits.sort()
            # 重新补全 inf
            new_splits = [-float('inf')] + new_splits + [float('inf')]
            self.ctrl.update_splits(feat0, new_splits)
            cfg0 = self.ctrl.state.binning_configs[feat0]
            self.assertEqual(cfg0.params.get("boundary_precision_mode"), "decimal")
            self.assertEqual(cfg0.params.get("boundary_precision_digits"), 1)

        # 3. 导出 Excel 与 Python
        excel_path = self.ctrl.export_excel_report(self.tmpdir)
        py_path = self.ctrl.export_python_rules(self.tmpdir)

        self.assertTrue(os.path.exists(excel_path))
        self.assertTrue(os.path.exists(py_path))

        # 4. 验证 Python 文件包含 woe 列生成
        with open(py_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def transform(df", content)
        self.assertIn("woe_", content)


if __name__ == "__main__":
    unittest.main()
