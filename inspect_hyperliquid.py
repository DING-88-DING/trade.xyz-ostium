"""
Hyperliquid Data Inspector
使用 Hyperliquid Python SDK 获取资产数据
SDK: https://github.com/hyperliquid-dex/hyperliquid-python-sdk

注意：
- 永续合约使用 coin 名称（如 BTC, ETH）
- 现货交易对使用 @{index} 格式（如 @107 表示 HYPE/USDC）
- Hyperliquid 没有黄金等 RWA 永续合约
"""

import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

# 导入配置
try:
    from config import HYPERLIQUID_API_URL
except ImportError:
    print("警告: 未找到 config.py，使用默认配置")
    HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"


def get_perpetuals_data():
    """
    获取永续合约数据（包含资金费率、OI、24h成交量等）
    
    Returns:
        perpetuals: 合约列表
        meta: 元数据
    """
    info = Info(HYPERLIQUID_API_URL, skip_ws=True)
    
    # 获取完整数据：meta + assetCtxs
    data = info.meta_and_asset_ctxs()
    
    meta = data[0] if len(data) > 0 else {}
    asset_ctxs = data[1] if len(data) > 1 else []
    
    universe = meta.get("universe", [])
    
    print(f"=== Hyperliquid 永续合约 ===")
    print(f"合约数量: {len(universe)}")
    
    # 合并 meta 和 assetCtxs 数据
    perpetuals = []
    for idx, asset in enumerate(universe):
        ctx = asset_ctxs[idx] if idx < len(asset_ctxs) else {}
        
        perp_info = {
            "index": idx,
            "coin": asset.get("name", ""),  # 统一使用 coin 字段名
            "szDecimals": asset.get("szDecimals"),
            "maxLeverage": asset.get("maxLeverage"),
            # 市场数据
            "funding": ctx.get("funding"),           # 资金费率（8小时）
            "openInterest": ctx.get("openInterest"), # 持仓量
            "dayNtlVlm": ctx.get("dayNtlVlm"),       # 24小时成交量（名义价值）
            "prevDayPx": ctx.get("prevDayPx"),       # 前一天价格
            # 价格数据
            "oraclePx": ctx.get("oraclePx"),         # 预言机价格
            "markPx": ctx.get("markPx"),             # 标记价格
            "midPx": ctx.get("midPx"),               # 中间价
            "premium": ctx.get("premium"),           # 溢价
            "impactPxs": ctx.get("impactPxs"),       # 冲击价格 [bid, ask]
        }
        perpetuals.append(perp_info)
    
    return perpetuals, meta


def get_spot_data():
    """
    获取现货数据
    
    注意：现货交易对名称格式：
    - PURR/USDC 直接使用 PURR
    - 其他使用 @{index}，如 @107 表示 HYPE/USDC
    
    Returns:
        spot_pairs: 现货交易对列表
        spot_meta: 现货元数据
    """
    info = Info(HYPERLIQUID_API_URL, skip_ws=True)
    
    # 获取现货元数据
    data = info.spot_meta_and_asset_ctxs()
    
    spot_meta = data[0] if len(data) > 0 else {}
    spot_ctxs = data[1] if len(data) > 1 else []
    
    universe = spot_meta.get("universe", [])
    tokens = spot_meta.get("tokens", [])
    
    print(f"\n=== Hyperliquid 现货 ===")
    print(f"交易对数量: {len(universe)}")
    print(f"代币数量: {len(tokens)}")
    
    # 构建代币索引映射
    token_map = {t["index"]: t for t in tokens}
    
    spot_pairs = []
    for idx, pair in enumerate(universe):
        ctx = spot_ctxs[idx] if idx < len(spot_ctxs) else {}
        token_indices = pair.get("tokens", [])
        
        base_token = token_map.get(token_indices[0], {}) if len(token_indices) > 0 else {}
        quote_token = token_map.get(token_indices[1], {}) if len(token_indices) > 1 else {}
        
        base_name = base_token.get("name", "")
        quote_name = quote_token.get("name", "")
        
        # 构建可读的交易对名称
        pair_name = pair.get("name", "")  # 原始名称如 @107
        readable_name = f"{base_name}/{quote_name}" if base_name and quote_name else pair_name
        
        spot_info = {
            "index": pair.get("index"),
            "coin": pair_name,           # API 需要的名称（@107 格式）
            "pair": readable_name,       # 可读名称（HYPE/USDC 格式）
            "base": base_name,
            "quote": quote_name,
            "baseFullName": base_token.get("fullName"),
            # 市场数据
            "prevDayPx": ctx.get("prevDayPx"),
            "dayNtlVlm": ctx.get("dayNtlVlm"),   # 24小时成交量
            "markPx": ctx.get("markPx"),
            "midPx": ctx.get("midPx"),
            "circulatingSupply": ctx.get("circulatingSupply"),
        }
        spot_pairs.append(spot_info)
    
    return spot_pairs, spot_meta


def save_data(perpetuals, spot_pairs, perp_meta, spot_meta):
    """保存数据到 JSON 文件"""
    data = {
        "perpetuals": perpetuals,
        "spot": spot_pairs,
        "perp_meta": perp_meta,
        "spot_meta": spot_meta
    }
    
    with open("hyperliquid_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存到 hyperliquid_response.json")


def print_summary(perpetuals, spot_pairs):
    """打印数据摘要"""
    print("\n=== 数据摘要 ===")
    
    # 永续合约统计
    active_perps = [p for p in perpetuals if p.get("openInterest") and float(p["openInterest"]) > 0]
    print(f"活跃永续合约: {len(active_perps)}/{len(perpetuals)}")
    
    # 按24h成交量排序前10
    sorted_perps = sorted(
        [p for p in perpetuals if p.get("dayNtlVlm")],
        key=lambda x: float(x["dayNtlVlm"]),
        reverse=True
    )[:10]
    
    print("\n永续合约 Top 10 (按24h成交量):")
    print("-" * 60)
    for p in sorted_perps:
        vol = float(p["dayNtlVlm"])
        funding = p.get("funding", "N/A")
        print(f"{p['coin']:8} | 24h Vol: ${vol:>15,.0f} | Funding: {funding}")
    print("-" * 60)
    
    # 现货统计
    active_spots = [s for s in spot_pairs if s.get("dayNtlVlm") and float(s["dayNtlVlm"]) > 0]
    print(f"\n活跃现货交易对: {len(active_spots)}/{len(spot_pairs)}")


def main():
    try:
        print("正在连接 Hyperliquid API...\n")
        
        # 获取永续合约数据
        perpetuals, perp_meta = get_perpetuals_data()
        
        # 获取现货数据
        spot_pairs, spot_meta = get_spot_data()
        
        # 打印摘要
        print_summary(perpetuals, spot_pairs)
        
        # 保存数据
        save_data(perpetuals, spot_pairs, perp_meta, spot_meta)
        
        # 保存资产名称列表
        all_names = set([p["coin"] for p in perpetuals])
        with open("hyperliquid_assets.txt", "w", encoding="utf-8") as f:
            for name in sorted(all_names):
                f.write(f"{name}\n")
        
        print(f"资产名称已保存到 hyperliquid_assets.txt")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
