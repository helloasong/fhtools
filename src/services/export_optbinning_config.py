"""
Optbinning 配置导出服务

提供将分箱配置导出为 JSON 格式的功能，支持跨项目复用配置。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import math

import numpy as np
import pandas as pd

from src.data.models import ProjectState, BinningConfig
from src.core.metrics import BinningMetrics


def _convert_to_serializable(obj: Any) -> Any:
    """
    将对象转换为 JSON 可序列化的格式
    
    处理 numpy 类型、pandas 类型等
    
    Args:
        obj: 任意对象
        
    Returns:
        JSON 可序列化的对象
    """
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj):
            return None
        if np.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return [_convert_to_serializable(x) for x in obj.tolist()]
    elif isinstance(obj, pd.Series):
        return [_convert_to_serializable(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_serializable(x) for x in obj]
    else:
        return obj


def export_optbinning_config(
    state: ProjectState,
    output_path: str,
    features: Optional[List[str]] = None
) -> str:
    """
    导出 Optbinning 配置为 JSON
    
    Args:
        state: 项目状态
        output_path: 输出文件路径
        features: 指定导出的变量列表，None 表示全部
        
    Returns:
        输出文件路径
        
    Raises:
        ValueError: 当没有可导出的变量时
        IOError: 当文件写入失败时
    """
    # 确定要导出的变量列表
    features_to_export = features or list(state.binning_results.keys())
    
    if not features_to_export:
        raise ValueError("没有可导出的分箱结果")
    
    # 构建导出数据结构
    export_data = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "project_name": state.project_name if hasattr(state, 'project_name') else "unknown",
        "target_variable": state.target_col,
        "total_variables": 0,
        "variables": {}
    }
    
    # 遍历变量并导出
    for feature in features_to_export:
        if feature not in state.binning_results:
            continue
            
        config = state.binning_configs.get(feature)
        metrics = state.binning_results.get(feature)
        
        if not config or not metrics:
            continue
        
        try:
            export_data["variables"][feature] = export_single_variable(
                feature, config, metrics
            )
            export_data["total_variables"] += 1
        except Exception as e:
            # 记录错误但继续导出其他变量
            print(f"警告: 导出变量 '{feature}' 时出错: {str(e)}")
            continue
    
    if export_data["total_variables"] == 0:
        raise ValueError("没有成功导出任何变量配置")
    
    # 写入 JSON 文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 使用自定义转换函数处理所有类型
            json.dump(_convert_to_serializable(export_data), f, ensure_ascii=False, indent=2)
    except IOError as e:
        raise IOError(f"写入文件失败: {str(e)}")
    
    return output_path


def _convert_split_value(s: Any) -> Any:
    """
    转换分割点值为可序列化格式
    
    Args:
        s: 分割点值
        
    Returns:
        可序列化的值
    """
    if isinstance(s, (int, float)):
        # 处理 NaN 和 Inf
        if math.isnan(s):
            return None
        if math.isinf(s):
            return "inf" if s > 0 else "-inf"
        return float(s)
    return str(s)


def export_single_variable(
    feature: str,
    config: BinningConfig,
    metrics: BinningMetrics
) -> Dict[str, Any]:
    """
    导出单个变量的配置
    
    Args:
        feature: 变量名
        config: 分箱配置
        metrics: 分箱指标
        
    Returns:
        变量配置字典
        
    Raises:
        ValueError: 当 metrics 数据不完整时
    """
    # 获取分箱表
    if metrics.summary_table is None or metrics.summary_table.empty:
        raise ValueError(f"变量 '{feature}' 的分箱表为空")
    
    df = metrics.summary_table.reset_index()
    
    # 构建 bins 列表
    bins = []
    for _, row in df.iterrows():
        bin_info = {
            "label": str(row['bin']),
            "count": int(row['total']),
            "bad": int(row['bad']),
            "good": int(row['good']),
            "bad_rate": float(row['bad_rate']),
            "woe": float(row['woe']),
            "iv": float(row['iv'])
        }
        # 可选字段：如果有 lift 则添加
        if 'lift' in row:
            bin_info["lift"] = float(row['lift'])
        bins.append(bin_info)
    
    # 计算总 IV
    total_iv = df['iv'].sum()
    
    # 构建变量配置
    variable_config = {
        "dtype": config.params.get('dtype', 'numerical'),
        "splits": [_convert_split_value(s) for s in config.splits],
        "n_bins": len(bins),
        "bin_stats": {
            "total_iv": float(total_iv),
            "bins": bins
        },
        "config": {
            k: v for k, v in config.params.items() 
            if v is not None and k not in ['special_codes']
        }
    }
    
    # 添加缺失值策略信息
    variable_config["missing_strategy"] = config.missing_strategy
    if config.missing_merge_label:
        variable_config["missing_merge_label"] = config.missing_merge_label
    
    # 添加单调性信息（确保转换为 Python bool）
    if hasattr(metrics, 'is_monotonic'):
        variable_config["bin_stats"]["is_monotonic"] = bool(metrics.is_monotonic)
    
    return variable_config


def load_optbinning_config(path: str) -> Dict[str, Any]:
    """
    加载 JSON 配置
    
    Args:
        path: JSON 文件路径
        
    Returns:
        配置字典
        
    Raises:
        FileNotFoundError: 当文件不存在时
        json.JSONDecodeError: 当 JSON 格式无效时
    """
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 基本验证
    if "version" not in config:
        raise ValueError("配置文件缺少 version 字段")
    if "variables" not in config:
        raise ValueError("配置文件缺少 variables 字段")
    
    return config


def export_optbinning_config_by_features(
    state: ProjectState,
    output_path: str,
    features: List[str]
) -> str:
    """
    导出指定变量的 Optbinning 配置
    
    Args:
        state: 项目状态
        output_path: 输出文件路径
        features: 指定导出的变量列表
        
    Returns:
        输出文件路径
    """
    if not features:
        raise ValueError("必须指定至少一个变量")
    
    return export_optbinning_config(state, output_path, features)
