# -*- coding: utf-8 -*-
"""
====================================================================
费率计算器模块 (fee_calculator.py)
====================================================================

这个文件的作用：
- 根据 VIP 等级和资产类型，计算实际的交易费率
- 封装了复杂的费率计算逻辑，让其他模块可以简单调用

主要功能：
1. get_hl_fee(): 获取 Hyperliquid 的费率
2. get_os_fee(): 获取 Ostium 的费率
3. calculate_hl_cost(): 计算 Hyperliquid 交易成本
4. calculate_os_cost(): 计算 Ostium 交易成本

什么是类 (class)？
- 类是一种将数据和函数组合在一起的方式
- 可以把它想象成一个"模板"，创建的每个实例都是基于这个模板
- 例如: FeeCalculator 类可以创建多个实例，每个实例可以有不同的 VIP 等级

什么是 self？
- self 代表类的当前实例
- 通过 self.xxx 可以访问实例的属性和方法
- 例如: self.vip_tier 表示"这个实例的 VIP 等级"
"""

# ==================== 导入依赖 ====================
# 从同目录下的 fee_config.py 导入配置
# 注意: 这里用 . 开头，表示"相对导入"，即从当前模块目录导入
from .fee_config import (
    FEE_SCHEDULE,           # Hyperliquid 费率表
    OSTIUM_FEE_SCHEDULE,    # Ostium 费率表
    REFERRAL_DISCOUNT,      # Referral 折扣
    HIP3_ASSETS,            # HIP-3 资产列表
    HIP3_STANDARD_ASSETS    # 使用标准费率的 HIP-3 资产
)


class FeeCalculator:
    """
    费率计算器类
    
    使用示例:
        # 创建一个 VIP 0 等级的计算器
        calc = FeeCalculator(vip_tier=0)
        
        # 获取 BTC 的费率
        btc_fee = calc.get_hl_fee('BTC')
        print(btc_fee)  # {'t': 0.0432, 'm': 0.0144}  (已应用 4% Referral 折扣)
        
        # 获取 GOLD 的费率 (HIP-3 资产)
        gold_fee = calc.get_hl_fee('GOLD', dex='xyz')
        print(gold_fee)  # {'t': 0.0864, 'm': 0.0288}  (hip3_standard 费率)
        
        # 计算交易成本
        cost = calc.calculate_hl_cost(size=1000, coin='BTC', order_type='maker')
        print(cost)  # 0.288 (美元)
    """
    
    def __init__(self, vip_tier: int = 0, referral_discount: float = REFERRAL_DISCOUNT):
        """
        初始化费率计算器 (构造函数)
        
        什么是 __init__？
        - 这是 Python 类的"构造函数"，在创建实例时自动调用
        - 用于初始化实例的属性
        
        Args:
            vip_tier (int): VIP 等级，范围 0-6，默认为 0
            referral_discount (float): Referral 折扣百分比，范围 0-100，默认为 4
        
        示例:
            calc = FeeCalculator(vip_tier=3, referral_discount=5)
        """
        # min() 和 max() 用于限制数值范围
        # min(max(vip_tier, 0), 6) 的含义:
        #   1. max(vip_tier, 0): 确保不小于 0
        #   2. min(..., 6): 确保不大于 6
        # 这样就把 vip_tier 限制在 0-6 的范围内
        self.vip_tier = min(max(vip_tier, 0), 6)
        
        # 保存 Referral 折扣
        self.referral_discount = referral_discount
    
    def set_vip_tier(self, tier: int):
        """
        更新 VIP 等级
        
        这个方法允许在不创建新实例的情况下更改 VIP 等级
        
        Args:
            tier (int): 新的 VIP 等级 (0-6)
        
        示例:
            calc.set_vip_tier(3)  # 将 VIP 等级改为 3
        """
        self.vip_tier = min(max(tier, 0), 6)
    
    def get_hl_fee(self, coin: str, dex: str = 'main') -> dict:
        """
        获取 Hyperliquid 费率
        
        这个方法会根据币种类型自动判断应该使用哪个费率表
        
        Args:
            coin (str): 币种名称，例如 'BTC', 'ETH', 'GOLD'
                       可能带有前缀，例如 'xyz:GOLD'
            dex (str): DEX 类型
                      'main' = 主站，交易加密货币
                      'xyz' = HIP-3 站，交易外汇/商品
        
        Returns:
            dict: 费率字典，包含两个键：
                  't' = Taker 费率 (百分比)
                  'm' = Maker 费率 (百分比)
        
        示例:
            fee = calc.get_hl_fee('BTC')
            print(fee)  # {'t': 0.0432, 'm': 0.0144}
            
            fee = calc.get_hl_fee('xyz:GOLD', dex='xyz')
            print(fee)  # {'t': 0.0864, 'm': 0.0288}
        """
        # ---- 步骤1: 判断是否为 xyz dex 资产 ----
        # 有两种判断方式:
        # 1. dex 参数明确指定为 'xyz'
        # 2. coin 名称以 'xyz:' 开头 (例如 'xyz:GOLD')
        is_xyz = dex == 'xyz' or coin.startswith('xyz:')
        
        # ---- 步骤2: 提取纯币种名 ----
        # 如果币种名包含冒号，取冒号后面的部分
        # 例如: 'xyz:GOLD' -> 'GOLD'
        # split(':') 将字符串按冒号分割成列表
        # [-1] 取列表的最后一个元素
        pure_coin = coin.split(':')[-1] if ':' in coin else coin
        
        # ---- 步骤3: 确定费率类型 ----
        if is_xyz or pure_coin in HIP3_ASSETS:
            # 这是 HIP-3 资产，需要判断用哪个费率表
            if pure_coin in HIP3_STANDARD_ASSETS:
                # GOLD 使用 hip3_standard (无折扣，费率高)
                fee_type = 'hip3_standard'
            else:
                # 其他 HIP-3 资产使用 hip3_growth (有折扣，费率低)
                fee_type = 'hip3_growth'
        else:
            # 普通加密货币，使用 perps_base 费率表
            fee_type = 'perps_base'
        
        # ---- 步骤4: 获取基础费率 ----
        # FEE_SCHEDULE[fee_type] 获取对应的费率表
        # [self.vip_tier] 获取对应 VIP 等级的费率
        # .copy() 创建一个副本，避免修改原始数据
        base_fee = FEE_SCHEDULE[fee_type][self.vip_tier].copy()
        
        # ---- 步骤5: 应用 Referral 折扣 ----
        # 计算折扣乘数: 如果折扣是 4%，乘数就是 0.96 (即 96%)
        discount_multiplier = 1 - (self.referral_discount / 100)
        
        # 对 Taker 和 Maker 费率都应用折扣
        base_fee['t'] = base_fee['t'] * discount_multiplier
        base_fee['m'] = base_fee['m'] * discount_multiplier
        
        return base_fee
    
    def get_os_fee(self, asset: str, group: str) -> dict:
        """
        获取 Ostium 费率
        
        Ostium 的费率比 Hyperliquid 简单:
        - 加密货币: 有 Maker/Taker 区分
        - 传统资产: 只有一个固定费率
        
        Args:
            asset (str): 资产名称，例如 'BTC', 'XAU' (黄金), 'EUR' (欧元)
            group (str): 资产组别，用于确定费率类型
                        'crypto' = 加密货币
                        'forex' = 外汇
                        'commodities' = 大宗商品
                        'stocks' = 股票
                        'indices' = 股票指数
        
        Returns:
            dict: 费率字典，格式取决于资产类型:
                  加密货币: {'t': Taker费率, 'm': Maker费率, 'oracle': 预言机费}
                  传统资产: {'rate': 固定费率, 'oracle': 预言机费}
        
        示例:
            # 加密货币
            fee = calc.get_os_fee('BTC', 'crypto')
            print(fee)  # {'t': 0.10, 'm': 0.03, 'oracle': 0.10}
            
            # 黄金 (传统资产)
            fee = calc.get_os_fee('XAU', 'commodities')
            print(fee)  # {'rate': 0.03, 'oracle': 0.10}
        """
        # 获取预言机费 (每次开仓都要付的固定费用)
        oracle_fee = OSTIUM_FEE_SCHEDULE['other']['oracle_fee']
        
        if group == 'crypto':
            # ---- 加密货币费率 ----
            # 使用 Maker/Taker 模型
            crypto_fee = OSTIUM_FEE_SCHEDULE['crypto']
            return {
                't': crypto_fee['t'],       # Taker 费率: 0.10%
                'm': crypto_fee['m'],       # Maker 费率: 0.03%
                'oracle': oracle_fee        # 预言机费: $0.10
            }
        else:
            # ---- 传统资产费率 ----
            # 使用固定费率，无 Maker/Taker 区分
            traditional = OSTIUM_FEE_SCHEDULE['traditional']
            
            # 查找费率的优先级:
            # 1. 先查特定资产 (如 'XAU', 'XAG')
            # 2. 再查资产组别 (如 'forex', 'indices')
            # 3. 都找不到就用 forex 的默认费率
            if asset in traditional:
                # 找到了特定资产的费率
                rate = traditional[asset]
            elif group in traditional:
                # 找到了资产组别的费率
                rate = traditional[group]
            else:
                # 使用默认费率
                rate = traditional.get('forex', 0.03)
            
            return {
                'rate': rate,           # 固定费率
                'oracle': oracle_fee    # 预言机费: $0.10
            }
    
    def calculate_hl_cost(self, size: float, coin: str, dex: str = 'main', 
                          order_type: str = 'maker') -> float:
        """
        计算 Hyperliquid 交易成本
        
        计算公式:
            成本 = 仓位大小 × 费率 × 2
            
        为什么乘以 2？
        因为一次完整的套利需要开仓和平仓两次操作，每次都要付手续费
        
        Args:
            size (float): 仓位大小 (美元)，例如 1000 表示 $1000
            coin (str): 币种名称
            dex (str): DEX 类型 ('main' 或 'xyz')
            order_type (str): 订单类型
                             'maker' = 挂单 (费率低)
                             'taker' = 吃单 (费率高)
        
        Returns:
            float: 交易成本 (美元)
        
        示例:
            # 计算用 $1000 交易 BTC，使用 Maker 订单的成本
            cost = calc.calculate_hl_cost(size=1000, coin='BTC', order_type='maker')
            print(cost)  # 0.288 (表示 $0.288)
            
            # 计算用 $5000 交易 GOLD，使用 Taker 订单的成本
            cost = calc.calculate_hl_cost(size=5000, coin='GOLD', dex='xyz', order_type='taker')
            print(cost)  # 8.64 (表示 $8.64)
        """
        # 获取费率
        fee = self.get_hl_fee(coin, dex)
        
        # 根据订单类型选择费率
        fee_rate = fee['m'] if order_type == 'maker' else fee['t']
        
        # 计算成本
        # size * (fee_rate / 100) = 单次交易成本
        # * 2 = 开仓 + 平仓总成本
        return size * (fee_rate / 100) * 2
    
    def calculate_os_cost(self, size: float, asset: str, group: str,
                          order_type: str = 'maker') -> float:
        """
        计算 Ostium 交易成本
        
        注意: Ostium 的成本计算比 Hyperliquid 复杂一点
        - 传统资产: 只收开仓费，不收平仓费
        - 加密货币: 需要区分 Maker/Taker
        - 额外: 还要加上预言机费 ($0.10)
        
        Args:
            size (float): 仓位大小 (美元)
            asset (str): 资产名称
            group (str): 资产组别
            order_type (str): 订单类型 ('maker' 或 'taker')
        
        Returns:
            float: 交易成本 (美元)
        
        示例:
            # 传统资产 (黄金)
            cost = calc.calculate_os_cost(size=1000, asset='XAU', group='commodities')
            print(cost)  # 0.40 (0.03% × 1000 + $0.10 = $0.30 + $0.10)
            
            # 加密货币 (BTC)
            cost = calc.calculate_os_cost(size=1000, asset='BTC', group='crypto', order_type='taker')
            print(cost)  # 1.10 (0.10% × 1000 + $0.10 = $1.00 + $0.10)
        """
        # 获取费率信息
        fee = self.get_os_fee(asset, group)
        
        if 'rate' in fee:
            # ---- 传统资产 ----
            # 使用固定费率，只收开仓费
            cost = size * (fee['rate'] / 100)
        else:
            # ---- 加密货币 ----
            # 根据订单类型选择 Maker 或 Taker 费率
            fee_rate = fee['m'] if order_type == 'maker' else fee['t']
            cost = size * (fee_rate / 100)
        
        # 加上预言机费 (这是固定费用，与仓位大小无关)
        cost += fee['oracle']
        
        return cost
