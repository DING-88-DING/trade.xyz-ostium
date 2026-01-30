# -*- coding: utf-8 -*-
"""
====================================================================
交易执行协调器 (trade_executor.py)
====================================================================

功能:
1. 协调 Hyperliquid 和 Ostium 两个交易所的下单
2. 管理冷却时间,防止重复下单
3. 验证余额
4. 记录交易历史
5. 发送通知

执行流程:
    检查开关 → 检查冷却 → 获取杠杆 → 验证余额 →
    HL下单 → OS下单 → 记录 → 通知 → 更新冷却
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime

# 导入配置
try:
    from config import (
        AUTO_TRADING_ENABLED,
        HYPERLIQUID_WALLET_ADDRESS,
        HYPERLIQUID_PRIVATE_KEY,
        OSTIUM_WALLET_ADDRESS,
        OSTIUM_PRIVATE_KEY,
        ARBITRUM_RPC_URL,
        TRADING_CONFIG
    )
except ImportError:
    print('[TradeExecutor] ⚠️  无法导入配置,请检查 config.py')
    AUTO_TRADING_ENABLED = False
    TRADING_CONFIG = {}

# 导入交易客户端
from .hl_trader import HyperliquidTrader
from .ostium_trader import OstiumTrader
from .trade_recorder import TradeRecorder

# 导入通知器
try:
    from arbitrage.notifier import get_notifier
except ImportError:
    print('[TradeExecutor] ⚠️  无法导入通知器')
    get_notifier = None


class TradeExecutor:
    """交易执行协调器"""
    
    def __init__(self):
        """初始化交易执行器"""
        self.enabled = AUTO_TRADING_ENABLED
        self.config = TRADING_CONFIG
        
        # 冷却时间记录 {'GOLD': timestamp, ...}
        self.last_trade_time: Dict[str, float] = {}
        
        # 初始化交易客户端
        if self.enabled:
            try:
                self.hl_trader = HyperliquidTrader(
                    HYPERLIQUID_WALLET_ADDRESS,
                    HYPERLIQUID_PRIVATE_KEY
                )
                self.os_trader = OstiumTrader(
                    OSTIUM_WALLET_ADDRESS,
                    OSTIUM_PRIVATE_KEY,
                    ARBITRUM_RPC_URL
                )
                print('[TradeExecutor] ✅ 交易执行器初始化成功')
            except Exception as e:
                print(f'[TradeExecutor] ❌ 初始化失败: {e}')
                self.enabled = False
        else:
            self.hl_trader = None
            self.os_trader = None
            print('[TradeExecutor] ⚠️  自动交易未启用')
        
        # 初始化交易记录器
        self.recorder = TradeRecorder()
        
        # 初始化通知器
        if get_notifier:
            self.notifier = get_notifier()
        else:
            self.notifier = None
    
    def check_cooldown(self, asset: str) -> bool:
        """
        检查冷却时间
        
        Args:
            asset: 资产名称
        
        Returns:
            True=可以交易, False=冷却中
        """
        cooldown = self.config.get('trade_cooldown', 300)
        last_time = self.last_trade_time.get(asset, 0)
        now = time.time()
        
        if now - last_time < cooldown:
            remaining = int(cooldown - (now - last_time))
            print(f'[TradeExecutor] ⏰ {asset} 冷却中,剩余 {remaining} 秒')
            return False
        
        return True
    
    def update_cooldown(self, asset: str):
        """更新冷却时间"""
        self.last_trade_time[asset] = time.time()
    
    def check_daily_limit(self, asset: str) -> bool:
        """
        检查每日交易次数限制
        
        Args:
            asset: 资产名称
        
        Returns:
            True=未超限, False=已超限
        """
        max_daily_trades = self.config.get('max_daily_trades', 20)
        today_count = self.recorder.get_today_trade_count(asset)
        
        if today_count >= max_daily_trades:
            print(f'[TradeExecutor] 🚫 {asset} 今日交易次数已达上限 ({today_count}/{max_daily_trades})')
            return False
        
        return True
    
    def execute_arbitrage_trade(self, pair_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行套利交易
        
        Args:
            pair_data: 套利机会数据,来自 arbitrage_engine,包含:
                - name: 资产显示名称
                - hl: Hyperliquid 合约信息
                - os: Ostium 合约信息
                - arbitrage: 套利分析结果 (包含 autoTradingSignal)
        
        Returns:
            执行结果字典:
                {
                    'success': bool,
                    'hl_order_id': str,
                    'os_order_id': str,
                    'error': str,
                    'leverage': int,
                    'position_value': float
                }
        """
        # ========== 1. 前置检查 ==========
        if not self.enabled:
            return {'success': False, 'error': '自动交易未启用'}
        
        # 模拟模式检查
        simulation_mode = self.config.get('simulation_mode', True)
        
        # 提取数据
        asset_name = pair_data.get('name', '')
        hl_contract = pair_data.get('hl', {})
        os_contract = pair_data.get('os', {})
        arb_data = pair_data.get('arbitrage', {})
        
        # ========== 2. 检查冷却时间 ==========
        if not self.check_cooldown(asset_name):
            return {'success': False, 'error': '冷却中'}
        
        # ==========3. 检查每日交易次数 ==========
        if not self.check_daily_limit(asset_name):
            return {'success': False, 'error': '超出每日交易次数限制'}
        
        # ========== 4. 获取价格和交易方向 ==========
        hl_mid = hl_contract.get('mid', 0)
        os_mid = os_contract.get('mid', 0)
        hl_coin = hl_contract.get('coin', '')
        os_asset = os_contract.get('asset', '')
        
        if not hl_mid or not os_mid:
            return {'success': False, 'error': '无法获取价格'}
        
        # 判断交易方向
        # HL价格 < OS价格: HL做多 + OS做空
        # HL价格 > OS价格: HL做空 + OS做多
        is_hl_long = hl_mid < os_mid
        direction = 'HL_LONG_OS_SHORT' if is_hl_long else 'HL_SHORT_OS_LONG'
        
        # ========== 5. 获取 Hyperliquid 最大杠杆 ==========
        max_leverage = self.hl_trader.get_max_leverage(hl_coin)
        if not max_leverage:
            return {'success': False, 'error': '无法获取最大杠杆'}
        
        # 应用杠杆乘数
        leverage_multiplier = self.config.get('leverage_multiplier', 1.0)
        leverage = int(max_leverage * leverage_multiplier)
        
        # ========== 6. 计算持仓价值 ==========
        margin = self.config.get('margin_size', 100)
        position_value = margin * leverage
        
        print(f'\n{"="*60}')
        print(f'[TradeExecutor] 🎯 准备执行套利交易')
        print(f'{"="*60}')
        print(f'资产: {asset_name}')
        print(f'方向: {direction}')
        print(f'保证金: ${margin}')
        print(f'杠杆: {leverage}x (最大{max_leverage}x × {leverage_multiplier})')
        print(f'持仓价值: ${position_value}')
        print(f'HL价格: ${hl_mid:.4f}')
        print(f'OS价格: ${os_mid:.4f}')
        print(f'价差: ${abs(hl_mid - os_mid):.4f}')
        print(f'模拟模式: {"是" if simulation_mode else "否"}')
        print(f'{"="*60}\n')
        
        # ========== 模拟模式: 只打印不下单 ==========
        if simulation_mode:
            print('[TradeExecutor] 🧪 模拟模式: 跳过实际下单')
            
            # 记录模拟交易
            trade_record = {
                'simulation': True,
                'asset': asset_name,
                'direction': direction,
                'margin': margin,
                'leverage': leverage,
                'position_value': position_value,
                'hl_price': hl_mid,
                'os_price': os_mid,
                'spread': abs(hl_mid - os_mid),
                'estimated_profit': arb_data.get('taker', {}).get('profitableSpread', 0) * margin * leverage / hl_mid
            }
            self.recorder.save_trade(trade_record)
            
            # 更新冷却时间
            self.update_cooldown(asset_name)
            
            return {
                'success': True,
                'simulation': True,
                'message': '模拟交易记录成功'
            }
        
        # ========== 7. 第一腿: Hyperliquid 市价单 ==========
        print(f'[TradeExecutor] 📤 第一腿: Hyperliquid {"买入" if is_hl_long else "卖出"} {hl_coin}')
        
        hl_order = self.hl_trader.place_market_order(
            coin=hl_coin,
            is_buy=is_hl_long,
            margin=margin,
            leverage=leverage,
            current_price=hl_mid
        )
        
        if not hl_order:
            print('[TradeExecutor] ❌ Hyperliquid 下单失败')
            return {'success': False, 'error': 'HL 下单失败'}
        
        print(f'[TradeExecutor] ✅ Hyperliquid 订单成功: {hl_order.get("order_id")}')
        
        # ========== 8. 第二腿: Ostium 市价单 ==========
        print(f'[TradeExecutor] 📤 第二腿: Ostium {"做多" if not is_hl_long else "做空"} {os_asset}')
        
        os_order = self.os_trader.place_market_order(
            asset=os_asset,
            is_long=not is_hl_long,  # 与HL相反
            margin=margin,
            leverage=leverage,
            current_price=os_mid
        )
        
        if not os_order:
            # 🚨 紧急情况: HL已成交但OS失败
            error_msg = f'🚨 紧急: {asset_name} HL已成交但OS失败,存在单边风险!'
            print(f'[TradeExecutor] {error_msg}')
            
            # 发送紧急通知
            if self.notifier:
                self.notifier.send_notification(
                    title='⚠️ 套利交易异常',
                    message=error_msg
                )
            
            return {'success': False, 'error': 'OS 下单失败, HL 已成交!', 'hl_order': hl_order}
        
        print(f'[TradeExecutor] ✅ Ostium 订单成功: {os_order.get("order_id")}')
        
        # ========== 9. 记录交易 ==========
        trade_record = {
            'asset': asset_name,
            'direction': direction,
            'margin': margin,
            'leverage': leverage,
            'position_value': position_value,
            'hl_order': hl_order,
            'os_order': os_order,
            'hl_price': hl_mid,
            'os_price': os_mid,
            'spread': abs(hl_mid - os_mid),
            'estimated_profit': arb_data.get('taker', {}).get('profitableSpread', 0) * margin * leverage / hl_mid,
            'total_cost': arb_data.get('taker', {}).get('totalCost', 0)
        }
        
        self.recorder.save_trade(trade_record)
        
        # ========== 10. 发送通知 ==========
        if self.notifier:
            title = f'💰 {asset_name} 套利交易成功!'
            message = (
                f'{direction}\n'
                f'保证金: ${margin}, 杠杆: {leverage}x\n'
                f'持仓: ${position_value}\n'
                f'价差: ${trade_record["spread"]:.4f}\n'
                f'预计盈利: ${trade_record["estimated_profit"]:.2f}'
            )
            self.notifier.send_notification(title, message)
        
        # ========== 11. 更新冷却时间 ==========
        self.update_cooldown(asset_name)
        
        print(f'\n[TradeExecutor] ✅ 套利交易完成!\n')
        
        return {
            'success': True,
            'hl_order_id': hl_order.get('order_id'),
            'os_order_id': os_order.get('order_id'),
            'leverage': leverage,
            'position_value': position_value
        }
