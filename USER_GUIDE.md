# 风控数据分箱工具使用指南

## 安装与启动
- 创建并激活虚拟环境：`python3 -m venv venv && source venv/bin/activate`
- 安装依赖：`pip install -r requirements.txt`
- 启动应用：
  - 方式一（推荐）：`python -m src.ui.main_window`
  - 方式二：`python run.py`
  - 如果需要直接运行文件：`PYTHONPATH=. python src/ui/main_window.py`

## 使用流程
- 数据导入：在 "Data Import" 页选择 CSV/Excel/Parquet 文件，填写项目名并创建项目；右侧预览表支持大表浏览。
- 变量分析 (EDA)：在 "EDA & Selection" 页选择变量，查看基础统计与分布图，并参考智能分箱建议。
- 分箱与微调：在 "Binning & Tuning" 页选择分箱算法与箱数；可拖拽切点、右键增删，选择缺失值策略；悬停可查看箱详情，指标表实时更新。
- 导出：在 "Export" 页选择导出目录，导出 Excel 报告、Python 规则与 SQL 规则。
- 快照：关闭应用时如有未保存更改，自动提示保存快照至项目目录 `snapshots/`。

## 分箱算法
- 等频、等距：无监督基础分箱，支持自定义箱数。
- 决策树：基于信息熵寻找最优切点，支持最大叶子节点数。
- 卡方分箱：预分桶（默认 64）+相邻合并，提高性能与稳定性。
- Best-KS：在候选边界上贪心选择最大 KS 切点（支持箱数与最小样本约束）。

## 缺失值策略
- `separate`：缺失值单独成箱。
- `ignore`：忽略缺失值不参与统计。
- `merge`：将缺失值归并到 Bad Rate 最接近的箱（或指定目标箱）。

## 导出内容
- Excel 报告：`binning_report.xlsx`，包含 Summary 与每变量子表（范围、Count、Bad Rate、WOE、IV、Lift）。
- Python 规则：`scorecard_transform.py`，提供 `transform(df)`，为每变量生成 `woe_<feature>` 列，包含缺失策略处理。
- SQL 规则：`scorecard_rules.sql`，输出每变量 `CASE WHEN` 片段，与切点和缺失策略一致。

## 性能与并发
- 大数据计算与导出通过后台线程异步执行，UI 显示进度避免卡顿。
- 卡方与 Best-KS 默认启用预分桶（可在 UI 算法参数中调整）。

## 注意事项
- 目标变量需为二分类（0/1），并在导入后自动识别。
- 分箱切点调整后需点击确认或触发重算以更新指标。
- 导出规则与快照均基于当前分箱配置与缺失策略，确保一致性。
