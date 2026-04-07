"""
Hyperliquid WebSocket 客户端
使用原生 WebSocket 直接订阅 allDexsAssetCtxs
"""

import asyncio
import json
import requests
from datetime import datetime
import websockets
from trade_hyperliquid.filters import is_hyperliquid_asset_excluded

# Hyperliquid WebSocket 地址
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"


class HyperliquidWSClient:
    """Hyperliquid WebSocket 客户端（原生 WebSocket）"""
    
    # 过滤条件：最小24小时成交量（美元）
    MIN_VOLUME_USD = 1_000_000  # 1M 美元
    
    def __init__(self, callback):
        """
        初始化
        :param callback: 数据回调函数
        """
        self.callback = callback
        self.meta_data = {}  # 存储元数据（包含交易量等信息）
        self.xyz_meta_data = {}  # 存储 xyz dex 元数据
        self.ws = None  # WebSocket 连接

        # 缓存 universe（币种列表），避免重复请求
        self.universes = {}  # {dex_name: universe}
        self._init_universes()


    def _init_universes(self):
        """初始化：获取并缓存所有 dex 的 universe（币种列表）"""
        try:
            print(f'[HL WS] 🔄 正在更新 Universe 映射...')
            # 获取主 dex
            response = requests.post(
                f"{HYPERLIQUID_API_URL}/info",
                headers={"Content-Type": "application/json"},
                json={"type": "meta"},
                timeout=10 # 添加超时防止阻塞太久
            )
            if response.status_code == 200:
                main_meta = response.json()
                self.universes[''] = main_meta.get('universe', [])
                print(f'[HL WS] ✅ 已缓存主 dex universe: {len(self.universes[""])} 个资产')

            # 获取 xyz dex
            try:
                xyz_response = requests.post(
                    f"{HYPERLIQUID_API_URL}/info",
                    headers={"Content-Type": "application/json"},
                    json={"type": "meta", "dex": "xyz"},
                    timeout=10
                )
                if xyz_response.status_code == 200:
                    xyz_meta = xyz_response.json()
                    self.universes['xyz'] = xyz_meta.get('universe', [])
                    print(f'[HL WS] ✅ 已缓存 xyz dex universe: {len(self.universes["xyz"])} 个资产')
            except Exception as e:
                print(f'[HL WS] ⚠️ 获取 xyz dex universe 失败: {e}')
                # 如果失败保留旧值，不轻易清空，除非是第一次
                if 'xyz' not in self.universes:
                    self.universes['xyz'] = []

        except Exception as e:
            print(f'[HL WS] ⚠️ 获取主 dex universe 失败: {e}')
            if '' not in self.universes:
                self.universes[''] = []

    async def _monitor_universe_updates(self):
        """
        后台任务：定期(每60秒)无条件刷新 Universe 映射
        确保资产列表是最新的，防止上新币导致数据错位
        """
        print('[HL WS] 🕵️ 启动 Universe 自动刷新任务 (每60秒)')
        while True:
            try:
                await asyncio.sleep(60)  # 每 60 秒刷新一次

                # 在 executor 中运行同步的 requests 请求，避免阻塞 asyncio 循环
                loop = asyncio.get_running_loop()

                # 定义获取数据的函数
                def fetch_meta(dex=""):
                    try:
                        payload = {"type": "meta"}
                        if dex:
                            payload["dex"] = dex

                        resp = requests.post(
                            f"{HYPERLIQUID_API_URL}/info",
                            headers={"Content-Type": "application/json"},
                            json=payload,
                            timeout=5
                        )
                        if resp.status_code == 200:
                            return resp.json().get('universe', [])
                        return None
                    except Exception:
                        return None

                # 1. 刷新主站
                new_main_universe = await loop.run_in_executor(None, fetch_meta, "")
                if new_main_universe:
                    self.universes[''] = new_main_universe
                    # print(f'[HL WS] 🔄 主站 Universe 已刷新 ({len(new_main_universe)} 个资产)')

                # 2. 刷新 xyz
                new_xyz_universe = await loop.run_in_executor(None, fetch_meta, "xyz")
                if new_xyz_universe:
                    self.universes['xyz'] = new_xyz_universe
                    # print(f'[HL WS] 🔄 xyz Universe 已刷新 ({len(new_xyz_universe)} 个资产)')

            except Exception as e:
                print(f'[HL WS] ⚠️ 自动刷新任务出错: {e}')
                # 出错不中断循环
                continue

    async def start(self):
        """启动 WebSocket 订阅,支持自动重连"""
        print('[HL WS] 开始连接 WebSocket...')

        # 启动后台巡检任务(只启动一次)
        asyncio.create_task(self._monitor_universe_updates())

        # 重连参数
        reconnect_delay = 1  # 初始重连延迟(秒)
        max_reconnect_delay = 60  # 最大重连延迟(秒)
        
        # 无限重连循环
        while True:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL) as websocket:
                    self.ws = websocket
                    print(f'[HL WS] ✅ 已连接到 {HYPERLIQUID_WS_URL}')
                    
                    # 连接成功,重置重连延迟
                    reconnect_delay = 1

                    # 发送订阅消息
                    subscribe_msg = {
                        "method": "subscribe",
                        "subscription": {
                            "type": "allDexsAssetCtxs"
                        }
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    print('[HL WS] ✅ 已发送 allDexsAssetCtxs 订阅请求')

                    # 持续接收消息
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.on_message(data)
                        except Exception as e:
                            print(f'[HL WS] ⚠️ 处理消息失败: {e}')

            except websockets.exceptions.ConnectionClosed:
                print(f'[HL WS] ⚠️ 连接已关闭,将在 {reconnect_delay} 秒后重连...')
            except Exception as e:
                print(f'[HL WS] ❌ WebSocket 连接失败: {e}')
                import traceback
                traceback.print_exc()
            
            # 等待后重连
            await asyncio.sleep(reconnect_delay)
            
            # 指数退避:每次重连延迟翻倍,但不超过最大值
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
            print(f'[HL WS] 🔄 正在尝试重新连接...(下次重连延迟: {reconnect_delay}秒)')
    
    
    def on_message(self, message):
        """处理所有 WebSocket 消息"""
        channel = message.get('channel', '')
        
        # 处理 allDexsAssetCtxs 消息
        if channel == 'allDexsAssetCtxs':
            print(f'[HL WS] 📊 收到 allDexsAssetCtxs 消息')
            self.on_all_dexs_asset_ctxs(message)
        elif channel == 'subscriptionResponse':
            print(f'[HL WS] ✅ 订阅成功: {message.get("data")}')
        else:
            print(f'[HL WS] 📩 收到消息: channel={channel}')
    
    def on_all_dexs_asset_ctxs(self, message):
        """处理 allDexsAssetCtxs 数据（所有 dex 的资产上下文）"""
        # print(f'[HL WS] 🐞 收到消息: channel={message.get("channel")}')

        if message.get('channel') == 'allDexsAssetCtxs' and 'data' in message:
            data = message['data']
            ctxs = data.get('ctxs', [])

            # ctxs[0] 是主站: ["", [{...}, {...}, ...]]
            # ctxs[7] 是 xyz: ["xyz", [{...}, {...}, ...]]
            # 只处理主站和 xyz

            for dex_entry in ctxs:
                if not dex_entry or len(dex_entry) < 2:
                    continue

                dex_name = dex_entry[0]  # "" 或 "xyz"
                asset_ctxs_array = dex_entry[1]  # 资产数据数组

                # 只处理主站 ("") 和 xyz
                if dex_name not in ['', 'xyz']:
                    continue

                if not isinstance(asset_ctxs_array, list):
                    continue

                # 获取缓存的 universe
                universe = self.universes.get(dex_name, [])

                # 如果本地还没获取到 universe，先跳过
                if not universe:
                    continue

                # 遍历资产数组，与 universe 按索引匹配
                for idx, ctx in enumerate(asset_ctxs_array):
                    if idx >= len(universe) or not isinstance(ctx, dict):
                        continue
                    
                    coin = universe[idx].get('name', '')
                    if not coin:
                        continue
                    
                    # 构建完整的币种名
                    if dex_name == 'xyz':
                        # xyz dex 的币种名：universe 中已经是 "GOLD" 格式，需要添加前缀
                        # 但需要检查是否已经有前缀，避免重复
                        if not coin.startswith('xyz:'):
                            full_coin_name = f"xyz:{coin}"
                        else:
                            full_coin_name = coin
                        
                        self.xyz_meta_data[full_coin_name] = {
                            'dayVolume': ctx.get('dayNtlVlm'),
                            'funding': ctx.get('funding'),
                            'openInterest': ctx.get('openInterest'),
                            'midPx': ctx.get('midPx'),  # 中间价
                            'impactPxs': ctx.get('impactPxs'),  # [bid, ask]
                        }
                    else:
                        # 主站
                        self.meta_data[coin] = {
                            'dayVolume': ctx.get('dayNtlVlm'),
                            'funding': ctx.get('funding'),
                            'openInterest': ctx.get('openInterest'),
                            'midPx': ctx.get('midPx'),
                            'impactPxs': ctx.get('impactPxs'),
                        }
            
            print(f'[HL WS] 📊 更新资产数据: {len(self.meta_data)} 主站, {len(self.xyz_meta_data)} xyz')
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
        contracts = []
        filtered_count = 0
        excluded_count = 0
        
        # 1. 处理主站资产
        for coin, meta in self.meta_data.items():
            if is_hyperliquid_asset_excluded(coin):
                excluded_count += 1
                continue

            day_volume = meta.get('dayVolume')
            mid_px = meta.get('midPx')
            impact_pxs = meta.get('impactPxs')
            funding = meta.get('funding')
            open_interest = meta.get('openInterest')
            
            # 过滤：交易量必须大于 MIN_VOLUME_USD
            if day_volume:
                try:
                    volume_usd = float(day_volume)
                    if volume_usd < self.MIN_VOLUME_USD:
                        filtered_count += 1
                        continue
                except (ValueError, TypeError):
                    # 无效的交易量数据，跳过
                    continue
            else:
                # 没有交易量数据，跳过
                continue
            
            # 提取 bid/ask
            bid = float(impact_pxs[0]) if impact_pxs and len(impact_pxs) > 0 else 0
            ask = float(impact_pxs[1]) if impact_pxs and len(impact_pxs) > 1 else 0
            mid = float(mid_px) if mid_px else (bid + ask) / 2 if bid and ask else 0
            
            # 调试：打印第一个合约的数据
            if coin == 'BTC':
                print(f'[HL WS] 🔍 BTC 数据: dayVolume={day_volume}, funding={funding}, OI={open_interest}')
            
            # 匹配前端期望的数据格式
            # 注意: funding 需要乘以 100 转换为百分比
            funding_hourly = float(funding) * 100 if funding else 0
            contracts.append({
                'coin': coin,
                'dex': 'main',  # 主站标记
                'bid': bid,
                'mid': mid,
                'ask': ask,
                'dayVolume_USD': float(day_volume) if day_volume else 0,  # 前端期望字段名
                'fundingRate': {
                    'rateHourly': round(funding_hourly, 6)  # 百分比格式
                },
                'openInterest': float(open_interest) if open_interest else 0,
            })
        
        # 2. 处理 xyz dex 资产
        for coin, meta in self.xyz_meta_data.items():
            if is_hyperliquid_asset_excluded(coin):
                excluded_count += 1
                continue

            day_volume = meta.get('dayVolume')
            mid_px = meta.get('midPx')
            impact_pxs = meta.get('impactPxs')
            funding = meta.get('funding')
            open_interest = meta.get('openInterest')
            
            # xyz dex 的股票、外汇等资产交易量可能很低，使用更低的门槛
            # 使用 1M 美元门槛（比主站的 2M 低）
            MIN_XYZ_VOLUME = 1_000_000  # xyz dex 最小交易量 1M
            
            if day_volume:
                try:
                    volume_usd = float(day_volume)
                    if volume_usd < MIN_XYZ_VOLUME:
                        filtered_count += 1
                        continue
                except (ValueError, TypeError):
                    continue
            else:
                continue
            
            bid = float(impact_pxs[0]) if impact_pxs and len(impact_pxs) > 0 else 0
            ask = float(impact_pxs[1]) if impact_pxs and len(impact_pxs) > 1 else 0
            mid = float(mid_px) if mid_px else (bid + ask) / 2 if bid and ask else 0
            
            # 调试：打印第一个 xyz 合约的数据
            if 'GOLD' in coin:
                print(f'[HL WS] 🔍 {coin} 数据: dayVolume={day_volume}, funding={funding}, OI={open_interest}')
            
            # 注意: funding 需要乘以 100 转换为百分比
            funding_hourly = float(funding) * 100 if funding else 0
            contracts.append({
                'coin': coin,
                'dex': 'xyz',  # xyz dex 标记
                'bid': bid,
                'mid': mid,
                'ask': ask,
                'dayVolume_USD': float(day_volume) if day_volume else 0,
                'fundingRate': {
                    'rateHourly': round(funding_hourly, 6)  # 百分比格式
                },
                'openInterest': float(open_interest) if open_interest else 0,
            })
        
        if filtered_count > 0:
            print(f'[HL WS] 🔍 过滤掉 {filtered_count} 个低交易量合约（< ${self.MIN_VOLUME_USD:,}）')
        
        print(f'[HL WS] 📤 发送 {len(contracts)} 个合约数据')
        if excluded_count > 0:
            print(f'[HL WS] 排除 {excluded_count} 个命中过滤配置的合约')

        return contracts


async def start_hl_ws_client(callback):
    """启动 HyperLiquid WebSocket 客户端"""
    client = HyperliquidWSClient(callback)
    await client.start()
