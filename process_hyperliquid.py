"""
Hyperliquid Data Processor
处理 Hyperliquid 数据，过滤高成交量合约，提取资金费率
"""

import json
from typing import Dict, List, Any


def load_data(filepath: str = "hyperliquid_response.json") -> Dict[str, Any]:
    """加载 Hyperliquid 响应数据"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def process_perpetuals(
    data: Dict[str, Any],
    min_volume_usd: float = 2_000_000
) -> List[Dict[str, Any]]:
    """
    处理永续合约数据：过滤高成交量合约，提取关键信息
    
    Args:
        data: 原始数据
        min_volume_usd: 最小24h成交量阈值（USD）
        
    Returns:
        过滤后的合约列表
    """
    perpetuals = data.get("perpetuals", [])
    
    filtered = []
    
    for perp in perpetuals:
        # 获取24h成交量
        day_volume = perp.get("dayNtlVlm")
        if not day_volume:
            continue
            
        volume = float(day_volume)
        
        # 过滤低成交量合约
        if volume < min_volume_usd:
            continue
        
        # 获取价格
        mark_px = perp.get("markPx")
        mid_px = perp.get("midPx")
        impact_pxs = perp.get("impactPxs", [])
        
        bid = float(impact_pxs[0]) if impact_pxs and len(impact_pxs) > 0 else None
        ask = float(impact_pxs[1]) if impact_pxs and len(impact_pxs) > 1 else None
        
        # 获取资金费率（Hyperliquid 返回的是 8 小时费率）
        funding_8h = perp.get("funding")
        funding_rate = float(funding_8h) if funding_8h else None
        
        # 计算每小时费率
        funding_hourly = funding_rate / 8 if funding_rate else None
        
        contract = {
            "coin": perp.get("coin"),
            "pair": f"{perp.get('coin')}/USD",
            # 价格
            "bid": bid,
            "mid": float(mid_px) if mid_px else None,
            "ask": ask,
            "markPx": float(mark_px) if mark_px else None,
            "oraclePx": float(perp.get("oraclePx")) if perp.get("oraclePx") else None,
            # 成交量和 OI
            "dayVolume_USD": round(volume, 2),
            "openInterest": perp.get("openInterest"),
            # 资金费率
            "fundingRate": {
                "rate8h": round(funding_rate * 100, 6) if funding_rate else None,  # 转为百分比
                "rateHourly": round(funding_hourly * 100, 6) if funding_hourly else None,
                "rateAnnualized": round(funding_rate * 100 * 3 * 365, 2) if funding_rate else None,  # 年化
            } if funding_rate is not None else None,
            # 其他
            "premium": perp.get("premium"),
            "maxLeverage": perp.get("maxLeverage"),
        }
        
        filtered.append(contract)
    
    # 按24h成交量降序排列
    filtered.sort(key=lambda x: x["dayVolume_USD"], reverse=True)
    
    return filtered


def save_results(contracts: List[Dict], filepath: str = "hyperliquid_filtered.json"):
    """保存处理结果"""
    result = {
        "total_filtered": len(contracts),
        "filter_criteria": "24h Volume > $2,000,000",
        "contracts": contracts
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"已保存 {len(contracts)} 个合约到 {filepath}")


def main():
    print("=" * 50)
    print("Hyperliquid Data Processor")
    print("=" * 50)
    
    # 加载数据
    print("\n正在加载数据...")
    data = load_data()
    print(f"加载了 {len(data.get('perpetuals', []))} 个永续合约")
    
    # 处理数据
    print("\n正在过滤和处理数据...")
    contracts = process_perpetuals(data, min_volume_usd=2_000_000)
    
    # 打印摘要
    print(f"\n符合条件的合约: {len(contracts)}")
    print("\n合约列表:")
    print("-" * 70)
    for c in contracts:
        funding = c.get("fundingRate", {})
        rate_8h = funding.get("rate8h", "N/A") if funding else "N/A"
        rate_str = f"{rate_8h}%" if rate_8h != "N/A" else "N/A"
        
        print(f"{c['coin']:8} | 24h Vol: ${c['dayVolume_USD']:>15,.0f} | Funding(8h): {rate_str:>10}")
    print("-" * 70)
    
    # 保存结果
    save_results(contracts)
    
    print("\n完成！")


if __name__ == "__main__":
    main()
