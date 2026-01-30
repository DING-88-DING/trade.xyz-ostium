# -*- coding: utf-8 -*-
"""
====================================================================
Trading 模块
====================================================================

自动交易功能模块,负责在 Hyperliquid 和 Ostium 执行套利交易

模块结构:
- hl_trader.py: Hyperliquid 交易客户端
- ostium_trader.py: Ostium 交易客户端
- trade_executor.py: 交易执行协调器
- trade_recorder.py: 交易记录器
"""

from .hl_trader import HyperliquidTrader
from .ostium_trader import OstiumTrader
from .trade_executor import TradeExecutor
from .trade_recorder import TradeRecorder

__all__ = [
    'HyperliquidTrader',
    'OstiumTrader', 
    'TradeExecutor',
    'TradeRecorder'
]
