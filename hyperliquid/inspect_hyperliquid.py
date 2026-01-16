"""
Hyperliquid 永续合约数据获取工具
================================================================================

功能说明:
    1. 获取主 DEX 永续合约数据（BTC, ETH, SOL 等主流加密货币）
    2. 获取 Builder-Deployed DEX 合约数据（GOLD, SILVER 等 TradFi 资产）
    3. 将数据保存到 JSON 文件供后续处理

API 文档:
    - Hyperliquid Info API: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
    - Python SDK: https://github.com/hyperliquid-dex/hyperliquid-python-sdk

数据流程:
    1. 调用 /info API (type: metaAndAssetCtxs) 获取主 DEX 数据
    2. 调用 /info API (type: perpDexs) 获取所有 Builder-Deployed DEX 列表
    3. 遍历每个 Builder DEX，获取其合约数据
    4. 合并所有数据并保存到 hyperliquid_response.json

输出文件:
    - hyperliquid_response.json: 包含 perpetuals（合约实时数据）和 perp_meta（元数据配置）
    - hyperliquid_assets.txt: 所有合约名称列表（用于快速查看）

使用方法:
    python inspect_hyperliquid.py
"""

import json
import os
import requests

# 获取脚本所在目录（确保无论从哪个目录运行都能找到正确的文件路径）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== 配置加载 ====================
# 尝试从 config.py 加载 API URL，如果不存在则使用默认值
try:
    from config import HYPERLIQUID_API_URL
except ImportError:
    # config.py 不存在时的默认配置
    print("警告: 未找到 config.py，使用默认配置")
    HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"


# ==================== API 请求函数 ====================

def get_perp_dexs():
    """
    获取所有永续合约 DEX 列表
    
    API 请求:
        POST {API_URL}/info
        Body: {"type": "perpDexs"}
    
    返回数据结构:
        [
            null,  # 第一个元素为 null，代表主 DEX
            {
                "name": "xyz",           # DEX 短名称（用于 API 调用）
                "fullName": "Trade XYZ", # DEX 完整名称
                "deployer": "0x..."      # 部署者地址
            },
            ...
        ]
    
    Returns:
        list: DEX 列表，包含 null（主 DEX）和各个 Builder-Deployed DEX 信息
    """
    # 构造 API 请求
    response = requests.post(
        f"{HYPERLIQUID_API_URL}/info",  # API 端点
        headers={"Content-Type": "application/json"},  # 必需的请求头
        json={"type": "perpDexs"}  # 请求类型：获取永续合约 DEX 列表
    )
    
    # 检查响应状态
    if response.status_code == 200:
        dexs = response.json()
        # 统计有效的 Builder-Deployed DEX 数量（排除 null 值）
        valid_dexs = [d for d in dexs if d is not None]
        print(f"发现 {len(valid_dexs)} 个 Builder-Deployed DEX")
        return dexs
    else:
        # 请求失败时返回空列表
        print(f"获取 perpDexs 失败: {response.status_code}")
        return []


def get_meta_and_asset_ctxs(dex: str = ""):
    """
    获取指定 DEX 的永续合约元数据和资产上下文
    
    API 请求:
        POST {API_URL}/info
        Body: {"type": "metaAndAssetCtxs"} 或 {"type": "metaAndAssetCtxs", "dex": "xyz"}
    
    返回数据结构 (response.json()):
        [
            # data[0] - 元数据 (meta)
            {
                "universe": [           # 合约配置列表
                    {
                        "name": "BTC",          # 合约名称
                        "szDecimals": 5,        # 数量小数位数
                        "maxLeverage": 40,      # 最大杠杆
                        "marginTableId": 40,    # 保证金表 ID
                        "onlyIsolated": false,  # 是否仅支持逐仓模式
                        "marginMode": "cross"   # 保证金模式
                    },
                    ...
                ],
                "marginTables": [...],  # 保证金层级配置
                "collateralToken": 0    # 抵押品代币索引
            },
            
            # data[1] - 资产上下文列表 (asset_ctxs)，与 universe 一一对应
            [
                {
                    "funding": "0.0000125",           # 每小时资金费率
                    "openInterest": "28865.53616",    # 持仓量（币数量）
                    "dayNtlVlm": "3378409248.59",     # 24小时成交量（USD）
                    "prevDayPx": "96507.0",           # 前一天收盘价
                    "oraclePx": "95630.0",            # Oracle 价格（来自预言机）
                    "markPx": "95636.0",              # 标记价格（用于计算盈亏）
                    "midPx": "95636.5",               # 中间价（买卖价均值）
                    "premium": "0.0000627418",        # 溢价率（标记价格与 Oracle 价格差异）
                    "impactPxs": ["95636.0", "95637.0"]  # 冲击价格 [买价, 卖价]
                },
                ...
            ]
        ]
    
    Args:
        dex: DEX 名称，空字符串 "" 表示主 DEX，"xyz" 等表示 Builder DEX
        
    Returns:
        tuple: (perpetuals, meta)
            - perpetuals: 合约数据列表，每个元素包含合约的完整信息
            - meta: 原始元数据，包含 universe 和 marginTables
    """
    # 构造请求体
    payload = {"type": "metaAndAssetCtxs"}
    if dex:
        # 如果指定了 DEX 名称，添加 dex 参数
        payload["dex"] = dex
    
    # 发送 POST 请求
    response = requests.post(
        f"{HYPERLIQUID_API_URL}/info",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    # 检查响应状态
    if response.status_code != 200:
        print(f"获取 {dex or '主 DEX'} 数据失败: {response.status_code}")
        return [], {}
    
    # 解析响应数据
    data = response.json()
    
    # data[0] 是元数据（包含 universe 配置列表）
    meta = data[0] if len(data) > 0 else {}
    
    # data[1] 是资产上下文列表（包含实时市场数据）
    asset_ctxs = data[1] if len(data) > 1 else []
    
    # 从元数据中获取合约配置列表
    universe = meta.get("universe", [])
    
    # 合并 universe 和 asset_ctxs 数据，构建完整的合约信息
    perpetuals = []
    for idx, asset in enumerate(universe):
        # 获取对应的市场数据（按索引匹配）
        ctx = asset_ctxs[idx] if idx < len(asset_ctxs) else {}
        
        # 构建合约信息对象
        perp_info = {
            # ===== 基础配置（来自 universe） =====
            "index": idx,                           # 合约在该 DEX 中的索引
            "coin": asset.get("name", ""),          # 合约名称（如 "BTC", "xyz:GOLD"）
            "dex": dex if dex else "main",          # 所属 DEX 名称
            "szDecimals": asset.get("szDecimals"),  # 数量小数位数（下单精度）
            "maxLeverage": asset.get("maxLeverage"),# 最大杠杆倍数
            
            # ===== 市场数据（来自 asset_ctxs） =====
            "funding": ctx.get("funding"),          # 每小时资金费率（字符串格式）
            "openInterest": ctx.get("openInterest"),# 持仓量（币数量）
            "dayNtlVlm": ctx.get("dayNtlVlm"),      # 24小时成交量（USD）
            "prevDayPx": ctx.get("prevDayPx"),      # 前一天收盘价
            
            # ===== 价格数据（来自 asset_ctxs） =====
            "oraclePx": ctx.get("oraclePx"),        # Oracle 预言机价格
            "markPx": ctx.get("markPx"),            # 标记价格（用于强平计算）
            "midPx": ctx.get("midPx"),              # 中间价（买卖价均值）
            "premium": ctx.get("premium"),          # 溢价率
            "impactPxs": ctx.get("impactPxs"),      # 冲击价格 [买入价, 卖出价]
        }
        perpetuals.append(perp_info)
    
    return perpetuals, meta


# ==================== 数据聚合函数 ====================

def get_all_perpetuals():
    """
    获取所有永续合约数据（主 DEX + 所有 Builder-Deployed DEX）
    
    执行步骤:
        1. 调用 get_meta_and_asset_ctxs("") 获取主 DEX 数据
        2. 调用 get_perp_dexs() 获取所有 Builder DEX 列表
        3. 遍历每个 Builder DEX，调用 get_meta_and_asset_ctxs(dex_name) 获取数据
        4. 合并所有数据返回
    
    Returns:
        tuple: (all_perpetuals, all_meta)
            - all_perpetuals: 所有合约的列表（主 DEX + Builder DEX）
            - all_meta: 元数据字典，按 DEX 名称索引
                {
                    "main": {...},     # 主 DEX 元数据
                    "xyz": {...},      # xyz DEX 元数据
                    "flx": {...},      # flx DEX 元数据
                    ...
                }
    """
    all_perpetuals = []  # 存储所有合约数据
    all_meta = {}        # 存储各 DEX 的元数据
    
    # ===== 步骤 1: 获取主 DEX 数据 =====
    print("=== 获取主 DEX 永续合约 ===")
    # dex="" 表示获取主 DEX（Hyperliquid 官方的永续合约）
    main_perps, main_meta = get_meta_and_asset_ctxs("")
    print(f"主 DEX 合约数量: {len(main_perps)}")
    
    # 将主 DEX 数据添加到结果中
    all_perpetuals.extend(main_perps)
    all_meta["main"] = main_meta
    
    # ===== 步骤 2: 获取 xyz DEX 数据（过滤掉其他 Builder DEX）=====
    print("\n=== 获取 xyz DEX 永续合约 ===")
    dexs = get_perp_dexs()  # 返回包含 null 和各 DEX 信息的列表
    
    # ===== 步骤 3: 只获取 xyz DEX 数据 =====
    # 过滤: 只保留 name 为 "xyz" 的 DEX
    for dex in dexs:
        # 跳过 null（代表主 DEX，已经在步骤 1 获取过了）
        if dex is None:
            continue
        
        # 获取 DEX 名称
        dex_name = dex.get("name", "")
        if not dex_name:
            continue
        
        # 只处理 xyz DEX，跳过其他 Builder DEX
        if dex_name != "xyz":
            print(f"跳过 DEX: {dex_name}")
            continue
        
        # 打印 DEX 信息
        print(f"获取 DEX: {dex_name} ({dex.get('fullName', '')})")
        
        # 获取该 DEX 的合约数据
        perps, meta = get_meta_and_asset_ctxs(dex_name)
        print(f"  合约数量: {len(perps)}")
        
        # 将数据添加到结果中
        all_perpetuals.extend(perps)
        all_meta[dex_name] = meta
    
    return all_perpetuals, all_meta


# ==================== 数据保存函数 ====================

def save_data(perpetuals, perp_meta):
    """
    保存数据到 JSON 文件
    
    输出文件结构 (hyperliquid_response.json):
        {
            "perpetuals": [             # 所有合约的实时数据列表
                {
                    "index": 0,
                    "coin": "BTC",
                    "dex": "main",
                    "szDecimals": 5,
                    "maxLeverage": 40,
                    "funding": "0.0000125",
                    "openInterest": "28865.53616",
                    "dayNtlVlm": "3378409248.59",
                    "prevDayPx": "96507.0",
                    "oraclePx": "95630.0",
                    "markPx": "95636.0",
                    "midPx": "95636.5",
                    "premium": "0.0000627418",
                    "impactPxs": ["95636.0", "95637.0"]
                },
                ...
            ],
            "perp_meta": {             # 各 DEX 的元数据配置
                "main": {
                    "universe": [...],
                    "marginTables": [...],
                    "collateralToken": 0
                },
                "xyz": {...},
                ...
            }
        }
    
    Args:
        perpetuals: 合约数据列表
        perp_meta: 元数据字典
    """
    # 构建输出数据结构
    data = {
        "perpetuals": perpetuals,  # 合约实时数据
        "perp_meta": perp_meta     # DEX 元数据配置
    }
    
    # 构建完整路径（相对于脚本所在目录）
    response_path = os.path.join(SCRIPT_DIR, "hyperliquid_response.json")
    
    # 写入 JSON 文件
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存到 hyperliquid_response.json")


# ==================== 主函数 ====================

def main():
    """
    主函数 - 执行完整的数据获取流程
    
    执行步骤:
        1. 调用 get_all_perpetuals() 获取所有永续合约数据
        2. 调用 save_data() 保存数据到 JSON 文件
        3. 生成资产名称列表文件 hyperliquid_assets.txt
        4. 打印统计信息
    """
    try:
        print("正在连接 Hyperliquid API...\n")
        
        # ===== 步骤 1: 获取所有永续合约数据 =====
        # 包含主 DEX 和所有 Builder-Deployed DEX 的合约
        perpetuals, perp_meta = get_all_perpetuals()
        
        # ===== 步骤 2: 保存数据到 JSON 文件 =====
        save_data(perpetuals, perp_meta)
        
        # ===== 步骤 3: 生成资产名称列表 =====
        # 提取所有合约名称（去重）
        all_names = set([p["coin"] for p in perpetuals])
        
        # 构建完整路径并写入文件
        assets_path = os.path.join(SCRIPT_DIR, "hyperliquid_assets.txt")
        with open(assets_path, "w", encoding="utf-8") as f:
            for name in sorted(all_names):
                f.write(f"{name}\n")
        
        print(f"资产名称已保存到 hyperliquid_assets.txt")
        
        # ===== 步骤 4: 打印统计信息 =====
        print(f"\n总计: {len(perpetuals)} 个永续合约")
        
    except Exception as e:
        # 捕获并打印异常信息
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
