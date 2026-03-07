import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LogisticRegression

def generate_mock_data(n_samples=20000, n_features=30, output_file='tests/mock_data.xlsx'):
    """
    生成模拟的风控建模数据。
    
    参数:
    n_samples (int): 样本数量
    n_features (int): 特征数量
    output_file (str): 输出文件路径
    """
    print(f"Generating mock data with {n_samples} samples and {n_features} features...")
    
    # 设置随机种子以保证结果可复现
    np.random.seed(42)
    
    # 生成特征数据
    # 假设前 20 个是连续型变量 (例如：年龄、收入、各种评分)
    # 假设后 10 个是离散型变量 (例如：性别、学历、职业代码)
    
    data = {}
    
    # 1. 连续型变量 (feature_01 ~ feature_20)
    for i in range(1, 21):
        col_name = f'feature_{i:02d}'
        # 使用不同的分布生成数据
        if i % 3 == 0:
            # 正态分布 (如：信用评分)
            data[col_name] = np.random.normal(loc=600, scale=50, size=n_samples)
        elif i % 3 == 1:
            # 对数正态分布 (如：收入，呈现长尾分布)
            data[col_name] = np.random.lognormal(mean=10, sigma=1, size=n_samples)
        else:
            # 均匀分布 (如：年龄)
            data[col_name] = np.random.uniform(low=18, high=60, size=n_samples)
            
    # 2. 离散型变量 (feature_21 ~ feature_30)
    for i in range(21, 31):
        col_name = f'feature_{i:02d}'
        # 随机生成类别
        n_categories = np.random.randint(2, 6) # 2到5个类别
        categories = [f'cat_{j}' for j in range(n_categories)]
        data[col_name] = np.random.choice(categories, size=n_samples)

    df = pd.DataFrame(data)
    
    # 3. 生成目标变量 (target)
    # 为了保证特征与目标变量有相关性，我们构造一个线性组合，并通过 Sigmoid 函数转化为概率
    
    # 先处理数值型特征
    numerical_cols = [c for c in df.columns if 'feature' in c and int(c.split('_')[1]) <= 20]
    
    # 随机生成权重
    weights = np.random.randn(len(numerical_cols))
    
    # 计算线性得分 (Logit)
    # 标准化特征以避免某些大数值特征主导
    df_norm = (df[numerical_cols] - df[numerical_cols].mean()) / df[numerical_cols].std()
    logits = np.dot(df_norm, weights)
    
    # 加入一些噪声
    logits += np.random.normal(0, 1, size=n_samples)
    
    # 转换为概率
    probs = 1 / (1 + np.exp(-logits))
    
    # 根据概率生成 0/1 标签 (target)
    # 调整阈值以控制 Bad Rate (假设 default rate 约为 5% - 10%)
    # 这里直接用二项分布生成
    df['target'] = np.random.binomial(n=1, p=probs)
    
    # 打印一些统计信息
    print(f"Data shape: {df.shape}")
    print(f"Target distribution:\n{df['target'].value_counts(normalize=True)}")
    
    # 4. 保存为 Excel
    print(f"Saving to {output_file}...")
    # 确保目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_excel(output_file, index=False)
    print("Done!")

if __name__ == "__main__":
    generate_mock_data()
