"""
Hyperliquid Data Inspector
使用 Hyperliquid Python SDK 获取资产数据
SDK: https://github.com/hyperliquid-dex/hyperliquid-python-sdk

功能：
- 获取主 DEX 永续合约（BTC, ETH, SOL 等）
- 获取 Builder-Deployed DEX 合约（GOLD, SILVER 等 TradFi 资产）
- 获取现货交易对
"""

import json
import requests
from hyperliquid.info import Info
from hyperliquid.utils import constants

# 配置
try:
    from config import HYPERLIQUID_API_URL
except ImportError:
    print("警告: 未找到 config.py，使用默认配置")
    HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"


def get_perp_dexs():
    """
    获取所有永续合约 DEX（包括主 DEX 和 Builder-Deployed DEX）
    
    Returns:
        DEX 列表
    """
    response = requests.post(
        f"{HYPERLIQUID_API_URL}/info",
        headers={"Content-Type": "application/json"},
        json={"type": "perpDexs"}
    )
    
    if response.status_code == 200:
        dexs = response.json()
        # 过滤掉 None 值（主 DEX 用空字符串表示）
        valid_dexs = [d for d in dexs if d is not None]
        print(f"发现 {len(valid_dexs)} 个 Builder-Deployed DEX")
        return dexs
    else:
        print(f"获取 perpDexs 失败: {response.status_code}")
        return []


def get_meta_and_asset_ctxs(dex: str = ""):
    """
    获取指定 DEX 的永续合约元数据和资产上下文
    
    Args:
        dex: DEX 名称，空字符串表示主 DEX
        
    Returns:
        (perpetuals, meta)
    """
    payload = {"type": "metaAndAssetCtxs"}
    if dex:
        payload["dex"] = dex
    
    response = requests.post(
        f"{HYPERLIQUID_API_URL}/info",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    if response.status_code != 200:
        print(f"获取 {dex or '主 DEX'} 数据失败: {response.status_code}")
        return [], {}
    
    data = response.json()
    meta = data[0] if len(data) > 0 else {}
    asset_ctxs = data[1] if len(data) > 1 else []
    
    universe = meta.get("universe", [])
    
    perpetuals = []
    for idx, asset in enumerate(universe):
        ctx = asset_ctxs[idx] if idx < len(asset_ctxs) else {}
        
        perp_info = {
            "index": idx,
            "coin": asset.get("name", ""),
            "dex": dex if dex else "main",
            "szDecimals": asset.get("szDecimals"),
            "maxLeverage": asset.get("maxLeverage"),
            # 市场数据
            "funding": ctx.get("funding"),
            "openInterest": ctx.get("openInterest"),
            "dayNtlVlm": ctx.get("dayNtlVlm"),
            "prevDayPx": ctx.get("prevDayPx"),
            # 价格数据
            "oraclePx": ctx.get("oraclePx"),
            "markPx": ctx.get("markPx"),
            "midPx": ctx.get("midPx"),
            "premium": ctx.get("premium"),
            "impactPxs": ctx.get("impactPxs"),
        }
        perpetuals.append(perp_info)
    
    return perpetuals, meta


def get_all_perpetuals():
    """
    获取所有永续合约（主 DEX + Builder-Deployed DEX）
    
    Returns:
        所有合约列表, 元数据字典
    """
    all_perpetuals = []
    all_meta = {}
    
    # 1. 获取主 DEX 数据
    print("=== 获取主 DEX 永续合约 ===")
    main_perps, main_meta = get_meta_and_asset_ctxs("")
    print(f"主 DEX 合约数量: {len(main_perps)}")
    all_perpetuals.extend(main_perps)
    all_meta["main"] = main_meta
    
    # 2. 获取所有 Builder-Deployed DEX
    print("\n=== 获取 Builder-Deployed DEX 永续合约 ===")
    dexs = get_perp_dexs()
    
    for dex in dexs:
        if dex is None:
            continue
            
        dex_name = dex.get("name", "")
        if not dex_name:
            continue
            
        print(f"获取 DEX: {dex_name} ({dex.get('fullName', '')})")
        perps, meta = get_meta_and_asset_ctxs(dex_name)
        print(f"  合约数量: {len(perps)}")
        
        all_perpetuals.extend(perps)
        all_meta[dex_name] = meta
    
    return all_perpetuals, all_meta


def get_spot_data():
    """获取现货数据"""
    info = Info(HYPERLIQUID_API_URL, skip_ws=True)
    
    data = info.spot_meta_and_asset_ctxs()
    
    spot_meta = data[0] if len(data) > 0 else {}
    spot_ctxs = data[1] if len(data) > 1 else []
    
    universe = spot_meta.get("universe", [])
    tokens = spot_meta.get("tokens", [])
    
    print(f"\n=== Hyperliquid 现货 ===")
    print(f"交易对数量: {len(universe)}")
    print(f"代币数量: {len(tokens)}")
    
    token_map = {t["index"]: t for t in tokens}
    
    spot_pairs = []
    for idx, pair in enumerate(universe):
        ctx = spot_ctxs[idx] if idx < len(spot_ctxs) else {}
        token_indices = pair.get("tokens", [])
        
        base_token = token_map.get(token_indices[0], {}) if len(token_indices) > 0 else {}
        quote_token = token_map.get(token_indices[1], {}) if len(token_indices) > 1 else {}
        
        base_name = base_token.get("name", "")
        quote_name = quote_token.get("name", "")
        
        pair_name = pair.get("name", "")
        readable_name = f"{base_name}/{quote_name}" if base_name and quote_name else pair_name
        
        spot_info = {
            "index": pair.get("index"),
            "coin": pair_name,
            "pair": readable_name,
            "base": base_name,
            "quote": quote_name,
            "baseFullName": base_token.get("fullName"),
            "prevDayPx": ctx.get("prevDayPx"),
            "dayNtlVlm": ctx.get("dayNtlVlm"),
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
    print("\n" + "=" * 60)
    print("数据摘要")
    print("=" * 60)
    
    # 按 DEX 分组统计
    dex_counts = {}
    for p in perpetuals:
        dex = p.get("dex", "unknown")
        dex_counts[dex] = dex_counts.get(dex, 0) + 1
    
    print("\n永续合约分布:")
    for dex, count in dex_counts.items():
        print(f"  {dex}: {count} 个合约")
    
    # 检查 TradFi 合约
    tradfi_assets = ["GOLD", "SILVER", "CL", "PAXG"]
    print("\n TradFi 资产检查:")
    for asset in tradfi_assets:
        found = [p for p in perpetuals if asset in p.get("coin", "").upper()]
        if found:
            for p in found:
                price = p.get("markPx") or p.get("midPx") or "N/A"
                print(f"  ✓ {p['coin']} (DEX: {p['dex']}) - 价格: {price}")
        else:
            print(f"  ✗ {asset} - 未找到")
    
    # 按24h成交量排序前10
    sorted_perps = sorted(
        [p for p in perpetuals if p.get("dayNtlVlm") and float(p["dayNtlVlm"]) > 0],
        key=lambda x: float(x["dayNtlVlm"]),
        reverse=True
    )[:10]
    
    print("\n永续合约 Top 10 (按24h成交量):")
    print("-" * 60)
    for p in sorted_perps:
        vol = float(p["dayNtlVlm"])
        funding = p.get("funding", "N/A")
        print(f"{p['coin']:10} [{p['dex']:6}] | 24h Vol: ${vol:>15,.0f} | Funding: {funding}")
    print("-" * 60)
    
    # 现货统计
    active_spots = [s for s in spot_pairs if s.get("dayNtlVlm") and float(s["dayNtlVlm"]) > 0]
    print(f"\n活跃现货交易对: {len(active_spots)}/{len(spot_pairs)}")


def main():
    try:
        print("正在连接 Hyperliquid API...\n")
        
        # 获取所有永续合约（包含 Builder-Deployed）
        perpetuals, perp_meta = get_all_perpetuals()
        
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
        print(f"\n总计: {len(perpetuals)} 个永续合约")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
