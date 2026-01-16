"""
Hyperliquid 永续合约数据处理器
================================================================================

功能说明:
    1. 加载 inspect_hyperliquid.py 生成的原始数据文件
    2. 过滤高成交量合约（默认 24h 成交量 > $2,000,000）
    3. 转换资金费率格式（小时/8小时/年化）
    4. 将处理后的数据保存到 JSON 文件

数据流程:
    hyperliquid_response.json  ->  [过滤 & 转换]  ->  hyperliquid_filtered.json
         (原始数据)                                    (处理后数据)

输入文件:
    - hyperliquid_response.json: 由 inspect_hyperliquid.py 生成的原始数据

输出文件:
    - hyperliquid_filtered.json: 过滤并格式化后的合约数据

使用方法:
    python process_hyperliquid.py

注意事项:
    - 资金费率: Hyperliquid 返回的是每小时费率，脚本会转换为 8小时/年化费率
    - 过滤条件: 默认过滤 24h 成交量低于 200万美元的合约
"""

import json
from typing import Dict, List, Any


# ==================== 数据加载函数 ====================

def load_data(filepath: str = "hyperliquid_response.json") -> Dict[str, Any]:
    """
    加载 Hyperliquid 原始响应数据
    
    输入文件结构 (hyperliquid_response.json):
        {
            "perpetuals": [         # 合约数据列表
                {
                    "index": 0,
                    "coin": "BTC",
                    "dex": "main",
                    "funding": "0.0000125",       # 每小时资金费率
                    "openInterest": "28865.53",
                    "dayNtlVlm": "3378409248.59", # 24h成交量（USD）
                    "markPx": "95636.0",
                    "midPx": "95636.5",
                    "oraclePx": "95630.0",
                    "impactPxs": ["95636.0", "95637.0"],
                    "premium": "0.0000627418",
                    "maxLeverage": 40
                },
                ...
            ],
            "perp_meta": {...}      # 元数据（本脚本不使用）
        }
    
    Args:
        filepath: JSON 文件路径
        
    Returns:
        dict: 解析后的 JSON 数据
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 数据处理函数 ====================

def process_perpetuals(
    data: Dict[str, Any],
    min_volume_usd: float = 2_000_000
) -> List[Dict[str, Any]]:
    """
    处理永续合约数据：过滤高成交量合约，提取并转换关键信息
    
    处理步骤:
        1. 遍历所有合约
        2. 过滤掉 24h 成交量低于阈值的合约
        3. 提取价格数据（买价/卖价/标记价格/Oracle价格）
        4. 转换资金费率（每小时 -> 8小时 -> 年化）
        5. 按成交量降序排列
    
    资金费率转换公式:
        - rate8h = rateHourly * 8
        - rateAnnualized = rateHourly * 24 * 365 = rateHourly * 8760
        - 注意: 输出时乘以 100 转换为百分比形式
    
    Args:
        data: 原始数据（load_data() 的返回值）
        min_volume_usd: 最小 24h 成交量阈值（USD），默认 200万
        
    Returns:
        list: 过滤并处理后的合约列表，按成交量降序排列
        
    输出数据结构:
        [
            {
                "coin": "BTC",                    # 合约名称
                "pair": "BTC/USD",                # 交易对
                "bid": 95636.0,                   # 买价（从 impactPxs[0] 提取）
                "mid": 95636.5,                   # 中间价
                "ask": 95637.0,                   # 卖价（从 impactPxs[1] 提取）
                "markPx": 95636.0,                # 标记价格
                "oraclePx": 95630.0,              # Oracle 价格
                "dayVolume_USD": 3378409248.59,   # 24h 成交量（USD）
                "openInterest": "28865.53616",    # 持仓量
                "fundingRate": {
                    "rate8h": 0.01,               # 8小时费率（%）
                    "rateHourly": 0.00125,        # 每小时费率（%）
                    "rateAnnualized": 10.95       # 年化费率（%）
                },
                "premium": "0.0000627418",        # 溢价率
                "maxLeverage": 40                 # 最大杠杆
            },
            ...
        ]
    """
    # 从原始数据中提取合约列表
    perpetuals = data.get("perpetuals", [])
    
    # 存储处理后的合约
    filtered = []
    
    # ===== 遍历每个合约进行处理 =====
    for perp in perpetuals:
        
        # ----- 步骤 1: 获取并检查 24h 成交量 -----
        day_volume = perp.get("dayNtlVlm")
        
        # 跳过没有成交量数据的合约
        if not day_volume:
            continue
        
        # 转换为浮点数
        volume = float(day_volume)
        
        # 过滤低成交量合约
        if volume < min_volume_usd:
            continue
        
        # ----- 步骤 2: 提取价格数据 -----
        mark_px = perp.get("markPx")      # 标记价格
        mid_px = perp.get("midPx")        # 中间价
        impact_pxs = perp.get("impactPxs", [])  # 冲击价格 [买价, 卖价]
        
        # 从 impactPxs 提取买价和卖价
        # impactPxs[0] = 买价（bid），impactPxs[1] = 卖价（ask）
        bid = float(impact_pxs[0]) if impact_pxs and len(impact_pxs) > 0 else None
        ask = float(impact_pxs[1]) if impact_pxs and len(impact_pxs) > 1 else None
        
        # ----- 步骤 3: 处理资金费率 -----
        # Hyperliquid API 返回的 funding 是每小时费率（字符串格式）
        funding_hourly_str = perp.get("funding")
        funding_hourly = float(funding_hourly_str) if funding_hourly_str else None
        
        # 计算 8 小时费率（用于与其他交易所对比，如 Binance）
        funding_8h = funding_hourly * 8 if funding_hourly else None
        
        # ----- 步骤 4: 构建输出数据结构 -----
        contract = {
            # ===== 基础信息 =====
            "coin": perp.get("coin"),                    # 合约名称（如 "BTC", "ETH"）
            "pair": f"{perp.get('coin')}/USD",           # 交易对（如 "BTC/USD"）
            
            # ===== 价格信息 =====
            "bid": bid,                                  # 买价（买入时的价格）
            "mid": float(mid_px) if mid_px else None,    # 中间价（买卖价平均值）
            "ask": ask,                                  # 卖价（卖出时的价格）
            "markPx": float(mark_px) if mark_px else None,  # 标记价格（用于计算盈亏和强平）
            "oraclePx": float(perp.get("oraclePx")) if perp.get("oraclePx") else None,  # Oracle 价格
            
            # ===== 成交量和持仓量 =====
            "dayVolume_USD": round(volume, 2),           # 24h 成交量（USD），保留2位小数
            "openInterest": perp.get("openInterest"),    # 持仓量（币数量）
            
            # ===== 资金费率 =====
            # 只有当资金费率存在时才创建 fundingRate 对象
            "fundingRate": {
                # 8小时费率（%）= 每小时费率 * 8 * 100
                "rate8h": round(funding_8h * 100, 6) if funding_8h else None,
                
                # 每小时费率（%）= 原始费率 * 100
                "rateHourly": round(funding_hourly * 100, 6) if funding_hourly else None,
                
                # 年化费率（%）= 8小时费率 * 3次/天 * 365天 = 8小时费率 * 1095
                # 或者: 每小时费率 * 24 * 365 = 每小时费率 * 8760
                "rateAnnualized": round(funding_8h * 100 * 3 * 365, 2) if funding_8h else None,
            } if funding_hourly is not None else None,
            
            # ===== 其他信息 =====
            "premium": perp.get("premium"),              # 溢价率（标记价格与Oracle价格的偏差）
            "maxLeverage": perp.get("maxLeverage"),      # 最大杠杆倍数
        }
        
        filtered.append(contract)
    
    # ===== 步骤 5: 按 24h 成交量降序排列 =====
    # 成交量最大的合约排在最前面
    filtered.sort(key=lambda x: x["dayVolume_USD"], reverse=True)
    
    return filtered


# ==================== 数据保存函数 ====================

def save_results(contracts: List[Dict], filepath: str = "hyperliquid_filtered.json"):
    """
    保存处理后的合约数据到 JSON 文件
    
    输出文件结构 (hyperliquid_filtered.json):
        {
            "total_filtered": 83,                    # 符合条件的合约数量
            "filter_criteria": "24h Volume > $2,000,000",  # 过滤条件说明
            "contracts": [                           # 合约数据列表
                {
                    "coin": "BTC",
                    "pair": "BTC/USD",
                    "bid": 95636.0,
                    "mid": 95636.5,
                    "ask": 95637.0,
                    "markPx": 95636.0,
                    "oraclePx": 95630.0,
                    "dayVolume_USD": 3378409248.59,
                    "openInterest": "28865.53616",
                    "fundingRate": {
                        "rate8h": 0.01,
                        "rateHourly": 0.00125,
                        "rateAnnualized": 10.95
                    },
                    "premium": "0.0000627418",
                    "maxLeverage": 40
                },
                ...  # 按成交量降序排列
            ]
        }
    
    Args:
        contracts: 处理后的合约列表
        filepath: 输出文件路径
    """
    # 构建输出数据结构
    result = {
        "total_filtered": len(contracts),            # 合约数量
        "filter_criteria": "24h Volume > $2,000,000", # 过滤条件
        "contracts": contracts                        # 合约数据
    }
    
    # 写入 JSON 文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"已保存 {len(contracts)} 个合约到 {filepath}")


# ==================== 主函数 ====================

def main():
    """
    主函数 - 执行完整的数据处理流程
    
    执行步骤:
        1. 加载原始数据 (hyperliquid_response.json)
        2. 过滤和处理数据（成交量过滤 + 费率转换）
        3. 打印合约摘要（名称、成交量、资金费率）
        4. 保存结果到 hyperliquid_filtered.json
    """
    # 打印标题
    print("=" * 50)
    print("Hyperliquid Data Processor")
    print("=" * 50)
    
    # ===== 步骤 1: 加载原始数据 =====
    print("\n正在加载数据...")
    data = load_data()
    
    # 打印加载的合约数量
    total_perps = len(data.get('perpetuals', []))
    print(f"加载了 {total_perps} 个永续合约")
    
    # ===== 步骤 2: 过滤和处理数据 =====
    print("\n正在过滤和处理数据...")
    # 过滤条件: 24h 成交量 > 200万美元
    contracts = process_perpetuals(data, min_volume_usd=2_000_000)
    
    # ===== 步骤 3: 打印合约摘要 =====
    print(f"\n符合条件的合约: {len(contracts)}")
    print("\n合约列表:")
    print("-" * 70)
    
    # 遍历打印每个合约的关键信息
    for c in contracts:
        # 获取资金费率信息
        funding = c.get("fundingRate", {})
        rate_8h = funding.get("rate8h", "N/A") if funding else "N/A"
        
        # 格式化费率字符串
        rate_str = f"{rate_8h}%" if rate_8h != "N/A" else "N/A"
        
        # 打印: 合约名称 | 24h成交量 | 8小时资金费率
        print(f"{c['coin']:8} | 24h Vol: ${c['dayVolume_USD']:>15,.0f} | Funding(8h): {rate_str:>10}")
    
    print("-" * 70)
    
    # ===== 步骤 4: 保存结果 =====
    save_results(contracts)
    
    print("\n完成！")


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
