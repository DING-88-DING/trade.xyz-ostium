# -*- coding: utf-8 -*-
"""
====================================================================
Ostium 交易客户端 (ostium_trader.py)
====================================================================

功能:
1. 下市价单 (永续合约)
2. 查询订单状态
3. 查询持仓信息

使用示例:
    from trading.ostium_trader import OstiumTrader
    
    trader = OstiumTrader(wallet_address, private_key, rpc_url)
    
    # 下市价单
    order = trader.place_market_order(
        asset='XAU',      # 黄金
        is_long=True,     # 做多
        margin=100,       # 保证金 $100
        leverage=10       # 10倍杠杆
    )
"""

from typing import Optional, Dict, Any

# 尝试导入 Ostium SDK (可选)
try:
    from ostium import Ostium
    OSTIUM_AVAILABLE = True
except ImportError:
    print('[OstiumTrader] ⚠️ ostium-python-sdk 未安装')
    print('[OstiumTrader] 请运行: pip install ostium-python-sdk')
    OSTIUM_AVAILABLE = False
    Ostium = None  # 避免后续代码报错


class OstiumTrader:
    """Ostium 交易客户端"""
    
    def __init__(self, wallet_address: str, private_key: str, rpc_url: str):
        """
        初始化交易客户端
        
        Args:
            wallet_address: 钱包地址
            private_key: 私钥 (用于签名交易)
            rpc_url: Arbitrum RPC URL
        """
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.rpc_url = rpc_url
        
        # 检查 SDK 是否可用
        if not OSTIUM_AVAILABLE:
            print('[OstiumTrader] ❌ Ostium SDK 不可用,请先安装')
            self.ostium = None
            return
        
        # 初始化 Ostium SDK
        try:
            self.ostium = Ostium(rpc_url, private_key)
            print('[OstiumTrader] ✅ Ostium 交易客户端初始化成功')
        except Exception as e:
            print(f'[OstiumTrader] ❌ 初始化失败: {e}')
            raise
    
    def place_market_order(
        self,
        asset: str,
        is_long: bool,
        margin: float,
        leverage: int,
        current_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        下市价单
        
        Args:
            asset: 资产名称 (如 'XAU'=黄金, 'HG'=铜, 'NDX'=纳指)
            is_long: True=做多, False=做空
            margin: 保证金金额 (USDC)
            leverage: 杠杆倍数
            current_price: 当前价格 (用于计算滑点,如果不提供会自动获取)
        
        Returns:
            订单信息字典,失败返回 None
            格式: {
                'order_id': '...',
                'asset': 'XAU',
                'side': 'long/short',
                'margin': 100,
                'leverage': 10,
                'position_value': 1000
            }
        """
        try:
            # 1. 获取当前价格 (如果未提供)
            if current_price is None:
                # 通过 Ostium SDK 获取价格
                market_data = self.ostium.get_market_data(asset)
                current_price = market_data.get('indexPrice')
                if not current_price:
                    print(f'[OstiumTrader] ❌ 无法获取 {asset} 的当前价格')
                    return None
            
            # 2. 计算持仓价值
            position_value = margin * leverage
            
            # 3. 计算可接受价格 (滑点控制 0.5%)
            if is_long:
                # 做多: 可接受的最高买入价
                acceptable_price = current_price * 1.005
            else:
                # 做空: 可接受的最低卖出价
                acceptable_price = current_price * 0.995
            
            print(f'[OstiumTrader] 准备下单: {asset} {"做多" if is_long else "做空"} '
                  f'保证金${margin}, 杠杆{leverage}x, 持仓${position_value}')
            
            # 4. 构建交易参数
            # USDC 作为抵押品 (Arbitrum 主网 USDC 地址)
            usdc_address = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
            
            # 调用 Ostium SDK 下单
            # 注意: 这里使用的是 ostium-python-sdk 的 increase_position 方法
            result = self.ostium.market.increase_position(
                market_id=asset,
                token_in=usdc_address,
                amount_in=margin,  # 保证金金额
                size_delta=position_value,  # 持仓价值变化
                is_long=is_long,
                acceptable_price=acceptable_price
            )
            
            if result and result.get('success'):
                order_info = {
                    'order_id': result.get('transaction_hash'),
                    'asset': asset,
                    'side': 'long' if is_long else 'short',
                    'margin': margin,
                    'leverage': leverage,
                    'position_value': position_value,
                    'acceptable_price': acceptable_price,
                    'timestamp': result.get('timestamp')
                }
                print(f'[OstiumTrader] ✅ 下单成功: {order_info}')
                return order_info
            else:
                print(f'[OstiumTrader] ❌ 下单失败: {result}')
                return None
        
        except Exception as e:
            print(f'[OstiumTrader] 下单异常: {e}')
            import traceback
            traceback.print_exc()
            return None
    
    def get_position(self, asset: str) -> Optional[Dict[str, Any]]:
        """
        查询某个资产的当前持仓
        
        Args:
            asset: 资产名称
        
        Returns:
            持仓信息,无持仓返回 None
        """
        try:
            positions = self.ostium.get_positions(self.wallet_address)
            
            for position in positions:
                if position.get('market_id') == asset:
                    return {
                        'asset': asset,
                        'size': float(position.get('size', 0)),
                        'is_long': position.get('is_long', True),
                        'entry_price': float(position.get('entry_price', 0)),
                        'unrealized_pnl': float(position.get('unrealized_pnl', 0)),
                        'leverage': float(position.get('leverage', 0))
                    }
            
            return None
        except Exception as e:
            print(f'[OstiumTrader] 查询持仓失败: {e}')
            return None
