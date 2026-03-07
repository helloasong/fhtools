import pandas as pd
import numpy as np

def recommend_method(series: pd.Series, target: pd.Series) -> str:
    if not pd.api.types.is_numeric_dtype(series):
        return 'decision_tree'
    n_unique = series.nunique(dropna=True)
    if n_unique < 10:
        return 'equal_width'
    skew = series.dropna().skew()
    corr = series.dropna().corr(target.loc[series.dropna().index]) if target is not None else 0.0
    if abs(corr) > 0.2:
        return 'decision_tree'
    if abs(skew) > 1.0:
        return 'chi_merge'
    return 'equal_freq'

METHOD_CN_MAP = {
    'equal_freq': '等频分箱',
    'equal_width': '等宽分箱',
    'decision_tree': '决策树分箱',
    'chi_merge': '卡方分箱',
    'best_ks': 'Best-KS 分箱',
    'manual': '自定义切点',
}

def method_to_cn(method: str) -> str:
    return METHOD_CN_MAP.get(method, method)
