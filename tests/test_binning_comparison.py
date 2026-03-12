"""分箱策略全面对比测试

对比以下策略在10种数据场景下的表现：
1. EqualFrequencyBinner - 等频分箱
2. EqualWidthBinner - 等宽分箱
3. DecisionTreeBinner - 决策树分箱
4. ChiMergeBinner - 卡方分箱
5. BestKSBinner - Best-KS分箱
6. SmartMonotonicBinner - 智能单调分箱（我们的方案）
"""
import pandas as pd
import numpy as np
import time
import os
import sys
import warnings
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有分箱器
from src.core.binning.unsupervised import EqualFrequencyBinner, EqualWidthBinner
from src.core.binning.supervised import DecisionTreeBinner, ChiMergeBinner, BestKSBinner
from src.core.binning.smart_monotonic import SmartMonotonicBinner

# 忽略警告
warnings.filterwarnings('ignore')


@dataclass
class BinningResult:
    """分箱结果数据结构"""
    strategy_name: str
    scenario_name: str
    n_bins: int
    is_monotonic: bool
    iv: float
    iv_loss: float  # 相对于原始决策树IV的损失
    exec_time: float
    success: bool
    error_msg: str = ""
    adjustment_method: str = ""  # 仅SmartMonotonicBinner使用


def check_monotonic(x: pd.Series, y: pd.Series, splits: List[float], trend: str = 'auto') -> Tuple[bool, str]:
    """检查分箱结果是否单调"""
    try:
        if len(splits) < 3:
            return True, 'ascending'
        
        x_binned = pd.cut(x, bins=splits, include_lowest=True)
        rates = x_binned.groupby(x_binned, observed=False).apply(lambda g: y[g.index].mean())
        
        if len(rates) < 2:
            return True, 'ascending'
        
        # 检查递增和递减
        asc = all(rates.iloc[i] <= rates.iloc[i+1] + 1e-10 for i in range(len(rates)-1))
        desc = all(rates.iloc[i] >= rates.iloc[i+1] - 1e-10 for i in range(len(rates)-1))
        
        if asc:
            return True, 'ascending'
        elif desc:
            return True, 'descending'
        else:
            return False, 'ascending' if sum(rates.diff().dropna() > 0) > len(rates)/2 else 'descending'
    except:
        return False, 'ascending'


def calculate_iv(x: pd.Series, y: pd.Series, splits: List[float]) -> float:
    """计算IV值"""
    try:
        if len(splits) < 3:
            return 0.0
        
        x_binned = pd.cut(x, bins=splits, include_lowest=True)
        total_good = (y == 0).sum()
        total_bad = (y == 1).sum()
        
        if total_bad == 0 or total_good == 0:
            return 0.0
        
        iv = 0.0
        for _, group in x_binned.groupby(x_binned, observed=False):
            good = (y[group.index] == 0).sum()
            bad = (y[group.index] == 1).sum()
            
            if good == 0 or bad == 0:
                continue
            
            good_dist = good / total_good
            bad_dist = bad / total_bad
            iv += (bad_dist - good_dist) * np.log(bad_dist / good_dist)
        
        return max(0, iv)
    except:
        return 0.0


class BinningComparisonTest:
    """分箱策略对比测试框架"""
    
    def __init__(self, data_dir: str = 'tests/test_data', max_bins: int = 5):
        self.data_dir = data_dir
        self.max_bins = max_bins
        self.results: List[BinningResult] = []
        
        # 初始化所有分箱器
        self.binner_map = {
            'EqualFrequency': EqualFrequencyBinner(),
            'EqualWidth': EqualWidthBinner(),
            'DecisionTree': DecisionTreeBinner(),
            'ChiMerge': ChiMergeBinner(),
            'BestKS': BestKSBinner(),
            'SmartMonotonic': SmartMonotonicBinner(),
        }
    
    def load_scenario_data(self, scenario_file: str) -> Tuple[pd.Series, pd.Series]:
        """加载场景数据"""
        filepath = os.path.join(self.data_dir, scenario_file)
        df = pd.read_csv(filepath)
        return df['x'], df['target']
    
    def run_strategy(self, strategy_name: str, x: pd.Series, y: pd.Series, 
                     scenario_name: str) -> BinningResult:
        """运行单个策略并收集结果"""
        binner = self.binner_map[strategy_name]
        
        start_time = time.time()
        
        try:
            # 不同策略的参数适配
            if strategy_name in ['EqualFrequency', 'EqualWidth']:
                binner.fit(x, n_bins=self.max_bins)
                splits = binner.splits
            elif strategy_name == 'DecisionTree':
                binner.fit(x, y, max_leaf_nodes=self.max_bins)
                splits = binner.splits
            elif strategy_name == 'ChiMerge':
                binner.fit(x, y, max_bins=self.max_bins)
                splits = binner.splits
            elif strategy_name == 'BestKS':
                binner.fit(x, y, max_bins=self.max_bins)
                splits = binner.splits
            elif strategy_name == 'SmartMonotonic':
                binner.fit(x, y, max_bins=self.max_bins, adjustment_method='auto')
                splits = binner.splits
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            
            exec_time = time.time() - start_time
            
            # 计算指标
            is_mono, _ = check_monotonic(x, y, splits)
            iv = calculate_iv(x, y, splits)
            n_bins = len(splits) - 1
            
            # 获取调整方法（仅SmartMonotonic）
            adj_method = ""
            if strategy_name == 'SmartMonotonic':
                adj_method = binner.adjustment_method or ""
            
            # IV损失需要后续计算（相对于最优IV）
            result = BinningResult(
                strategy_name=strategy_name,
                scenario_name=scenario_name,
                n_bins=n_bins,
                is_monotonic=is_mono,
                iv=iv,
                iv_loss=0.0,  # 稍后计算
                exec_time=exec_time,
                success=True,
                adjustment_method=adj_method
            )
            
        except Exception as e:
            exec_time = time.time() - start_time
            result = BinningResult(
                strategy_name=strategy_name,
                scenario_name=scenario_name,
                n_bins=0,
                is_monotonic=False,
                iv=0.0,
                iv_loss=0.0,
                exec_time=exec_time,
                success=False,
                error_msg=str(e)
            )
        
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        # 获取所有场景文件
        scenario_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.csv') and f != 'summary.csv'])
        
        strategies = list(self.binner_map.keys())
        
        print("="*80)
        print("分箱策略全面对比测试")
        print("="*80)
        print(f"测试策略: {', '.join(strategies)}")
        print(f"场景数量: {len(scenario_files)}")
        print(f"最大箱数: {self.max_bins}")
        print("="*80)
        
        total_tests = len(scenario_files) * len(strategies)
        current = 0
        
        for scenario_file in scenario_files:
            scenario_name = scenario_file.replace('.csv', '')
            x, y = self.load_scenario_data(scenario_file)
            
            print(f"\n📊 场景: {scenario_name} (n={len(x)})")
            print("-"*60)
            
            scenario_results = []
            
            for strategy_name in strategies:
                current += 1
                result = self.run_strategy(strategy_name, x, y, scenario_name)
                scenario_results.append(result)
                self.results.append(result)
                
                # 实时输出
                status = "✅" if result.success else "❌"
                mono = "单调" if result.is_monotonic else "非单调"
                print(f"  [{current}/{total_tests}] {status} {strategy_name:15s} | "
                      f"{result.n_bins}箱 | {mono} | IV={result.iv:.4f} | "
                      f"{result.exec_time*1000:.1f}ms")
                
                if not result.success:
                    print(f"      错误: {result.error_msg[:50]}")
            
            # 计算IV损失（相对于该场景下最高IV）
            max_iv = max([r.iv for r in scenario_results if r.success])
            for result in scenario_results:
                if result.success and max_iv > 0:
                    result.iv_loss = (max_iv - result.iv) / max_iv
        
        print("\n" + "="*80)
        print("测试完成！")
        print("="*80)
    
    def generate_report(self) -> pd.DataFrame:
        """生成对比报告"""
        df = pd.DataFrame([{
            '策略': r.strategy_name,
            '场景': r.scenario_name,
            '成功': r.success,
            '箱数': r.n_bins,
            '单调': r.is_monotonic,
            'IV': r.iv,
            'IV损失': r.iv_loss,
            '耗时(ms)': r.exec_time * 1000,
            '调整方法': r.adjustment_method,
        } for r in self.results])
        
        return df
    
    def generate_summary(self) -> pd.DataFrame:
        """生成汇总统计"""
        df = self.generate_report()
        
        summary = df.groupby('策略').agg({
            '成功': 'mean',
            '单调': 'mean',
            'IV': 'mean',
            'IV损失': 'mean',
            '耗时(ms)': 'mean',
            '箱数': 'mean',
        }).round(4)
        
        summary.columns = ['成功率', '单调率', '平均IV', '平均IV损失', '平均耗时(ms)', '平均箱数']
        
        # 计算综合得分
        # 得分 = 单调率*40 + 成功率*30 + (1-IV损失)*20 + (1-归一化耗时)*10
        summary['综合得分'] = (
            summary['单调率'] * 40 +
            summary['成功率'] * 30 +
            (1 - summary['平均IV损失']) * 20 +
            (1 - summary['平均耗时(ms)'] / summary['平均耗时(ms)'].max()) * 10
        ).round(2)
        
        return summary.sort_values('综合得分', ascending=False)
    
    def save_results(self, output_dir: str = 'tests/test_results'):
        """保存测试结果"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存详细结果
        df = self.generate_report()
        df.to_csv(f'{output_dir}/detailed_results_{timestamp}.csv', index=False)
        
        # 保存汇总
        summary = self.generate_summary()
        summary.to_csv(f'{output_dir}/summary_{timestamp}.csv')
        
        # 保存文本报告
        with open(f'{output_dir}/report_{timestamp}.txt', 'w') as f:
            f.write("="*80 + "\n")
            f.write("分箱策略对比测试报告\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            f.write("【综合排名】\n")
            f.write(summary.to_string())
            f.write("\n\n")
            
            f.write("【详细结果】\n")
            f.write(df.to_string())
        
        print(f"\n📁 结果已保存到 {output_dir}/")
        print(f"   - detailed_results_{timestamp}.csv")
        print(f"   - summary_{timestamp}.csv")
        print(f"   - report_{timestamp}.txt")
        
        return summary


def main():
    """主函数"""
    test = BinningComparisonTest(max_bins=5)
    test.run_all_tests()
    summary = test.save_results()
    
    print("\n" + "="*80)
    print("【综合排名】")
    print("="*80)
    print(summary)
    print("="*80)
    
    # 检查SmartMonotonic是否领先
    smart_rank = summary.index.get_loc('SmartMonotonic') + 1 if 'SmartMonotonic' in summary.index else -1
    
    print(f"\n🏆 SmartMonotonicBinner 排名: 第{smart_rank}名")
    
    if smart_rank == 1:
        print("✅ SmartMonotonicBinner 领先！")
    else:
        print("⚠️ SmartMonotonicBinner 未领先，需要优化")
        # 输出落后的指标
        smart_row = summary.loc['SmartMonotonic']
        print(f"\n📊 SmartMonotonicBinner 指标:")
        print(f"   单调率: {smart_row['单调率']:.2%}")
        print(f"   成功率: {smart_row['成功率']:.2%}")
        print(f"   平均IV: {smart_row['平均IV']:.4f}")
        print(f"   平均IV损失: {smart_row['平均IV损失']:.2%}")


if __name__ == '__main__':
    main()
