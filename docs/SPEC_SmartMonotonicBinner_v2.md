# SmartMonotonicBinner v2 详细设计文档 (SPEC)

**版本**: v2.0  
**日期**: 2026-03-12

---

## 1. 架构设计

### 1.1 类结构

```python
class SmartMonotonicBinner(BaseBinner):
    # 类常量
    DEFAULT_MAX_BINS = 10
    DEFAULT_MIN_BINS = 2
    DEFAULT_MONOTONIC_TREND = 'auto'
    DEFAULT_ADJUSTMENT_METHOD = 'auto'
    DEFAULT_IV_TOLERANCE = 0.1
    DEFAULT_MIN_SAMPLES_PER_BIN = 50
    
    # 属性
    _is_monotonic: bool
    _adjustment_method: Optional[str]
    _adjustment_info: List[str]
    _original_iv: float
    _final_iv: float
    _splits: List[float]
    
    # 公共方法
    __init__()
    fit(x, y, **kwargs) -> SmartMonotonicBinner
    transform(x) -> pd.Series
    
    # 属性访问器
    is_monotonic -> bool
    adjustment_method -> Optional[str]
    adjustment_info -> List[str]
    iv_loss -> float
    splits -> List[float]
    
    # 私有方法 - 策略实现
    _fit_none(x, y, max_bins, min_bins, target_trend, min_samples_per_bin)
    _fit_merge(x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
    _fit_pava(x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
    _fit_auto(x, y, max_bins, min_bins, target_trend, iv_tolerance, min_samples_per_bin)
    
    # 私有方法 - 核心算法
    _decision_tree_binning(x, y, max_bins, min_samples_per_bin)
    _force_monotonic_merge(x, y, splits, target_trend, min_bins)
    _find_best_merge(bin_stats, target_trend)
    _pava_smooth(values)
    _smooth_bad_rates(x, y, splits, target_trend)
    _optimize_cutpoints(x, y, splits, target_trend)
    _calculate_monotonic_score(x, y, splits, target_trend)
    
    # 私有方法 - 工具
    _calculate_iv(x, y, splits)
    _check_monotonic(x, y, splits)
    _is_monotonic_list(values, trend)
    _determine_trend(bad_rates)
    _fallback_bins(x)
    _log(msg)
```

### 1.2 流程图

```
fit(x, y, **kwargs)
    │
    ├── 参数解析
    │   ├── max_bins, min_bins
    │   ├── monotonic_trend
    │   ├── adjustment_method
    │   ├── iv_tolerance
    │   └── min_samples_per_bin
    │
    ├── 确定 target_trend
    │   └── 如果 auto，则通过中位数二分判断
    │
    ├── 策略分发
    │   ├── adjustment_method == 'none' → _fit_none()
    │   ├── adjustment_method == 'merge' → _fit_merge()
    │   ├── adjustment_method == 'pava' → _fit_pava()
    │   └── adjustment_method == 'auto' → _fit_auto()
    │
    └── 返回 self


_fit_merge() / _fit_pava() / _fit_auto()
    │
    ├── for try_bins in range(max_bins, min_bins-1, -1):
    │   │
    │   ├── splits = _decision_tree_binning(try_bins)
    │   │
    │   ├── 检查是否已单调
    │   │   └── 是 → 返回结果
    │   │
    │   ├── 尝试调整
    │   │   ├── merge: _force_monotonic_merge()
    │   │   ├── pava: _pava_smooth() + _smooth_bad_rates()
    │   │   └── auto: 先merge，不行再pava
    │   │
    │   ├── 检查IV损失
    │   │   └── IV损失 <= tolerance → 返回结果
    │   │
    │   └── 继续尝试更少箱数
    │
    └── 保底 _fallback_bins()


_force_monotonic_merge()
    │
    ├── 细粒度分箱（如20箱）
    │
    ├── 计算每箱统计（count, events, bad_rate）
    │
    ├── while 不单调 且 箱数 > min_bins:
    │   │
    │   ├── _find_best_merge() 找到IV损失最小的合并点
    │   │
    │   └── 合并并更新统计
    │
    └── 返回最终 splits


_find_best_merge()
    │
    ├── best_idx = 0, best_iv_loss = inf
    │
    ├── for i in range(len(stats) - 1):
    │   │
    │   ├── 模拟合并 i 和 i+1
    │   │   └── merged_rate = (e1+e2)/(c1+c2)
    │   │
    │   ├── 计算IV损失
    │   │   └── iv_loss = |r1 - merged| + |r2 - merged|
    │   │
    │   ├── 检查合并后是否单调
    │   │   └── 是 且 iv_loss < best → 更新 best
    │   │
    │   └── 继续下一个
    │
    └── return best_idx


_optimize_cutpoints()
    │
    ├── best_splits = current, best_score = current_score
    │
    ├── for 每个内部切点 i:
    │   │
    │   ├── search_range = ±10%
    │   │
    │   ├── for delta in 线性搜索11个点:
    │   │   │
    │   │   ├── test_splits = 替换切点
    │   │   │
    │   │   ├── 确保有序性
    │   │   │
    │   │   ├── score = _calculate_monotonic_score()
    │   │   │
    │   │   └── score > best → 更新 best
    │   │
    │   └── 继续下一个切点
    │
    └── return best_splits


_pava_smooth(values)
    │
    ├── smoothed = values.copy()
    │
    ├── i = 0
    │
    ├── while i < n - 1:
    │   │
    │   ├── if 违反单调性 (smoothed[i] > smoothed[i+1]):
    │   │   │
    │   │   ├── avg = (smoothed[i] + smoothed[i+1]) / 2
    │   │   ├── smoothed[i] = avg
    │   │   ├── smoothed[i+1] = avg
    │   │   │
    │   │   └── j = i
    │   │       while j > 0 and 仍违反:
    │   │           avg = (smoothed[j-1] + smoothed[j]) / 2
    │   │           smoothed[j-1] = avg
    │   │           smoothed[j] = avg
    │   │           j -= 1
    │   │
    │   └── i += 1
    │
    └── return smoothed
```

---

## 2. 算法详解

### 2.1 最佳合并算法 (_find_best_merge)

**目标**: 每次合并不是贪婪地选第一个违反点，而是选择IV损失最小的合并对

**输入**:
- `bin_stats`: DataFrame，包含 count, events, bad_rate
- `target_trend`: 'ascending' 或 'descending'

**输出**: 最佳合并点的索引

**算法步骤**:

```python
def _find_best_merge(self, bin_stats, target_trend):
    best_idx = 0
    best_iv_loss = float('inf')
    
    for i in range(len(bin_stats) - 1):
        # 1. 模拟合并
        merged_count = bin_stats.iloc[i]['count'] + bin_stats.iloc[i+1]['count']
        merged_events = bin_stats.iloc[i]['events'] + bin_stats.iloc[i+1]['events']
        merged_rate = merged_events / merged_count
        
        # 2. 计算IV损失
        # IV ≈ Σ (bad_rate_diff) * log(odds_ratio)
        # 简化：使用 bad_rate 变化的绝对值和
        iv_loss = (
            abs(merged_rate - bin_stats.iloc[i]['bad_rate']) +
            abs(merged_rate - bin_stats.iloc[i+1]['bad_rate'])
        )
        
        # 3. 检查合并后是否单调
        temp_rates = bin_stats['bad_rate'].copy()
        temp_rates.iloc[i] = merged_rate
        temp_rates = temp_rates.drop(temp_rates.index[i+1])
        
        if self._is_monotonic_series(temp_rates, target_trend):
            if iv_loss < best_iv_loss:
                best_iv_loss = iv_loss
                best_idx = i
    
    return best_idx
```

**时间复杂度**: O(n²)，n为箱数（通常n<20，可接受）

### 2.2 切点微调算法 (_optimize_cutpoints)

**目标**: 在保持箱数不变的前提下，微调切点位置改善单调性

**输入**:
- x, y: 原始数据
- splits: 当前切点
- target_trend: 目标趋势

**输出**: 优化后的 splits

**关键设计决策**:
- 搜索范围: ±10%（经验值，平衡效果和性能）
- 搜索步数: 11个点（包含端点，步长=2%）
- 切点顺序保护: 确保单调不减

**算法步骤**:

```python
def _optimize_cutpoints(self, x, y, splits, target_trend):
    best_splits = list(splits)  # 复制
    best_score = self._calculate_monotonic_score(x, y, splits, target_trend)
    
    # 遍历每个内部切点
    for i in range(1, len(splits) - 1):
        original = splits[i]
        
        # 计算搜索范围
        if original == 0:
            search_range = 0.1
        else:
            search_range = abs(original) * 0.1
        
        # 线性搜索
        for delta in np.linspace(-search_range, search_range, 11):
            if abs(delta) < 1e-10:  # 跳过原点
                continue
            
            test_val = original + delta
            
            # 确保在前后切点之间
            if test_val <= splits[i-1] or test_val >= splits[i+1]:
                continue
            
            test_splits = splits.copy()
            test_splits[i] = test_val
            
            score = self._calculate_monotonic_score(x, y, test_splits, target_trend)
            
            if score > best_score:
                best_score = score
                best_splits = test_splits
    
    return best_splits
```

**单调性评分函数**:

```python
def _calculate_monotonic_score(self, x, y, splits, target_trend):
    """
    计算单调性评分 (0-100)
    
    评分维度:
    1. 单调程度 (60分): 违反单调的点数比例
    2. IV保留 (30分): 相对于原始IV的比例
    3. 箱数合理 (10分): 是否在合理范围内
    """
    try:
        x_binned = pd.cut(x, bins=splits, include_lowest=True)
        bad_rates = x_binned.groupby(x_binned, observed=False).apply(
            lambda g: y[g.index].mean()
        )
        
        score = 0
        
        # 1. 单调程度 (60分)
        violations = 0
        for i in range(len(bad_rates) - 1):
            if target_trend == 'ascending':
                if bad_rates.iloc[i] > bad_rates.iloc[i+1]:
                    violations += 1
            else:
                if bad_rates.iloc[i] < bad_rates.iloc[i+1]:
                    violations += 1
        
        mono_score = 60 * (1 - violations / (len(bad_rates) - 1))
        score += mono_score
        
        # 2. IV (30分) - 简化计算
        iv = self._calculate_iv(x, y, splits)
        if iv > 0.3:
            score += 30
        elif iv > 0.1:
            score += 20
        elif iv > 0.02:
            score += 10
        
        # 3. 箱数 (10分)
        n_bins = len(splits) - 1
        if 3 <= n_bins <= 8:
            score += 10
        elif n_bins >= 2:
            score += 5
        
        return score
    except:
        return 0
```

### 2.3 PAVA算法 (_pava_smooth)

**目标**: 实现保序回归，使序列单调同时最小化平方误差

**算法正确性**: 数学证明收敛，最小二乘最优

**复杂度**: O(n²) 最坏情况，O(n) 平均情况

**实现细节**:

```python
def _pava_smooth(self, values):
    """
    PAVA (Pool Adjacent Violators Algorithm)
    
    关键实现点:
    1. 原地修改数组，减少内存分配
    2. 向后传播确保全局单调
    3. 使用平均池化
    """
    n = len(values)
    smoothed = np.array(values, dtype=float)
    
    i = 0
    while i < n - 1:
        # 检查是否违反递增单调性
        if smoothed[i] > smoothed[i + 1] + 1e-10:  # 加入容差
            # 计算池化平均值
            pool_sum = smoothed[i] + smoothed[i + 1]
            pool_count = 2
            
            # 向后传播，检查前面的点
            j = i - 1
            while j >= 0 and smoothed[j] > pool_sum / pool_count + 1e-10:
                pool_sum += smoothed[j]
                pool_count += 1
                j -= 1
            
            # 设置池化值
            pool_avg = pool_sum / pool_count
            for k in range(j + 1, i + 2):
                smoothed[k] = pool_avg
            
            # 回退到池化区域起点重新检查
            i = j + 1 if j >= 0 else 0
        else:
            i += 1
    
    return smoothed
```

---

## 3. 接口规范

### 3.1 fit 方法参数

```python
def fit(self, x: pd.Series, y: Optional[pd.Series] = None, **kwargs) -> 'SmartMonotonicBinner':
    """
    拟合智能单调分箱
    
    Parameters
    ----------
    x : pd.Series
        特征数据
    y : pd.Series, optional
        目标变量（0/1），必需
    **kwargs :
        max_bins : int, default=10
            最大箱数
        min_bins : int, default=2
            最小箱数
        monotonic_trend : str, default='auto'
            单调趋势：'auto', 'ascending', 'descending'
        adjustment_method : str, default='auto'
            调整方法：'auto', 'merge', 'pava', 'none'
        iv_tolerance : float, default=0.1
            IV损失容忍度（0-1）
        min_samples_per_bin : int, default=50
            每箱最小样本数
            
    Returns
    -------
    self : SmartMonotonicBinner
        返回自身，支持链式调用
        
    Raises
    ------
    ValueError
        当 y 为 None 或样本数不足时
    """
```

### 3.2 属性规范

| 属性 | 类型 | 说明 | 示例值 |
|-----|------|-----|-------|
| splits | List[float] | 分箱切点，包含±inf | `[-inf, 100.5, 200.3, inf]` |
| is_monotonic | bool | 是否满足单调性 | `True` |
| adjustment_method | str/None | 实际使用的调整方法 | `'merge'`, `'pava'`, `'none'`, `'fallback'` |
| adjustment_info | List[str] | 处理过程日志 | `['决策树5箱', '合并至3箱']` |
| iv_loss | float | IV损失比例 | `0.05` (5%) |

---

## 4. 测试策略

### 4.1 单元测试矩阵

| 测试项 | 输入条件 | 期望结果 |
|-------|---------|---------|
| _find_best_merge | 已知IV损失分布 | 返回正确索引 |
| _pava_smooth | 非单调序列 | 返回单调序列 |
| _optimize_cutpoints | 可优化切点 | 单调性改善 |
| _fit_none | 不单调数据 | 返回原始，is_monotonic=False |
| _fit_merge | 不单调数据 | 返回单调，adjustment_method='merge' |
| _fit_pava | 不单调数据 | 返回单调，adjustment_method='pava' |
| _fit_auto | 各种数据 | 智能选择最优方法 |

### 4.2 集成测试场景

```python
# 场景1: 天然单调数据
x = feature_02  # 强负相关
result = binner.fit(x, y, max_bins=5)
assert result.is_monotonic == True
assert result.adjustment_method == 'none'

# 场景2: 需要merge调整
x = feature_01  # 弱相关，波动大
result = binner.fit(x, y, max_bins=5, adjustment_method='merge')
assert result.is_monotonic == True
assert result.iv_loss < 0.1

# 场景3: 严格IV限制
x = feature_01
result = binner.fit(x, y, max_bins=5, iv_tolerance=0.01)
# 可能退到更少箱数，但IV损失<1%
assert result.iv_loss <= 0.01 or result.adjustment_method == 'fallback'

# 场景4: 100%有解保证
for _ in range(100):
    x = np.random.randn(1000)
    y = np.random.randint(0, 2, 1000)
    result = binner.fit(pd.Series(x), pd.Series(y))
    assert len(result.splits) >= 2  # 至少2箱
```

---

## 5. 性能预算

| 操作 | 时间预算 | 备注 |
|-----|---------|-----|
| 决策树分箱 | <100ms | sklearn内部优化 |
| 最佳合并 | <50ms | n<20，O(n²)可接受 |
| 切点微调 | <200ms | 11点搜索×n_bins |
| PAVA平滑 | <10ms | 线性算法 |
| 总体（10万样本） | <1s | 单变量 |

---

SPEC 完成，准备开始实施！
