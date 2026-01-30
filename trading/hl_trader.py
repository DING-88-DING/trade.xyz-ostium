# -*- coding: utf-8 -*-
"""
====================================================================
Hyperliquid 交易客户端 (hl_trader.py)
====================================================================

功能:
1. 获取币种的最大杠杆
2. 下市价单 (使用 IOC 限价单模拟)
3. 查询订单状态
4. 查询持仓信息

使用示例:
    from trading.hl_trader import HyperliquidTrader
    
    trader = HyperliquidTrader(wallet_address, private_key)
    
    # 获取最大杠杆
    max_lev = trader.get_max_leverage('GOLD')
    print(f'GOLD 最大杠杆: {max_lev}x')
    
    # 下市价单
    order = trader.place_market_order(
        coin='GOLD',
        is_buy=True,
        margin=100,
        leverage=10
    )
"""

import requests
from typing import Optional, Dict, Any

# 尝试导入 Hyperliquid SDK (可选)
try:
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    print('[HLTrader] ⚠️ hyperliquid-python-sdk 未安装')
    print('[HLTrader] 请运行: pip install hyperliquid-python-sdk')
    HYPERLIQUID_AVAILABLE = False
    Exchange = None
    Info = None


class HyperliquidTrader:
    """Hyperliquid 交易客户端"""
    
    def __init__(self, wallet_address: str, private_key: str, base_url: str = "https://api.hyperliquid.xyz"):
        """
        初始化交易客户端
        
        Args:
            wallet_address: 钱包地址
            private_key: 私钥 (用于签名交易)
            base_url: API 基础 URL
        """
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.base_url = base_url
        
        # 检查 SDK 是否可用
        if not HYPERLIQUID_AVAILABLE:
            print('[HLTrader] ❌ Hyperliquid SDK 不可用,请先安装')
            self.exchange = None
            self.info = None
            return
        
        # 初始化 SDK
        try:
            self.exchange = Exchange(wallet_address, base_url, private_key=private_key)
            self.info = Info(base_url)
            print('[HLTrader] ✅ Hyperliquid 交易客户端初始化成功')
        except Exception as e:
            print(f'[HLTrader] ❌ 初始化失败: {e}')
            raise
    
    def get_max_leverage(self, coin: str) -> Optional[int]:
        """
        获取币种的最大杠杆倍数
        
        Args:
            coin: 币种名称 (如 'BTC', 'GOLD')
        
        Returns:
            最大杠杆倍数 (整数), 失败返回 None
        """
        try:
            # 获取 meta 信息
            meta = self.info.meta()
            
            # 查找币种
            for asset_info in meta.get('universe', []):
                if asset_info.get('name') == coin:
                    max_lev = asset_info.get('maxLeverage', 20)
                    print(f'[HLTrader] {coin} 最大杠杆: {max_lev}x')
                    return int(max_lev)
            
            print(f'[HLTrader] ⚠️ 未找到币种 {coin} 的信息,使用默认杠杆 20x')
            return 20
        except Exception as e:
            print(f'[HLTrader] 获取最大杠杆失败: {e}')
            return None
    
    def calculate_position_size(self, margin: float, leverage: int, price: float) -> float:
        """
        计算实际下单数量
        
        Args:
            margin: 保证金 (USD)
            leverage: 杠杆倍数
            price: 当前价格
        
        Returns:
            下单数量 (coin 数量)
        
        示例:
            margin=$100, leverage=10x, price=$2650/GOLD
            position_value = $100 * 10 = $1000
            size = $1000 / $2650 = 0.377 个 GOLD
        """
        position_value = margin * leverage
        size = position_value / price if price > 0 else 0
        return size
    
    def place_market_order(
        self,
        coin: str,
        is_buy: bool,
        margin: float,
        leverage: int,
        current_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        下市价单 (使用 IOC 限价单模拟市价单)
        
        Args:
            coin: 币种名称 (如 'GOLD')
            is_buy: True=买入(做多), False=卖出(做空)
            margin: 保证金金额 (USD)
            leverage: 杠杆倍数
            current_price: 当前价格 (如果不提供会自动获取)
        
        Returns:
            订单信息字典,失败返回 None
            格式: {
                'order_id': '...',
                'coin': 'GOLD',
                'side': 'buy/sell',
                'size': 0.377,
                'price': 2650.5,
                'margin': 100,
                'leverage': 10
            }
        """
        try:
            # 1. 获取当前价格 (如果未提供)
            if current_price is None:
                market_data = self.info.all_mids()
                current_price = market_data.get(coin)
                if not current_price:
                    print(f'[HLTrader] ❌ 无法获取 {coin} 的当前价格')
                    return None
            
            # 2. 计算下单数量
            size = self.calculate_position_size(margin, leverage, current_price)
            
            # 3. 设置限价 (留0.5%滑点余地)
            # 买入: 用 ask 价格 * 1.005
            # 卖出: 用 bid 价格 * 0.995
            if is_buy:
                limit_price = current_price * 1.005
            else:
                limit_price = current_price * 0.995
            
            # 4. 构建订单参数
            order = {
                'coin': coin,
                'is_buy': is_buy,
                'sz': size,  # 数量
                'limit_px': limit_price,  # 限价
                'order_type': {'limit': {'tif': 'Ioc'}},  # IOC = Immediate or Cancel (市价单效果)
                'reduce_only': False
            }
            
            print(f'[HLTrader] 准备下单: {coin} {"买入" if is_buy else "卖出"} '
                  f'{size:.6f}个 @${limit_price:.2f}, 杠杆{leverage}x, 保证金${margin}')
            
            # 5. 设置杠杆
            try:
                self.exchange.update_leverage(leverage, coin)
                print(f'[HLTrader] 已设置杠杆: {leverage}x')
            except Exception as e:
                print(f'[HLTrader] ⚠️ 设置杠杆失败: {e}')
            
            # 6. 下单
            result = self.exchange.order(coin, is_buy, size, limit_price, {'limit': {'tif': 'Ioc'}})
            
            if result and result.get('status') == 'ok':
                order_info = {
                    'order_id': result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid'),
                    'coin': coin,
                    'side': 'buy' if is_buy else 'sell',
                    'size': size,
                    'price': limit_price,
                    'margin': margin,
                    'leverage': leverage,
                    'timestamp': result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('timestamp')
                }
                print(f'[HLTrader] ✅ 下单成功: {order_info}')
                return order_info
            else:
                print(f'[HLTrader] ❌ 下单失败: {result}')
                return None
        
        except Exception as e:
            print(f'[HLTrader] 下单异常: {e}')
            import traceback
            traceback.print_exc()
            return None
    
    def get_position(self, coin: str) -> Optional[Dict[str, Any]]:
        """
        查询某个币种的当前持仓
        
        Args:
            coin: 币种名称
        
        Returns:
            持仓信息,无持仓返回 None
        """
        try:
            user_state = self.info.user_state(self.wallet_address)
            
            for position in user_state.get('assetPositions', []):
                pos = position.get('position', {})
                if pos.get('coin') == coin:
                    return {
                        'coin': coin,
                        'size': float(pos.get('szi', 0)),
                        'entry_price': float(pos.get('entryPx', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': float(pos.get('leverage', {}).get('value', 0))
                    }
            
            return None
        except Exception as e:
            print(f'[HLTrader] 查询持仓失败: {e}')
            return None
