# Optbinning 集成开发计划

> 版本: v1.0  
> 日期: 2026-03-11  
> 目标: 完成 Phase 1 MVP 开发

---

## 1. 开发阶段划分

### Phase 1.1: 基础组件 (可并行)
- **Task 1**: 适配器实现
- **Task 2**: 推荐参数算法
- **Task 3**: 配置面板组件

### Phase 1.2: 集成与联调 (依赖 1.1)
- **Task 4**: 控制器集成
- **Task 5**: 视图层改造

### Phase 1.3: 测试与验收
- **Task 6**: 单元测试
- **Task 7**: 集成测试
- **Task 8**: 验收测试

---

## 2. 任务详细规划

### Task 1: 适配器实现 (optbinning_adapter.py)
**目标**: 将 OptimalBinning 包装为符合 BaseBinner 接口
**预计耗时**: 2h
**验收标准**:
- [ ] 继承 BaseBinner
- [ ] 实现 fit() 方法，支持所有核心参数
- [ ] 实现 transform() 方法
- [ ] splits 属性正确返回切点
- [ ] 异常处理：optbinning 未安装时友好降级

**核心参数映射**:
| 内部参数 | Optbinning 参数 | 默认值 |
|----------|-----------------|--------|
| solver | solver | 'cp' |
| divergence | divergence | 'iv' |
| monotonic_trend | monotonic_trend | 'auto' |
| max_n_bins | max_n_bins | 10 |
| min_n_bins | min_n_bins | 2 |
| max_n_prebins | max_n_prebins | 20 |
| min_prebin_size | min_prebin_size | 0.05 |
| special_codes | special_codes | None |
| time_limit | time_limit | 100 |

---

### Task 2: 推荐参数算法 (recommend_params.py)
**目标**: 根据数据规模推荐最优参数
**预计耗时**: 1h
**验收标准**:
- [ ] 支持 <1万 / 1-10万 / >10万 三档
- [ ] 返回完整的参数字典
- [ ] 包含求解器、预分箱数、箱大小、时间限制

**推荐逻辑**:
```python
def get_recommended_params(n_samples):
    if n_samples < 10_000:
        return {...}  # 小数据配置
    elif n_samples < 100_000:
        return {...}  # 中数据配置
    else:
        return {...}  # 大数据配置
```

---

### Task 3: 配置面板组件 (optbinning_config_panel.py)
**目标**: 创建 Optbinning 专属配置面板
**预计耗时**: 3h
**验收标准**:
- [ ] 基础配置：求解器、目标、趋势、箱数范围(min-max)
- [ ] "⚡恢复推荐"按钮
- [ ] 点击按钮弹出确认对话框
- [ ] 所有参数有 Tooltip 提示
- [ ] 可获取当前配置字典

**UI 布局**:
```
┌────────────────────────────────────────┐
│ 求解器: [CP ▼]        目标: [IV ▼]     │
│ 单调性: [Auto ▼]      箱数: [2] - [10] │
│ 特殊值: [________]    [⚡恢复推荐]      │
└────────────────────────────────────────┘
```

---

### Task 4: 控制器集成 (project_controller.py)
**目标**: 注册 Optbinning 算法，支持新参数
**预计耗时**: 1.5h
**验收标准**:
- [ ] binners 字典添加 'optimal' -> OptimalBinningAdapter
- [ ] run_binning() 支持 Optbinning 参数传递
- [ ] 自动检测 optbinning 是否安装
- [ ] 未安装时从 binners 中移除

---

### Task 5: 视图层改造 (combined_view.py)
**目标**: 动态面板切换，默认选中 Optbinning
**预计耗时**: 2.5h
**验收标准**:
- [ ] method_map 更新顺序，"最优分箱"置顶
- [ ] 动态显示/隐藏配置面板
- [ ] 选择"最优分箱"显示新面板
- [ ] 选择传统方法显示原面板
- [ ] 运行按钮 loading 状态
- [ ] 切换方法时不丢失配置

**修改点**:
1. `init_ui()`: 添加 Optbinning 配置面板，使用 QStackedWidget
2. `on_method_changed()`: 切换显示的面板
3. `run_binning()`: 根据当前方法获取对应参数

---

### Task 6: 单元测试
**目标**: 核心组件单元测试
**预计耗时**: 2h
**测试文件**:
- tests/test_optbinning_adapter.py
- tests/test_recommend_params.py

**用例**:
- TC-001: 基础拟合测试
- TC-002: 带约束拟合测试
- TC-003: 转换测试
- TC-004: 求解器选择测试
- TC-005: 推荐参数正确性测试

---

### Task 7: 集成测试
**目标**: 端到端流程测试
**预计耗时**: 1.5h
**测试文件**: tests/test_optbinning_integration.py

**用例**:
- TC-101: 默认分箱方法检查
- TC-102: 配置面板切换测试
- TC-103: 恢复推荐值按钮测试
- TC-104: 端到端分箱测试
- TC-105: 依赖缺失处理测试

---

### Task 8: 验收测试
**目标**: 按确认项目清单逐项验证
**预计耗时**: 1h
**验收清单**: 见 PRD 9.1 Phase 1 功能确认

---

## 3. 并行策略

```
Phase 1.1 (可并行):
  ├── Task 1: 适配器实现 ─────┐
  ├── Task 2: 推荐算法 ───────┤──> Phase 1.2
  └── Task 3: 配置面板 ───────┘

Phase 1.2 (依赖 1.1):
  ├── Task 4: 控制器集成
  └── Task 5: 视图层改造

Phase 1.3:
  ├── Task 6: 单元测试
  ├── Task 7: 集成测试
  └── Task 8: 验收测试
```

---

## 4. 文件清单

### 新建文件
```
src/core/binning/optbinning_adapter.py       # Task 1
src/utils/recommend_params.py                # Task 2
src/ui/widgets/optbinning_config_panel.py    # Task 3
tests/test_optbinning_adapter.py             # Task 6
tests/test_recommend_params.py               # Task 6
tests/test_optbinning_integration.py         # Task 7
```

### 修改文件
```
src/controllers/project_controller.py        # Task 4
src/ui/views/combined_view.py                # Task 5
```

---

## 5. 风险提示

| 风险 | 缓解措施 |
|------|----------|
| optbinning 安装复杂 | 作为可选依赖，提供降级方案 |
| 求解器性能问题 | 默认使用 CP，大数据自动切换 LS |
| UI 布局冲突 | 使用 QStackedWidget 隔离面板 |
| 参数传递错误 | 统一使用字典传递，增加校验 |

---

## 6. 验收标准 (Phase 1)

- [x] 最优分箱设为默认选项
- [x] 原有6种算法保留并可用
- [x] 动态面板切换正常
- [x] 求解器/目标/趋势/箱数配置正常
- [x] 一键恢复推荐值按钮工作
- [x] 推荐值根据样本量正确计算
- [x] 基础参数提示(Tooltip)
- [x] 运行按钮loading状态
- [x] 单变量分箱结果正确
- [x] 依赖缺失处理正确
