# -*- coding: utf-8 -*-
"""
====================================================================
套利模块初始化文件 (__init__.py)
====================================================================

这个文件的作用：
- Python 中，一个文件夹要被识别为"模块"，必须包含 __init__.py 文件
- 这个文件定义了从 arbitrage 模块可以导入哪些内容
- 其他代码可以直接写: from arbitrage import ArbitrageEngine

使用示例：
    # 导入整个模块
    from arbitrage import ArbitrageEngine, FeeCalculator
    
    # 创建套利引擎
    engine = ArbitrageEngine(vip_tier=0)
"""

# ==================== 从子模块导入配置 ====================
# 从 fee_config.py 导入费率表和配置常量
from .fee_config import (
    FEE_SCHEDULE,           # Hyperliquid 费率表 (VIP 0-6)
    OSTIUM_FEE_SCHEDULE,    # Ostium 费率表
    NAME_MAPPING,           # 资产名称映射 (Ostium -> Hyperliquid)
    ARBITRAGE_CONFIG,       # 套利计算参数 (仓位大小、回本时间等)
    REFERRAL_DISCOUNT       # Referral 折扣百分比
)

# ==================== 从子模块导入类 ====================
# 从各个 .py 文件导入核心类
from .fee_calculator import FeeCalculator           # 费率计算器
from .arbitrage_calculator import ArbitrageCalculator   # 套利计算器
from .arbitrage_engine import ArbitrageEngine       # 套利引擎（主入口）

# ==================== 定义公开接口 ====================
# __all__ 列表定义了当别人使用 "from arbitrage import *" 时会导入哪些内容
# 这是一种控制模块公开 API 的方式
__all__ = [
    # 配置常量
    'FEE_SCHEDULE',
    'OSTIUM_FEE_SCHEDULE', 
    'NAME_MAPPING',
    'ARBITRAGE_CONFIG',
    'REFERRAL_DISCOUNT',
    # 核心类
    'FeeCalculator',
    'ArbitrageCalculator',
    'ArbitrageEngine'
]
