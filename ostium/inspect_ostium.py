"""
Ostium 交易对数据获取工具
================================================================================

功能说明:
    1. 使用 Ostium Python SDK 连接 Arbitrum 网络
    2. 获取所有交易对信息（包含费率配置）
    3. 获取所有交易对的最新价格
    4. 按资产类别分析交易对
    5. 将数据保存到 JSON 文件供后续处理

SDK 信息:
    - 安装: pip install ostium-python-sdk
    - 文档: https://github.com/0xOstium/ostium-python-sdk
    - 网络: Arbitrum Mainnet

数据流程:
    Ostium SDK  ->  [获取交易对 + 价格]  ->  ostium_response.json
                                          ->  ostium_assets.txt

输出文件:
    - ostium_response.json: 包含 pairs（交易对）、prices（价格）、analysis（分析结果）
    - ostium_assets.txt: 所有资产名称列表

资产分类 (groupIndex):
    - 0: crypto (加密货币) - 如 BTC/USD, ETH/USD
    - 1: forex (外汇) - 如 EUR/USD, GBP/USD  
    - 2: commodities (大宗商品) - 如 XAU/USD (黄金), XAG/USD (白银)
    - 3: stocks (股票) - 如 TSLA/USD, AAPL/USD
    - 4: indices (指数) - 如 SPX/USD, NDX/USD

使用方法:
    python inspect_ostium.py

注意事项:
    - 需要配置 ARBITRUM_RPC_URL（在 config.py 中设置）
    - SDK 使用异步方式获取数据
"""

import json
import os
import asyncio
from typing import Dict, List, Any

# ==================== SDK 导入 ====================
# Ostium Python SDK 用于与 Arbitrum 上的 Ostium 协议交互
from ostium_python_sdk import OstiumSDK
from ostium_python_sdk.config import NetworkConfig

# 获取脚本所在目录（确保无论从哪个目录运行都能找到正确的文件路径）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== 配置加载 ====================
# 尝试从 config.py 加载 Arbitrum RPC URL
try:
    from config import ARBITRUM_RPC_URL
except ImportError:
    # config.py 不存在时的警告
    print("警告: 未找到 config.py，请设置 ARBITRUM_RPC_URL")
    ARBITRUM_RPC_URL = None


# ==================== 常量定义 ====================

# 资产分类映射（根据 Ostium 协议的 groupIndex 定义）
# groupIndex 是链上合约返回的分类索引
GROUP_INDEX_MAP = {
    0: "crypto",       # 加密货币（BTC, ETH 等）- 有资金费率
    1: "forex",        # 外汇（EUR, GBP 等）- 有隔夜费
    2: "commodities",  # 大宗商品（XAU 黄金, XAG 白银, CL 原油等）- 有隔夜费
    3: "stocks",       # 股票（TSLA, AAPL 等）- 有隔夜费
    4: "indices"       # 指数（SPX, NDX 等）- 有隔夜费
}


# ==================== 数据获取函数 ====================

async def fetch_all_data() -> Dict[str, Any]:
    """
    使用 SDK 获取所有 Ostium 数据
    
    SDK 调用:
        1. sdk.subgraph.get_pairs() - 获取交易对信息（从 The Graph 子图）
        2. sdk.price.get_latest_prices() - 获取最新价格（从价格预言机）
    
    交易对数据 (pairs) 包含:
        - id: 交易对 ID
        - from/to: 基础资产/报价资产
        - groupIndex: 资产分类索引
        - longOI/shortOI: 多头/空头持仓量（原始值，需除以 1e18）
        - curFundingLong/curFundingShort: 当前资金费率（仅 crypto）
        - rolloverFeePerBlock: 隔夜费率（非 crypto 资产）
        - openFeeP/closeFeeP: 开仓/平仓手续费
        - minLeverage/maxLeverage: 最小/最大杠杆
    
    价格数据 (prices) 包含:
        - from/to: 基础资产/报价资产
        - bid/ask/mid: 买价/卖价/中间价
        - isMarketOpen: 市场是否开放（非 crypto 资产有交易时间限制）
    
    Returns:
        dict: {"pairs": [...], "prices": [...]}
    """
    # ===== 步骤 1: 初始化 SDK =====
    # 使用主网配置（Arbitrum Mainnet）
    config = NetworkConfig.mainnet()
    
    # 创建 SDK 实例，传入 RPC URL 用于链上数据读取
    sdk = OstiumSDK(config, rpc_url=ARBITRUM_RPC_URL)
    
    print("正在通过 SDK 获取数据...")
    
    # ===== 步骤 2: 获取交易对信息 =====
    # 从 The Graph 子图获取所有交易对的详细信息
    # 包含：费率配置、持仓量、杠杆限制等
    pairs = await sdk.subgraph.get_pairs()
    print(f"获取到 {len(pairs)} 个交易对信息")
    
    # ===== 步骤 3: 获取最新价格 =====
    # 从价格预言机获取所有交易对的实时价格
    # 包含：买价、卖价、中间价、市场状态
    prices = await sdk.price.get_latest_prices()
    print(f"获取到 {len(prices)} 个价格数据")
    
    return {"pairs": pairs, "prices": prices}


# ==================== 数据分析函数 ====================

def analyze_pairs(pairs: List[Dict]) -> Dict[str, Any]:
    """
    分析交易对数据：按资产类别分组，提取费率信息
    
    分析内容:
        1. 按 groupIndex 将交易对分类到不同类别
        2. 提取每个交易对的关键费率信息
        3. 统计所有唯一资产名称
    
    费率字段说明:
        - fundingFeePerBlockP: 每区块资金费率（crypto 资产）
        - rolloverFeePerBlockP: 每区块隔夜费率（非 crypto 资产）
        - openFeeP: 开仓手续费（基点）
        - closeFeeP: 平仓手续费（基点）
    
    Args:
        pairs: 从 subgraph 获取的交易对列表
        
    Returns:
        dict: 分析结果
            {
                "categories": {
                    "crypto": [...],      # 加密货币交易对
                    "forex": [...],       # 外汇交易对
                    "commodities": [...], # 大宗商品交易对
                    "stocks": [...],      # 股票交易对
                    "indices": [...],     # 指数交易对
                    "other": [...]        # 未分类
                },
                "all_assets": ["BTC", "ETH", "USD", ...],  # 所有唯一资产
                "total_pairs": 25                          # 交易对总数
            }
    """
    print(f"\n=== Ostium 交易对分析 ===")
    print(f"总交易对数: {len(pairs)}")
    
    # ===== 初始化分类容器 =====
    # 为每个资产类别创建空列表
    categories = {name: [] for name in GROUP_INDEX_MAP.values()}
    categories["other"] = []  # 未知分类
    
    # 存储所有唯一资产名称
    all_assets = set()
    
    # ===== 遍历每个交易对进行分类 =====
    for pair in pairs:
        # 提取资产名称
        from_asset = pair.get("from", "")  # 基础资产（如 "BTC"）
        to_asset = pair.get("to", "")      # 报价资产（如 "USD"）
        group_index = pair.get("groupIndex")  # 分类索引
        
        # 添加到资产集合
        all_assets.add(from_asset)
        all_assets.add(to_asset)
        
        # 提取关键信息（含费率配置）
        pair_info = {
            "id": pair.get("id"),                          # 交易对 ID
            "from": from_asset,                            # 基础资产
            "to": to_asset,                                # 报价资产
            "pair": f"{from_asset}/{to_asset}",            # 交易对名称
            "groupIndex": group_index,                     # 分类索引
            # 费率配置
            "fundingFeePerBlockP": pair.get("fundingFeePerBlockP"),  # 资金费率/区块
            "rolloverFeePerBlockP": pair.get("rolloverFeePerBlockP"), # 隔夜费/区块
            "openFeeP": pair.get("openFeeP"),              # 开仓手续费
            "closeFeeP": pair.get("closeFeeP"),            # 平仓手续费
            # 杠杆限制
            "minLeverage": pair.get("minLeverage"),        # 最小杠杆
            "maxLeverage": pair.get("maxLeverage"),        # 最大杠杆
        }
        
        # 根据 groupIndex 分类
        category = GROUP_INDEX_MAP.get(group_index, "other")
        categories[category].append(pair_info)
    
    # ===== 打印分类统计 =====
    print(f"\n资产分类（按 groupIndex）:")
    for name, items in categories.items():
        if items:  # 只打印有内容的分类
            print(f"  {name}: {len(items)}")
    
    print(f"\n所有唯一资产 ({len(all_assets)}): {sorted(all_assets)}")
    
    return {
        "categories": categories,           # 按类别分组的交易对
        "all_assets": sorted(list(all_assets)),  # 所有唯一资产（已排序）
        "total_pairs": len(pairs)           # 交易对总数
    }


# ==================== 数据保存函数 ====================

def save_data(pairs: List[Dict], prices: List[Dict], analysis: Dict[str, Any]):
    """
    保存所有数据到 JSON 文件
    
    输出文件结构 (ostium_response.json):
        {
            "pairs": [                      # 交易对原始数据
                {
                    "id": "0",
                    "from": "BTC",
                    "to": "USD",
                    "groupIndex": 0,
                    "longOI": "16190118096356189197",
                    "shortOI": "19987432486160506187",
                    "curFundingLong": 2973925102,
                    "curFundingShort": -2416694579,
                    "rolloverFeePerBlock": 0,
                    ...
                },
                ...
            ],
            "prices": [                     # 价格数据
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
            "analysis": {                   # 分析结果
                "categories": {...},
                "all_assets": [...],
                "total_pairs": 25
            }
        }
    
    Args:
        pairs: 交易对数据列表
        prices: 价格数据列表
        analysis: 分析结果字典
    """
    # 构建输出数据
    data = {
        "pairs": pairs,       # 交易对原始数据
        "prices": prices,     # 价格数据
        "analysis": analysis  # 分析结果
    }
    
    # 构建完整路径（相对于脚本所在目录）
    response_path = os.path.join(SCRIPT_DIR, "ostium_response.json")
    assets_path = os.path.join(SCRIPT_DIR, "ostium_assets.txt")
    
    # 写入 JSON 文件
    # default=str 用于处理无法序列化的对象（如 Decimal）
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n数据已保存到 ostium_response.json")
    
    # 保存资产名称列表（便于快速查看支持的资产）
    with open(assets_path, "w", encoding="utf-8") as f:
        for asset in analysis["all_assets"]:
            f.write(f"{asset}\n")
    print(f"资产列表已保存到 ostium_assets.txt")


# ==================== 辅助函数 ====================

def print_sample_data(pairs: List[Dict]):
    """
    打印示例数据用于验证
    
    选择 BTC 交易对作为示例，打印其完整的原始数据结构，
    便于开发者了解数据格式。
    
    Args:
        pairs: 交易对列表
    """
    # 查找 BTC 交易对
    btc_pair = next((p for p in pairs if p.get("from") == "BTC"), None)
    
    if btc_pair:
        print(f"\n=== 示例数据 (BTC) ===")
        # 格式化打印 JSON
        print(json.dumps(btc_pair, indent=2, default=str))


# ==================== 主函数 ====================

async def main():
    """
    主函数 - 执行完整的数据获取流程（异步）
    
    执行步骤:
        1. 初始化 SDK 并获取所有数据（交易对 + 价格）
        2. 分析交易对数据（按类别分组）
        3. 打印 BTC 示例数据
        4. 保存所有数据到 JSON 文件
    
    注意: 使用 asyncio.run() 运行此异步函数
    """
    # 打印标题
    print("=" * 50)
    print("Ostium Data Inspector (SDK Mode)")
    print("=" * 50)
    
    try:
        # ===== 步骤 1: 获取所有数据 =====
        data = await fetch_all_data()
        pairs = data["pairs"]    # 交易对信息
        prices = data["prices"]  # 价格数据
        
        # ===== 步骤 2: 分析交易对数据 =====
        analysis = analyze_pairs(pairs)
        
        # ===== 步骤 3: 打印示例数据 =====
        print_sample_data(pairs)
        
        # ===== 步骤 4: 保存数据 =====
        save_data(pairs, prices, analysis)
        
        # 完成提示
        print("\n" + "=" * 50)
        print("数据获取完成！")
        print("=" * 50)
        
    except ImportError:
        # SDK 未安装的错误处理
        print("\n错误: ostium-python-sdk 未安装")
        print("请运行: pip install ostium-python-sdk")
    except Exception as e:
        # 其他错误的处理
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


# ==================== 程序入口 ====================
if __name__ == "__main__":
    # 使用 asyncio.run() 运行异步主函数
    asyncio.run(main())
