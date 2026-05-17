"""
组合策略分析核心模块

基于已有单变量分箱结果，通过笛卡尔积交叉组合挖掘多变量联合策略规则。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

from src.data.models import BinningConfig


@dataclass
class CrossBinningFilters:
    """组合策略筛选参数"""
    min_sample_rate: float = 0.005
    bad_rate_mode: str = "relative"
    bad_rate_high_multiplier: float = 2.0
    bad_rate_low_multiplier: float = 0.5
    min_lift: float = 1.0
    sort_by: str = "bad_rate_desc"
    max_combinations: int = 5000
    show_all: bool = False  # 不过滤，仅排序展示全部组合


@dataclass
class CrossBinningRule:
    """单条组合策略规则"""
    rule_id: str = ""
    risk_level: str = ""
    conditions: List[Dict] = field(default_factory=list)
    condition_str: str = ""
    sample_count: int = 0
    sample_rate: float = 0.0
    bad_count: int = 0
    bad_rate: float = 0.0
    overall_bad_rate: float = 0.0
    lift: float = 0.0
    woe: float = 0.0
    iv: float = 0.0


@dataclass
class CrossBinningResult:
    """组合策略分析结果"""
    overall_bad_rate: float = 0.0
    total_combinations: int = 0
    filtered_combinations: int = 0
    rules: List[CrossBinningRule] = field(default_factory=list)
    feature_names: List[str] = field(default_factory=list)
    feature_bin_counts: Dict[str, int] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame 便于展示和导出"""
        if not self.rules:
            return pd.DataFrame()
        rows = []
        for r in self.rules:
            rows.append({
                "规则编号": r.rule_id,
                "风险等级": r.risk_level,
                "组合条件": r.condition_str,
                "样本数": r.sample_count,
                "占比": r.sample_rate,
                "坏样本数": r.bad_count,
                "坏账率": r.bad_rate,
                "整体坏账率": r.overall_bad_rate,
                "Lift": r.lift,
                "WOE": r.woe,
                "IV": r.iv,
            })
        return pd.DataFrame(rows)


@dataclass
class CrossBinningHeatmapData:
    """二维热力图数据（仅2变量时使用）"""
    feature_x: str = ""
    feature_y: str = ""
    x_labels: List[str] = field(default_factory=list)
    y_labels: List[str] = field(default_factory=list)
    bad_rate_matrix: Optional[pd.DataFrame] = None
    sample_count_matrix: Optional[pd.DataFrame] = None
    lift_matrix: Optional[pd.DataFrame] = None


class CrossBinningAnalyzer:
    """组合策略分析器

    基于已有单变量分箱结果，通过笛卡尔积交叉组合挖掘多变量联合策略规则。
    所有计算均为 pandas 向量化操作。
    """

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        target_col: str,
        features: List[str],
        configs: Dict[str, BinningConfig],
        filters: CrossBinningFilters,
        filtered_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> CrossBinningResult:
        """执行组合策略分析

        Args:
            df: 原始数据
            target_col: 目标变量列名
            features: 选择的变量名列表（2~N个）
            configs: 各变量的分箱配置
            filters: 筛选参数
            filtered_data_map: 各变量过滤后的数据子集

        Returns:
            CrossBinningResult
        """
        CrossBinningAnalyzer._validate_inputs(df, target_col, features, configs, filters)

        working_df = CrossBinningAnalyzer._build_working_df(
            df, features, target_col, filtered_data_map
        )

        overall_bad_rate = float(working_df[target_col].mean())

        # 对每个变量做箱标签映射
        bin_cols = []
        for feat in features:
            cfg = configs[feat]
            bin_col = f"__bin_{feat}"
            working_df[bin_col] = CrossBinningAnalyzer._apply_binning(
                working_df[feat], cfg
            )
            bin_cols.append(bin_col)

        # 按箱标签 groupby 计算统计量
        grouped = working_df.groupby(bin_cols, observed=False)[target_col].agg(
            ["count", "sum"]
        )
        grouped.columns = ["total", "bad"]
        grouped["good"] = grouped["total"] - grouped["bad"]
        grouped["bad_rate"] = grouped["bad"] / grouped["total"]
        grouped["total_pct"] = grouped["total"] / len(working_df)
        grouped["lift"] = grouped["bad_rate"] / overall_bad_rate

        # WOE / IV 计算
        total_bad = int(working_df[target_col].sum())
        total_good = len(working_df) - total_bad
        eps = 1e-10
        grouped["bad_dist"] = grouped["bad"] / total_bad
        grouped["good_dist"] = grouped["good"] / total_good
        grouped["woe"] = np.log((grouped["good_dist"] + eps) / (grouped["bad_dist"] + eps))
        grouped["iv"] = (grouped["good_dist"] - grouped["bad_dist"]) * grouped["woe"]

        # 筛选
        mask = CrossBinningAnalyzer._apply_filters(
            grouped, overall_bad_rate, filters
        )
        filtered = grouped[mask].copy()

        # 排序
        filtered = CrossBinningAnalyzer._sort_results(filtered, filters.sort_by)

        # 构建规则
        rules = CrossBinningAnalyzer._build_rules(
            filtered, features, overall_bad_rate
        )

        return CrossBinningResult(
            overall_bad_rate=overall_bad_rate,
            total_combinations=len(grouped),
            filtered_combinations=len(filtered),
            rules=rules,
            feature_names=features,
            feature_bin_counts={f: len(configs[f].splits) - 1 for f in features},
        )

    @staticmethod
    def build_heatmap_data(
        df: pd.DataFrame,
        target_col: str,
        feature_x: str,
        feature_y: str,
        config_x: BinningConfig,
        config_y: BinningConfig,
        filtered_data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> CrossBinningHeatmapData:
        """构建二维热力图数据"""
        working_df = CrossBinningAnalyzer._build_working_df(
            df, [feature_x, feature_y], target_col, filtered_data_map
        )

        working_df["__bin_x"] = CrossBinningAnalyzer._apply_binning(
            working_df[feature_x], config_x
        )
        working_df["__bin_y"] = CrossBinningAnalyzer._apply_binning(
            working_df[feature_y], config_y
        )

        # 确保 y 轴从上到下是有序的（箱标签按中值排序）
        grouped = (
            working_df.groupby(["__bin_y", "__bin_x"], observed=False)[target_col]
            .agg(["count", "sum", "mean"])
            .reset_index()
        )
        grouped.columns = ["__bin_y", "__bin_x", "total", "bad", "bad_rate"]
        grouped["lift"] = grouped["bad_rate"] / working_df[target_col].mean()

        # 提取唯一标签并排序
        x_labels = sorted(grouped["__bin_x"].unique(), key=lambda x: _interval_sort_key(x))
        y_labels = sorted(grouped["__bin_y"].unique(), key=lambda x: _interval_sort_key(x), reverse=True)

        # 构建矩阵
        bad_rate_matrix = grouped.pivot(index="__bin_y", columns="__bin_x", values="bad_rate")
        sample_count_matrix = grouped.pivot(index="__bin_y", columns="__bin_x", values="total")
        lift_matrix = grouped.pivot(index="__bin_y", columns="__bin_x", values="lift")

        # 按排序后的标签重新索引
        bad_rate_matrix = bad_rate_matrix.reindex(index=y_labels, columns=x_labels)
        sample_count_matrix = sample_count_matrix.reindex(index=y_labels, columns=x_labels)
        lift_matrix = lift_matrix.reindex(index=y_labels, columns=x_labels)

        def fmt_label(label):
            if isinstance(label, pd.Interval):
                left = f"{label.left:.1f}" if np.isfinite(label.left) else "-∞"
                right = f"{label.right:.1f}" if np.isfinite(label.right) else "+∞"
                return f"[{left},{right})"
            return str(label)

        return CrossBinningHeatmapData(
            feature_x=feature_x,
            feature_y=feature_y,
            x_labels=[fmt_label(l) for l in x_labels],
            y_labels=[fmt_label(l) for l in y_labels],
            bad_rate_matrix=bad_rate_matrix,
            sample_count_matrix=sample_count_matrix,
            lift_matrix=lift_matrix,
        )

    # ===================== 私有方法 =====================

    @staticmethod
    def _validate_inputs(df, target_col, features, configs, filters):
        if len(features) < 2:
            raise ValueError("至少需要选择2个变量")
        if len(features) > 5:
            raise ValueError("最多支持5个变量同时交叉")

        total_bins = 1
        for feat in features:
            if feat not in configs:
                raise ValueError(f"变量 '{feat}' 未进行分箱")
            n_bins = len(configs[feat].splits) - 1
            total_bins *= n_bins

        if total_bins > filters.max_combinations:
            raise ValueError(
                f"笛卡尔积组合数 {total_bins} 超过上限 {filters.max_combinations}，"
                f"建议减少变量数或合并部分变量的箱"
            )

    @staticmethod
    def _build_working_df(df, features, target_col, filtered_data_map):
        """构建工作数据集（取各变量过滤后数据的索引交集）"""
        cols = [target_col] + features
        working = df[cols].copy()

        if filtered_data_map:
            valid_indices = set(working.index)
            for feat in features:
                if feat in filtered_data_map and filtered_data_map[feat] is not None:
                    valid_indices &= set(filtered_data_map[feat].index)
            if valid_indices:
                working = working.loc[list(valid_indices)]

        working = working.dropna(subset=[target_col])
        return working

    @staticmethod
    def _apply_binning(series: pd.Series, cfg: BinningConfig) -> pd.Series:
        """应用分箱配置，返回箱标签"""
        unique_splits = sorted(list(set(cfg.splits)))
        binned = pd.cut(series, bins=unique_splits, include_lowest=True)
        return binned

    @staticmethod
    def _apply_filters(grouped, overall_bad_rate, filters):
        if filters.show_all:
            # 不过滤模式：展示全部组合
            return pd.Series(True, index=grouped.index)

        # 样本占比筛选
        mask_sample = grouped["total_pct"] >= filters.min_sample_rate

        # 坏账率偏离度筛选（高风险 OR 优质客群）
        high_thresh = overall_bad_rate * filters.bad_rate_high_multiplier
        low_thresh = overall_bad_rate * filters.bad_rate_low_multiplier
        mask_rate = (grouped["bad_rate"] >= high_thresh) | (grouped["bad_rate"] <= low_thresh)

        # Lift 筛选：高风险方向 lift >= min_lift，优质客群方向 lift <= 1/min_lift
        if filters.min_lift > 1.0:
            mask_lift = (grouped["lift"] >= filters.min_lift) | (grouped["lift"] <= (1.0 / filters.min_lift))
        else:
            mask_lift = True  # min_lift <= 1.0 时不做 lift 筛选

        return mask_sample & mask_rate & mask_lift

    @staticmethod
    def _sort_results(grouped, sort_by):
        if sort_by == "bad_rate_desc":
            return grouped.sort_values("bad_rate", ascending=False)
        elif sort_by == "lift_desc":
            return grouped.sort_values("lift", ascending=False)
        elif sort_by == "sample_desc":
            return grouped.sort_values("total", ascending=False)
        return grouped

    @staticmethod
    def _build_rules(grouped, features, overall_bad_rate) -> List[CrossBinningRule]:
        rules = []
        bin_col_names = [f"__bin_{f}" for f in features]

        for idx, (group_key, row) in enumerate(grouped.iterrows()):
            conditions = []
            condition_parts = []

            if len(features) == 1:
                group_keys = [group_key]
            else:
                group_keys = list(group_key)

            for feat, bin_label in zip(features, group_keys):
                if isinstance(bin_label, pd.Interval):
                    left = (
                        CrossBinningAnalyzer._fmt_value(bin_label.left)
                        if np.isfinite(bin_label.left)
                        else "-∞"
                    )
                    right = (
                        CrossBinningAnalyzer._fmt_value(bin_label.right)
                        if np.isfinite(bin_label.right)
                        else "+∞"
                    )
                    label_str = f"[{left}, {right})"
                    condition_parts.append(f"{feat}∈{label_str}")
                else:
                    label_str = str(bin_label)
                    condition_parts.append(f"{feat}={label_str}")

                conditions.append(
                    {
                        "variable": feat,
                        "bin_label": label_str,
                        "interval": (
                            bin_label if isinstance(bin_label, pd.Interval) else None
                        ),
                    }
                )

            bad_rate = float(row["bad_rate"])
            if bad_rate >= overall_bad_rate * 3.0:
                risk_level = "extreme-high"
            elif bad_rate >= overall_bad_rate * 2.0:
                risk_level = "high"
            elif bad_rate <= overall_bad_rate * 0.5:
                risk_level = "low"
            else:
                risk_level = "normal"

            rule = CrossBinningRule(
                rule_id=f"Rule-{idx + 1:03d}",
                risk_level=risk_level,
                conditions=conditions,
                condition_str=" ∧ ".join(condition_parts),
                sample_count=int(row["total"]),
                sample_rate=float(row["total_pct"]),
                bad_count=int(row["bad"]),
                bad_rate=bad_rate,
                overall_bad_rate=overall_bad_rate,
                lift=float(row["lift"]),
                woe=float(row["woe"]),
                iv=float(row["iv"]),
            )
            rules.append(rule)

        return rules

    @staticmethod
    def _fmt_value(v):
        """智能格式化数值：大数用整数+千分位，小数保留合适精度"""
        if not np.isfinite(v):
            return str(v)
        av = abs(v)
        if av >= 10000:
            return f"{v:,.0f}"
        elif av >= 100:
            return f"{v:.1f}"
        elif av >= 1:
            return f"{v:.2f}"
        else:
            return f"{v:.3f}"


def _interval_sort_key(interval):
    """用于对 pd.Interval 进行排序的辅助函数"""
    if isinstance(interval, pd.Interval):
        left = interval.left if np.isfinite(interval.left) else -np.inf
        return left
    return str(interval)
