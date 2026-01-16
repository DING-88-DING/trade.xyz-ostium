"""
Ostium 交易对数据处理器
================================================================================

功能说明:
    1. 加载 inspect_ostium.py 生成的原始数据文件
    2. 过滤高 OI（持仓量）的合约（默认 OI > $2,000,000）
    3. 计算并转换费率（资金费率 / 隔夜费率）
    4. 将处理后的数据保存到 JSON 文件

数据流程:
    ostium_response.json  ->  [过滤 & 计算费率]  ->  ostium_filtered.json
         (原始数据)                                   (处理后数据)

输入文件:
    - ostium_response.json: 由 inspect_ostium.py 生成的原始数据

输出文件:
    - ostium_filtered.json: 过滤并格式化后的合约数据

费率类型说明:
    - crypto 资产（BTC, ETH）: 使用资金费率（Funding Rate）
        - curFundingLong: 多头支付的费率
        - curFundingShort: 空头支付的费率
    - 非 crypto 资产（股票、外汇、商品、指数）: 使用隔夜费率（Rollover Rate）
        - rolloverFeePerBlock: 每区块的隔夜费率

费率计算公式:
    - 原始值单位: 每秒费率（18位精度，需除以 1e18）
    - 每小时费率 = 原始值 * 3600 / 1e18 * 100（转为百分比）
    - 每日费率 = 每小时费率 * 24
    - 8小时费率 = 每小时费率 * 8

OI 计算公式:
    - 总 OI（币数量）= (longOI + shortOI) / 1e18
    - 总 OI（USD）= 总 OI * 中间价

使用方法:
    python process_ostium.py

注意事项:
    - Ostium 不提供 24h 成交量数据，使用 OI 作为过滤条件
    - Arbitrum 出块速度约 4 块/秒（此脚本使用保守估计 1 块/秒）
"""

import json
from typing import Dict, List, Any


# ==================== 数据加载函数 ====================

def load_data(filepath: str = "ostium_response.json") -> Dict[str, Any]:
    """
    加载 Ostium 原始响应数据
    
    输入文件结构 (ostium_response.json):
        {
            "pairs": [                      # 交易对列表
                {
                    "id": "0",
                    "from": "BTC",
                    "to": "USD",
                    "group": {"name": "crypto"},
                    "longOI": "16190118096356189197",    # 多头OI（原始值）
                    "shortOI": "19987432486160506187",   # 空头OI（原始值）
                    "curFundingLong": 2973925102,       # 多头资金费率/秒
                    "curFundingShort": -2416694579,     # 空头资金费率/秒
                    "rolloverFeePerBlock": 0            # 隔夜费/区块
                },
                ...
            ],
            "prices": [                     # 价格列表
                {
                    "from": "BTC",
                    "to": "USD",
                    "bid": 94939.15,
                    "ask": 94947.61,
                    "mid": 94943.38,
                    "isMarketOpen": true
                },
                ...
            ],
            "analysis": {...}               # 分析结果（本脚本不使用）
        }
    
    Args:
        filepath: JSON 文件路径
        
    Returns:
        dict: 解析后的 JSON 数据
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 费率计算函数 ====================

def calculate_funding_rate(cur_funding: int, precision: int = 18) -> float:
    """
    计算每小时资金费率（仅用于 crypto 资产）
    
    Ostium 的资金费率存储格式:
        - curFundingLong/curFundingShort: 每秒费率，18位精度
        - 正值表示该方向需要支付费用，负值表示收取费用
    
    计算公式:
        每小时费率(%) = |curFunding| * 3600秒 / 1e18 * 100
    
    示例:
        curFundingLong = 2973925102
        rate_hourly = 2973925102 * 3600 / 1e18 * 100 = 0.00107%
    
    Args:
        cur_funding: 当前资金费率原始值（每秒，18位精度）
        precision: 精度位数（默认 18）
        
    Returns:
        float: 每小时资金费率百分比
    """
    # 使用绝对值，转换为每小时百分比
    return abs(cur_funding) * 3600 / (10 ** precision) * 100


def calculate_rollover_rate(rollover_per_block: int, precision: int = 18) -> float:
    """
    计算每小时隔夜费率（用于非 crypto 资产：股票、外汇、商品、指数）
    
    Ostium 的隔夜费率存储格式:
        - rolloverFeePerBlock: 每区块费率，18位精度
        - Arbitrum 出块速度: 约 4 块/秒
        - 本脚本使用保守估计: 1 块/秒（即 rollover 值直接当作每秒费率）
    
    计算公式（保守估计）:
        每小时费率(%) = rolloverFeePerBlock * 3600 / 1e18 * 100
    
    实际计算（更精确）:
        每小时费率(%) = rolloverFeePerBlock * (4块/秒 * 3600秒) / 1e18 * 100
    
    Args:
        rollover_per_block: 每区块隔夜费率（18位精度）
        precision: 精度位数（默认 18）
        
    Returns:
        float: 每小时隔夜费率百分比
    """
    return abs(rollover_per_block) * 3600 / (10 ** precision) * 100


# ==================== OI 计算函数 ====================

def get_total_oi_usd(pair: Dict, prices: List[Dict]) -> float:
    """
    计算交易对的总 OI（以 USD 计价）
    
    OI (Open Interest) = 持仓量，表示市场上未平仓的合约总量
    
    计算步骤:
        1. 从 pair 中获取 longOI 和 shortOI（原始值，18位精度）
        2. 将原始值除以 1e18 得到实际币数量
        3. 从 prices 中查找对应的中间价
        4. OI（USD）= OI（币数量）* 中间价
    
    示例:
        longOI = 16190118096356189197
        shortOI = 19987432486160506187
        total_oi_coins = (16190... + 19987...) / 1e18 = 36.17 BTC
        mid_price = 94943.38
        total_oi_usd = 36.17 * 94943.38 = $3,434,819
    
    Args:
        pair: 交易对数据
        prices: 价格列表
        
    Returns:
        float: 总 OI 金额（USD）
    """
    # ===== 步骤 1: 获取原始 OI 值 =====
    long_oi = int(pair.get("longOI", 0))   # 多头持仓量（原始值）
    short_oi = int(pair.get("shortOI", 0)) # 空头持仓量（原始值）
    
    # ===== 步骤 2: 转换为实际币数量 =====
    total_oi = (long_oi + short_oi) / 1e18
    
    # ===== 步骤 3: 查找对应价格 =====
    from_asset = pair.get("from", "")
    to_asset = pair.get("to", "")
    
    mid_price = 1.0  # 默认价格（找不到时使用）
    for price in prices:
        if price.get("from") == from_asset and price.get("to") == to_asset:
            mid_price = price.get("mid", 1.0)
            break
    
    # ===== 步骤 4: 计算 USD 价值 =====
    return total_oi * mid_price


# ==================== 数据处理函数 ====================

def process_data(
    data: Dict[str, Any],
    min_oi_usd: float = 2_000_000
) -> List[Dict[str, Any]]:
    """
    处理数据：过滤高 OI 合约，计算费率
    
    处理步骤:
        1. 遍历所有交易对
        2. 计算每个交易对的 OI（USD）
        3. 过滤掉 OI 低于阈值的交易对
        4. 匹配价格数据
        5. 根据资产类别计算对应的费率（资金费率或隔夜费率）
        6. 按 OI 降序排列
    
    费率处理逻辑:
        - crypto 资产: 计算 fundingRate（多头/空头分别计算）
        - 非 crypto 资产: 计算 rolloverRate（隔夜费）
    
    Args:
        data: 原始数据（load_data() 的返回值）
        min_oi_usd: 最小 OI 阈值（USD），默认 200万
        
    Returns:
        list: 过滤并处理后的合约列表，按 OI 降序排列
        
    输出数据结构:
        [
            {
                "pair": "BTC/USD",                # 交易对名称
                "from": "BTC",                    # 基础资产
                "to": "USD",                      # 报价资产
                "group": "crypto",                # 资产类别
                "bid": 94939.15,                  # 买价
                "mid": 94943.38,                  # 中间价
                "ask": 94947.61,                  # 卖价
                "isMarketOpen": true,             # 市场是否开放
                "totalOI_USD": 3434819.22,        # 总 OI（USD）
                "longOI": "16190...",             # 多头 OI（原始值）
                "shortOI": "19987...",            # 空头 OI（原始值）
                "fundingRate": {                  # 资金费率（仅 crypto）
                    "longPayHourly": 0.001071,    # 多头每小时费率(%)
                    "shortPayHourly": 0.00087,    # 空头每小时费率(%)
                    "longPay8h": 0.008565,        # 多头8小时费率(%)
                    "shortPay8h": 0.00696         # 空头8小时费率(%)
                },
                "rolloverRate": null,             # 隔夜费（非 crypto 资产使用）
                "_raw": {                         # 原始值（便于验证）
                    "curFundingLong": 2973925102,
                    "curFundingShort": -2416694579,
                    "rolloverFeePerBlock": 0
                }
            },
            ...
        ]
    """
    # 从原始数据中提取交易对和价格
    pairs = data.get("pairs", [])
    prices = data.get("prices", [])
    
    # ===== 创建价格快速查找表 =====
    # key: "BTC/USD", value: 价格数据
    price_map = {}
    for price in prices:
        key = f"{price.get('from')}/{price.get('to')}"
        price_map[key] = price
    
    # 存储处理后的合约
    filtered_contracts = []
    
    # ===== 遍历每个交易对进行处理 =====
    for pair in pairs:
        # 提取资产信息
        from_asset = pair.get("from", "")
        to_asset = pair.get("to", "")
        pair_name = f"{from_asset}/{to_asset}"
        
        # ----- 步骤 1: 计算总 OI（USD） -----
        total_oi_usd = get_total_oi_usd(pair, prices)
        
        # ----- 步骤 2: 过滤低 OI 合约 -----
        if total_oi_usd < min_oi_usd:
            continue
        
        # ----- 步骤 3: 获取价格数据 -----
        price_data = price_map.get(pair_name, {})
        
        # ----- 步骤 4: 获取原始费率值 -----
        # curFundingLong/Short: 资金费率（crypto 资产使用）
        cur_funding_long = int(pair.get("curFundingLong", 0))
        cur_funding_short = int(pair.get("curFundingShort", 0))
        # rolloverFeePerBlock: 隔夜费（非 crypto 资产使用）
        rollover_per_block = int(pair.get("rolloverFeePerBlock", 0))
        
        # ----- 步骤 5: 计算费率 -----
        # 多头资金费率（每小时 %）
        funding_long_rate_hourly = calculate_funding_rate(cur_funding_long)
        # 空头资金费率（每小时 %）
        funding_short_rate_hourly = calculate_funding_rate(cur_funding_short)
        # 隔夜费率（每小时 %）
        rollover_rate_hourly = calculate_rollover_rate(rollover_per_block)
        
        # ----- 步骤 6: 判断资产类别 -----
        # crypto 资产有资金费率，其他资产有隔夜费
        group_name = pair.get("group", {}).get("name", "unknown")
        is_crypto = group_name == "crypto"
        
        # ----- 步骤 7: 构建输出数据结构 -----
        contract = {
            # ===== 基础信息 =====
            "pair": pair_name,                      # 交易对名称
            "from": from_asset,                     # 基础资产
            "to": to_asset,                         # 报价资产
            "group": group_name,                    # 资产类别
            
            # ===== 价格数据 =====
            "bid": price_data.get("bid"),           # 买价
            "mid": price_data.get("mid"),           # 中间价
            "ask": price_data.get("ask"),           # 卖价
            "isMarketOpen": price_data.get("isMarketOpen"),  # 市场是否开放
            
            # ===== OI 数据 =====
            "totalOI_USD": round(total_oi_usd, 2),  # 总 OI（USD）
            "longOI": pair.get("longOI"),           # 多头 OI（原始值）
            "shortOI": pair.get("shortOI"),         # 空头 OI（原始值）
            
            # ===== 资金费率（仅 crypto 资产） =====
            "fundingRate": {
                # 多头每小时费率(%)
                "longPayHourly": round(funding_long_rate_hourly, 6) if is_crypto else None,
                # 空头每小时费率(%)
                "shortPayHourly": round(funding_short_rate_hourly, 6) if is_crypto else None,
                # 多头8小时费率(%) = 每小时 * 8
                "longPay8h": round(funding_long_rate_hourly * 8, 6) if is_crypto else None,
                # 空头8小时费率(%) = 每小时 * 8
                "shortPay8h": round(funding_short_rate_hourly * 8, 6) if is_crypto else None,
            } if is_crypto else None,
            
            # ===== 隔夜费率（非 crypto 资产） =====
            "rolloverRate": {
                # 每小时费率(%)
                "hourly": round(rollover_rate_hourly, 6),
                # 每日费率(%) = 每小时 * 24
                "daily": round(rollover_rate_hourly * 24, 6),
            } if not is_crypto and rollover_per_block > 0 else None,
            
            # ===== 原始值（便于验证和调试） =====
            "_raw": {
                "curFundingLong": cur_funding_long,
                "curFundingShort": cur_funding_short,
                "rolloverFeePerBlock": rollover_per_block,
            }
        }
        
        filtered_contracts.append(contract)
    
    # ===== 步骤 8: 按 OI 降序排列 =====
    filtered_contracts.sort(key=lambda x: x["totalOI_USD"], reverse=True)
    
    return filtered_contracts


# ==================== 数据保存函数 ====================

def save_results(contracts: List[Dict], filepath: str = "ostium_filtered.json"):
    """
    保存处理后的合约数据到 JSON 文件
    
    输出文件结构 (ostium_filtered.json):
        {
            "total_filtered": 13,                    # 符合条件的合约数量
            "filter_criteria": "Total OI > $2,000,000",  # 过滤条件说明
            "contracts": [                           # 合约数据列表
                {
                    "pair": "BTC/USD",
                    "from": "BTC",
                    "to": "USD",
                    "group": "crypto",
                    "bid": 94939.15,
                    "mid": 94943.38,
                    "ask": 94947.61,
                    "isMarketOpen": true,
                    "totalOI_USD": 3434819.22,
                    "longOI": "16190...",
                    "shortOI": "19987...",
                    "fundingRate": {...},
                    "rolloverRate": null,
                    "_raw": {...}
                },
                ...  # 按 OI 降序排列
            ]
        }
    
    Args:
        contracts: 处理后的合约列表
        filepath: 输出文件路径
    """
    # 构建输出数据结构
    result = {
        "total_filtered": len(contracts),             # 合约数量
        "filter_criteria": "Total OI > $2,000,000",   # 过滤条件
        "contracts": contracts                         # 合约数据
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
        1. 加载原始数据 (ostium_response.json)
        2. 过滤和处理数据（OI 过滤 + 费率计算）
        3. 打印合约摘要（名称、OI、费率）
        4. 保存结果到 ostium_filtered.json
    """
    # 打印标题
    print("=" * 50)
    print("Ostium Data Processor")
    print("=" * 50)
    
    # ===== 步骤 1: 加载原始数据 =====
    print("\n正在加载数据...")
    data = load_data()
    
    # 打印加载的交易对数量
    total_pairs = len(data.get('pairs', []))
    print(f"加载了 {total_pairs} 个交易对")
    
    # ===== 步骤 2: 过滤和处理数据 =====
    print("\n正在过滤和处理数据...")
    # 过滤条件: 总 OI > 200万美元
    contracts = process_data(data, min_oi_usd=2_000_000)
    
    # ===== 步骤 3: 打印合约摘要 =====
    print(f"\n符合条件的合约: {len(contracts)}")
    print("\n合约列表:")
    print("-" * 60)
    
    # 遍历打印每个合约的关键信息
    for c in contracts:
        # 构建费率信息字符串
        rate_info = ""
        
        if c.get("fundingRate"):
            # crypto 资产: 显示多头和空头资金费率
            rate_info = f"Long: {c['fundingRate']['longPayHourly']:.4f}%/h, Short: {c['fundingRate']['shortPayHourly']:.4f}%/h"
        elif c.get("rolloverRate"):
            # 非 crypto 资产: 显示隔夜费率
            rate_info = f"Rollover: {c['rolloverRate']['hourly']:.4f}%/h"
        
        # 打印: 交易对 | OI | 费率
        print(f"{c['pair']:12} | OI: ${c['totalOI_USD']:>12,.0f} | {rate_info}")
    
    print("-" * 60)
    
    # ===== 步骤 4: 保存结果 =====
    save_results(contracts)
    
    print("\n完成！")


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
