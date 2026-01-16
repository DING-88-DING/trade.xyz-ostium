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
# 将父目录添加到 sys.path，以便能够 import 父目录的 config.py
import sys
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# 尝试从 config.py 加载 Arbitrum RPC URL
try:
    from config import ARBITRUM_RPC_URL
except ImportError:
    # config.py 不存在时的警告
    print("警告: 未找到 config.py，请设置 ARBITRUM_RPC_URL")
    ARBITRUM_RPC_URL = None




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



# ==================== 数据保存函数 ====================

def save_data(pairs: List[Dict], prices: List[Dict]):
    """
    保存所有数据到 JSON 文件
    
    输出文件结构 (ostium_response.json):
        {
            "pairs": [...],   # 交易对原始数据
            "prices": [...]   # 价格数据
        }
    
    Args:
        pairs: 交易对数据列表
        prices: 价格数据列表
    """
    # 构建输出数据
    data = {
        "pairs": pairs,       # 交易对原始数据
        "prices": prices      # 价格数据
    }
    
    # 构建完整路径（相对于脚本所在目录）
    response_path = os.path.join(SCRIPT_DIR, "ostium_response.json")
    assets_path = os.path.join(SCRIPT_DIR, "ostium_assets.txt")
    
    # 写入 JSON 文件
    # default=str 用于处理无法序列化的对象（如 Decimal）
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n数据已保存到 ostium_response.json")
    print(f"  交易对数量: {len(pairs)}")
    print(f"  价格数据数量: {len(prices)}")
    
    # 收集所有唯一资产名称并保存
    all_assets = set()
    for pair in pairs:
        all_assets.add(pair.get("from", ""))
        all_assets.add(pair.get("to", ""))
    
    with open(assets_path, "w", encoding="utf-8") as f:
        for asset in sorted(all_assets):
            if asset:  # 跳过空字符串
                f.write(f"{asset}\n")
    print(f"资产列表已保存到 ostium_assets.txt ({len(all_assets)} 个资产)")


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
        2. 打印 BTC 示例数据
        3. 保存所有数据到 JSON 文件
    
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
        
        # ===== 步骤 2: 打印示例数据 =====
        print_sample_data(pairs)
        
        # ===== 步骤 3: 保存数据 =====
        save_data(pairs, prices)
        
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
