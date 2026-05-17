# FHBinningTool - 数据过滤引擎需求文档 (PRD)

> **版本**: v1.1 (已修订：移除 CASE WHEN，仅保留 AND/OR/NOT 布尔逻辑)  
> **日期**: 2026-05-17  
> **作者**: AI Assistant  
> **状态**: 需求评审中  

---

## 1. 背景与目标

### 1.1 背景
FHBinningTool 当前的数据流程是：导入宽表 → 自动识别数值型特征 → EDA统计 → 分箱分析。在实际风控场景中，宽表往往包含数千列特征，且不同指标（特征列）需要根据业务规则设置不同的数据过滤条件。例如：
- 某些指标需要排除异常值（如年龄 > 120 的记录）
- 某些指标只在特定产品线下有效（如 `product_type == 'A'`）
- 某些指标需要同时满足多个条件（如 `age > 18 AND status == 'active'`）

### 1.2 目标
为 FHBinningTool 增加一套**数据过滤引擎**，支持：
1. **全局默认过滤规则**：统一应用于所有指标的默认过滤条件
2. **指标自定义过滤规则**：针对单个指标的特殊过滤条件，**覆盖**全局规则
3. **可视化规则编辑器**：美观的 UI 支持 AND / OR / NOT 布尔逻辑组合
4. **实时效果预览**：配置过滤规则时即时看到剩余样本数

---

## 2. 术语定义

| 术语 | 定义 |
|------|------|
| **过滤规则 (FilterRule)** | 针对一个指标（或全局）的数据筛选条件，决定哪些行参与该指标的分箱计算 |
| **条件节点 (ConditionNode)** | 规则树上的叶子节点，表示一个原子判断（如 `age > 18`） |
| **逻辑节点 (LogicNode)** | 规则树上的分支节点，表示 AND / OR / NOT 逻辑组合 |
| **全局规则 (GlobalRule)** | 默认应用于所有指标的过滤规则 |
| **指标规则 (FeatureRule)** | 绑定到特定指标名的过滤规则，优先级高于全局规则 |
| **规则覆盖** | 当指标存在自定义规则时，完全忽略全局规则，使用自定义规则 |

---

## 3. 功能需求

### 3.1 过滤规则引擎核心功能

#### FR-001: 全局默认过滤规则
- **描述**: 用户可配置一组全局过滤规则，默认应用于所有指标的分箱计算
- **细节**:
  - 全局规则存储在项目级别 (`ProjectState.global_filter_rule`)
  - 新建项目时，全局规则默认为空（不过滤任何数据）
  - 全局规则可随时编辑、启用/禁用、删除
  - 支持多条全局规则以 AND/OR 组合

#### FR-002: 指标级自定义过滤规则
- **描述**: 每个指标可配置独立的过滤规则，**完全覆盖**全局规则
- **细节**:
  - 指标规则存储在 `ProjectState.feature_filter_rules: Dict[str, FilterRule]`
  - 指标规则独立于 `binning_configs`，可在分箱前单独配置
  - 当指标存在自定义规则时，该指标分箱时仅使用自定义规则，忽略全局规则
  - 指标规则可随时清空（恢复使用全局规则）
  - UI 上需清晰标识当前指标使用的是全局规则还是自定义规则

#### FR-003: 规则优先级与覆盖机制
- **描述**: 明确的多层级规则优先级体系，每个指标可独立选择过滤模式
- **指标过滤模式（三选一）**:
  | 模式 | 行为 | 说明 |
  |------|------|------|
  | **使用全局规则** (默认) | 应用全局过滤规则 | 指标没有独立配置时的默认行为 |
  | **使用自定义规则** | 应用该指标独立配置的规则 | 完全替代全局规则 |
  | **不应用过滤** | 任何过滤规则都不应用 | 即使全局规则存在，该指标也完全不过滤 |
- **优先级顺序（从高到低）**:
  1. 指标自定义规则（模式为 `CUSTOM` 时）
  2. 全局默认规则（模式为 `GLOBAL` 且全局规则存在且启用时）
  3. 无过滤（模式为 `DISABLED`，或全局规则未配置/禁用时）
- **细节**:
  - 指标自定义规则是一个完整的规则树，不是对全局规则的"增量修改"
  - 每个指标的模式独立存储，切换模式不影响已保存的自定义规则内容
  - 从 `CUSTOM` 切到 `GLOBAL` 再切回 `CUSTOM`，自定义规则内容保留

#### FR-004: 规则执行与数据流集成
- **描述**: 过滤规则在分箱计算前应用，仅影响分箱输入数据
- **执行时机**:
  ```
  controller.run_binning(feature, method, **kwargs)
    └→ 获取该指标生效的过滤规则
    └→ 从 self.df 应用过滤得到 filtered_df
    └→ 从 filtered_df 取 x, y 传入 binner.fit()
    └→ 分箱结果基于过滤后的数据统计
  ```
- **细节**:
  - 过滤不修改 `self.df` 原始数据，仅生成分箱用的临时子集
  - 分箱结果中需记录使用的过滤规则摘要（便于追溯）
  - EDA 统计建议基于**未过滤**的原始数据（保持数据全貌），或在 UI 区分显示

---

### 3.2 条件表达式能力

#### FR-005: 原子条件 (ConditionNode)
- **描述**: 最基本的判断单元 `[变量] [操作符] [值]`
- **支持的操作符**:

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `==` | 等于 | `gender == 'M'` |
| `!=` | 不等于 | `status != 'deleted'` |
| `>` / `>=` | 大于 / 大于等于 | `age > 18` |
| `<` / `<=` | 小于 / 小于等于 | `score <= 100` |
| `in` | 在列表中 | `city in ['北京', '上海', '广州']` |
| `not in` | 不在列表中 | `type not in ['test', 'internal']` |
| `is null` | 为空 | `phone is null` |
| `is not null` | 不为空 | `email is not null` |
| `between` | 在区间内（闭区间） | `age between [18, 60]` |
| `like` | 模糊匹配（%通配） | `name like '张%'` |

- **左值（变量）**: 可选择数据集中的任意列（不限于当前分箱指标）
- **右值（比较值）**: 
  - 常量值（字符串、数值、日期）
  - 支持多值输入（逗号分隔，用于 `in` / `not in`）
  - 区间输入（两个值，用于 `between`）

#### FR-006: 逻辑组合 (LogicNode)
- **描述**: 使用 AND / OR / NOT 组合多个条件
- **支持的逻辑操作符**:
  - `AND`: 所有子条件同时满足
  - `OR`: 任一子条件满足
  - `NOT`: 否定单个子条件
- **细节**:
  - 支持任意深度的嵌套组合（如 `(A AND B) OR (C AND NOT D)`）
  - UI 上通过树形结构或缩进层级清晰展示嵌套关系
  - 默认新添加的条件之间为 `AND` 关系，用户可手动改为 `OR`

#### FR-007: 特殊值处理
- **描述**: 过滤规则中需支持对缺失值、特殊编码值的处理
- **支持的特殊值类型**:
  - 缺失值 (`null` / `NaN`) —— 通过 `is null` / `is not null` 操作符
  - 特殊编码值（如 `-9999` 表示未获取）—— 作为普通常量值处理
  - 空字符串 —— 通过 `== ''` 或 `is null`（取决于业务定义）

---

### 3.3 过滤规则 UI 编辑器

#### FR-008: 规则编辑器总体布局
- **描述**: 一个美观、直观的可视化规则编辑器组件
- **建议布局**:
  ```
  ┌─────────────────────────────────────────────────┐
  │  [指标: age]        [使用全局规则 ▼]  [测试规则] │  ← 头部
  ├─────────────────────────────────────────────────┤
  │                                                  │
  │  ┌─ 规则树可视化区域 ─────────────────────────┐  │
  │  │                                            │  │
  │  │  [AND]                                     │  │
  │  │  ├── [age] [>] [18]              [✏️] [🗑️] │  │
  │  │  ├── [gender] [==] [M]           [✏️] [🗑️] │  │
  │  │  └── [OR]                                  │  │
  │  │      ├── [city] [in] [北京,上海] [✏️] [🗑️] │  │
  │  │      └── [score] [>=] [600]      [✏️] [🗑️] │  │
  │  │                                            │  │
  │  └────────────────────────────────────────────┘  │
  │                                                  │
  │  [+ 添加条件]  [+ 添加AND组]  [+ 添加OR组]        │  ← 操作按钮
  │                                                  │
  │  ┌─ 效果预览 ─────────────────────────────────┐  │
  │  │  过滤前样本: 100,000  过滤后样本: 87,532   │  │
  │  │  过滤比例: 12.47%  预计剩余: 87,532       │  │
  │  └────────────────────────────────────────────┘  │
  │                                                  │
  │  [取消]                            [保存规则 ✓]  │  ← 底部按钮
  └─────────────────────────────────────────────────┘
  ```

#### FR-009: 条件行编辑器
- **描述**: 单条条件的编辑界面
- **交互方式**:
  - **新建**: 点击 "+ 添加条件" → 弹出/内联展开条件编辑行
  - **编辑**: 点击条件行旁的编辑按钮 → 条件行变为可编辑状态
  - **删除**: 点击条件行旁的删除按钮 → 确认后删除
- **条件行组件**:
  ```
  [变量下拉框 ▼] [操作符下拉框 ▼] [值输入框] [✓确认] [✗取消]
  ```
  - 变量下拉框：列出数据集中所有列名，支持搜索
  - 操作符下拉框：根据变量类型动态显示适用的操作符
    - 数值型：`> >= < <= == != between in not in is null is not null`
    - 字符串型：`== != in not in like is null is not null`
    - 日期型：`> >= < <= == != between is null is not null`
  - 值输入框：根据操作符动态切换输入方式
    - 单值：普通输入框
    - 多值：标签输入框（逗号分隔，可带自动完成）
    - 区间：双输入框（最小值 ~ 最大值）
    - null：无输入框，操作符本身就表达了条件

#### FR-010: 逻辑组嵌套编辑
- **描述**: 支持在规则树中创建 AND/OR 逻辑组
- **交互方式**:
  - 选中一个或多个条件 → 点击 "合并为AND组" / "合并为OR组"
  - 或点击 "+ 添加AND组" → 添加一个空的 AND 组，然后向其中拖入条件
  - 逻辑组本身可嵌套（AND 组内可包含 OR 子组）
  - 逻辑组有清晰的视觉层级（缩进、边框、背景色区分）
  - 每个逻辑组显示一个下拉框选择 `AND` / `OR`
- **NOT 操作**: 每个条件行和逻辑组头部提供一个 "取反" 开关（Toggle），开启后条件取反

#### FR-011: 规则测试与效果预览
- **描述**: 配置规则时实时计算并显示过滤效果
- **预览信息**:
  - 过滤前总样本数
  - 过滤后样本数
  - 过滤掉的样本数和比例
  - 每个条件的独立命中数（可选高级功能）
- **实现方式**:
  - 用户点击 "测试规则" 按钮或启用实时预览开关时，在后台线程执行过滤
  - 使用 `Worker(QThread)` 避免阻塞 UI
  - 预览基于当前 `ProjectController.df` 的完整数据

#### FR-012: 指标过滤模式切换（三态控制）
- **描述**: 每个指标提供明确的过滤模式切换，支持一键禁用该指标的所有过滤
- **切换选项**:
  - **使用全局规则**（默认）：该指标使用全局默认规则
  - **使用自定义规则**：该指标使用独立配置的规则
  - **不应用过滤**：该指标不使用任何过滤（即使全局规则存在）
- **UI 设计建议（两种方案可选）**:
  - **方案A - 下拉框**: 编辑器头部放置 `QComboBox`，三选项切换
  - **方案B - 按钮组** (推荐): 编辑器头部放置三个 `QPushButton` 组成的按钮组，当前选中项高亮，更直观
    ```
    [使用全局规则] [使用自定义规则] [不应用过滤]
    ```
- **各模式下的 UI 表现**:
  | 模式 | 规则编辑器 | 预览面板 | 列表图标标识 |
  |------|-----------|---------|------------|
  | 使用全局规则 | 只读显示全局规则预览，提示"正在使用全局规则" | 显示全局规则生效后的样本数 | 🌐 全局标识 |
  | 使用自定义规则 | 可编辑，初始为空或上次保存的规则 | 显示自定义规则生效后的样本数 | ⚙️ 自定义标识 |
  | 不应用过滤 | 隐藏，显示提示"该指标不参与任何数据过滤" | 显示原始样本数（无过滤） | 🚫 禁用标识 |
- **状态持久化**: 切换模式立即保存到 `ProjectState`，自定义规则内容在切换时不丢失

---

### 3.4 系统集成需求

#### FR-013: 数据模型扩展
- **描述**: 在现有数据模型中增加过滤规则相关字段
- **修改文件**: `src/data/models.py`
- **新增数据结构**:
  ```python
  @dataclass
  class FilterCondition:
      """原子条件节点"""
      variable: str                    # 变量名
      operator: str                    # 操作符
      value: Union[str, float, List, None]  # 比较值
      negate: bool = False             # 是否取反 (NOT)
  
  @dataclass
  class FilterLogicNode:
      """逻辑组合节点"""
      operator: str  # 'AND' | 'OR'
      children: List[Union[FilterCondition, 'FilterLogicNode']]
  
  @dataclass
  class FilterRule:
      """完整的过滤规则"""
      name: Optional[str] = None       # 规则名称（可选）
      enabled: bool = True             # 是否启用
      root: Union[FilterLogicNode, FilterCondition, None] = None
      created_at: Optional[str] = None
      updated_at: Optional[str] = None
  
  class FilterMode(Enum):
      """指标过滤模式"""
      GLOBAL = "global"      # 使用全局规则
      CUSTOM = "custom"      # 使用自定义规则
      DISABLED = "disabled"  # 不应用任何过滤
  
  @dataclass
  class FeatureFilterSetting:
      """单个指标的过滤设置"""
      mode: FilterMode = FilterMode.GLOBAL
      rule: Optional[FilterRule] = None  # 仅在 mode=CUSTOM 时生效
  ```
- **ProjectState 扩展**:
  ```python
  @dataclass
  class ProjectState:
      # ... 现有字段 ...
      global_filter_rule: Optional[FilterRule] = None
      feature_filter_settings: Dict[str, FeatureFilterSetting] = field(default_factory=dict)
  ```

#### FR-014: 控制器集成
- **描述**: 在 `ProjectController` 中集成过滤规则的执行逻辑
- **修改文件**: `src/controllers/project_controller.py`
- **新增方法**:
  ```python
  def get_effective_filter_rule(self, feature: str) -> Optional[FilterRule]:
      """获取指定指标生效的过滤规则"""
      
  def apply_filter_rule(self, df: pd.DataFrame, rule: FilterRule) -> pd.DataFrame:
      """对 DataFrame 应用过滤规则，返回过滤后的子集"""
      
  def get_filter_preview(self, rule: FilterRule) -> dict:
      """获取过滤规则的预览统计信息"""
  ```
- **修改 `run_binning` 方法**:
  - 在获取 x, y 之前，先获取生效的过滤规则
  - 应用过滤规则得到 `filtered_df`
  - 基于 `filtered_df` 执行分箱
  - 在 `BinningConfig` 中记录使用的过滤规则摘要

#### FR-015: 持久化兼容
- **描述**: 过滤规则需随项目一起保存和加载
- **细节**:
  - `FilterRule` 及其子类必须支持 pickle 序列化（与现有 `.fht` 格式兼容）
  - 旧项目文件（无过滤规则字段）加载时，新字段使用默认值（None / empty dict）
  - 确保向后兼容

#### FR-016: UI 入口与页面集成
- **描述**: 在合适的位置提供过滤规则配置的入口
- **建议集成点**:

| 入口位置 | 功能 | 优先级 |
|---------|------|--------|
| **ImportView** | 数据导入页面增加"数据过滤配置"区域，配置全局规则 | P0 |
| **CombinedView** | 分析与调参页面为每个指标增加过滤规则配置入口 | P0 |
| **全局配置对话框** | 独立的全局过滤规则配置对话框（可从菜单或导入页打开） | P1 |

- **CombinedView 集成方式**:
  - 在变量列表右侧、统计卡片上方增加"过滤规则"区域（可折叠）
  - 或在分箱配置工具栏区域增加过滤规则按钮，点击弹出 `FilterRuleDialog`
  - 选中的指标在变量列表中以特殊图标标识"使用自定义过滤"状态

---

## 4. 非功能需求

### 4.1 性能需求
- **NFR-001**: 过滤规则预览计算需在 3 秒内完成（10万行数据）
- **NFR-002**: 分箱时的过滤应用不应显著增加分箱耗时（增加 < 20%）
- **NFR-003**: UI 编辑器中规则的增删改需流畅，无明显卡顿

### 4.2 用户体验需求
- **NFR-004**: 规则编辑器需支持键盘快捷键（Enter 确认、Delete 删除、ESC 取消）
- **NFR-005**: 条件过多时编辑器区域需支持滚动，保持操作按钮始终可见
- **NFR-006**: 提供规则模板的快速选择（如"排除缺失值"、"排除异常值"、"常见年龄段"）
- **NFR-007**: 规则配置有误时提供清晰的错误提示（如"变量不存在"、"值类型不匹配"）

### 4.3 兼容性需求
- **NFR-008**: 向后兼容旧项目文件（无过滤规则字段）
- **NFR-009**: 过滤规则的数据结构与 pickle 序列化兼容
- **NFR-010**: 导出功能（Excel/Python/SQL）需在报告中注明过滤规则的使用情况

---

## 5. UI/UX 设计规范

### 5.1 视觉风格（遵循现有项目风格）

```css
/* 过滤规则编辑器容器 */
FilterEditor {
    background: linear-gradient(to bottom, #FFFFFF, #F4F7FB);
    border: 1px solid #E3E6EA;
    border-radius: 10px;
    padding: 16px;
}

/* 条件行 */
ConditionRow {
    background: #FFFFFF;
    border: 1px solid #D7DEE8;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
}

/* 逻辑组容器 */
LogicGroup {
    background: #F8FAFD;
    border: 1px solid #E3E6EA;
    border-radius: 8px;
    padding: 12px;
    margin: 4px 0 4px 24px;  /* 左侧缩进表示层级 */
}

/* 操作按钮 */
ActionButton {
    background: linear-gradient(to bottom, #E8EEF6, #D9E4F5);
    border: 1px solid #C9D6EA;
    border-radius: 8px;
    padding: 6px 12px;
    color: #333;
}

/* 主要操作按钮（保存、测试） */
PrimaryButton {
    background: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
}

/* 删除按钮 */
DangerButton {
    background: transparent;
    color: #E53935;
    border: none;
}

/* 输入框 */
FilterInput {
    background: #FFFFFF;
    border: 1px solid #D7DEE8;
    border-radius: 8px;
    padding: 4px 8px;
}
```

### 5.2 交互规范

| 交互 | 行为 |
|------|------|
| 添加条件 | 点击"+ 添加条件"，在当前逻辑组末尾插入新的条件编辑行 |
| 编辑条件 | 点击条件行的编辑图标，该行变为可编辑状态（输入框 + 下拉框） |
| 确认编辑 | 点击 ✓ 或按 Enter，验证输入合法性后保存 |
| 取消编辑 | 点击 ✗ 或按 ESC，恢复原始值 |
| 删除条件 | 点击 🗑️ 图标，无确认直接删除（可撤销需后续迭代） |
| 合并为组 | 多选条件后点击"合并为AND/OR组"，原条件移入新组 |
| 取消分组 | 选中逻辑组点击"取消分组"，子条件提升到父级 |
| 规则测试 | 点击"测试规则"，后台计算，结果显示在预览区 |
| 实时预览 | 开启开关后，每次规则变更自动触发预览（带防抖） |

---

## 6. 技术方案建议

### 6.1 核心过滤执行引擎

建议新建文件 `src/core/filtering/engine.py`：

```python
class FilterEngine:
    """过滤规则执行引擎"""
    
    @staticmethod
    def apply(df: pd.DataFrame, rule: FilterRule) -> pd.DataFrame:
        """应用过滤规则到 DataFrame"""
        if not rule or not rule.enabled or not rule.root:
            return df
        mask = FilterEngine._eval_node(df, rule.root)
        return df[mask]
    
    @staticmethod
    def _eval_node(df, node):
        """递归计算规则节点的布尔掩码"""
        if isinstance(node, FilterCondition):
            return FilterEngine._eval_condition(df, node)
        elif isinstance(node, FilterLogicNode):
            return FilterEngine._eval_logic(df, node)
    
    @staticmethod
    def _eval_condition(df, cond):
        """计算原子条件"""
        col = df[cond.variable]
        op = cond.operator
        val = cond.value
        # ... 根据操作符计算掩码 ...
        mask = ...
        return ~mask if cond.negate else mask
    
    @staticmethod
    def _eval_logic(df, node):
        """计算逻辑组合"""
        masks = [FilterEngine._eval_node(df, child) for child in node.children]
        if node.operator == 'AND':
            result = masks[0]
            for m in masks[1:]:
                result = result & m
            return result
        elif node.operator == 'OR':
            result = masks[0]
            for m in masks[1:]:
                result = result | m
            return result
```

### 6.2 新增文件清单

| 文件路径 | 说明 | 类型 |
|---------|------|------|
| `src/core/filtering/engine.py` | 过滤规则执行引擎 | 新增 |
| `src/core/filtering/__init__.py` | 过滤模块入口 | 新增 |
| `src/data/models.py` | 扩展 FilterRule 相关数据结构 | 修改 |
| `src/ui/widgets/filter_rule_editor.py` | 过滤规则编辑器主组件 | 新增 |
| `src/ui/widgets/filter_condition_row.py` | 单条件行编辑器 | 新增 |
| `src/ui/widgets/filter_logic_group.py` | 逻辑组容器组件 | 新增 |
| `src/ui/widgets/filter_preview_panel.py` | 过滤效果预览面板 | 新增 |
| `src/ui/dialogs/filter_rule_dialog.py` | 过滤规则配置对话框 | 新增 |
| `src/controllers/project_controller.py` | 集成过滤逻辑 | 修改 |
| `src/ui/views/import_view.py` | 增加全局规则配置入口 | 修改 |
| `src/ui/views/combined_view.py` | 增加指标级规则配置入口 | 修改 |
| `style.qss` | 增加过滤编辑器相关样式 | 修改 |

### 6.3 与现有系统的协作关系

```
ImportView
  └─ FilterRuleDialog (全局规则配置)
       └─ FilterRuleEditor
            ├─ FilterConditionRow
            └─ FilterLogicGroup

CombinedView
  └─ FilterRuleDialog (指标级规则配置)
       └─ FilterRuleEditor
            └─ (同上组件)

ProjectController
  ├─ get_effective_filter_rule(feature) → FilterRule
  ├─ apply_filter_rule(df, rule) → filtered_df
  └─ run_binning(feature, method, **kwargs)
       └─ FilterEngine.apply(df, rule) → filtered_df
            └─ binner.fit(filtered_df[feature], filtered_df[target])
```

---

## 7. 边界情况与异常处理

| 场景 | 处理策略 |
|------|---------|
| 规则引用的列在数据中不存在 | 运行时抛出友好错误，UI 提示"变量 xxx 不存在于数据集中" |
| 规则中的值类型与列类型不匹配 | 尝试类型转换，失败时提示类型不匹配 |
| 过滤后数据为空 | 分箱时提示"过滤后数据为空，无法分箱"，保留空结果状态 |
| 过滤后某箱样本数过少 | 正常传入分箱算法，由算法自身的 min_samples 参数处理 |
| 循环嵌套过深 | 设置最大嵌套深度（如 10 层），超过时拒绝保存 |
| 旧项目文件加载 | 新字段使用默认值，不报错 |

---

## 8. 后续扩展方向

1. **规则模板库**: 预置常用过滤模板（风控场景下的标准过滤条件）
2. **规则导入导出**: 将过滤规则导出为 JSON/YAML，跨项目复用
3. **规则版本管理**: 记录规则的修改历史，支持回滚
4. **批量规则应用**: 一次为多个指标设置相同的自定义规则
5. **规则生效报告**: 导出每个指标的过滤规则及过滤前后统计对比

---

## 9. 验收标准

- [ ] 全局过滤规则可在 ImportView 中配置并保存到项目
- [ ] 指标级过滤规则可在 CombinedView 中为每个指标独立配置
- [ ] 自定义规则正确覆盖全局规则
- [ ] 支持 AND / OR / NOT 任意深度的条件组合
- [ ] 规则编辑器 UI 美观，符合现有项目风格
- [ ] 过滤效果可实时预览（样本数变化）
- [ ] 过滤规则正确影响分箱计算结果
- [ ] 旧项目文件向后兼容
- [ ] 所有修改遵循现有代码风格和架构模式
