"""
过滤引擎常量定义
"""

# 支持的操作符
SUPPORTED_OPERATORS = [
    '==', '!=',
    '>', '>=', '<', '<=',
    'in', 'not in',
    'between',
    'like',
    'is null', 'is not null',
]

# 按数据类型推荐的操作符
OPERATORS_BY_TYPE = {
    'numeric': ['>', '>=', '<', '<=', '==', '!=', 'between', 'in', 'not in', 'is null', 'is not null'],
    'string': ['==', '!=', 'in', 'not in', 'like', 'is null', 'is not null'],
    'datetime': ['>', '>=', '<', '<=', '==', '!=', 'between', 'is null', 'is not null'],
    'boolean': ['==', '!=', 'is null', 'is not null'],
    'object': ['==', '!=', 'in', 'not in', 'like', 'is null', 'is not null'],
}

# 逻辑操作符
LOGIC_OPERATORS = ['AND', 'OR']

# 最大嵌套深度（防止过深嵌套导致性能/栈溢出问题）
MAX_NESTING_DEPTH = 10
