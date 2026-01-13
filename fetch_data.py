# -*- coding: utf-8 -*-
"""
数据获取模块
从 Ostium 和 Trade.xyz 两个平台获取合约数据
"""

import requests
import websocket
import json
import time
import threading
from typing import Dict, List, Optional


class OstiumFetcher:
    """Ostium 平台数据获取类"""
    
    def __init__(self):
        self.api_url = "https://metadata-backend.ostium.io/graph"
        self.graphql_query = {
            "operationName": "GetPairsAndMetadata",
            "variables": {},
            "query": """query GetPairsAndMetadata {
                pairs(first: 1000) {
                    id
                    from
                    to
                    volume
                    lastTradePrice
                    lastFundingRate
                    longOI
                    shortOI
                    __typename
                }
            }"""
        }
    
    def fetch(self) -> List[Dict]:
        """
        获取 Ostium 平台的合约数据
        
        Returns:
            List[Dict]: 合约数据列表
        """
        try:
            print("正在从 Ostium 获取数据...")
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
            }
            
            response = requests.post(
                self.api_url,
                json=self.graphql_query,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get('data', {}).get('pairs', [])
            
            # 处理和转换数据
            processed_pairs = []
            for pair in pairs:
                try:
                    # 交易量单位转换 (假设原始单位是 wei,需要除以 10^18)
                    volume_raw = int(pair.get('volume', 0))
                    volume_usd = volume_raw / 1e18  # 转换为标准单位
                    
                    # 价格单位转换
                    price_raw = pair.get('lastTradePrice', '0')
                    price = int(price_raw) / 1e18 if price_raw else 0
                    
                    # 资金费率转换
                    funding_rate_raw = pair.get('lastFundingRate', '0')
                    funding_rate = int(funding_rate_raw) / 1e10 if funding_rate_raw else 0
                    
                    processed_pair = {
                        'symbol': f"{pair.get('from', '')}/{pair.get('to', '')}",
                        'from': pair.get('from', ''),
                        'to': pair.get('to', ''),
                        'volume_24h': volume_usd,
                        'price': price,
                        'funding_rate': funding_rate,
                        'platform': 'Ostium'
                    }
                    
                    processed_pairs.append(processed_pair)
                except (ValueError, TypeError) as e:
                    print(f"处理合约数据时出错: {pair.get('from', 'unknown')}/{pair.get('to', 'unknown')} - {e}")
                    continue
            
            print(f"从 Ostium 获取到 {len(processed_pairs)} 个合约")
            return processed_pairs
            
        except requests.exceptions.RequestException as e:
            print(f"从 Ostium 获取数据失败: {e}")
            return []


class TradeXYZFetcher:
    """Trade.xyz 平台数据获取类 (WebSocket)"""
    
    def __init__(self):
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.data = []
        self.received_data = False
        self.ws = None
        self.coin_name_map = {}  # coin索引到真实名称的映射
    
    def fetch_coin_names(self) -> Dict[str, str]:
        """
        获取合约名称映射表
        调用spotMeta接口获取coin到真实名称的映射
        
        数据结构说明:
        - universe数组中每个项目有tokens数组，如 "tokens": [2, 0]
        - tokens[0] 是token索引，需要在根级tokens数组中查找
        - 根级tokens数组中每个token有name和index字段
        
        Returns:
            Dict[str, str]: coin索引到名称的映射字典 (如 "@1" -> "HFUN")
        """
        try:
            print("正在获取合约名称映射...")
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
            }
            
            payload = {
                "type": "spotMeta"
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            universe = data.get('universe', [])
            tokens = data.get('tokens', [])
            
            # 构建token index到token name的映射表
            # tokens数组中每个元素有index和name字段
            token_index_to_name = {}
            for token in tokens:
                token_index = token.get('index')
                token_name = token.get('name', '')
                if token_index is not None and token_name:
                    token_index_to_name[token_index] = token_name
            
            # 构建coin索引到名称的映射
            # universe中每个项目的tokens[0]对应根级tokens数组中的token index
            # WebSocket中coin格式为 "@数字"，数字对应universe中的index
            coin_map = {}
            for item in universe:
                universe_index = item.get('index')  # 这是universe中的索引，对应WebSocket中的@数字
                tokens_array = item.get('tokens', [])
                
                if universe_index is not None and len(tokens_array) > 0:
                    # tokens[0]是指向根级tokens数组的索引
                    token_ref_index = tokens_array[0]
                    # 从token索引映射表中获取真实名称
                    real_name = token_index_to_name.get(token_ref_index, '')
                    
                    if real_name:
                        # WebSocket中coin格式为 "@数字"
                        coin_key = f"@{universe_index}"
                        coin_map[coin_key] = real_name
            
            print(f"获取到 {len(coin_map)} 个合约名称映射")
            return coin_map
            
        except requests.exceptions.RequestException as e:
            print(f"获取合约名称映射失败: {e}")
            return {}
    
    def on_message(self, ws, message):
        """WebSocket 消息接收回调"""
        try:
            data = json.loads(message)
            channel = data.get('channel', '')
            
            # 处理 spotAssetCtxs 频道的数据(现货数据)
            if channel == 'spotAssetCtxs':
                contracts = data.get('data', [])
                for contract in contracts:
                    self._process_contract(contract)
                self.received_data = True
            
            # 处理订阅响应
            elif channel == 'subscriptionResponse':
                print(f"订阅成功: {data.get('data', {}).get('subscription', {}).get('type', 'unknown')}")
                
        except json.JSONDecodeError as e:
            print(f"解析 WebSocket 消息失败: {e}")
        except Exception as e:
            print(f"处理 WebSocket 消息时出错: {e}")
    
    def _process_contract(self, contract: Dict):
        """处理单个合约数据"""
        try:
            # 提取关键数据
            day_ntl_vlm = contract.get('dayNtlVlm', '0')
            volume_24h = float(day_ntl_vlm) if day_ntl_vlm else 0
            
            mark_px = contract.get('markPx', '0')
            price = float(mark_px) if mark_px else 0
            
            # Trade.xyz现货没有资金费率,设置为0
            funding_rate = 0
            
            coin = contract.get('coin', '')  # 格式是 "PURR/USDC" 或 "@1" 等
            
            # 如果coin是索引格式(@开头),则映射到真实名称
            if coin in self.coin_name_map:
                real_name = self.coin_name_map[coin]
                symbol = real_name
            else:
                symbol = coin
            
            processed_contract = {
                'symbol': symbol,
                'coin': symbol,  # coin也使用映射后的真实名称
                'volume_24h': volume_24h,
                'price': price,
                'funding_rate': funding_rate,
                'platform': 'Trade.xyz'
            }
            
            self.data.append(processed_contract)
            
        except (ValueError, TypeError) as e:
            print(f"处理合约数据时出错: {contract.get('coin', 'unknown')} - {e}")
    
    def on_error(self, ws, error):
        """WebSocket 错误回调"""
        print(f"WebSocket 错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 关闭回调"""
        print(f"WebSocket 连接关闭")
    
    def on_open(self, ws):
        """WebSocket 连接建立回调"""
        print("WebSocket 连接已建立,正在订阅数据...")
        
        # 订阅现货合约数据
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "spotAssetCtxs"
            }
        }
        ws.send(json.dumps(subscribe_msg))
    
    def fetch(self, timeout: int = 10) -> List[Dict]:
        """
        获取 Trade.xyz 平台的合约数据
        
        Args:
            timeout: 等待数据超时时间(秒)
            
        Returns:
            List[Dict]: 合约数据列表
        """
        try:
            print("正在从 Trade.xyz 获取数据...")
            
            # 首先获取合约名称映射
            self.coin_name_map = self.fetch_coin_names()
            
            self.data = []
            self.received_data = False
            
            # 创建 WebSocket 连接
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            # 在单独的线程中运行 WebSocket
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 等待接收数据
            start_time = time.time()
            while not self.received_data and (time.time() - start_time) < timeout:
                time.sleep(0.5)
            
            # 关闭连接
            if self.ws:
                self.ws.close()
            
            if not self.received_data:
                print("WebSocket 数据接收超时")
            else:
                print(f"从 Trade.xyz 获取到 {len(self.data)} 个合约")
            
            return self.data
            
        except Exception as e:
            print(f"从 Trade.xyz 获取数据失败: {e}")
            return []


def filter_by_volume(contracts: List[Dict], min_volume: float = 1000000) -> List[Dict]:
    """
    根据24小时交易量过滤合约
    
    Args:
        contracts: 合约列表
        min_volume: 最小交易量阈值(默认1M美元)
        
    Returns:
        List[Dict]: 过滤后的合约列表
    """
    filtered = [c for c in contracts if c.get('volume_24h', 0) >= min_volume]
    print(f"过滤后剩余 {len(filtered)} 个合约(交易量 >= ${min_volume:,.0f})")
    return filtered


def save_to_json(data: List[Dict], filename: str):
    """
    将数据保存到JSON文件
    
    Args:
        data: 要保存的数据
        filename: 文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")
    except Exception as e:
        print(f"保存数据到 {filename} 失败: {e}")


if __name__ == "__main__":
    # 测试代码
    print("=== 测试 Ostium 数据获取 ===")
    ostium_fetcher = OstiumFetcher()
    ostium_data = ostium_fetcher.fetch()
    ostium_filtered = filter_by_volume(ostium_data)
    save_to_json(ostium_filtered, "ostium_data.json")
    
    print("\n=== 测试 Trade.xyz 数据获取 ===")
    tradexyz_fetcher = TradeXYZFetcher()
    tradexyz_data = tradexyz_fetcher.fetch(timeout=15)
    tradexyz_filtered = filter_by_volume(tradexyz_data)
    save_to_json(tradexyz_filtered, "tradexyz_data.json")
