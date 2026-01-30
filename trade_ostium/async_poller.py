"""
Ostium 异步轮询器
定期获取 Ostium 数据并通过回调发送
"""

import asyncio
import traceback
from datetime import datetime
from ostium_python_sdk import OstiumSDK
from ostium_python_sdk.config import NetworkConfig
import os

# Arbitrum RPC URL (优先级：环境变量 > config.py > 默认公共节点)
ARBITRUM_RPC_URL = os.getenv('ARBITRUM_RPC_URL')

if not ARBITRUM_RPC_URL:
    # 如果环境变量未设置，尝试从父目录 config.py 读取
    try:
        import sys
        # 添加父目录到 sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        import config
        # 获取默认兜底 RPC (优先从配置读取，没有则用硬编码)
        default_rpc = getattr(config, 'DEFAULT_ARBITRUM_RPC', 'https://arb1.arbitrum.io/rpc')

        if hasattr(config, 'ARBITRUM_RPC_URL') and config.ARBITRUM_RPC_URL:
            rpc_url = config.ARBITRUM_RPC_URL
            # 增加有效性校验
            if "YOUR_API_KEY" in rpc_url or "your-api-key" in rpc_url:
                print(f'[OS Poller] ⚠️ 检测到 config.py 中的 RPC URL 包含占位符，忽略该配置')
                ARBITRUM_RPC_URL = default_rpc
                print(f'[OS Poller] 将使用兜底公共节点: {ARBITRUM_RPC_URL}')
            else:
                ARBITRUM_RPC_URL = rpc_url
                print(f'[OS Poller] 使用 config.py 中的 RPC: {ARBITRUM_RPC_URL[:20]}...')
        else:
            # 如果 config 中没有 ARBITRUM_RPC_URL，直接使用兜底
            ARBITRUM_RPC_URL = default_rpc

    except ImportError:
        pass

# 如果仍然没有（ImportError 或者其他情况），使用硬编码默认节点
if not ARBITRUM_RPC_URL:
    ARBITRUM_RPC_URL = 'https://arb1.arbitrum.io/rpc'
    print('[OS Poller] ⚠️ 使用内置硬编码 RPC (可能不稳定)')

# 最小持仓量（美元）- 用于过滤
MIN_OI_USD = 1_000_000  # 1M 美元


class OstiumAsyncPoller:
    """Ostium 异步轮询器"""
    
    def __init__(self, callback, interval=1):
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
        print(f'[OS Poller] 正在连接 RPC: {rpc_url}')
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
        filtered_count = 0
        
        for pair in pairs:
            pair_name = f"{pair.get('from', '')}/{pair.get('to', '')}"
            price_data = price_map.get(pair_name, {})
            
            if price_data:
                # 计算持仓量（OI）
                long_oi = int(pair.get('longOI', 0))
                short_oi = int(pair.get('shortOI', 0))
                total_oi = (long_oi + short_oi) / 1e18
                mid_price = price_data.get('mid', 1.0)
                total_oi_usd = total_oi * mid_price if mid_price else 0
                
                # 过滤：持仓量必须大于 MIN_OI_USD
                if total_oi_usd < MIN_OI_USD:
                    filtered_count += 1
                    continue
                
                # 获取资产组
                group_name = pair.get('group', {}).get('name', '')
                is_crypto = group_name == 'crypto'
                
                # 资金费率（仅 crypto 资产）
                cur_funding_long = int(pair.get('curFundingLong', 0))
                cur_funding_short = int(pair.get('curFundingShort', 0))
                
                # Crypto 资金费率：每秒费率 -> 每小时费率（百分比）
                funding_long_hourly = abs(cur_funding_long) * 3600 / 1e18 * 100 if cur_funding_long else None
                funding_short_hourly = abs(cur_funding_short) * 3600 / 1e18 * 100 if cur_funding_short else None
                
                # 隔夜费率（非 crypto 资产）
                rollover_per_block = int(pair.get('rolloverFeePerBlock', 0))
                BLOCKS_PER_HOUR = 4 * 3600  # Arbitrum 约 4 块/秒
                rollover_hourly = abs(rollover_per_block) * BLOCKS_PER_HOUR / 1e18 * 100 if rollover_per_block else None
                
                contracts.append({
                    'pair': pair_name,
                    'from': pair.get('from', ''),
                    'to': pair.get('to', ''),
                    'group': group_name,
                    'bid': price_data.get('bid', 0),
                    'mid': price_data.get('mid', 0),
                    'ask': price_data.get('ask', 0),
                    'totalOI_USD': round(total_oi_usd, 2),
                    'longOI': pair.get('longOI'),
                    'shortOI': pair.get('shortOI'),
                    'fundingRate': {
                        'longPayHourly': round(funding_long_hourly, 6) if funding_long_hourly else None,
                        'shortPayHourly': round(funding_short_hourly, 6) if funding_short_hourly else None,
                        'longPay8h': round(funding_long_hourly * 8, 6) if funding_long_hourly else None,
                        'shortPay8h': round(funding_short_hourly * 8, 6) if funding_short_hourly else None,
                    } if is_crypto and (funding_long_hourly or funding_short_hourly) else None,
                    'rolloverRate': {
                        'hourly': round(rollover_hourly, 6) if rollover_hourly else None,
                        'daily': round(rollover_hourly * 24, 6) if rollover_hourly else None,
                    } if not is_crypto and rollover_hourly else None,
                })
        
        if filtered_count > 0:
            print(f'[OS Poller] 🔍 过滤掉 {filtered_count} 个低 OI 合约（< ${MIN_OI_USD:,}）')
        
        return contracts


async def start_os_poller(callback, interval=2):
    """启动 Ostium 轮询器"""
    poller = OstiumAsyncPoller(callback, interval)
    await poller.start()
