# -*- coding: utf-8 -*-
"""
数据对比模块
对比 Ostium 和 Trade.xyz 两个平台的合约数据
"""

import json
from typing import Dict, List, Tuple


def normalize_symbol(symbol: str) -> str:
    """
    标准化合约符号以便匹配
    
    Args:
        symbol: 原始合约符号
        
    Returns:
        str: 标准化后的符号
    """
    # 移除可能的前缀(如 "xyz:")
    symbol = symbol.split(':')[-1]
    
    # 统一转换为大写
    symbol = symbol.upper()
    
    # 处理常见的命名差异
    replacements = {
        'BTC/USD': 'BTC',
        'ETH/USD': 'ETH',
        'BITCOIN': 'BTC',
        'ETHEREUM': 'ETH',
    }
    
    for old, new in replacements.items():
        if old in symbol:
            symbol = symbol.replace(old, new)
    
    return symbol


def match_contracts(ostium_data: List[Dict], tradexyz_data: List[Dict]) -> List[Dict]:
    """
    匹配两个平台的相同合约
    
    Args:
        ostium_data: Ostium 平台数据
        tradexyz_data: Trade.xyz 平台数据
        
    Returns:
        List[Dict]: 匹配成功的合约对比数据
    """
    # 创建 Trade.xyz 数据的查找字典
    tradexyz_dict = {}
    for contract in tradexyz_data:
        normalized = normalize_symbol(contract['symbol'])
        tradexyz_dict[normalized] = contract
    
    matched_contracts = []
    
    for ostium_contract in ostium_data:
        # 尝试多种匹配方式
        symbol_variants = [
            normalize_symbol(ostium_contract['symbol']),
            normalize_symbol(ostium_contract.get('from', '')),
            f"{ostium_contract.get('from', '')}".upper(),
        ]
        
        tradexyz_contract = None
        matched_symbol = None
        
        for variant in symbol_variants:
            if variant in tradexyz_dict:
                tradexyz_contract = tradexyz_dict[variant]
                matched_symbol = variant
                break
        
        if tradexyz_contract:
            # 计算价格差异
            ostium_price = ostium_contract.get('price', 0)
            tradexyz_price = tradexyz_contract.get('price', 0)
            
            if ostium_price > 0 and tradexyz_price > 0:
                price_diff = tradexyz_price - ostium_price
                price_diff_pct = (price_diff / ostium_price) * 100
            else:
                price_diff = 0
                price_diff_pct = 0
            
            # 计算资金费率差异
            ostium_funding = ostium_contract.get('funding_rate', 0)
            tradexyz_funding = tradexyz_contract.get('funding_rate', 0)
            funding_diff = tradexyz_funding - ostium_funding
            
            matched_contract = {
                'symbol': ostium_contract['symbol'],
                'matched_symbol': matched_symbol,
                'ostium': {
                    'price': ostium_price,
                    'funding_rate': ostium_funding,
                    'volume_24h': ostium_contract.get('volume_24h', 0)
                },
                'tradexyz': {
                    'price': tradexyz_price,
                    'funding_rate': tradexyz_funding,
                    'volume_24h': tradexyz_contract.get('volume_24h', 0)
                },
                'comparison': {
                    'price_diff': price_diff,
                    'price_diff_pct': price_diff_pct,
                    'funding_diff': funding_diff,
                    'has_arbitrage_opportunity': abs(price_diff_pct) > 0.5  # 价格差异>0.5%视为套利机会
                }
            }
            
            matched_contracts.append(matched_contract)
    
    print(f"成功匹配 {len(matched_contracts)} 个合约")
    return matched_contracts


def generate_comparison_report(matched_contracts: List[Dict]) -> Dict:
    """
    生成对比报告
    
    Args:
        matched_contracts: 匹配的合约列表
        
    Returns:
        Dict: 对比报告
    """
    # 按价格差异百分比排序
    sorted_by_price_diff = sorted(
        matched_contracts,
        key=lambda x: abs(x['comparison']['price_diff_pct']),
        reverse=True
    )
    
    # 按资金费率差异排序
    sorted_by_funding_diff = sorted(
        matched_contracts,
        key=lambda x: abs(x['comparison']['funding_diff']),
        reverse=True
    )
    
    # 统计套利机会
    arbitrage_opportunities = [
        c for c in matched_contracts
        if c['comparison']['has_arbitrage_opportunity']
    ]
    
    report = {
        'total_matched': len(matched_contracts),
        'arbitrage_opportunities': len(arbitrage_opportunities),
        'top_price_differences': sorted_by_price_diff[:10],
        'top_funding_differences': sorted_by_funding_diff[:10],
        'all_comparisons': matched_contracts
    }
    
    return report


def save_comparison_result(report: Dict, filename: str = "comparison_result.json"):
    """
    保存对比结果到JSON文件
    
    Args:
        report: 对比报告
        filename: 文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"对比结果已保存到 {filename}")
    except Exception as e:
        print(f"保存对比结果失败: {e}")


def load_json_file(filename: str) -> List[Dict]:
    """
    从JSON文件加载数据
    
    Args:
        filename: 文件名
        
    Returns:
        List[Dict]: 数据列表
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"文件未找到: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"解析JSON文件失败: {filename} - {e}")
        return []


if __name__ == "__main__":
    # 测试代码
    print("=== 加载数据 ===")
    ostium_data = load_json_file("ostium_data.json")
    tradexyz_data = load_json_file("tradexyz_data.json")
    
    if ostium_data and tradexyz_data:
        print(f"Ostium 数据: {len(ostium_data)} 个合约")
        print(f"Trade.xyz 数据: {len(tradexyz_data)} 个合约")
        
        print("\n=== 匹配合约 ===")
        matched = match_contracts(ostium_data, tradexyz_data)
        
        print("\n=== 生成对比报告 ===")
        report = generate_comparison_report(matched)
        
        print(f"发现 {report['arbitrage_opportunities']} 个潜在套利机会")
        
        save_comparison_result(report)
    else:
        print("无法加载数据文件,请先运行 fetch_data.py 获取数据")
