"""
Data Comparison Tool
比较 Hyperliquid 和 Ostium 两个平台的资产数据
"""

import json
from typing import Dict, Set, List


def load_json(filename: str) -> dict:
    """加载 JSON 文件"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"文件未找到: {filename}")
        return {}
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误 {filename}: {e}")
        return {}


def get_hyperliquid_assets(data: dict) -> Set[str]:
    """从 Hyperliquid 数据中提取资产名称"""
    assets = set()

    # 永续合约资产
    perpetuals = data.get("perpetuals", [])
    for item in perpetuals:
        name = item.get("name", "")
        if name:
            assets.add(name.upper())

    # 现货资产
    spot = data.get("spot", [])
    for item in spot:
        base = item.get("base", "")
        if base:
            assets.add(base.upper())

    return assets


def get_ostium_assets(data: dict) -> Set[str]:
    """从 Ostium 数据中提取资产名称"""
    assets = set()

    # 从分析结果中获取
    analysis = data.get("analysis", {})
    all_assets = analysis.get("all_assets", [])

    for asset in all_assets:
        if asset:
            assets.add(asset.upper())

    # 如果没有分析结果，从原始数据获取
    if not assets:
        raw_prices = data.get("raw_prices", [])
        for item in raw_prices:
            from_asset = item.get("from", "")
            to_asset = item.get("to", "")
            if from_asset:
                assets.add(from_asset.upper())
            if to_asset:
                assets.add(to_asset.upper())

    return assets


def compare_assets(hl_assets: Set[str], ost_assets: Set[str]) -> Dict:
    """比较两个平台的资产"""
    # 交集 - 两个平台都有的资产
    common = hl_assets.intersection(ost_assets)

    # Hyperliquid 独有
    hl_only = hl_assets - ost_assets

    # Ostium 独有
    ost_only = ost_assets - hl_assets

    return {
        "common": sorted(common),
        "hyperliquid_only": sorted(hl_only),
        "ostium_only": sorted(ost_only)
    }


def print_comparison_report(comparison: Dict, hl_assets: Set[str], ost_assets: Set[str]):
    """打印比较报告"""
    print("=" * 60)
    print("        Hyperliquid vs Ostium 资产比较报告")
    print("=" * 60)

    print(f"\n📊 统计概览:")
    print(f"   Hyperliquid 资产总数: {len(hl_assets)}")
    print(f"   Ostium 资产总数: {len(ost_assets)}")
    print(f"   共同资产数量: {len(comparison['common'])}")

    print(f"\n✅ 共同资产 ({len(comparison['common'])}):")
    if comparison['common']:
        # 分行显示，每行 10 个
        common_list = comparison['common']
        for i in range(0, len(common_list), 10):
            print(f"   {', '.join(common_list[i:i+10])}")
    else:
        print("   (无)")

    print(f"\n🔵 Hyperliquid 独有 ({len(comparison['hyperliquid_only'])}):")
    if comparison['hyperliquid_only']:
        hl_only = comparison['hyperliquid_only']
        for i in range(0, min(len(hl_only), 50), 10):
            print(f"   {', '.join(hl_only[i:i+10])}")
        if len(hl_only) > 50:
            print(f"   ... 还有 {len(hl_only) - 50} 个")
    else:
        print("   (无)")

    print(f"\n🟠 Ostium 独有 ({len(comparison['ostium_only'])}):")
    if comparison['ostium_only']:
        ost_only = comparison['ostium_only']
        for i in range(0, min(len(ost_only), 50), 10):
            print(f"   {', '.join(ost_only[i:i+10])}")
        if len(ost_only) > 50:
            print(f"   ... 还有 {len(ost_only) - 50} 个")
    else:
        print("   (无)")

    print("\n" + "=" * 60)


def save_comparison_result(comparison: Dict, hl_assets: Set[str], ost_assets: Set[str]):
    """保存比较结果到 JSON 文件"""
    result = {
        "summary": {
            "hyperliquid_total": len(hl_assets),
            "ostium_total": len(ost_assets),
            "common_count": len(comparison["common"]),
            "hyperliquid_only_count": len(comparison["hyperliquid_only"]),
            "ostium_only_count": len(comparison["ostium_only"])
        },
        "common_assets": comparison["common"],
        "hyperliquid_only": comparison["hyperliquid_only"],
        "ostium_only": comparison["ostium_only"]
    }

    with open("comparison_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("比较结果已保存到 comparison_result.json")


def main():
    print("正在加载数据...\n")

    # 加载数据
    hl_data = load_json("hyperliquid_response.json")
    ost_data = load_json("ostium_response.json")

    if not hl_data:
        print("请先运行 python inspect_hyperliquid.py 获取 Hyperliquid 数据")
        return

    if not ost_data:
        print("请先运行 python inspect_ostium.py 获取 Ostium 数据")
        return

    # 提取资产
    print("正在提取资产...")
    hl_assets = get_hyperliquid_assets(hl_data)
    ost_assets = get_ostium_assets(ost_data)

    print(f"Hyperliquid 资产: {len(hl_assets)}")
    print(f"Ostium 资产: {len(ost_assets)}")

    # 比较资产
    print("\n正在比较资产...\n")
    comparison = compare_assets(hl_assets, ost_assets)

    # 打印报告
    print_comparison_report(comparison, hl_assets, ost_assets)

    # 保存结果
    save_comparison_result(comparison, hl_assets, ost_assets)


if __name__ == "__main__":
    main()
