"""
Ostium Data Inspector
使用 Python SDK 获取资产数据（包含价格和费率）
SDK: pip install ostium-python-sdk
文档: https://github.com/0xOstium/ostium-python-sdk
"""

import json
import asyncio
from typing import Dict, List, Any

# 导入 SDK
from ostium_python_sdk import OstiumSDK
from ostium_python_sdk.config import NetworkConfig

# 导入配置（RPC URL）
try:
    from config import ARBITRUM_RPC_URL
except ImportError:
    print("警告: 未找到 config.py，请设置 ARBITRUM_RPC_URL")
    ARBITRUM_RPC_URL = None

# 资产分类映射（根据 SDK 返回的 groupIndex）
GROUP_INDEX_MAP = {
    0: "crypto",
    1: "forex",
    2: "commodities",
    3: "stocks",
    4: "indices"
}


async def fetch_all_data() -> Dict[str, Any]:
    """
    使用 SDK 获取所有数据：交易对信息和价格
    
    Returns:
        包含 pairs（交易对详情含费率）和 prices（价格数据）的字典
    """
    # 初始化 SDK（使用主网配置）
    config = NetworkConfig.mainnet()
    sdk = OstiumSDK(config, rpc_url=ARBITRUM_RPC_URL)
    
    print("正在通过 SDK 获取数据...")
    
    # 获取所有交易对信息（包含费率等详细数据）
    pairs = await sdk.subgraph.get_pairs()
    print(f"获取到 {len(pairs)} 个交易对信息")
    
    # 获取所有最新价格
    prices = await sdk.price.get_latest_prices()
    print(f"获取到 {len(prices)} 个价格数据")
    
    return {"pairs": pairs, "prices": prices}


def analyze_pairs(pairs: List[Dict]) -> Dict[str, Any]:
    """
    分析交易对数据，按 groupIndex 分类并提取费率信息
    
    Args:
        pairs: 从 subgraph 获取的交易对列表
        
    Returns:
        分析结果字典
    """
    print(f"\n=== Ostium 交易对分析 ===")
    print(f"总交易对数: {len(pairs)}")
    
    # 按 groupIndex 分类
    categories = {name: [] for name in GROUP_INDEX_MAP.values()}
    categories["other"] = []
    all_assets = set()
    
    for pair in pairs:
        from_asset = pair.get("from", "")
        to_asset = pair.get("to", "")
        group_index = pair.get("groupIndex")
        
        all_assets.add(from_asset)
        all_assets.add(to_asset)
        
        # 提取关键信息（含费率）
        pair_info = {
            "id": pair.get("id"),
            "from": from_asset,
            "to": to_asset,
            "pair": f"{from_asset}/{to_asset}",
            "groupIndex": group_index,
            "fundingFeePerBlockP": pair.get("fundingFeePerBlockP"),
            "rolloverFeePerBlockP": pair.get("rolloverFeePerBlockP"),
            "openFeeP": pair.get("openFeeP"),
            "closeFeeP": pair.get("closeFeeP"),
            "minLeverage": pair.get("minLeverage"),
            "maxLeverage": pair.get("maxLeverage"),
        }
        
        # 使用 groupIndex 分类
        category = GROUP_INDEX_MAP.get(group_index, "other")
        categories[category].append(pair_info)
    
    # 打印统计
    print(f"\n资产分类（按 groupIndex）:")
    for name, items in categories.items():
        if items:
            print(f"  {name}: {len(items)}")
    
    print(f"\n所有唯一资产 ({len(all_assets)}): {sorted(all_assets)}")
    
    return {
        "categories": categories,
        "all_assets": sorted(list(all_assets)),
        "total_pairs": len(pairs)
    }


def save_data(pairs: List[Dict], prices: List[Dict], analysis: Dict[str, Any]):
    """保存所有数据到 JSON 文件"""
    data = {
        "pairs": pairs,
        "prices": prices,
        "analysis": analysis
    }
    
    with open("ostium_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n数据已保存到 ostium_response.json")
    
    # 保存资产列表
    with open("ostium_assets.txt", "w", encoding="utf-8") as f:
        for asset in analysis["all_assets"]:
            f.write(f"{asset}\n")
    print(f"资产列表已保存到 ostium_assets.txt")


def print_sample_data(pairs: List[Dict]):
    """打印示例数据用于验证"""
    btc_pair = next((p for p in pairs if p.get("from") == "BTC"), None)
    if btc_pair:
        print(f"\n=== 示例数据 (BTC) ===")
        print(json.dumps(btc_pair, indent=2, default=str))


async def main():
    """主函数：获取、分析并保存 Ostium 数据"""
    print("=" * 50)
    print("Ostium Data Inspector (SDK Mode)")
    print("=" * 50)
    
    try:
        # 获取所有数据
        data = await fetch_all_data()
        pairs = data["pairs"]
        prices = data["prices"]
        
        # 分析交易对数据
        analysis = analyze_pairs(pairs)
        
        # 打印示例
        print_sample_data(pairs)
        
        # 保存数据
        save_data(pairs, prices, analysis)
        
        print("\n" + "=" * 50)
        print("数据获取完成！")
        print("=" * 50)
        
    except ImportError:
        print("\n错误: ostium-python-sdk 未安装")
        print("请运行: pip install ostium-python-sdk")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
