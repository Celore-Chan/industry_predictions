"""
A股企业分类获取（完整版）
包含上市代码、企业名称、行业
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

# ========== 1. 获取成分股 ==========
def get_all_stocks():
    """获取A股成分股"""
    try:
        df = ak.stock_info_a_code_name()
        df = df[['code', 'name']]
        df.columns = ['SECURITY_CODE', 'SECURITY_NAME_ABBR']
        df['SECURITY_CODE'] = df['SECURITY_CODE'].astype(str).str.zfill(6)
        # 筛选上证股票（以6开头）
        #df = df[df['SECURITY_CODE'].str.startswith('6')].reset_index(drop=True)
        print(f"✓ 获取到 {len(df)} 只上证成分股")
        return df
    except Exception as e:
        print(f"方法1失败: {e}")
        return pd.DataFrame()

# ========== 2. 获取财务数据 ==========
def get_financial_data(ts_code):
    code = ts_code.split('.')[0]
    all_data = {}
    
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "pageSize": "10",
        "pageNumber": "1",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")(DATE_TYPE_CODE="001")',
        "reportName": 'RPT_DMSK_FN_INCOME'
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
        if data.get('success') and data.get('result') and data['result'].get('data'):
            all_data['income'] = pd.DataFrame(data['result']['data'])
        else:
            all_data['income'] = pd.DataFrame()
    except:
        all_data['income'] = pd.DataFrame()
    time.sleep(0.3)
    return all_data

# ========== 5. 主程序 ==========
def main():
    print("=" * 60)
    print("A股企业分类（完整版）")
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
        industry = '未知'
        if not all_data.get('income', pd.DataFrame()).empty:
            industry = all_data['income'].iloc[0].get('INDUSTRY_NAME', '未知')
        print(f"\n[{idx+1}/{total}] {ts_code} {name} {industry}")

        all_results.append({
            'ts_code': ts_code,
            'name': name,
            'industry': industry
        })

        time.sleep(0.8)nn

    if all_results:
        result_df = pd.DataFrame(all_results)

        # 定义输出列顺序（分组排列）
        cols_order = [
            # 基本信息
            'ts_code', 'name', 'industry'
        ]

        result_df = result_df[cols_order]
        result_df.to_csv('industry.csv', index=False, encoding='utf-8-sig')

        print("\n" + "=" * 60)
        print(f"保存完成！共 {len(all_results)} 条记录")
        print(f"输出文件: industry.csv")
        print(f"总列数: {len(cols_order)}")
        print("=" * 60)

        # 预览
        print("\n前5行预览:")
        print(result_df.head().to_string())
    else:
        print("无有效数据")


if __name__ == '__main__':
    main()