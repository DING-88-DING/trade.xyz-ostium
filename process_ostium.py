"""
Ostium Data Processor
处理 Ostium 数据，过滤高 OI 合约，计算资金费率
注意：Ostium API 不提供24小时成交量，使用 OI（持仓量）作为替代筛选条件
"""

import json
from typing import Dict, List, Any


def load_data(filepath: str = "ostium_response.json") -> Dict[str, Any]:
    """加载 Ostium 响应数据"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_funding_rate(cur_funding: int, precision: int = 18) -> float:
    """
    计算每小时资金费率
    公式: rate_per_hour = curFunding * 3600 / 1e18 * 100
    
    Args:
        cur_funding: 当前资金费率原始值
        precision: 精度（默认 1e18）
        
    Returns:
        每小时资金费率百分比
    """
    return abs(cur_funding) * 3600 / (10 ** precision) * 100


def calculate_rollover_rate(rollover_per_block: int, precision: int = 18) -> float:
    """
    计算每小时隔夜费率
    公式: rate_per_hour = rolloverFeePerBlock * 3600 / 1e18 * 100
    (假设每秒约1个区块，实际 Arbitrum 约 4 块/秒，但这里使用保守估计)
    
    Args:
        rollover_per_block: 每区块隔夜费率
        precision: 精度
        
    Returns:
        每小时隔夜费率百分比
    """
    return abs(rollover_per_block) * 3600 / (10 ** precision) * 100


def get_total_oi_usd(pair: Dict, prices: List[Dict]) -> float:
    """
    计算交易对的总 OI（以 USD 计价）
    公式: (longOI + shortOI) / 1e18 * mid_price
    
    Args:
        pair: 交易对数据
        prices: 价格列表
        
    Returns:
        总 OI 金额（USD）
    """
    long_oi = int(pair.get("longOI", 0))
    short_oi = int(pair.get("shortOI", 0))
    total_oi = (long_oi + short_oi) / 1e18
    
    # 查找对应价格
    from_asset = pair.get("from", "")
    to_asset = pair.get("to", "")
    
    mid_price = 1.0
    for price in prices:
        if price.get("from") == from_asset and price.get("to") == to_asset:
            mid_price = price.get("mid", 1.0)
            break
    
    return total_oi * mid_price


def process_data(
    data: Dict[str, Any],
    min_oi_usd: float = 2_000_000
) -> List[Dict[str, Any]]:
    """
    处理数据：过滤高 OI 合约，计算费率
    
    Args:
        data: 原始数据
        min_oi_usd: 最小 OI 阈值（USD）
        
    Returns:
        过滤后的合约列表
    """
    pairs = data.get("pairs", [])
    prices = data.get("prices", [])
    
    # 创建价格快速查找表
    price_map = {}
    for price in prices:
        key = f"{price.get('from')}/{price.get('to')}"
        price_map[key] = price
    
    filtered_contracts = []
    
    for pair in pairs:
        from_asset = pair.get("from", "")
        to_asset = pair.get("to", "")
        pair_name = f"{from_asset}/{to_asset}"
        
        # 计算总 OI
        total_oi_usd = get_total_oi_usd(pair, prices)
        
        # 过滤低 OI 合约
        if total_oi_usd < min_oi_usd:
            continue
        
        # 获取价格数据
        price_data = price_map.get(pair_name, {})
        
        # 获取原始费率值
        cur_funding_long = int(pair.get("curFundingLong", 0))
        cur_funding_short = int(pair.get("curFundingShort", 0))
        rollover_per_block = int(pair.get("rolloverFeePerBlock", 0))
        
        # 计算费率
        funding_long_rate_hourly = calculate_funding_rate(cur_funding_long)
        funding_short_rate_hourly = calculate_funding_rate(cur_funding_short)
        rollover_rate_hourly = calculate_rollover_rate(rollover_per_block)
        
        # 判断费率类型（crypto 有资金费率，其他有隔夜费）
        group_name = pair.get("group", {}).get("name", "unknown")
        is_crypto = group_name == "crypto"
        
        contract = {
            "pair": pair_name,
            "from": from_asset,
            "to": to_asset,
            "group": group_name,
            # 价格数据
            "bid": price_data.get("bid"),
            "mid": price_data.get("mid"),
            "ask": price_data.get("ask"),
            "isMarketOpen": price_data.get("isMarketOpen"),
            # OI 数据
            "totalOI_USD": round(total_oi_usd, 2),
            "longOI": pair.get("longOI"),
            "shortOI": pair.get("shortOI"),
            # 费率数据（每小时 %）
            "fundingRate": {
                "longPayHourly": round(funding_long_rate_hourly, 6) if is_crypto else None,
                "shortPayHourly": round(funding_short_rate_hourly, 6) if is_crypto else None,
                "longPay8h": round(funding_long_rate_hourly * 8, 6) if is_crypto else None,
                "shortPay8h": round(funding_short_rate_hourly * 8, 6) if is_crypto else None,
            } if is_crypto else None,
            "rolloverRate": {
                "hourly": round(rollover_rate_hourly, 6),
                "daily": round(rollover_rate_hourly * 24, 6),
            } if not is_crypto and rollover_per_block > 0 else None,
            # 原始值（便于验证）
            "_raw": {
                "curFundingLong": cur_funding_long,
                "curFundingShort": cur_funding_short,
                "rolloverFeePerBlock": rollover_per_block,
            }
        }
        
        filtered_contracts.append(contract)
    
    # 按 OI 降序排列
    filtered_contracts.sort(key=lambda x: x["totalOI_USD"], reverse=True)
    
    return filtered_contracts


def save_results(contracts: List[Dict], filepath: str = "ostium_filtered.json"):
    """保存处理结果"""
    result = {
        "total_filtered": len(contracts),
        "filter_criteria": "Total OI > $2,000,000",
        "contracts": contracts
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"已保存 {len(contracts)} 个合约到 {filepath}")


def main():
    print("=" * 50)
    print("Ostium Data Processor")
    print("=" * 50)
    
    # 加载数据
    print("\n正在加载数据...")
    data = load_data()
    print(f"加载了 {len(data.get('pairs', []))} 个交易对")
    
    # 处理数据
    print("\n正在过滤和处理数据...")
    contracts = process_data(data, min_oi_usd=2_000_000)
    
    # 打印摘要
    print(f"\n符合条件的合约: {len(contracts)}")
    print("\n合约列表:")
    print("-" * 60)
    for c in contracts:
        rate_info = ""
        if c.get("fundingRate"):
            rate_info = f"Long: {c['fundingRate']['longPayHourly']:.4f}%/h, Short: {c['fundingRate']['shortPayHourly']:.4f}%/h"
        elif c.get("rolloverRate"):
            rate_info = f"Rollover: {c['rolloverRate']['hourly']:.4f}%/h"
        
        print(f"{c['pair']:12} | OI: ${c['totalOI_USD']:>12,.0f} | {rate_info}")
    print("-" * 60)
    
    # 保存结果
    save_results(contracts)
    
    print("\n完成！")


if __name__ == "__main__":
    main()
