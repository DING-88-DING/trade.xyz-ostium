"""
Ostium 异步轮询器
每2秒轮询一次 Ostium API 获取最新数据

功能:
- 异步并发请求
- 2秒间隔轮询
- 错误重试
"""

import asyncio
from datetime import datetime
from ostium_python_sdk import OstiumSDK
from ostium_python_sdk.config import NetworkConfig
import os


class OstiumAsyncPoller:
    """Ostium 异步轮询器"""
    
    def __init__(self, callback, interval=2):
        """
        初始化
        :param callback: 数据回调函数
        :param interval: 轮询间隔(秒)
        """
        self.callback = callback
        self.interval = interval
        
        # 读取 RPC URL
        rpc_url = os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc')
        
        # 初始化 SDK
        config = NetworkConfig.mainnet()
        self.sdk = OstiumSDK(config, rpc_url=rpc_url)
        
        print(f'[OS Poller] 初始化完成，轮询间隔: {interval}秒')
    
    async def start(self):
        """启动轮询"""
        print('[OS Poller] 开始轮询...')
        
        while True:
            try:
                # 获取数据
                data = await self._fetch_data()
                
                # 发送给回调
                if data:
                    self.callback(data)
                
                # 等待下一次轮询
                await asyncio.sleep(self.interval)
                
            except Exception as e:
                print(f'[OS Poller] ❌ 错误: {e}')
                # 出错后等待5秒再重试
                await asyncio.sleep(5)
    
    async def _fetch_data(self):
        """获取 Ostium 数据"""
        try:
            # 获取所有交易对（使用 subgraph）
            pairs = await self.sdk.subgraph.get_pairs()
            
            # 获取最新价格（使用 price 模块）
            prices = await self.sdk.price.get_latest_prices()
            
            # 构建合约列表
            contracts = await self._build_contracts(pairs, prices)
            
            return {
                'contracts': contracts,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f'[OS Poller] 获取数据失败: {e}')
            import traceback
            traceback.print_exc()
            return None
    
    async def _build_contracts(self, pairs, prices):
        """构建合约列表"""
        # 将价格列表转换为字典，key 为 "from/to" 格式
        price_map = {}
        for price in prices:
            key = f"{price.get('from')}/{price.get('to')}"
            price_map[key] = price
        
        contracts = []
        
        for pair in pairs:
            pair_name = f"{pair.get('from', '')}/{pair.get('to', '')}"
            price_data = price_map.get(pair_name, {})
            
            if price_data:
                contracts.append({
                    'pair': pair_name,
                    'from': pair.get('from', ''),
                    'to': pair.get('to', ''),
                    'group': pair.get('group', {}).get('name', ''),
                    'bid': price_data.get('bid', 0),
                    'mid': price_data.get('mid', 0),
                    'ask': price_data.get('ask', 0),
                    # TODO: 添加其他字段如 OI, funding rate 等
                })
        
        return contracts


async def start_os_poller(callback, interval=2):
    """启动 Ostium 轮询器"""
    poller = OstiumAsyncPoller(callback, interval)
    await poller.start()
