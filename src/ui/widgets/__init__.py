"""UI 组件模块

包含可复用的 UI 组件和控件。
"""

from src.ui.widgets.optbinning_config_panel_compact import (
    OptbinningConfigPanel,
    SOLVER_OPTIONS,
    DIVERGENCE_OPTIONS,
    MONOTONIC_TREND_OPTIONS,
    DTYPE_OPTIONS,
)

from src.ui.widgets.rich_tooltip_label import (
    RichTooltipLabel,
    RichTooltipHelper,
    RichTooltipWrapper,
    TooltipLabel,
    TooltipHelper,
    get_param_tooltip,
    PARAM_TOOLTIPS,
    create_labeled_widget,
    add_tooltip_to_widget,
)

from src.ui.widgets.advanced_params_panel_compact import (
    AdvancedParamsPanel,
)

from src.ui.widgets.solve_status_widget import (
    SolveStatusWidget,
    SolveStatusIndicator,
)

__all__ = [
    # Optbinning 配置面板
    'OptbinningConfigPanel',
    'SOLVER_OPTIONS',
    'DIVERGENCE_OPTIONS',
    'MONOTONIC_TREND_OPTIONS',
    'DTYPE_OPTIONS',
    # 富文本提示组件
    'RichTooltipLabel',
    'RichTooltipHelper',
    'RichTooltipWrapper',
    'TooltipLabel',  # 别名
    'TooltipHelper',  # 别名
    'get_param_tooltip',
    'PARAM_TOOLTIPS',
    'create_labeled_widget',
    'add_tooltip_to_widget',
    # 高级参数面板
    'AdvancedParamsPanel',
    # 求解状态组件
    'SolveStatusWidget',
    'SolveStatusIndicator',
]
