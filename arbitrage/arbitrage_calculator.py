# -*- coding: utf-8 -*-
"""
====================================================================
套利计算器模块 (arbitrage_calculator.py)
====================================================================

这个文件的作用：
- 计算两个交易所之间的套利机会
- 从前端 js/arbitrage.js 迁移过来的核心算法

什么是套利 (Arbitrage)？
- 利用同一资产在不同市场的价格差异赚取利润
- 例如: BTC 在 Hyperliquid 卖 $100,000，在 Ostium 卖 $99,900
        你可以在 Ostium 买入，同时在 Hyperliquid 卖出，锁定 $100 价差

套利的三种回本方式：
1. 价差套利: 如果价格差足够大，可以直接覆盖手续费成本
2. 资金费率套利: 利用两个平台的资金费率差异，持仓赚取费率差
3. 综合套利: 价差 + 资金费率的组合

什么是 Dict, List, Any, Optional？
- 这些是 Python 的"类型提示"(Type Hints)
- 用于告诉读者（和 IDE）函数参数/返回值的类型
- Dict[str, Any] 表示"字典，键是字符串，值是任意类型"
- 不影响代码运行，只是文档作用
"""

# ==================== 导入依赖 ====================
# typing 模块提供类型提示工具
from typing import Dict, Optional, Any

# 从配置文件导入套利参数
from .fee_config import ARBITRAGE_CONFIG


class ArbitrageCalculator:
    """
    套利计算器类
    
    核心功能：
    - 计算套利成本和回本时间
    - 同时计算 Maker 和 Taker 两种方案
    
    使用示例:
        calc = ArbitrageCalculator()
        
        # 计算套利
        result = calc.calculate_arbitrage(
            hl_contract={'mid': 100000, 'bid': 99990, 'ask': 100010, 'fundingRate': {'rateHourly': 0.001}},
            os_contract={'mid': 99900, 'bid': 99890, 'ask': 99910, 'fundingRate': {'longPayHourly': 0.002}},
            hl_fee={'t': 0.045, 'm': 0.015},
            os_fee={'rate': 0.03, 'oracle': 0.10}
        )
        
        print(result['maker'])  # Maker 方案的套利分析
        print(result['taker'])  # Taker 方案的套利分析
    """
    
    def __init__(self, position_size: float = None, max_funding_hours: float = None):
        """
        初始化套利计算器
        
        Args:
            position_size (float): 每次交易的仓位大小 (美元)
                                  如果不传，使用配置文件中的默认值 ($1000)
            max_funding_hours (float): 资金费率回本的最大小时数
                                      如果超过这个时间才能回本，认为不值得
                                      默认 12 小时
        """
        # 使用 or 语法: 如果 position_size 是 None 或 0，就用配置值
        self.position_size = position_size or ARBITRAGE_CONFIG['position_size']
        self.max_funding_hours = max_funding_hours or ARBITRAGE_CONFIG['max_funding_hours']
    
    def calculate_single_arbitrage(
        self,
        hl_cost: float,
        os_cost: float,
        hl_contract: Dict[str, Any],
        os_contract: Dict[str, Any],
        order_type: str = 'maker'
    ) -> Dict[str, Any]:
        """
        计算单一方案的套利数据
        
        这是核心计算函数，分析一种订单类型 (Maker 或 Taker) 下的套利可行性
        
        Args:
            hl_cost (float): Hyperliquid 的交易成本 (美元)
            os_cost (float): Ostium 的交易成本 (美元)
            hl_contract (dict): Hyperliquid 合约数据，包含:
                               - 'mid': 中间价 (买卖价的平均值)
                               - 'bid': 买一价 (你卖出时的成交价)
                               - 'ask': 卖一价 (你买入时的成交价)
                               - 'fundingRate': {'rateHourly': 小时费率}
            os_contract (dict): Ostium 合约数据，格式类似 hl_contract
            order_type (str): 'maker' 或 'taker'
        
        Returns:
            dict: 套利分析结果，包含以下字段:
                - totalCost: 总交易成本 (美元)
                - breakEvenSpreadUSD: 回本所需的最小价差 (美元)
                - currentSpreadUSD: 当前价差 (美元)
                - spreadCanProfit: 价差是否足够回本 (True/False)
                - fundingDiff: 资金费率差异 (百分比)
                - fundingHours: 通过资金费率回本需要的时间 (小时)
                - fundingValid: 资金费率回本是否可行
                - comboHours: 综合回本时间 (小时)
                - comboValid: 综合回本是否可行
                - anyCanProfit: 任意方式能否回本
        """
        # ==================== 准备工作 ====================
        size = self.position_size           # 仓位大小
        max_hours = self.max_funding_hours  # 最大回本时间
        total_cost = hl_cost + os_cost      # 总成本 = HL成本 + OS成本
        
        # ==================== 获取价格数据 ====================
        # 使用 .get() 方法安全获取字典值，如果键不存在返回默认值 0
        # 使用 "or 0" 处理 None 值
        hl_mid = hl_contract.get('mid', 0) or 0    # HL 中间价
        hl_bid = hl_contract.get('bid', 0) or 0    # HL 买一价 (你卖出时用)
        hl_ask = hl_contract.get('ask', 0) or 0    # HL 卖一价 (你买入时用)
        
        os_mid = os_contract.get('mid', 0) or 0    # OS 中间价
        os_bid = os_contract.get('bid', 0) or 0    # OS 买一价
        os_ask = os_contract.get('ask', 0) or 0    # OS 卖一价
        
        # ==================== 计算价差 ====================
        # 价差计算方式取决于订单类型
        if order_type == 'taker':
            # ---- Taker 模式: 使用真实的 bid/ask 价格 ----
            # Taker 是"吃单"，立即成交，价格没有协商空间
            # 
            # 套利方向判断:
            # 如果 HL 价格 > OS 价格:
            #   - 在 HL 做空 (卖出，用 bid 价)
            #   - 在 OS 做多 (买入，用 ask 价)
            #   - 价差 = HL的bid - OS的ask
            # 如果 HL 价格 < OS 价格:
            #   - 在 HL 做多 (买入，用 ask 价)
            #   - 在 OS 做空 (卖出，用 bid 价)
            #   - 价差 = OS的bid - HL的ask
            
            if hl_mid > os_mid:
                # HL 做空 (用 bid), OS 做多 (用 ask)
                hl_price = hl_bid
                os_price = os_ask
                current_spread_usd = hl_price - os_price
            else:
                # HL 做多 (用 ask), OS 做空 (用 bid)
                hl_price = hl_ask
                os_price = os_bid
                current_spread_usd = os_price - hl_price
            
            # 价差可能为负（盘口交叉），说明没有套利空间
            # max(0, x) 确保价差不小于 0
            current_spread_usd = max(0, current_spread_usd)
            
            # 计算平均价格 (用于后续计算)
            avg_price = (hl_price + os_price) / 2 if (hl_price + os_price) > 0 else 1
        else:
            # ---- Maker 模式: 使用中间价 ----
            # Maker 是"挂单"，你可以设定价格等待成交
            # 假设可以在接近 mid 价格成交
            current_spread_usd = abs(hl_mid - os_mid)  # abs() 取绝对值
            avg_price = (hl_mid + os_mid) / 2 if (hl_mid + os_mid) > 0 else 1
        
        # ==================== 计算回本价差 ====================
        # 回本价差 = 至少需要多少价差才能覆盖手续费成本
        # 公式: break_even_spread = total_cost * avg_price / size
        # 
        # 为什么这样算？
        # 假设你有 $1000 仓位，价差是 $10/个，资产价格是 $100/个
        # 你能买 10 个，每个赚 $10，总盈利 = $100
        # 这 $100 要覆盖手续费 total_cost
        # 
        # 反推: 如果手续费是 $X，需要的价差 = $X / 10个 = $X * $100 / $1000
        break_even_spread_usd = total_cost * avg_price / size if size > 0 else 0
        
        # ==================== 资金费率回本计算 ====================
        # 资金费率 (Funding Rate) 是永续合约特有的机制
        # 每隔一段时间，多头和空头之间会有费用转移
        # 如果费率为正: 多头付钱给空头
        # 如果费率为负: 空头付钱给多头
        
        # 获取 HL 的小时费率
        hl_funding_rate = hl_contract.get('fundingRate', {})
        hl_funding = hl_funding_rate.get('rateHourly', 0) if hl_funding_rate else 0
        
        # 获取 OS 的费率
        # OS 对于 crypto 用 fundingRate，对于传统资产用 rolloverRate
        os_funding_rate = os_contract.get('fundingRate', {})
        os_rollover_rate = os_contract.get('rolloverRate', {})
        
        if os_funding_rate:
            # Crypto 资产
            os_funding = os_funding_rate.get('longPayHourly', 0) or 0
        elif os_rollover_rate:
            # 传统资产 (外汇、商品等)
            os_funding = os_rollover_rate.get('hourly', 0) or 0
        else:
            os_funding = 0
        
        # 计算费率差异 (取绝对值)
        funding_diff = abs(hl_funding - os_funding)
        
        # 每小时能从费率差异中赚多少钱
        # 公式: 仓位大小 × 费率差异(转为小数)
        funding_per_hour = size * (funding_diff / 100) if funding_diff > 0 else 0
        
        # 计算回本时间
        if funding_per_hour > 0:
            # 回本时间 = 总成本 / 每小时收益
            funding_hours = total_cost / funding_per_hour
            # 判断是否在可接受时间内回本
            funding_valid = funding_hours <= max_hours and funding_hours > 0
        else:
            # 没有费率差异，无法通过费率回本
            funding_hours = float('inf')  # 无穷大
            funding_valid = False
        
        # ==================== 计算价差收益 ====================
        # 如果当前价差能带来多少利润
        spread_profit = current_spread_usd * size / avg_price if avg_price > 0 else 0
        
        # ==================== 综合回本计算 ====================
        # 综合回本 = 用价差收益抵消一部分成本，剩余部分用费率回本
        remaining_cost = total_cost - spread_profit  # 剩余需要回本的成本
        
        if remaining_cost > 0 and funding_per_hour > 0:
            # 还需要额外时间通过费率回本
            combo_hours = remaining_cost / funding_per_hour
        elif remaining_cost <= 0:
            # 价差收益已经足够覆盖成本，不需要额外时间
            combo_hours = 0
        else:
            # 无法回本
            combo_hours = float('inf')
        
        combo_valid = combo_hours <= max_hours
        
        # ==================== 判断是否能回本 ====================
        spread_can_profit = current_spread_usd >= break_even_spread_usd
        any_can_profit = spread_can_profit or funding_valid or combo_valid
        
        # ==================== 返回结果 ====================
        return {
            'totalCost': round(total_cost, 4),                  # 总成本
            'breakEvenSpreadUSD': round(break_even_spread_usd, 6),  # 回本价差
            'currentSpreadUSD': round(current_spread_usd, 6),   # 当前价差
            'spreadCanProfit': spread_can_profit,               # 价差能否回本
            'fundingDiff': round(funding_diff, 6),              # 费率差异
            'fundingHours': round(funding_hours, 2) if funding_valid else None,  # 费率回本时间
            'fundingValid': funding_valid,                      # 费率回本是否可行
            'comboHours': round(combo_hours, 2) if combo_valid else None,  # 综合回本时间
            'comboValid': combo_valid,                          # 综合回本是否可行
            'anyCanProfit': any_can_profit                      # 任意方式能否回本
        }
    
    def calculate_arbitrage(
        self,
        hl_contract: Dict[str, Any],
        os_contract: Dict[str, Any],
        hl_fee: Dict[str, float],
        os_fee: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算套利成本和回本
        
        这个函数同时计算 Maker 和 Taker 两种订单类型的套利方案
        用户可以根据结果选择更优的方案
        
        Args:
            hl_contract (dict): Hyperliquid 合约数据
            os_contract (dict): Ostium 合约数据
            hl_fee (dict): Hyperliquid 费率，格式: {'t': Taker费率, 'm': Maker费率}
            os_fee (dict): Ostium 费率，格式取决于资产类型:
                          - 加密货币: {'t': Taker, 'm': Maker, 'oracle': 预言机费}
                          - 传统资产: {'rate': 固定费率, 'oracle': 预言机费}
        
        Returns:
            dict: 包含两种方案的套利分析:
                  {
                      'maker': {...},  # Maker 方案的分析结果
                      'taker': {...}   # Taker 方案的分析结果
                  }
        
        使用建议:
        - 如果你能挂单等待成交，看 maker 方案 (成本低)
        - 如果你需要立即成交，看 taker 方案 (更真实)
        """
        size = self.position_size
        
        # 获取预言机费 (默认 $0.10)
        oracle_fee = os_fee.get('oracle', 0.10)
        
        # ========== 方案1: Maker (挂单) 费率 ==========
        # Maker 费率通常更低，因为你在"提供流动性"
        
        # 确定 OS 的费率
        if 'rate' in os_fee:
            # 传统资产: 固定费率
            os_rate_maker = os_fee['rate']
        else:
            # 加密货币: 使用 Maker 费率
            os_rate_maker = os_fee.get('m', 0.03)
        
        # 计算成本
        # HL: 开仓 + 平仓，所以 × 2
        hl_cost_maker = size * (hl_fee['m'] / 100) * 2
        # OS: 传统资产只收开仓费 + 预言机费
        os_cost_maker = size * (os_rate_maker / 100) + oracle_fee
        
        # 调用单方案计算
        maker_result = self.calculate_single_arbitrage(
            hl_cost_maker, os_cost_maker, hl_contract, os_contract, 'maker'
        )
        
        # ========== 方案2: Taker (吃单) 费率 ==========
        # Taker 费率更高，但能立即成交
        
        if 'rate' in os_fee:
            # 传统资产: 费率不变
            os_rate_taker = os_fee['rate']
        else:
            # 加密货币: 使用 Taker 费率
            os_rate_taker = os_fee.get('t', 0.10)
        
        hl_cost_taker = size * (hl_fee['t'] / 100) * 2
        os_cost_taker = size * (os_rate_taker / 100) + oracle_fee
        
        taker_result = self.calculate_single_arbitrage(
            hl_cost_taker, os_cost_taker, hl_contract, os_contract, 'taker'
        )
        
        # 返回两种方案
        return {
            'maker': maker_result,
            'taker': taker_result
        }
