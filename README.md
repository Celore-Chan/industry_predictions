```markdown
# 🏭 KNN Industry Classifier for Chinese A-Share Market
```
> 基于 Hadoop MapReduce 的 K 近邻行业分类系统，对沪深 A 股 5000+ 上市公司进行行业归类，附带完整的数据采集、可视化流程。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Hadoop](https://img.shields.io/badge/Hadoop-3.x-green.svg)](https://hadoop.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 项目概览

本项目实现了一套完整的**A股上市公司行业分类**流水线：

1. **数据采集**：从东方财富数据中心爬取沪市及全部A股上市公司的历年财务报表（利润表、资产负债表、现金流量表）
2. **特征工程**：计算27项财务指标（盈利能力、增长趋势、成本结构、利润含金量、综合对比）
3. **KNN 分类**：基于 Hadoop MapReduce 实现分布式 KNN 算法，使用沪市成分股作为训练集，对全市场5000+股票进行行业归类
4. **结果可视化**：散点图、行业分布、置信度分析等图形化展示

---

## 🏗 系统架构

```
┌────────────────────────────────────────────────────────────┐
│                      Data Pipeline                         │
├───────────┬───────────┬──────────────┬─────────────────────┤
│ 东方财富API│  AKShare  │  Python 爬虫 │  财务报表原始数据     │
└─────┬─────┴─────┬─────┴──────┬───────┴──────────┬──────────┘
      │           │            │                  │
      ▼           ▼            ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Feature Engineering                      │
│  27维财务指标：ROE, ROA, 毛利率, 净利率, 营收增长率...         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Hadoop MapReduce KNN Classifier                │
│  ┌──────────┐    ┌───────────┐    ┌────────────────────┐   │
│  │  Mapper  │──▶│  Shuffle  │──▶│     Reducer        │   │
│  │ 距离计算  │    │  排序分组 │    │  K近邻投票 + 置信度  │   │
│  └──────────┘    └───────────┘    └────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Visualization                           │
│  散点图 | 行业分布 | 置信度直方图 | 综合仪表盘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 项目结构

```
.

├── code/
│   ├── astock_raw_capture.py        # 数据采集：爬取东方财富A股无行业财务三表并进行特征工程
│   ├── sh_capture.py                # 数据采集：爬取东方财富沪市财务三表并进行特征工程
│   ├── z-score.py                   # 数据标准化：Z-score 归一化
│   ├── IndustryKNN.java             # Hadoop MapReduce KNN 分类器
│   └── visualize.py                 # 结果可视化：matplotlib 图表   
├── src/
│   ├── train_standardized.csv       # 训练集（沪市）
│   ├── test_standardized.csv        # 测试集（全A股）
│   ├── astock_raw_features.csv      # 可信度统计图表
│   └── sh_features.csv              # 可信度散点分布
├── res/
│   ├── result.csv                   # MapReduce 输出结果
│   ├── scatter_plot.png             # 可信度散点分布
│   └── dashboard.png                # 可信度统计图表
└── README.md
```

---

### 环境要求

| 组件 | 版本要求 |
|:---|:---|
| Python | ≥ 3.8 |
| Hadoop | 3.x |
| Java | ≥ 11 |
| pip 依赖 | pandas, numpy, requests, akshare, matplotlib|

### 安装依赖

```bash
# Python 依赖
pip install pandas numpy requests akshare matplotlib

# Hadoop 环境（需自行配置）
# 确保 HDFS 和 YARN 正常运行
```

### 第一步：数据采集与特征工程

```bash
# 获取原始财务三表数据
python astock_raw_capture.py
python sh_capture.py
```

生成 `astock_raw_features.csv` 和 `sh_features.csv`。

### 第三步：数据标准化

```bash
# Z-score 标准化
python z-score.py
```

生成 `train_standardized.csv` 和 `test_standardized.csv`。

### 第四步：上传至 HDFS

```bash
hdfs dfs -mkdir -p /industry_predictions/input
hdfs dfs -put train_standardized.csv /industry_predictions/input/
hdfs dfs -put test_standardized.csv /industry_predictions/input/
```

### 第五步：运行 KNN 分类

```bash
# 编译
javac -classpath $(hadoop classpath) -d . IndustryKNN.java
jar cvf IndustryKNN.jar exp5/

# 运行（K=7，排除ST企业）
hadoop jar IndustryKNN.jar exp5.IndustryKNN \
    /exp5/input/train_standardized.csv \
    /exp5/output \
    /exp5/input/test_standardized.csv \
    7
```

### 第六步：结果可视化

```bash
# 命令行图表
python visualize.py
```

---

## 📊 特征指标说明

### 盈利能力质量组
| 指标 | 公式 |
|:---|:---|
| 毛利率 | `(营业收入 - 营业成本) / 营业收入` |
| 净利率 | `归母净利润 / 营业收入` |
| 营业利润率 | `营业利润 / 营业收入` |
| 扣非ROE | `扣非净利润 / 平均净资产` |
| 扣非ROA | `扣非净利润 / 平均总资产` |

### 增长与趋势组
| 指标 | 说明 |
|:---|:---|
| 营收增长率 | 最近一年同比 |
| 归母净利润增长率 | 最近一年同比 |
| 扣非净利润增长率 | 最近一年同比 |

### 成本费用结构组
| 指标 | 公式 |
|:---|:---|
| 销售费用率 | `销售费用 / 营业收入` |
| 管理费用率 | `管理费用 / 营业收入` |
| 财务费用率 | `财务费用 / 营业收入` |

### 利润含金量组
| 指标 | 公式 |
|:---|:---|
| 扣非净利润占比 | `扣非净利润 / 归母净利润` |
| 有效税率 | `所得税 / 利润总额` |

### 综合对比指标
| 指标 | 公式 |
|:---|:---|
| 盈利质量综合得分 | `毛利率 × 扣非净利润占比 × (1 - 销售费用率)` |
| 增收增利匹配度 | `营收增长率 - 总成本增长率` |

---

## 📈 输出结果格式

MapReduce 输出格式（`predictions.txt`）：

```
000001.SZ	平安银行	银行	0.86
000002.SZ	万科A	房地产	1.00
600519.SH	贵州茅台	食品饮料	0.71
```

| 列 | 说明 |
|:---|:---|
| `ts_code` | 股票代码（带交易所后缀） |
| `name` | 股票名称 |
| `industry` | 预测的申万一级行业 |
| `confidence` | KNN 投票置信度（0~1） |

---

## 🎯 可视化示例

### 散点图
![散点图](screenshots/scatter_plot.png)

### 综合仪表盘
![仪表盘](screenshots/dashboard.png)

---

## 🔧 关键特性

- ✅ **全量数据**：覆盖沪深北全部 A 股 5000+ 上市公司
- ✅ **27 维特征**：多维度财务指标体系
- ✅ **分布式计算**：基于 Hadoop MapReduce，支持大规模数据
- ✅ **ST 过滤**：自动排除 *ST/ST 等风险警示企业
- ✅ **置信度评估**：输出 KNN 投票置信度
- ✅ **表头跳过**：自动跳过 CSV 表头行
- ✅ **多格式输出**：支持 Python 画图

---

## 📌 项目总结与分析

使用27项财务指标构建行业分类模型，发现企业财务表现对行业归属的解释能力有限，KNN模型整体准确率约10%，表明单纯依赖财务报表难以有效刻画行业边界，行业分类更多受到商业模式与产业链位置影响。

---

## ⚠️ 注意事项

1. **数据源稳定性**：东方财富数据中心接口为非公开 API，可能随时调整参数，如遇问题请检查接口 URL 和字段名
2. **请求频率**：爬取全市场数据时建议 `sleep ≥ 0.5s`，否则可能触发反爬
3. **金融企业**：银行、保险、券商等金融企业的某些指标（如毛利率、流动比率）天然为 NaN，已在特征工程中处理
4. **标准化**：KNN 对量纲敏感，务必在分类前做 Z-score 标准化

---

## 📝 License

MIT License

---

## 👤 作者

- **Celore Chan**

---

## 🙏 致谢

- [东方财富数据中心](https://data.eastmoney.com/) - 财务数据来源
- [AKShare](https://github.com/akfamily/akshare) - A股数据接口库
- [Apache Hadoop](https://hadoop.apache.org/) - 分布式计算框架
