"""
A股企业财务指标计算（完整版）
包含盈利能力质量、增长趋势、成本费用结构、利润含金量、综合对比指标
"""
import requests
import pandas as pd
import numpy as np
import time
import akshare as ak

# ========== 配置 ==========
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/"
}

REPORT_NAMES = {
    'income': 'RPT_DMSK_FN_INCOME',
    'balance': 'RPT_DMSK_FN_BALANCE',
    'cashflow': 'RPT_DMSK_FN_CASHFLOW'
}

# ========== 1. 获取成分股 ==========
def get_all_stocks():
    """获取沪深北全部A股（含北交所）"""
    try:
        df = ak.stock_info_a_code_name()
        df = df[['code', 'name']]
        df.columns = ['SECURITY_CODE', 'SECURITY_NAME_ABBR']
        df['SECURITY_CODE'] = df['SECURITY_CODE'].astype(str).str.zfill(6)
        print(f"获取到 {len(df)} 只A股")
        return df
    except Exception as e:
        print(f"获取全市场股票失败: {e}")
        return pd.DataFrame()

# ========== 2. 获取行业 ==========
def get_all_industry():
    """获取申万一级行业（东方财富 datacenter 接口）"""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    industry_dict = {}
    page = 1
    while True:
        params = {
            "sortColumns": "SECURITY_CODE",
            "sortTypes": "1",
            "pageSize": "500",
            "pageNumber": str(page),
            "columns": "SECURITY_CODE,INDUSTRY_NAME",
            "reportName": "RPT_F10_ORG_BASICINFO"
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            if data.get('success') and data.get('result') and data['result'].get('data'):
                df = pd.DataFrame(data['result']['data'])
                for _, row in df.iterrows():
                    code = str(row['SECURITY_CODE']).zfill(6)
                    industry_dict[code] = row.get('INDUSTRY_NAME', '未知')
                if len(df) < 500:  # 最后一页
                    break
                page += 1
                time.sleep(0.3)
            else:
                break
        except Exception as e:
            print(f"行业接口请求失败: {e}")
            break
    print(f"获取到 {len(industry_dict)} 条行业信息")
    return industry_dict

# ========== 3. 获取财务数据 ==========
def get_financial_data(ts_code):
    code = ts_code.split('.')[0]
    all_data = {}
    for report_type, report_name in REPORT_NAMES.items():
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": "10",
            "pageNumber": "1",
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")(DATE_TYPE_CODE="001")',
            "reportName": report_name
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            if data.get('success') and data.get('result') and data['result'].get('data'):
                all_data[report_type] = pd.DataFrame(data['result']['data'])
            else:
                all_data[report_type] = pd.DataFrame()
        except:
            all_data[report_type] = pd.DataFrame()
        time.sleep(0.3)
    return all_data

# ========== 4. 计算所有指标 ==========
def calculate_metrics(all_data):
    """
    计算完整指标体系（近五年均值 + 最近一年值）
    返回: dict 包含所有指标
    """
    df_income = all_data.get('income', pd.DataFrame())
    df_balance = all_data.get('balance', pd.DataFrame())
    df_cashflow = all_data.get('cashflow', pd.DataFrame())

    if df_income.empty or df_balance.empty:
        return None

    # 处理年份
    for df_name, df in [('income', df_income), ('balance', df_balance), ('cashflow', df_cashflow)]:
        if not df.empty and 'REPORT_DATE' in df.columns:
            df['YEAR'] = pd.to_datetime(df['REPORT_DATE']).dt.year
            df.sort_values('YEAR', inplace=True)
            df = df[df['YEAR'].between(2019, 2023)]
            if df_name == 'income':
                df_income = df.reset_index(drop=True)
            elif df_name == 'balance':
                df_balance = df.reset_index(drop=True)
            elif df_name == 'cashflow':
                df_cashflow = df.reset_index(drop=True)

    if df_income.empty or df_balance.empty:
        return None

    if df_cashflow.empty:
        df_cashflow = pd.DataFrame({'YEAR': df_income['YEAR'], 'NETCASH_OPERATE': np.nan})

    # ===== 提取原始字段 =====
    income_fields = {
        'YEAR': df_income['YEAR'],
        'TOTAL_OPERATE_INCOME': pd.to_numeric(df_income['TOTAL_OPERATE_INCOME'], errors='coerce'),
        'TOTAL_OPERATE_COST': pd.to_numeric(df_income['TOTAL_OPERATE_COST'], errors='coerce'),
        'OPERATE_COST': pd.to_numeric(df_income['OPERATE_COST'], errors='coerce'),
        'SALE_EXPENSE': pd.to_numeric(df_income['SALE_EXPENSE'], errors='coerce'),
        'MANAGE_EXPENSE': pd.to_numeric(df_income['MANAGE_EXPENSE'], errors='coerce'),
        'FINANCE_EXPENSE': pd.to_numeric(df_income['FINANCE_EXPENSE'], errors='coerce'),
        'OPERATE_TAX_ADD': pd.to_numeric(df_income['OPERATE_TAX_ADD'], errors='coerce'),
        'OPERATE_PROFIT': pd.to_numeric(df_income['OPERATE_PROFIT'], errors='coerce'),
        'TOTAL_PROFIT': pd.to_numeric(df_income['TOTAL_PROFIT'], errors='coerce'),
        'INCOME_TAX': pd.to_numeric(df_income['INCOME_TAX'], errors='coerce'),
        'PARENT_NETPROFIT': pd.to_numeric(df_income['PARENT_NETPROFIT'], errors='coerce'),
        'DEDUCT_PARENT_NETPROFIT': pd.to_numeric(df_income['DEDUCT_PARENT_NETPROFIT'], errors='coerce'),
        # 同比增长率字段（东方财富已计算好）
        'TOI_RATIO': pd.to_numeric(df_income['TOI_RATIO'], errors='coerce'),          # 营收增长率
        'TOE_RATIO': pd.to_numeric(df_income['TOE_RATIO'], errors='coerce'),          # 总成本增长率
        'PARENT_NETPROFIT_RATIO': pd.to_numeric(df_income['PARENT_NETPROFIT_RATIO'], errors='coerce'),  # 归母净利润增长率
        'DPN_RATIO': pd.to_numeric(df_income['DPN_RATIO'], errors='coerce'),          # 扣非净利润增长率
        'OPERATE_PROFIT_RATIO': pd.to_numeric(df_income['OPERATE_PROFIT_RATIO'], errors='coerce'),  # 营业利润增长率
    }

    balance_fields = {
        'YEAR': df_balance['YEAR'],
        'TOTAL_ASSETS': pd.to_numeric(df_balance['TOTAL_ASSETS'], errors='coerce'),
        'FIXED_ASSET': pd.to_numeric(df_balance['FIXED_ASSET'], errors='coerce'),
        'TOTAL_LIABILITIES': pd.to_numeric(df_balance['TOTAL_LIABILITIES'], errors='coerce'),
        'TOTAL_EQUITY': pd.to_numeric(df_balance['TOTAL_EQUITY'], errors='coerce'),
        'DEBT_ASSET_RATIO': pd.to_numeric(df_balance['DEBT_ASSET_RATIO'], errors='coerce'),
        'CURRENT_RATIO': pd.to_numeric(df_balance['CURRENT_RATIO'], errors='coerce'),
    }

    cashflow_fields = {
        'YEAR': df_cashflow['YEAR'],
        'NETCASH_OPERATE': pd.to_numeric(df_cashflow['NETCASH_OPERATE'], errors='coerce'),
    }

    # 合并
    df1 = pd.DataFrame(income_fields)
    df2 = pd.DataFrame(balance_fields)
    df3 = pd.DataFrame(cashflow_fields)
    merged = df1.merge(df2, on='YEAR', how='left').merge(df3, on='YEAR', how='left')

    # ====================================================
    # 一、盈利能力质量组
    # ====================================================

    # 毛利率 = (营业总收入 - 营业成本) / 营业总收入
    merged['GROSS_MARGIN'] = (merged['TOTAL_OPERATE_INCOME'] - merged['OPERATE_COST']) / merged['TOTAL_OPERATE_INCOME']

    # 净利率 = 归母净利润 / 营业总收入
    merged['NET_MARGIN'] = merged['PARENT_NETPROFIT'] / merged['TOTAL_OPERATE_INCOME']

    # 营业利润率 = 营业利润 / 营业总收入
    merged['OPERATE_MARGIN'] = merged['OPERATE_PROFIT'] / merged['TOTAL_OPERATE_INCOME']

    # 费用利润率 = (销售费用 + 管理费用) / 营业利润
    merged['EXPENSE_PROFIT_RATIO'] = (merged['SALE_EXPENSE'] + merged['MANAGE_EXPENSE']) / merged['OPERATE_PROFIT']

    # ====================================================
    # 二、增长与趋势质量组（直接取同比字段，除以100转为小数）
    # ====================================================
    merged['REVENUE_GROWTH'] = merged['TOI_RATIO'] / 100           # 营收增长率
    merged['TOTAL_COST_GROWTH'] = merged['TOE_RATIO'] / 100        # 总成本增长率
    merged['NET_PROFIT_GROWTH'] = merged['PARENT_NETPROFIT_RATIO'] / 100   # 归母净利润增长率
    merged['DEDUCTED_PROFIT_GROWTH'] = merged['DPN_RATIO'] / 100          # 扣非净利润增长率
    merged['OPERATE_PROFIT_GROWTH'] = merged['OPERATE_PROFIT_RATIO'] / 100 # 营业利润增长率

    # ====================================================
    # 三、成本费用结构组
    # ====================================================

    # 成本收入比 = 营业成本 / 营业总收入
    merged['COST_INCOME_RATIO'] = merged['OPERATE_COST'] / merged['TOTAL_OPERATE_INCOME']

    # 销售费用率 = 销售费用 / 营业总收入
    merged['SELL_EXPENSE_RATE'] = merged['SALE_EXPENSE'] / merged['TOTAL_OPERATE_INCOME']

    # 管理费用率 = 管理费用 / 营业总收入
    merged['ADMIN_EXPENSE_RATE'] = merged['MANAGE_EXPENSE'] / merged['TOTAL_OPERATE_INCOME']

    # 财务费用率 = 财务费用 / 营业总收入
    merged['FINANCE_EXPENSE_RATE'] = merged['FINANCE_EXPENSE'] / merged['TOTAL_OPERATE_INCOME']

    # 税金及附加率 = 税金及附加 / 营业总收入
    merged['TAX_SURCHARGE_RATE'] = merged['OPERATE_TAX_ADD'] / merged['TOTAL_OPERATE_INCOME']

    # ====================================================
    # 四、利润含金量组
    # ====================================================

    # 扣非净利润占比 = 扣非归母净利润 / 归母净利润
    merged['DEDUCTED_PROFIT_RATIO'] = merged['DEDUCT_PARENT_NETPROFIT'] / merged['PARENT_NETPROFIT']

    # 有效税率 = 所得税 / 利润总额
    merged['EFFECTIVE_TAX_RATE'] = merged['INCOME_TAX'] / merged['TOTAL_PROFIT']

    # ====================================================
    # 五、综合对比指标
    # ====================================================

    # 1. 盈利质量综合得分 = 毛利率 × 扣非净利润占比 × (1 - 销售费用率)
    merged['PROFIT_QUALITY_SCORE'] = (
        merged['GROSS_MARGIN'] * 
        merged['DEDUCTED_PROFIT_RATIO'] * 
        (1 - merged['SELL_EXPENSE_RATE'])
    )

    # 2. 增收增利匹配度 = 营收增长率 - 总成本增长率
    merged['REVENUE_COST_MATCH'] = merged['REVENUE_GROWTH'] - merged['TOTAL_COST_GROWTH']

    # 3. 费用效率杠杆 = 毛利率 - 净利率（差值越小越好，但这里取原值）
    merged['EXPENSE_EFFICIENCY_LEVER'] = merged['GROSS_MARGIN'] - merged['NET_MARGIN']

    # 4. 利润可持续性系数 = 扣非净利润增长率 / 归母净利润增长率
    merged['PROFIT_SUSTAINABILITY'] = merged['DEDUCTED_PROFIT_GROWTH'] / merged['NET_PROFIT_GROWTH'].abs()
    merged['PROFIT_SUSTAINABILITY'] = merged['PROFIT_SUSTAINABILITY'].replace([np.inf, -np.inf], np.nan)

    # ====================================================
    # 六、之前的指标（保留）
    # ====================================================

    # 净资产
    merged['EQUITY'] = merged['TOTAL_EQUITY'].fillna(merged['TOTAL_ASSETS'] - merged['TOTAL_LIABILITIES'])
    merged['EQUITY_LAG'] = merged['EQUITY'].shift(1)
    merged['AVG_EQUITY'] = (merged['EQUITY'] + merged['EQUITY_LAG']) / 2
    merged['TOTAL_ASSETS_LAG'] = merged['TOTAL_ASSETS'].shift(1)
    merged['AVG_TOTAL_ASSETS'] = (merged['TOTAL_ASSETS'] + merged['TOTAL_ASSETS_LAG']) / 2

    # 扣非ROE
    merged['ROE_DEDUCTED'] = merged['DEDUCT_PARENT_NETPROFIT'] / merged['AVG_EQUITY']
    # 扣非ROA
    merged['ROA_DEDUCTED'] = merged['DEDUCT_PARENT_NETPROFIT'] / merged['AVG_TOTAL_ASSETS']
    # 利润增长率（原始版本）
    merged['NET_PROFIT_LAG'] = merged['PARENT_NETPROFIT'].shift(1)
    merged['PROFIT_GROWTH_ORIG'] = (merged['PARENT_NETPROFIT'] - merged['NET_PROFIT_LAG']) / merged['NET_PROFIT_LAG'].abs()
    # 扣非利润/经营性现金流
    merged['CF_RATIO'] = (merged['DEDUCT_PARENT_NETPROFIT'] / merged['NETCASH_OPERATE'].abs()).replace([np.inf, -np.inf], np.nan)
    # 固定资产/总资产
    merged['FIX_ASSET_RATIO'] = merged['FIXED_ASSET'] / merged['TOTAL_ASSETS']
    # 资产负债率
    merged['DEBT_RATIO'] = merged['DEBT_ASSET_RATIO'] / 100
    # 流动比
    merged['CURRENT_RATIO_VAL'] = merged['CURRENT_RATIO'] / 100

    # ====================================================
    # 汇总：近五年均值 + 最近一年值
    # ====================================================
    valid_data = merged.iloc[1:].tail(5)  # 跳过第一年（shift导致的NaN）
    if len(valid_data) == 0:
        return None

    # 需要取近五年均值的指标
    avg_metrics = [
        # 原指标
        'ROE_DEDUCTED', 'ROA_DEDUCTED', 'CF_RATIO', 'FIX_ASSET_RATIO',
        # 盈利能力质量组
        'GROSS_MARGIN', 'NET_MARGIN', 'OPERATE_MARGIN', 'EXPENSE_PROFIT_RATIO',
        # 成本费用结构组
        'COST_INCOME_RATIO', 'SELL_EXPENSE_RATE', 'ADMIN_EXPENSE_RATE', 
        'FINANCE_EXPENSE_RATE', 'TAX_SURCHARGE_RATE',
        # 利润含金量组
        'DEDUCTED_PROFIT_RATIO', 'EFFECTIVE_TAX_RATE',
        # 综合对比指标
        'PROFIT_QUALITY_SCORE', 'REVENUE_COST_MATCH', 'EXPENSE_EFFICIENCY_LEVER',
        'PROFIT_SUSTAINABILITY', 'PROFIT_GROWTH_ORIG',
    ]

    # 取均值
    averages = valid_data[avg_metrics].mean().to_dict()

    # 最近一年的值
    latest = valid_data.iloc[-1]
    averages.update({
        # 原指标
        'DEBT_RATIO': latest['DEBT_RATIO'],
        'CURRENT_RATIO': latest['CURRENT_RATIO_VAL'],
        # 增长与趋势质量组（取最近一年同比增长）
        'REVENUE_GROWTH': latest['REVENUE_GROWTH'],
        'TOTAL_COST_GROWTH': latest['TOTAL_COST_GROWTH'],
        'NET_PROFIT_GROWTH': latest['NET_PROFIT_GROWTH'],
        'DEDUCTED_PROFIT_GROWTH': latest['DEDUCTED_PROFIT_GROWTH'],
        'OPERATE_PROFIT_GROWTH': latest['OPERATE_PROFIT_GROWTH'],
    })

    return averages

# ========== 5. 主程序 ==========
def main():
    print("=" * 60)
    print("A股企业财务指标计算（完整版）")
    print("=" * 60)

    stocks = get_all_stocks()
    if stocks.empty:
        return

    #industry_dict = get_all_industry()
    
    all_results = []
    total = len(stocks)

    for idx, row in stocks.iterrows():
        code = str(row['SECURITY_CODE']).zfill(6)
        name = row['SECURITY_NAME_ABBR']
        #industry = industry_dict.get(code, '未知')

        ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"

        # 在 main() 的循环中，获取 all_data 后直接提取行业
        all_data = get_financial_data(ts_code)
        # 从利润表第一行提取行业
        #industry = '\0'
        #if not all_data.get('income', pd.DataFrame()).empty:
        #    industry = all_data['income'].iloc[0].get('INDUSTRY_NAME', '未知')
        metrics = calculate_metrics(all_data)
        print(f"\n[{idx+1}/{total}] {ts_code} {name}")

        if metrics:
            metrics['ts_code'] = ts_code
            metrics['name'] = name
            #metrics['industry'] = industry
            all_results.append(metrics)
            print(f"  ✓ 毛利率: {metrics['GROSS_MARGIN']:.2%}, 净利率: {metrics['NET_MARGIN']:.2%}")
        else:
            print(f"  ✗ 数据不足")

        time.sleep(0.1)

    if all_results:
        result_df = pd.DataFrame(all_results)

        # 定义输出列顺序（分组排列）
        cols_order = [
            # 基本信息
            'ts_code', 'name',
            
            # 原指标
            'ROE_DEDUCTED', 'ROA_DEDUCTED', 'PROFIT_GROWTH_ORIG', 'CF_RATIO',
            'FIX_ASSET_RATIO', 'DEBT_RATIO', 'CURRENT_RATIO',
            
            # 一、盈利能力质量组
            'GROSS_MARGIN', 'NET_MARGIN', 'OPERATE_MARGIN', 'EXPENSE_PROFIT_RATIO',
            
            # 二、增长与趋势质量组（最近一年同比）
            'REVENUE_GROWTH', 'TOTAL_COST_GROWTH', 'NET_PROFIT_GROWTH',
            'DEDUCTED_PROFIT_GROWTH', 'OPERATE_PROFIT_GROWTH',
            
            # 三、成本费用结构组
            'COST_INCOME_RATIO', 'SELL_EXPENSE_RATE', 'ADMIN_EXPENSE_RATE',
            'FINANCE_EXPENSE_RATE', 'TAX_SURCHARGE_RATE',
            
            # 四、利润含金量组
            'DEDUCTED_PROFIT_RATIO', 'EFFECTIVE_TAX_RATE',
            
            # 五、综合对比指标
            'PROFIT_QUALITY_SCORE', 'REVENUE_COST_MATCH',
            'EXPENSE_EFFICIENCY_LEVER', 'PROFIT_SUSTAINABILITY',
        ]

        result_df = result_df[cols_order]
        result_df.to_csv('astock_features.csv', index=False, encoding='utf-8-sig')

        print("\n" + "=" * 60)
        print(f"保存完成！共 {len(all_results)} 条记录")
        print(f"输出文件: astock_features.csv")
        print(f"总列数: {len(cols_order)}")
        print("=" * 60)

        # 预览
        print("\n前5行预览:")
        print(result_df.head().to_string())
    else:
        print("无有效数据")


if __name__ == '__main__':
    main()