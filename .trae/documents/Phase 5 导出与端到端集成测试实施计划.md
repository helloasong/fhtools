## 目标
- 完成分箱结果的导出（Excel 报告、Python 规则代码）。
- 增强持久化与快照恢复能力（保存分箱快照并可重新加载）。
- 完成端到端集成测试，覆盖“导入→EDA→分箱→微调→导出”的主流程。

## 模块与文件
- Services:
  - `src/services/export_service.py`: 导出实现（Excel、Python、可选SQL）。
- UI:
  - `src/ui/views/export_view.py`: 导出视图（选择导出内容与路径，进度提示）。
- Controller:
  - 扩展 `ProjectController`: 聚合分箱结果为统一 DataFrame、触发导出函数、快照保存/加载。
- Workers:
  - `src/utils/workers.py`: QThread 封装（导出与大数据计算异步化）。
- Tests:
  - `tests/test_integration.py`: 端到端集成测试（无UI，直调Controller与Service）。

## 导出功能实现
### Excel 报告
- 汇总表（Summary sheet）：
  - 列：`feature`, `bin_range`, `count`, `percent`, `bad_count`, `bad_rate`, `good_count`, `good_rate`, `woe`, `iv`, `lift`。
  - 每个变量一个子表（Sheets：按 `feature` 命名），包含该变量的所有箱明细。
- 技术要点：
  - 使用 `pandas.ExcelWriter(engine='openpyxl')` 写多 sheet。
  - 对百万级数据，避免写原始明细，只写分箱统计。
  - 所有数值格式化（百分比、保留小数）。

### Python 规则代码
- 生成 `scorecard_transform.py`：
  - 提供 `transform(df)`：对输入 DataFrame 按快照中的切点进行分箱并生成对应的 WOE 列（`woe_<feature>`）。
  - 规则基于 `ProjectState.binning_configs` 与 `splits`。
  - 对缺失值根据配置策略处理（忽略/单独成箱/归并）。

### 可选：SQL 导出（占位）
- 生成每个变量的 CASE WHEN 规则片段（后续迭代）。

## 快照与持久化增强
- 快照保存：
  - 在项目目录 `snapshots/` 写入 `snapshot_<timestamp>.fht`（pickle的 `ProjectState`）。
  - 内容包含：目标列、特征列、每个特征的 `BinningConfig` 与最新 `BinningMetrics`。
- 快照加载：
  - 导出视图提供“加载快照”入口；
  - Controller 提供 `load_snapshot(file_path)` 将状态覆盖并刷新视图。
- 退出保护：
  - Controller 维护 `dirty` 标记；UI关闭时若 `dirty=True` 弹窗提示保存。

## UI 实现
### ExportView
- 控件：
  - 导出类型复选：`Excel 报告`、`Python 规则`（可扩展 `SQL`）。
  - 路径选择器：目标文件夹；
  - 选项：是否按变量分别生成Sheet、是否覆盖已有文件；
  - 进度条与状态提示（使用 `QThread`）。
- 行为：
  - 点击“导出”→ 启动 `Worker` 执行导出→ 完成后弹窗提示并打开文件夹。

## Controller 扩展
- `get_binning_summary_df()`：聚合所有特征的 `summary_table` 为一张汇总表，追加 `feature_name` 字段。
- `export_excel(dir_path)`：生成 `binning_report.xlsx`（包含 Summary 及每个特征Sheet）。
- `export_python(dir_path)`：生成 `scorecard_transform.py`。
- `save_snapshot()` / `load_snapshot()`：管理快照文件。

## 异步与性能
- 耗时任务（导出、计算）统一通过 `QThread` 执行；
- 进度反馈：`QProgressBar` 显示不定进度或分阶段进度；
- 避免UI阻塞：禁止在主线程读写大文件或跑统计。

## 集成测试（tests/test_integration.py）
- 场景：
  1. 使用 `tests/mock_data.xlsx` 创建新项目并加载数据；
  2. 自动识别目标与特征；
  3. 对 3 个特征分别运行等频/决策树/卡方分箱；
  4. 手动调整某个特征的切点后重算；
  5. 导出 Excel 报告与 Python 规则；
  6. 断言导出文件存在且结构正确（Summary列齐全，Python文件包含对应特征规则）。
- 验收：
  - 测试全部通过；
  - 运行时无未捕获异常；
  - 报告与代码文件大小与内容合理。

## 里程碑与交付
- 里程碑 A：完成 `ExportService` 与 `ExportView`，可导出Excel与Python。
- 里程碑 B：完成快照保存/加载与退出保护。
- 里程碑 C：完成 `tests/test_integration.py` 并通过。

## 后续增强（规划）
- 数据预览替换为 `QTableView + QAbstractTableModel` 支持百万级虚拟滚动；
- 双轴图（样本数/Bad Rate）与悬停详细提示；
- 算法建议引擎：基于分布与相关性自动推荐分箱法；
- SQL 导出、CLI 批处理模式。