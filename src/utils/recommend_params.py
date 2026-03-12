"""推荐参数算法模块

根据数据规模智能推荐最优分箱参数，帮助用户在不同数据量下获得最佳性能和效果。
"""

from typing import Dict, Any


# 小数据 (< 10,000) 推荐参数
_SMALL_DATA_PARAMS = {
    'solver': 'cp',
    'prebinning_method': 'cart',
    'max_n_prebins': 20,
    'min_prebin_size': 0.05,
    'max_n_bins': 5,
    'min_n_bins': 2,
    'min_bin_size': 0.05,
    'time_limit': 30,
    'gamma': 0
}

# 中数据 (10,000 - 100,000) 推荐参数
_MEDIUM_DATA_PARAMS = {
    'solver': 'cp',
    'prebinning_method': 'cart',
    'max_n_prebins': 20,
    'min_prebin_size': 0.05,
    'max_n_bins': 5,
    'min_n_bins': 2,
    'min_bin_size': 0.05,
    'time_limit': 100,
    'gamma': 0
}

# 大数据 (> 100,000) 推荐参数
# 注意：LS solver 在 optbinning 0.21.0 有 bug，暂时使用 CP
_LARGE_DATA_PARAMS = {
    'solver': 'cp',
    'prebinning_method': 'quantile',
    'max_n_prebins': 50,
    'min_prebin_size': 0.02,
    'max_n_bins': 10,
    'min_n_bins': 2,
    'min_bin_size': 0.02,
    'time_limit': 200,
    'gamma': 0.1
}

# 数据规模阈值
_SMALL_THRESHOLD = 10000
_LARGE_THRESHOLD = 100000


def get_recommended_params(n_samples: int) -> Dict[str, Any]:
    """
    根据样本量推荐分箱参数

    根据数据规模（小/中/大）返回最优的分箱参数配置，以平衡计算效率和分箱质量。

    Args:
        n_samples: 样本数量，应为正整数

    Returns:
        推荐参数字典，包含以下键:
        - solver: 求解器类型 ('cp' 或 'ls')
        - max_n_prebins: 预分箱最大数量
        - min_prebin_size: 预分箱最小占比
        - max_n_bins: 最大箱数
        - min_n_bins: 最小箱数
        - min_bin_size: 每箱最小占比
        - time_limit: 求解时间限制(秒)
        - gamma: 正则化系数

    Example:
        >>> params = get_recommended_params(50000)
        >>> print(params['solver'])
        'cp'
    """
    if n_samples <= 0:
        # 边界条件：返回小数据默认参数
        return _SMALL_DATA_PARAMS.copy()

    if n_samples < _SMALL_THRESHOLD:
        return _SMALL_DATA_PARAMS.copy()
    elif n_samples <= _LARGE_THRESHOLD:
        return _MEDIUM_DATA_PARAMS.copy()
    else:
        return _LARGE_DATA_PARAMS.copy()


def get_data_scale_label(n_samples: int) -> str:
    """
    获取数据规模标签

    根据样本量返回友好的中文数据规模标签，包含格式化后的样本数量。

    Args:
        n_samples: 样本数量

    Returns:
        数据规模标签，格式为 "规模标签 (数量)"。
        例如: "小数据 (5,000样本)", "中数据 (5万样本)", "大数据 (100万样本)"

    Example:
        >>> get_data_scale_label(5000)
        '小数据 (5,000样本)'
        >>> get_data_scale_label(50000)
        '中数据 (5万样本)'
        >>> get_data_scale_label(0)
        '小数据 (0样本)'
    """
    formatted_num = format_number(n_samples)

    if n_samples <= 0:
        scale = "小数据"
    elif n_samples < _SMALL_THRESHOLD:
        scale = "小数据"
    elif n_samples <= _LARGE_THRESHOLD:
        scale = "中数据"
    else:
        scale = "大数据"

    return f"{scale} ({formatted_num}样本)"


def format_number(n: int) -> str:
    """
    格式化数字为友好的中文表示

    将数字转换为中文习惯表示法，如 50000 -> "5万", 1000000 -> "100万"。
    小于1万的数字使用千分位格式，大于等于1万的使用"万"单位。

    Args:
        n: 要格式化的整数

    Returns:
        格式化后的字符串

    Example:
        >>> format_number(5000)
        '5,000'
        >>> format_number(50000)
        '5万'
        >>> format_number(1500000)
        '150万'
        >>> format_number(0)
        '0'
        >>> format_number(-100)
        '-100'
    """
    if n < 10000 and n > -10000:
        # 小于1万，使用千分位格式
        return f"{n:,}"
    else:
        # 大于等于1万，使用"万"单位
        wan = n / 10000
        # 如果是整数万，不显示小数
        if wan == int(wan):
            return f"{int(wan)}万"
        else:
            # 保留一位小数
            return f"{wan:.1f}万"
