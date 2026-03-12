# SmartMonotonicBinner 产品需求文档 (PRD)

**版本**: v1.0  
**日期**: 2026-03-12  
**作者**: AI Assistant  
**状态**: 设计中

---

## 1. 背景与目标

### 1.1 问题背景

当前风控建模中，分箱(binning)是变量处理的核心环节。但现有方案面临以下痛点：

| 问题 | 影响 |
|-----|------|
| **optbinning追求最优解** | 经常无解(70%有解率)，需人工反复调参 |
| **手工分箱效率低** | 每个变量需人工检查单调性，耗时耗力 |
| **业务可解释性要求高** | 强制单调性是监管和业务的硬性要求 |
| **零人工干预需求** | 批量处理数百变量时，无法逐个微调 |

### 1.2 核心目标

**目标**: 开发一个100%有解、最大化自动化、最小化人工干预的智能单调分箱器

**关键指标**:
- ✅ **有解率**: 100%（保底2分箱）
- ✅ **单调达成率**: >90%（多层策略+后处理）
- ✅ **IV损失**: <10%（智能合并而非强制）
- ✅ **零人工干预**: 全自动处理，无需逐个调参

### 1.3 用户场景

**场景1**: 批量分箱500个变量
> "我要一次性跑完所有变量，不想因为几个变量不单调就卡住"

**场景2**: 监管报送
> "监管要求所有入模变量必须单调，不能有风险不可解释的波动"

**场景3**: 快速迭代
> "模型要每周迭代，没时间逐个检查变量单调性"

---

## 2. 功能需求

### 2.1 基础功能

| 需求编号 | 功能 | 优先级 | 说明 |
|---------|------|-------|------|
| FR-001 | 最大/最小箱数控制 | P0 | 用户可设置max_bins/min_bins |
| FR-002 | 单调趋势指定 | P0 | auto/ascending/descending |
| FR-003 | IV损失容忍度 | P1 | 默认10%，可配置 |
| FR-004 | 每箱最小样本数 | P1 | 默认50，防止过拟合 |

### 2.2 高级功能

| 需求编号 | 功能 | 优先级 | 说明 |
|---------|------|-------|------|
| FR-005 | 调整方法选择 | P1 | auto/merge/pava/none |
| FR-006 | 智能策略选择 | P2 | 根据数据特征自动选择最佳策略 |
| FR-007 | 切点微调优化 | P2 | 局部搜索优化切点位置 |
| FR-008 | 质量评估报告 | P2 | 输出质量评分和处理流程 |

### 2.3 保底机制（100%有解保证）

```
策略层级（从高到低尝试）：

Level 1: 约束决策树分箱
    ↓ 失败或IV损失过大
Level 2: 自适应决策树（减少箱数）
    ↓ 失败
Level 3: 强制单调合并（最佳IV损失）
    ↓ 失败
Level 4: PAVA平滑（保持箱数）
    ↓ 失败
Level 5: 保底2分箱（中位数切分）← 100%成功
```

---

## 3. 技术方案详细设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    SmartMonotonicBinner                      │
├─────────────────────────────────────────────────────────────┤
│  1. 数据预分析 (_analyze_data)                               │
│     ├── 样本数、分布、异常值检测                             │
│     ├── 天然相关性分析                                       │
│     └── 输出数据特征报告                                     │
├─────────────────────────────────────────────────────────────┤
│  2. 策略选择 (_select_strategy)                              │
│     ├── 小样本 → simple_quantile                            │
│     ├── 天然单调+大样本 → constrained_tree                  │
│     ├── 有异常值 → robust_tree                              │
│     └── 默认 → adaptive_tree                                │
├─────────────────────────────────────────────────────────────┤
│  3. 分箱执行 (_execute_strategy)                             │
│     ├── 主策略尝试                                           │
│     ├── 减少箱数重试 (max_bins → max_bins/2 → 3)            │
│     ├── 强制单调合并                                         │
│     └── 保底方案                                             │
├─────────────────────────────────────────────────────────────┤
│  4. 后处理优化 (_post_process)                               │
│     ├── 切点微调优化 (_optimize_cutpoints)                  │
│     │   └── 局部搜索±10%范围                                │
│     └── PAVA平滑 (_smooth_bad_rates)                        │
│         └── 保序回归算法                                     │
├─────────────────────────────────────────────────────────────┤
│  5. 质量验证 (_validate_result)                              │
│     ├── 单调性检查                                           │
│     ├── 每箱最小样本检查                                     │
│     └── 综合质量评分                                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心算法详解

#### 3.2.1 强制单调合并（最佳IV损失版）

**问题**: 贪婪合并首个违反点可能不是最优解

**改进**: 每次选择IV损失最小的合并对

```python
def _find_best_merge(self, bin_stats, target_trend):
    """
    找到最佳合并点（最小化IV损失）
    
    算法:
    1. 遍历所有相邻箱对 (i, i+1)
    2. 模拟合并，计算合并后的bad_rate
    3. 计算IV损失 = |原rate1 - 新rate| + |原rate2 - 新rate|
    4. 检查合并后是否改善单调性
    5. 返回IV损失最小的可行合并点
    """
    best_idx = 0
    best_iv_loss = float('inf')
    
    for i in range(len(bin_stats) - 1):
        # 模拟合并
        merged_bad_rate = (
            bin_stats.iloc[i]['events'] + bin_stats.iloc[i+1]['events']
        ) / (
            bin_stats.iloc[i]['count'] + bin_stats.iloc[i+1]['count']
        )
        
        # 计算IV损失
        iv_loss = (
            abs(merged_bad_rate - bin_stats.iloc[i]['bad_rate']) +
            abs(merged_bad_rate - bin_stats.iloc[i+1]['bad_rate'])
        )
        
        # 检查是否改善单调性
        temp_rates = bin_stats['bad_rate'].copy()
        temp_rates.iloc[i] = merged_bad_rate
        temp_rates = temp_rates.drop(temp_rates.index[i+1])
        
        if self._is_monotonic_series(temp_rates, target_trend):
            if iv_loss < best_iv_loss:
                best_iv_loss = iv_loss
                best_idx = i
    
    return best_idx
```

#### 3.2.2 切点微调优化

**目的**: 在不减少箱数的前提下，通过微调切点位置改善单调性

```python
def _optimize_cutpoints(self, x, y, splits):
    """
    微调切点位置优化单调性
    
    算法:
    1. 对每个内部切点（第1个到倒数第2个）
    2. 在切点±10%范围内进行线性搜索（11个点）
    3. 评估每个候选切点的单调性评分
    4. 选择评分最高的切点组合
    """
    best_splits = splits.copy()
    best_score = self._calculate_monotonic_score(x, y, splits)
    
    for i in range(1, len(splits) - 1):
        original = splits[i]
        search_range = abs(original) * 0.1 if original != 0 else 0.1
        
        for delta in np.linspace(-search_range, search_range, 11):
            if delta == 0:
                continue
            
            test_splits = splits.copy()
            test_splits[i] = original + delta
            
            # 确保有序性
            if not all(test_splits[j] <= test_splits[j+1] 
                      for j in range(len(test_splits)-1)):
                continue
            
            score = self._calculate_monotonic_score(x, y, test_splits)
            if score > best_score:
                best_score = score
                best_splits = test_splits
    
    return self._evaluate_splits(x, y, best_splits)
```

#### 3.2.3 PAVA平滑算法（保序回归）

**目的**: 保持箱数不变，通过调整bad rate使其单调

```python
def _pava_smooth(self, values):
    """
    Pool Adjacent Violators Algorithm (PAVA)
    
    算法步骤:
    1. 从左到右遍历序列
    2. 发现违反单调性时，合并相邻两点（取平均）
    3. 向后传播合并（检查前面的点是否也违反）
    4. 重复直到整个序列单调
    
    特性:
    - 数学保证收敛
    - 最小二乘意义下的最优单调逼近
    """
    n = len(values)
    smoothed = values.copy()
    
    i = 0
    while i < n - 1:
        if smoothed[i] > smoothed[i + 1]:  # 违反递增
            # 合并为平均
            avg = (smoothed[i] + smoothed[i + 1]) / 2
            smoothed[i] = avg
            smoothed[i + 1] = avg
            
            # 向后传播
            j = i
            while j > 0 and smoothed[j - 1] > smoothed[j]:
                avg = (smoothed[j - 1] + smoothed[j]) / 2
                smoothed[j - 1] = avg
                smoothed[j] = avg
                j -= 1
        i += 1
    
    return smoothed
```

### 3.3 调整方法说明

| 方法 | 算法 | 特点 | 适用场景 |
|-----|------|-----|---------|
| **auto** | 智能选择 | 优先merge，IV损失大则用pava | **默认推荐** |
| **merge** | 最佳IV损失合并 | 箱数可能减少，IV损失可控 | 追求低IV损失 |
| **pava** | 保序回归 | 保持箱数，数学保证单调 | 必须保持箱数 |
| **none** | 仅检查 | 不调整，返回原始结果 | 分析对比用 |

### 3.4 质量评分体系

```python
def _quality_score(self, iv, is_mono, n_bins):
    """
    综合质量评分 (0-100)
    
    评分维度:
    - IV权重: 40分
        * >0.3: 40分 (强预测力)
        * 0.1-0.3: 30分 (中等)
        * 0.02-0.1: 20分 (弱)
        * <0.02: 0分 (几乎无预测力)
    
    - 单调性权重: 40分
        * 满足单调: 40分
        * 不满足: 0分
    
    - 箱数适中权重: 20分
        * 3-8箱: 20分 (最佳)
        * 2箱或>8箱: 10分 (可接受)
    """
    score = 0
    
    # IV评分
    if iv > 0.3:
        score += 40
    elif iv > 0.1:
        score += 30
    elif iv > 0.02:
        score += 20
    
    # 单调性评分
    if is_mono:
        score += 40
    
    # 箱数评分
    if 3 <= n_bins <= 8:
        score += 20
    elif n_bins >= 2:
        score += 10
    
    return score
```

---

## 4. 接口定义

### 4.1 类定义

```python
class SmartMonotonicBinner(BaseBinner):
    """
    智能单调分箱器
    
    参数:
        max_bins (int): 最大箱数，默认10
        min_bins (int): 最小箱数，默认2
        trend (str): 单调趋势，'auto'/'ascending'/'descending'，默认'auto'
        adjustment_method (str): 调整方法，'auto'/'merge'/'pava'/'none'，默认'auto'
        iv_tolerance (float): IV损失容忍度，默认0.1
        min_samples_per_bin (int): 每箱最小样本数，默认50
        min_iv_threshold (float): 最小IV阈值，默认0.02
    
    属性:
        splits (List[float]): 分箱切点
        iv (float): IV值
        is_monotonic (bool): 是否单调
        quality_score (int): 质量评分(0-100)
        adjustment_method (str): 实际使用的调整方法
        debug_info (List[str]): 处理流程日志
    """
    
    def __init__(self, max_bins=10, min_bins=2, trend='auto',
                 adjustment_method='auto', iv_tolerance=0.1,
                 min_samples_per_bin=50, min_iv_threshold=0.02):
        ...
    
    def fit(self, x: pd.Series, y: pd.Series) -> 'SmartMonotonicBinner':
        """拟合分箱器"""
        ...
    
    def transform(self, x: pd.Series) -> pd.Series:
        """应用分箱"""
        ...
    
    def get_debug_info(self) -> str:
        """获取处理流程日志"""
        ...
```

### 4.2 使用示例

```python
from src.core.binning.smart_monotonic import SmartMonotonicBinner

# 基础用法
binner = SmartMonotonicBinner(max_bins=8)
binner.fit(x, y)
print(f"分箱: {binner.splits}, IV: {binner.iv:.4f}")

# 高级用法
binner = SmartMonotonicBinner(
    max_bins=10,
    min_bins=3,
    trend='ascending',           # 强制递增
    adjustment_method='pava',    # 使用PAVA平滑
    iv_tolerance=0.05,           # 严格5% IV损失限制
    min_samples_per_bin=100      # 每箱至少100样本
)
binner.fit(x, y)

print(f"是否单调: {binner.is_monotonic}")
print(f"质量评分: {binner.quality_score}")
print(f"调整方法: {binner.adjustment_method}")
print(f"处理流程:\n{binner.get_debug_info()}")
```

---

## 5. 测试用例

### 5.1 功能测试

| 用例编号 | 场景 | 输入 | 期望输出 |
|---------|------|-----|---------|
| TC-001 | 天然单调数据 | feature_02 (强负相关) | 5箱，单调，IV>0.1 |
| TC-002 | 波动数据 | feature_01 (弱相关) | 3-5箱，单调，IV损失<10% |
| TC-003 | 小样本 | n=500 | 成功，箱数自动减少 |
| TC-004 | 有异常值 | 含极端值 | robust_tree策略，正常分箱 |
| TC-005 | 严格IV限制 | iv_tolerance=0.01 | 可能退到2箱，但满足约束 |
| TC-006 | 强制递增 | trend='ascending' | 严格递增，即使数据倾向递减 |
| TC-007 | 仅检查 | adjustment_method='none' | 不调整，返回原始单调性状态 |

### 5.2 性能测试

| 用例编号 | 场景 | 要求 |
|---------|------|-----|
| PT-001 | 单变量10万样本 | <1秒 |
| PT-002 | 批量100变量 | <30秒 |
| PT-003 | 内存占用 | <500MB |

### 5.3 稳定性测试

| 用例编号 | 场景 | 要求 |
|---------|------|-----|
| ST-001 | 随机数据100次 | 100%有解，>90%单调 |
| ST-002 | 常数特征 | 保底2箱，不崩溃 |
| ST-003 | 全缺失值 | 抛出清晰错误 |

---

## 6. UI集成需求

### 6.1 配置面板

```
分箱方法: [智能单调分箱 ▼]

基础配置:
  箱数: [5 ▲▼]  (2-20)
  单调趋势: [自动 ▼]  (自动/递增/递减)
  缺失值策略: [单独成箱 ▼]

高级配置 (可折叠):
  调整方法: [自动 ▼]  (自动/合并/PAVA/仅检查)
  IV容忍度: [10% ▲▼]  (0-50%)
  每箱最小样本: [50 ▲▼]

运行日志:
  [显示处理流程和调试信息]
```

### 6.2 结果展示

```
分箱结果:
  实际箱数: 5
  IV值: 0.1523
  是否单调: ✅ 是 (递增)
  调整方法: pava
  IV损失: 0.0%
  质量评分: 90/100
  
处理流程:
  1. 数据特征分析: 样本20000, 天然相关-0.27
  2. 选择策略: adaptive_tree
  3. 决策树分箱: 5箱，IV=0.1523
  4. 检查单调性: 不单调
  5. 尝试merge: IV损失15% > 容忍度10%
  6. 使用pava平滑: 成功，IV损失0%
  7. 最终验证通过
```

---

## 7. 实施计划

### 7.1 开发阶段

| 阶段 | 任务 | 工期 | 依赖 |
|-----|------|-----|------|
| Phase 1 | 核心框架重构 | 1天 | 无 |
| Phase 2 | 最佳合并算法 | 0.5天 | Phase 1 |
| Phase 3 | PAVA平滑完善 | 0.5天 | Phase 1 |
| Phase 4 | 切点微调优化 | 1天 | Phase 1 |
| Phase 5 | 数据预分析 | 0.5天 | 无 |
| Phase 6 | 策略选择器 | 0.5天 | Phase 5 |
| Phase 7 | UI集成 | 1天 | Phase 1-6 |
| Phase 8 | 测试完善 | 1天 | Phase 1-7 |

**总工期**: 6天

### 7.2 优先级划分

**P0（必须实现）**:
- [ ] 核心框架重构（_fit_merge, _fit_pava, _fit_auto）
- [ ] 最佳合并算法（最小IV损失）
- [ ] 基础参数支持（adjustment_method, iv_tolerance）

**P1（强烈建议）**:
- [ ] 切点微调优化
- [ ] PAVA平滑完善
- [ ] UI配置面板

**P2（锦上添花）**:
- [ ] 数据预分析
- [ ] 智能策略选择
- [ ] 质量评分展示

### 7.3 验收标准

- [ ] 23个单元测试全部通过
- [ ] mock数据20个变量，>90%单调且IV损失<10%
- [ ] 100次随机数据测试，100%有解
- [ ] 性能: 10万样本<1秒
- [ ] 代码审查通过

---

## 8. 附录

### 8.1 术语表

| 术语 | 说明 |
|-----|------|
| PAVA | Pool Adjacent Violators Algorithm，保序回归算法 |
| IV | Information Value，信息值，衡量变量预测力 |
| WOE | Weight of Evidence，证据权重 |
| Bad Rate | 坏样本率，每箱中y=1的比例 |
| 单调性 | bad rate随特征值递增或递减的趋势 |

### 8.2 参考资源

- [PAVA算法论文](https://en.wikipedia.org/wiki/Isotonic_regression)
- [评分卡分箱最佳实践](https://www.kdnuggets.com/2019/12/complete-guide-scorecard-development.html)
- [Optimal Binning理论](https://arxiv.org/abs/2001.08025)

---

**文档历史**:
- v1.0 (2026-03-12): 初稿
