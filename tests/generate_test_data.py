"""生成多场景测试数据用于分箱策略对比测试

生成10种不同特征的数据场景，覆盖各种业务中可能遇到的情况。
"""
import pandas as pd
import numpy as np
from typing import Tuple


def generate_linear_monotonic(n: int = 10000, seed: int = 42) -> Tuple[pd.Series, pd.Series]:
    """场景1: 强线性相关（完全单调）
    
    特征与目标呈强线性关系，分箱应该很容易达到单调。
    """
    np.random.seed(seed)
    x = np.random.normal(50, 15, n)
    # 线性关系：x越大，y=1概率越高
    prob = 1 / (1 + np.exp(-(x - 50) / 10))  # sigmoid转换
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='linear_monotonic'), pd.Series(y, name='target')


def generate_weak_noisy(n: int = 10000, seed: int = 43) -> Tuple[pd.Series, pd.Series]:
    """场景2: 弱相关+噪音（波动大）
    
    特征与目标相关性弱，且有大量噪音，考验抗噪能力。
    """
    np.random.seed(seed)
    x = np.random.normal(50, 20, n)
    # 弱相关 + 强噪音
    prob = 0.3 + 0.1 * (x - 50) / 50 + np.random.normal(0, 0.1, n)
    prob = np.clip(prob, 0.01, 0.99)
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='weak_noisy'), pd.Series(y, name='target')


def generate_u_shaped(n: int = 10000, seed: int = 44) -> Tuple[pd.Series, pd.Series]:
    """场景3: U型关系（非单调）
    
    中间低两边高的U型关系，对单调分箱是挑战。
    """
    np.random.seed(seed)
    x = np.random.normal(0, 2, n)
    # U型：x远离0时y=1概率增加
    prob = 0.1 + 0.8 * (x ** 2) / (4 + x ** 2)
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='u_shaped'), pd.Series(y, name='target')


def generate_long_tail(n: int = 10000, seed: int = 45) -> Tuple[pd.Series, pd.Series]:
    """场景4: 长尾分布（指数分布）
    
    收入、消费等常见长尾数据。
    """
    np.random.seed(seed)
    x = np.random.exponential(100, n)
    # 长尾分布，x越大y=1概率越高但增长减缓
    prob = 1 - np.exp(-x / 200)
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='long_tail'), pd.Series(y, name='target')


def generate_bimodal(n: int = 10000, seed: int = 46) -> Tuple[pd.Series, pd.Series]:
    """场景5: 双峰分布（两个群体）
    
    两个明显不同的群体，如好坏客户混合。
    """
    np.random.seed(seed)
    # 两个正态分布混合
    n1 = n // 2
    n2 = n - n1
    x1 = np.random.normal(30, 5, n1)
    x2 = np.random.normal(70, 5, n2)
    x = np.concatenate([x1, x2])
    
    # 第一峰y=0多，第二峰y=1多
    y1 = (np.random.random(n1) < 0.2).astype(int)
    y2 = (np.random.random(n2) < 0.8).astype(int)
    y = np.concatenate([y1, y2])
    
    # 随机打乱
    idx = np.random.permutation(n)
    return pd.Series(x[idx], name='bimodal'), pd.Series(y[idx], name='target')


def generate_small_sample(n: int = 500, seed: int = 47) -> Tuple[pd.Series, pd.Series]:
    """场景6: 小样本（n=500）
    
    小样本情况，考验稳定性。
    """
    np.random.seed(seed)
    x = np.random.normal(50, 15, n)
    prob = 1 / (1 + np.exp(-(x - 50) / 15))
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='small_sample'), pd.Series(y, name='target')


def generate_high_cardinality(n: int = 10000, seed: int = 48) -> Tuple[pd.Series, pd.Series]:
    """场景7: 高基数类别特征（1000+类别）
    
    类别型特征，如邮编、商户ID等。
    """
    np.random.seed(seed)
    # 1000个类别，每个类别有基础概率
    categories = np.random.choice(1000, n)
    base_probs = np.random.beta(2, 5, 1000)  # 每个类别的基础概率
    probs = base_probs[categories]
    y = (np.random.random(n) < probs).astype(int)
    return pd.Series(categories, name='high_cardinality'), pd.Series(y, name='target')


def generate_extreme_imbalance(n: int = 10000, seed: int = 49) -> Tuple[pd.Series, pd.Series]:
    """场景8: 极端不平衡（99:1）
    
    欺诈检测等常见不平衡场景。
    """
    np.random.seed(seed)
    x = np.random.normal(50, 15, n)
    # 99%为0，1%为1
    prob = 0.01 + 0.1 * (x > 60).astype(float)
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='extreme_imbalance'), pd.Series(y, name='target')


def generate_random_no_relation(n: int = 10000, seed: int = 50) -> Tuple[pd.Series, pd.Series]:
    """场景9: 完全随机（无相关性）
    
    特征与目标完全无关，考验保底机制。
    """
    np.random.seed(seed)
    x = np.random.normal(50, 15, n)
    y = (np.random.random(n) < 0.3).astype(int)  # 完全随机
    return pd.Series(x, name='random'), pd.Series(y, name='target')


def generate_step_function(n: int = 10000, seed: int = 51) -> Tuple[pd.Series, pd.Series]:
    """场景10: 阶梯函数（分段常数）
    
    业务规则常见的阶梯型关系。
    """
    np.random.seed(seed)
    x = np.random.uniform(0, 100, n)
    # 阶梯型概率
    prob = np.where(x < 25, 0.1,
           np.where(x < 50, 0.3,
           np.where(x < 75, 0.5, 0.8)))
    y = (np.random.random(n) < prob).astype(int)
    return pd.Series(x, name='step_function'), pd.Series(y, name='target')


def save_test_data(output_dir: str = 'tests/test_data'):
    """生成并保存所有测试数据"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    generators = [
        ('01_linear_monotonic', generate_linear_monotonic),
        ('02_weak_noisy', generate_weak_noisy),
        ('03_u_shaped', generate_u_shaped),
        ('04_long_tail', generate_long_tail),
        ('05_bimodal', generate_bimodal),
        ('06_small_sample', generate_small_sample),
        ('07_high_cardinality', generate_high_cardinality),
        ('08_extreme_imbalance', generate_extreme_imbalance),
        ('09_random', generate_random_no_relation),
        ('10_step_function', generate_step_function),
    ]
    
    all_data = {}
    
    for name, generator in generators:
        x, y = generator()
        df = pd.DataFrame({'x': x, 'target': y})
        
        # 保存单个文件
        filepath = f'{output_dir}/{name}.csv'
        df.to_csv(filepath, index=False)
        
        # 汇总信息
        all_data[name] = {
            'n_samples': len(df),
            'event_rate': df['target'].mean(),
            'x_mean': df['x'].mean(),
            'x_std': df['x'].std(),
            'x_min': df['x'].min(),
            'x_max': df['x'].max(),
        }
        
        print(f"✅ 生成 {name}: {len(df)} 样本, 正例率 {df['target'].mean():.2%}")
    
    # 保存汇总信息
    summary_df = pd.DataFrame(all_data).T
    summary_df.to_csv(f'{output_dir}/summary.csv')
    print(f"\n📊 汇总信息已保存到 {output_dir}/summary.csv")
    
    return summary_df


if __name__ == '__main__':
    summary = save_test_data()
    print("\n" + "="*60)
    print("测试数据生成完成！")
    print("="*60)
    print(summary)
