"""
数据过滤引擎模块

提供过滤规则的执行、校验和预览功能。
"""

from src.core.filtering.engine import FilterEngine, FilterPreviewResult
from src.core.filtering.validation import FilterValidator, FilterValidationError
from src.core.filtering.constants import (
    SUPPORTED_OPERATORS,
    OPERATORS_BY_TYPE,
    LOGIC_OPERATORS,
    MAX_NESTING_DEPTH,
)

__all__ = [
    'FilterEngine',
    'FilterPreviewResult',
    'FilterValidator',
    'FilterValidationError',
    'SUPPORTED_OPERATORS',
    'OPERATORS_BY_TYPE',
    'LOGIC_OPERATORS',
    'MAX_NESTING_DEPTH',
]
