"""
Hyperliquid WebSocket 客户端
订阅实时价格和订单簿数据

功能:
- 订阅 allMids (所有中间价)
- 订阅 l2Book (订单簿 bid/ask)
- 订阅 fundingRate (资金费率)
"""

import asyncio
import json
from datetime import datetime

# 从 hyperliquid-python-sdk 包导入
# 注意：目录已重命名为 trade_hyperliquid，不再与 SDK 包冲突
from hyperliquid.info import Info
from hyperliquid.utils import constants


class HyperliquidWSClient:
    """Hyperliquid WebSocket 客户端"""
    
    def __init__(self, callback):
        """
        初始化
        :param callback: 数据回调函数
        """
        self.callback = callback
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)
        self.price_data = {}  # 存储价格数据
        self.orderbook_data = {}  # 存储订单簿数据
        self.funding_data = {}  # 存储资金费率
        
    async def start(self):
        """启动 WebSocket 订阅"""
        print('[HL WS] 开始订阅数据流...')
        
        # 订阅所有中间价
        self.info.subscribe({'type': 'allMids'}, self.on_all_mids)
        print('[HL WS] ✅ 已订阅 allMids')
        
        # 订阅常用币种的订单簿
        # 主网加密货币：直接使用币种名
        # HIP-3 资产：需要 xyz: 前缀（如 xyz:GOLD）
        priority_coins = [
            'BTC', 'ETH', 'SOL', 'ARB',  # 主网
            'xyz:GOLD', 'xyz:SILVER', 'xyz:COPPER', 'xyz:XYZ100'  # HIP-3
        ]
        subscribed = []
        for coin in priority_coins:
            try:
                self.info.subscribe({
                    'type': 'l2Book',
                    'coin': coin
                }, self.on_orderbook)
                subscribed.append(coin)
            except Exception as e:
                print(f'[HL WS] ⚠️ 订阅 {coin} 订单簿失败: {e}')
        
        print(f'[HL WS] ✅ 已订阅 {len(subscribed)} 个币种的订单簿: {", ".join(subscribed)}')
        
        # 保持连接
        while True:
            await asyncio.sleep(1)
    
    def on_all_mids(self, message):
        """处理 allMids 数据"""
        if message.get('channel') == 'allMids' and 'data' in message:
            mids = message['data'].get('mids', {})
            self.price_data['mids'] = mids
            self._send_update()
    
    def on_orderbook(self, message):
        """处理订单簿数据"""
        if message.get('channel') == 'l2Book' and 'data' in message:
            data = message['data']
            coin = data.get('coin')
            levels = data.get('levels', [[],[]])
            
            # 提取 bid/ask
            if len(levels) >= 2 and len(levels[0]) > 0 and len(levels[1]) > 0:
                bid = float(levels[0][0]['px'])  # 最高买价
                ask = float(levels[1][0]['px'])  # 最低卖价
                mid = (bid + ask) / 2
                
                self.orderbook_data[coin] = {
                    'bid': bid,
                    'mid': mid,
                    'ask': ask
                }
                self._send_update()
    
    def _send_update(self):
        """发送数据更新"""
        contracts = self._build_contracts()
        if contracts:
            data = {
                'contracts': contracts,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.callback(data)
    
    def _build_contracts(self):
        """构建合约列表"""
        # TODO: 需要从 meta API 获取完整的合约信息
        # 这里先简化处理，只返回有订单簿数据的币种
        contracts = []
        
        for coin, book_data in self.orderbook_data.items():
            mid_price = self.price_data.get('mids', {}).get(coin, book_data['mid'])
            
            contracts.append({
                'coin': coin,
                'bid': book_data['bid'],
                'mid': float(mid_price) if mid_price else book_data['mid'],
                'ask': book_data['ask'],
                # TODO: 添加其他字段
            })
        
        return contracts


async def start_hl_ws_client(callback):
    """启动 HyperLiquid WebSocket 客户端"""
    client = HyperliquidWSClient(callback)
    await client.start()
