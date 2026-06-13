"""
KNN 分类结果可视化（服务器版，无需 GUI）
"""
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，无需 tkinter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import Counter

# ========== 设置中文字体 ==========
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 读取数据（容错解析） ==========
def load_predictions(filepath='predictions.txt'):
    """读取 MapReduce 输出，自动检测格式"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            # 用所有空白字符分割
            parts = line.split()
            if len(parts) < 3:
                print(f"跳过(列数<3) 第{line_num}行: {line[:50]}")
                continue
            
            ts_code = parts[0]
            
            # 找到行业和数值列
            industry = ''
            confidence = 0
            neighbors = 0
            votes = ''
            name_parts = []
            found_industry = False
            
            for i in range(1, len(parts)):
                part = parts[i]
                try:
                    val = float(part)
                    # 这是置信度（数值）
                    confidence = val
                    # 前面的都是行业名
                    industry = ' '.join(parts[1:i])
                    name_parts = []  # 行业后面才是名称（这里假设输出格式: code name industry conf）
                    # 实际上 name 在 code 之后，industry 之前
                    # 重新计算：parts[1] 到 parts[i-1] 中，最后一个是行业，其余是名称
                    if i > 2:
                        name_parts = parts[1:i-1]  # code 之后、industry 之前的都是名称
                        industry = parts[i-1]
                    else:
                        industry = parts[1]
                    
                    if i + 1 < len(parts):
                        neighbors = int(parts[i+1])
                    if i + 2 < len(parts):
                        votes = parts[i+2]
                    found_industry = True
                    break
                except ValueError:
                    continue
            
            if not found_industry:
                industry = parts[-1]
            
            name = ' '.join(name_parts) if name_parts else parts[1] if len(parts) > 1 else ''
            
            data.append({
                'ts_code': ts_code,
                'name': name,
                'industry': industry,
                'confidence': confidence,
                'neighbors': neighbors,
                'votes': votes
            })
    
    return pd.DataFrame(data)

# ========== 图表1：散点图 ==========
def plot_scatter(df):
    fig, ax = plt.subplots(figsize=(16, 8))
    
    industries = df['industry'].unique()
    industry_to_x = {ind: i for i, ind in enumerate(industries)}
    df_temp = df.copy()
    df_temp['x'] = df_temp['industry'].map(industry_to_x)
    np.random.seed(42)
    df_temp['x_jitter'] = df_temp['x'] + np.random.uniform(-0.4, 0.4, len(df_temp))
    
    colors = plt.cm.tab20(np.linspace(0, 1, len(industries)))
    
    for i, (ind, group) in enumerate(df_temp.groupby('industry')):
        ax.scatter(group['x_jitter'], group['confidence'],
                   c=[colors[i % len(colors)]], alpha=0.5, s=8, edgecolors='none')
    
    ax.set_xlabel('Industry', fontsize=12)
    ax.set_ylabel('Confidence', fontsize=12)
    ax.set_title('KNN Industry Classification Scatter Plot', fontsize=14)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks(range(len(industries)))
    ax.set_xticklabels(industries, rotation=90, fontsize=6)
    ax.axhline(y=0.8, color='green', linestyle='--', alpha=0.5)
    ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig('scatter_plot.png', dpi=150)
    print("散点图已保存: scatter_plot.png")
    plt.close()

# ========== 图表2：行业分布 ==========
def plot_industry_distribution(df):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    dist = df['industry'].value_counts().head(20)
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(dist)))
    bars = ax.barh(range(len(dist)), dist.values, color=colors)
    
    ax.set_yticks(range(len(dist)))
    ax.set_yticklabels(dist.index, fontsize=8)
    ax.set_xlabel('Count', fontsize=12)
    ax.set_title('Top 20 Predicted Industries', fontsize=14)
    ax.invert_yaxis()
    
    for bar, val in zip(bars, dist.values):
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, str(val), va='center', fontsize=8)
    
    ax.grid(True, alpha=0.2, axis='x')
    plt.tight_layout()
    plt.savefig('industry_distribution.png', dpi=150)
    print("行业分布图已保存: industry_distribution.png")
    plt.close()

# ========== 图表3：置信度分布 ==========
def plot_confidence_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1 = axes[0]
    ax1.hist(df['confidence'], bins=20, edgecolor='white', color='steelblue', alpha=0.8)
    ax1.axvline(x=0.8, color='green', linestyle='--', linewidth=2, label='80%')
    ax1.axvline(x=0.5, color='red', linestyle='--', linewidth=2, label='50%')
    ax1.axvline(x=df['confidence'].mean(), color='orange', linestyle='-', linewidth=2,
                label=f'Mean: {df["confidence"].mean():.2%}')
    ax1.set_xlabel('Confidence', fontsize=11)
    ax1.set_ylabel('Samples', fontsize=11)
    ax1.set_title('Confidence Distribution', fontsize=13)
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.2)
    
    ax2 = axes[1]
    high = (df['confidence'] >= 0.8).sum()
    mid = ((df['confidence'] >= 0.5) & (df['confidence'] < 0.8)).sum()
    low = (df['confidence'] < 0.5).sum()
    
    sizes = [high, mid, low]
    labels = [f'High(>=80%): {high}', f'Mid(50-80%): {mid}', f'Low(<50%): {low}']
    colors_pie = ['#4caf50', '#ff9800', '#f44336']
    
    ax2.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Confidence Level', fontsize=13)
    
    plt.tight_layout()
    plt.savefig('confidence_distribution.png', dpi=150)
    print("置信度分布图已保存: confidence_distribution.png")
    plt.close()

# ========== 图表4：综合仪表盘 ==========
def plot_dashboard(df):
    fig = plt.figure(figsize=(18, 14))
    
    # 左上：散点图
    ax1 = fig.add_subplot(2, 2, 1)
    industries = df['industry'].unique()
    industry_to_x = {ind: i for i, ind in enumerate(industries)}
    df_temp = df.copy()
    df_temp['x'] = df_temp['industry'].map(industry_to_x)
    np.random.seed(42)
    df_temp['x_jitter'] = df_temp['x'] + np.random.uniform(-0.4, 0.4, len(df_temp))
    
    for i, (ind, group) in enumerate(df_temp.groupby('industry')):
        ax1.scatter(group['x_jitter'], group['confidence'], alpha=0.4, s=5)
    
    ax1.set_ylabel('Confidence')
    ax1.set_title('Scatter Plot')
    ax1.axhline(y=0.8, color='green', linestyle='--', alpha=0.5)
    ax1.axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.2)
    
    # 右上：直方图
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.hist(df['confidence'], bins=25, edgecolor='white', color='steelblue', alpha=0.8)
    ax2.axvline(x=df['confidence'].mean(), color='orange', linewidth=2)
    ax2.axvline(x=0.8, color='green', linestyle='--')
    ax2.axvline(x=0.5, color='red', linestyle='--')
    ax2.set_xlabel('Confidence')
    ax2.set_ylabel('Count')
    ax2.set_title('Histogram')
    ax2.grid(True, alpha=0.2)
    
    # 左下：行业分布
    ax3 = fig.add_subplot(2, 2, 3)
    dist = df['industry'].value_counts().head(15)
    ax3.barh(range(len(dist)), dist.values, color=plt.cm.viridis(np.linspace(0.2, 0.9, len(dist))))
    ax3.set_yticks(range(len(dist)))
    ax3.set_yticklabels(dist.index, fontsize=7)
    ax3.set_xlabel('Count')
    ax3.set_title(f'Top 15 Industries (Total: {df["industry"].nunique()})')
    ax3.invert_yaxis()
    
    # 右下：统计
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    stats = (
        f"Total Samples: {len(df)}\n"
        f"Industries: {df['industry'].nunique()}\n"
        f"Mean Confidence: {df['confidence'].mean():.2%}\n"
        f"High(>=80%): {(df['confidence']>=0.8).sum()}\n"
        f"Mid(50-80%): {((df['confidence']>=0.5)&(df['confidence']<0.8)).sum()}\n"
        f"Low(<50%): {(df['confidence']<0.5).sum()}\n"
        f"Max: {df['confidence'].max():.2%}\n"
        f"Min: {df['confidence'].min():.2%}"
    )
    ax4.text(0.5, 0.5, stats, transform=ax4.transAxes, fontsize=14,
             verticalalignment='center', horizontalalignment='center',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))
    
    plt.suptitle('KNN Classification Dashboard', fontsize=18, y=0.98)
    plt.tight_layout()
    plt.savefig('dashboard.png', dpi=150)
    print("综合仪表盘已保存: dashboard.png")
    plt.close()

# ========== 主函数 ==========
def main():
    print("=" * 50)
    print("KNN 分类结果可视化")
    print("=" * 50)
    
    df = load_predictions('predictions.txt')
    if len(df) == 0:
        print("错误: 未加载到任何数据")
        return
    
    print(f"加载数据: {len(df)} 条预测结果")
    print(f"行业数: {df['industry'].nunique()}")
    print(f"平均置信度: {df['confidence'].mean():.2%}")
    
    print("\n1. 生成散点图...")
    plot_scatter(df)
    
    print("2. 生成行业分布图...")
    plot_industry_distribution(df)
    
    print("3. 生成置信度分布图...")
    plot_confidence_distribution(df)
    
    print("4. 生成综合仪表盘...")
    plot_dashboard(df)
    
    print("\n✅ 所有图表已生成!")

if __name__ == '__main__':
    main()