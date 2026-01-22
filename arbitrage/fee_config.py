# -*- coding: utf-8 -*-
"""
====================================================================
费率配置模块 (fee_config.py)
====================================================================

这个文件的作用：
- 存储所有费率相关的配置数据
- 从前端 js/config.js 迁移过来的配置
- 作为"数据源"被其他模块引用

包含的配置：
1. Hyperliquid VIP 0-6 费率表 (FEE_SCHEDULE)
2. Ostium 费率表 (OSTIUM_FEE_SCHEDULE)
3. 资产名称映射 (NAME_MAPPING)
4. 套利计算参数 (ARBITRAGE_CONFIG)

什么是 bps (基点)？
- 1 bps = 0.01% = 0.0001
- 例如: 3 bps = 0.03% = 0.0003

什么是 Maker/Taker 费率？
- Maker (挂单): 你挂一个订单等待成交，提供流动性，费率较低
- Taker (吃单): 你直接吃掉别人的挂单，消耗流动性，费率较高
"""

# ============ 用户可调整的配置 ============

# Referral 折扣 (推荐人返佣)
# 如果你有推荐码，可以获得一定比例的手续费折扣
# 范围: 0-100，默认 4 表示 4% 的折扣
REFERRAL_DISCOUNT = 4


# ============ Hyperliquid 费率表 ============
# 数据来源: Hyperliquid 交易界面的 Fee Schedule 页面
# 
# 费率单位: 百分比 (例如 0.045 表示 0.045%)
# 't' = Taker 费率 (吃单)
# 'm' = Maker 费率 (挂单)
#
# VIP 等级说明:
#   VIP 0: 30天交易量 < $5M (500万美元)
#   VIP 1: 30天交易量 >= $5M
#   VIP 2: 30天交易量 >= $25M (2500万美元)
#   VIP 3: 30天交易量 >= $100M (1亿美元)
#   VIP 4: 30天交易量 >= $500M (5亿美元)
#   VIP 5: 30天交易量 >= $2B (20亿美元)
#   VIP 6: 30天交易量 >= $7B (70亿美元)

FEE_SCHEDULE = {
    # -------- 主流加密货币永续合约 (Perps Base) --------
    # 适用于: BTC, ETH, SOL, ARB 等主流加密货币
    # 这是最常见的费率类别
    'perps_base': {
        # VIP等级: {'t': Taker费率, 'm': Maker费率}
        0: {'t': 0.045, 'm': 0.015},    # VIP 0: Taker 0.045%, Maker 0.015%
        1: {'t': 0.04, 'm': 0.012},     # VIP 1: Taker 0.04%, Maker 0.012%
        2: {'t': 0.035, 'm': 0.008},    # VIP 2: 费率更低
        3: {'t': 0.03, 'm': 0.004},     # VIP 3: 费率更低
        4: {'t': 0.028, 'm': 0.0},      # VIP 4+: Maker 免费!
        5: {'t': 0.026, 'm': 0.0},      # VIP 5: Taker 继续降低
        6: {'t': 0.024, 'm': 0.0},      # VIP 6: 最低费率
    },
    
    # -------- HIP-3 Growth Mode (高折扣模式) --------
    # HIP-3 是 Hyperliquid 的新资产上线计划
    # Growth Mode 给予 90%+ 的费率折扣来吸引交易量
    # 适用于: 外汇 (EUR, GBP, JPY), 白银 (SILVER), 铜 (COPPER), 纳指 (XYZ100) 等
    # 注意: 黄金 (GOLD) 不在此类别！
    'hip3_growth': {
        0: {'t': 0.009, 'm': 0.003},    # 比 perps_base 便宜 80%!
        1: {'t': 0.008, 'm': 0.0024},
        2: {'t': 0.007, 'm': 0.0016},
        3: {'t': 0.006, 'm': 0.0008},
        4: {'t': 0.0056, 'm': 0.0},
        5: {'t': 0.0052, 'm': 0.0},
        6: {'t': 0.0048, 'm': 0.0},
    },
    
    # -------- HIP-3 Standard (标准模式，无折扣) --------
    # 适用于: GOLD (黄金)
    # 为什么黄金不享受 Growth Mode 折扣？
    # 因为 Hyperliquid 上已经有 PAXG-USDC 现货交易对跟踪金价，
    # 所以 GOLD 永续合约不需要额外的激励来建立流动性
    # 费率是 perps_base 的 2 倍！
    'hip3_standard': {
        0: {'t': 0.090, 'm': 0.030},    # 比 perps_base 贵 2 倍
        1: {'t': 0.080, 'm': 0.024},
        2: {'t': 0.070, 'm': 0.016},
        3: {'t': 0.060, 'm': 0.008},
        4: {'t': 0.056, 'm': 0.0},
        5: {'t': 0.052, 'm': 0.0},
        6: {'t': 0.048, 'm': 0.0},
    },
}


# ============ Ostium 费率表 ============
# 数据来源: https://ostium-labs.gitbook.io/ostium-docs/trading/fees
# 
# Ostium 的费率结构比 Hyperliquid 简单：
# - 加密货币: 使用 Maker/Taker 模型
# - 传统资产 (外汇、商品): 使用固定开仓费，无 Maker/Taker 区分
#
# 费率单位: 百分比 (与 Hyperliquid 统一)

OSTIUM_FEE_SCHEDULE = {
    # -------- 传统资产费率 (固定费率) --------
    # 这些资产只在开仓时收费，平仓免费
    # 无 Maker/Taker 区分，费率固定
    'traditional': {
        # 外汇 (Forex) - 货币对
        'forex': 0.03,      # 3 bps = 0.03% (例如 EUR/USD, GBP/USD)
        
        # 股票指数 (Indices)
        'indices': 0.05,    # 5 bps = 0.05% (例如 S&P500, 纳斯达克)
        
        # 股票 (Stocks)
        'stocks': 0.05,     # 5 bps = 0.05%
        
        # 贵金属 (Precious Metals) - 每种金属费率不同
        'XAU': 0.03,        # 黄金 (Gold): 3 bps - 最低费率
        'XAG': 0.15,        # 白银 (Silver): 15 bps
        'XPT': 0.20,        # 铂金 (Platinum): 20 bps
        'XPD': 0.20,        # 钯金 (Palladium): 20 bps
        'HG': 0.15,         # 铜 (Copper): 15 bps
        
        # 能源 (Energy)
        'CL': 0.10,         # 原油 (Crude Oil): 10 bps
    },
    
    # -------- 加密货币费率 (Maker/Taker 模型) --------
    # 加密货币的费率取决于两个因素:
    # 1. 杠杆倍数: <= 20x 用 Maker, > 20x 用 Taker
    # 2. OI 平衡: 减少 OI 不平衡用 Maker, 增加 OI 不平衡用 Taker
    'crypto': {
        'm': 0.03,      # Maker: 3 bps (杠杆 ≤ 20x 且 减少OI不平衡)
        't': 0.10,      # Taker: 10 bps (杠杆 > 20x 或 增加OI不平衡)
    },
    
    # -------- 其他固定费用 --------
    # 这些是与费率无关的固定金额费用
    'other': {
        'oracle_fee': 0.10,     # 预言机费: $0.10 (每次开仓时收取，用于支付价格数据)
        'close_fee': 0,         # 平仓费: $0 (通常免费)
        # 注意: SL/TP 自动触发时不收取预言机费
    }
}


# ============ 资产名称映射 ============
# 不同交易所对同一资产有不同的命名
# 这个映射表用于将 Ostium 的资产名转换为 Hyperliquid 的资产名
# 格式: 'Ostium名称': 'Hyperliquid名称'
#
# 例如: 黄金在 Ostium 叫 "XAU"，在 Hyperliquid 叫 "GOLD"
NAME_MAPPING = {
    'XAU': 'GOLD',      # 黄金: Ostium 用国际代码 XAU, HL 用英文 GOLD
    'XAG': 'SILVER',    # 白银: Ostium 用国际代码 XAG, HL 用英文 SILVER
    'HG': 'COPPER',     # 铜: Ostium 用期货代码 HG, HL 用英文 COPPER
    'NDX': 'XYZ100',    # 纳斯达克100: Ostium 用 NDX, HL 用 XYZ100
}

# 反向映射 (Hyperliquid -> Ostium)
# 使用 Python 字典推导式自动生成反向映射
# 例如: {'GOLD': 'XAU', 'SILVER': 'XAG', ...}
REVERSE_NAME_MAPPING = {v: k for k, v in NAME_MAPPING.items()}


# ============ 优先显示资产 ============
# 在前端 UI 中，这些资产会排在列表最前面
# 因为它们是跨平台套利最有价值的资产
PRIORITY_ASSETS = [
    # Hyperliquid 资产名
    'GOLD', 'SILVER', 'COPPER', 'XYZ100',
    # Ostium 资产名 (有些可能重复，但不影响)
    'XAU', 'XAG', 'HG', 'NDX'
]


# ============ 套利计算设置 ============
# 这些参数用于计算套利收益和回本时间
ARBITRAGE_CONFIG = {
    # 下单金额 (USD)
    # 假设每次交易使用多少资金
    # 这个值用于计算手续费成本和预期收益
    'position_size': 1000,      # 默认 $1000
    
    # 资金费率回本最大时间 (小时)
    # 如果通过资金费率差异回本需要超过这个时间，则认为不值得
    # 因为费率可能会变化，时间太长风险太大
    'max_funding_hours': 12,    # 默认 12 小时
    
    # 监控的资产列表（HL 名称）
    # 当这些资产出现套利机会时会发送通知
    'monitored_assets': ['GOLD', 'SILVER', 'COPPER', 'XYZ100'],
    
    # 通知冷却时间（秒）
    # 同一资产在此时间内不会重复发送通知
    'notification_cooldown': 60,
    
    # 预期收敛价差 (Expected Spread)
    # 不同资产对的价差通常不会收敛到0，而是收敛到一个常见值
    # 计算套利时会将这个值作为"目标价差"
    # 格式: {'资产名(HL名)': 预期价差(USD)}
    'expected_spread': {
        'GOLD': 0,       # 黄金: 通常收敛到 $0
        'SILVER': 0,     # 白银: 通常收敛到 $0
        'COPPER': 0.002, # 铜: 通常收敛到 $0.002
        'XYZ100': 10,    # 纳指100: 通常收敛到 $10
    },
}


# ============ HIP-3 资产列表 ============
# 这些资产属于 Hyperliquid 的 HIP-3 (xyz dex)
# 费率计算时需要使用 hip3_growth 或 hip3_standard 费率表
HIP3_ASSETS = [
    # 贵金属
    'GOLD', 'SILVER', 'COPPER',
    # 外汇 (主要货币)
    'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF',
    # 股指
    'XYZ100',  # 纳斯达克100
]

# 这些资产使用 hip3_standard 费率 (无折扣)
# 目前只有 GOLD，其他 HIP-3 资产都使用 hip3_growth (有折扣)
HIP3_STANDARD_ASSETS = ['GOLD']
