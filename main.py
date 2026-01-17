"""
DEX 费率对比系统 - 主程序
一体化流程：获取数据 -> 处理数据 -> 启动服务器 -> 定时刷新

功能：
1. 获取 Hyperliquid 和 Ostium 数据（复用子目录模块）
2. 处理并过滤数据（保存在内存中）
3. 启动 HTTP 服务器（动态提供 JSON API）
4. 每 30 秒自动刷新数据

使用方法：
    python main.py
    然后访问 http://localhost:8080/comparison.html
"""

import json
import time
import threading
import asyncio
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 将脚本目录添加到 sys.path，以便导入子目录模块
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 导入配置
try:
    from config import HYPERLIQUID_API_URL, ARBITRUM_RPC_URL
except ImportError:
    print("警告: 未找到 config.py，使用默认配置")
    HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"
    ARBITRUM_RPC_URL = None

# ==================== 导入子目录模块 ====================
# 复用子目录的数据获取函数，避免代码重复

from hyperliquid.inspect_hyperliquid import get_all_perpetuals as hl_get_all_perpetuals
from ostium.inspect_ostium import fetch_all_data as os_fetch_all_data


# ==================== 配置 ====================

# 服务器配置
SERVER_PORT = 8080

# 数据刷新间隔（秒）
REFRESH_INTERVAL = 30

# 过滤条件
HL_MIN_VOLUME = 2_000_000    # Hyperliquid 最小24h成交量
OS_MIN_OI = 2_000_000        # Ostium 最小 OI


# ==================== 内存数据存储 ====================

# 全局数据存储
DATA_STORE = {
    "hyperliquid": {
        "total_filtered": 0,
        "filter_criteria": f"24h Volume > ${HL_MIN_VOLUME:,}",
        "updated_at": None,
        "contracts": []
    },
    "ostium": {
        "total_filtered": 0,
        "filter_criteria": f"Total OI > ${OS_MIN_OI:,}",
        "updated_at": None,
        "contracts": []
    }
}

# 数据锁（线程安全）
DATA_LOCK = threading.Lock()


# ==================== Hyperliquid 数据处理 ====================

def process_hyperliquid_data(perpetuals, min_volume=HL_MIN_VOLUME):
    """处理 Hyperliquid 数据，过滤高成交量合约"""
    filtered = []
    
    for perp in perpetuals:
        day_volume = perp.get("dayNtlVlm")
        if not day_volume:
            continue
        
        volume = float(day_volume)
        if volume < min_volume:
            continue
        
        impact_pxs = perp.get("impactPxs", [])
        bid = float(impact_pxs[0]) if impact_pxs and len(impact_pxs) > 0 else None
        ask = float(impact_pxs[1]) if impact_pxs and len(impact_pxs) > 1 else None
        
        funding_str = perp.get("funding")
        # Hyperliquid API 返回的 funding 已经是 1 小时费率（每小时结算一次）
        funding_hourly = float(funding_str) if funding_str else None
        funding_8h = funding_hourly * 8 if funding_hourly else None
        
        mid_px = perp.get("midPx")
        mark_px = perp.get("markPx")
        oracle_px = perp.get("oraclePx")
        
        contract = {
            "coin": perp.get("coin"),
            "pair": f"{perp.get('coin')}/USD",
            "dex": perp.get("dex"),  # 用于判断费率类别: "main" = 加密货币, "xyz" = HIP-3
            "bid": bid,
            "mid": float(mid_px) if mid_px else None,
            "ask": ask,
            "markPx": float(mark_px) if mark_px else None,
            "oraclePx": float(oracle_px) if oracle_px else None,
            "dayVolume_USD": round(volume, 2),
            "openInterest": perp.get("openInterest"),
            "fundingRate": {
                "rate8h": round(funding_8h * 100, 6) if funding_8h else None,
                "rateHourly": round(funding_hourly * 100, 6) if funding_hourly else None,
                "rateAnnualized": round(funding_hourly * 100 * 24 * 365, 2) if funding_hourly else None,
            } if funding_hourly is not None else None,
            "premium": perp.get("premium"),
            "maxLeverage": perp.get("maxLeverage"),
        }
        filtered.append(contract)
    
    # 按成交量排序
    filtered.sort(key=lambda x: x["dayVolume_USD"], reverse=True)
    return filtered


# ==================== Ostium 数据处理 ====================

def process_ostium_data(pairs, prices, min_oi=OS_MIN_OI):
    """处理 Ostium 数据，过滤高 OI 合约"""
    # 创建价格映射
    price_map = {}
    for price in prices:
        key = f"{price.get('from')}/{price.get('to')}"
        price_map[key] = price
    
    # 分组映射
    GROUP_INDEX_MAP = {0: "crypto", 1: "forex", 2: "commodities", 3: "stocks", 4: "indices"}
    
    filtered = []
    
    for pair in pairs:
        from_asset = pair.get("from", "")
        to_asset = pair.get("to", "")
        pair_name = f"{from_asset}/{to_asset}"
        
        # 计算 OI
        long_oi = int(pair.get("longOI", 0))
        short_oi = int(pair.get("shortOI", 0))
        total_oi = (long_oi + short_oi) / 1e18
        
        # 获取价格
        price_data = price_map.get(pair_name, {})
        mid_price = price_data.get("mid", 1.0)
        total_oi_usd = total_oi * mid_price if mid_price else 0
        
        # 过滤
        if total_oi_usd < min_oi:
            continue
        
        # 提取费率
        cur_funding_long = int(pair.get("curFundingLong", 0))
        cur_funding_short = int(pair.get("curFundingShort", 0))
        rollover_per_block = int(pair.get("rolloverFeePerBlock", 0))
        
        # 计算费率
        # Arbitrum 出块速度约 4 块/秒，每小时 = 4 * 3600 = 14400 块
        BLOCKS_PER_HOUR = 4 * 3600
        
        # Crypto 的资金费率（curFundingLong/Short 是每秒费率）
        funding_long_hourly = abs(cur_funding_long) * 3600 / 1e18 * 100 if cur_funding_long else None
        funding_short_hourly = abs(cur_funding_short) * 3600 / 1e18 * 100 if cur_funding_short else None
        
        # 非 Crypto 的隔夜费率（rolloverFeePerBlock 是每区块费率）
        rollover_hourly = abs(rollover_per_block) * BLOCKS_PER_HOUR / 1e18 * 100 if rollover_per_block else None
        
        # 获取分组
        group_index = pair.get("group", {}).get("id")
        group_name = pair.get("group", {}).get("name", "unknown")
        if group_index:
            group_name = GROUP_INDEX_MAP.get(int(group_index), group_name)
        
        is_crypto = group_name == "crypto"
        
        contract = {
            "pair": pair_name,
            "from": from_asset,
            "to": to_asset,
            "group": group_name,
            "bid": price_data.get("bid"),
            "mid": price_data.get("mid"),
            "ask": price_data.get("ask"),
            "isMarketOpen": price_data.get("isMarketOpen"),
            "totalOI_USD": round(total_oi_usd, 2),
            "longOI": pair.get("longOI"),
            "shortOI": pair.get("shortOI"),
            "fundingRate": {
                "longPayHourly": round(funding_long_hourly, 6) if funding_long_hourly else None,
                "shortPayHourly": round(funding_short_hourly, 6) if funding_short_hourly else None,
                "longPay8h": round(funding_long_hourly * 8, 6) if funding_long_hourly else None,
                "shortPay8h": round(funding_short_hourly * 8, 6) if funding_short_hourly else None,
            } if is_crypto and (funding_long_hourly or funding_short_hourly) else None,
            "rolloverRate": {
                "hourly": round(rollover_hourly, 6) if rollover_hourly else None,
                "daily": round(rollover_hourly * 24, 6) if rollover_hourly else None,
            } if not is_crypto and rollover_hourly else None,
        }
        filtered.append(contract)
    
    # 按 OI 排序
    filtered.sort(key=lambda x: x["totalOI_USD"], reverse=True)
    return filtered


# ==================== 数据刷新任务 ====================

def refresh_data():
    """刷新所有数据（保存到内存）"""
    global DATA_STORE
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"[{timestamp}] 开始刷新数据...")
    print('='*50)
    
    try:
        # 1. 获取 Hyperliquid 数据（调用子目录模块）
        print("\n[1/4] 获取 Hyperliquid 数据...")
        hl_perpetuals, _ = hl_get_all_perpetuals()
        print(f"[HL] 获取到 {len(hl_perpetuals)} 个合约")
        
        # 2. 处理 Hyperliquid 数据
        print("[2/4] 处理 Hyperliquid 数据...")
        hl_filtered = process_hyperliquid_data(hl_perpetuals)
        
        # 3. 获取 Ostium 数据（调用子目录模块）
        print("\n[3/4] 获取 Ostium 数据...")
        try:
            os_data = asyncio.run(os_fetch_all_data())
            pairs = os_data.get("pairs", [])
            prices = os_data.get("prices", [])
            print(f"[OS] 获取到 {len(pairs)} 个交易对, {len(prices)} 个价格")
        except Exception as e:
            print(f"[OS] 获取数据失败: {e}")
            pairs, prices = [], []
        
        # 4. 处理 Ostium 数据
        os_filtered = []
        if pairs:
            print("[4/4] 处理 Ostium 数据...")
            os_filtered = process_ostium_data(pairs, prices)
        else:
            print("[OS] 无数据，跳过处理")
        
        # 5. 更新内存数据（线程安全）
        with DATA_LOCK:
            DATA_STORE["hyperliquid"] = {
                "total_filtered": len(hl_filtered),
                "filter_criteria": f"24h Volume > ${HL_MIN_VOLUME:,}",
                "updated_at": timestamp,
                "contracts": hl_filtered
            }
            DATA_STORE["ostium"] = {
                "total_filtered": len(os_filtered),
                "filter_criteria": f"Total OI > ${OS_MIN_OI:,}",
                "updated_at": timestamp,
                "contracts": os_filtered
            }
        
        print(f"\n✓ 数据刷新完成")
        print(f"   Hyperliquid: {len(hl_filtered)} 个合约")
        print(f"   Ostium: {len(os_filtered)} 个合约")
        
    except Exception as e:
        print(f"\n✗ 数据刷新失败: {e}")
        import traceback
        traceback.print_exc()


def data_refresh_loop():
    """数据刷新循环（后台线程）"""
    while True:
        time.sleep(REFRESH_INTERVAL)
        refresh_data()


# ==================== HTTP 服务器 ====================

class APIHTTPHandler(BaseHTTPRequestHandler):
    """HTTP 处理器：提供静态文件和 JSON API"""
    
    def log_message(self, format, *args):
        # 只记录关键请求
        request_line = str(args[0]) if args else ""
        if any(ext in request_line for ext in ['.html', '.json', '/api/']):
            print(f"[HTTP] {request_line}")
    
    def send_json(self, data):
        """发送 JSON 响应"""
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(content)
    
    def send_file(self, filepath, content_type):
        """发送文件"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, 'File not found')
    
    def do_GET(self):
        """处理 GET 请求"""
        path = self.path.split('?')[0]  # 移除查询参数
        
        # API 端点：返回内存中的数据
        if path == '/hyperliquid_filtered.json':
            with DATA_LOCK:
                self.send_json(DATA_STORE["hyperliquid"])
            return
        
        if path == '/ostium_filtered.json':
            with DATA_LOCK:
                self.send_json(DATA_STORE["ostium"])
            return
        
        # 静态文件
        if path == '/' or path == '/index.html':
            path = '/comparison.html'
        
        # 确定文件路径和类型
        filepath = os.path.join(SCRIPT_DIR, path.lstrip('/'))
        
        content_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.ico': 'image/x-icon',
        }
        
        ext = os.path.splitext(path)[1].lower()
        content_type = content_types.get(ext, 'application/octet-stream')
        
        self.send_file(filepath, content_type)


def start_server():
    """启动 HTTP 服务器"""
    server = HTTPServer(('0.0.0.0', SERVER_PORT), APIHTTPHandler)
    
    print(f"\n🌐 HTTP 服务器已启动:")
    print(f"   本地访问: http://localhost:{SERVER_PORT}/comparison.html")
    print(f"   API 端点: /hyperliquid_filtered.json, /ostium_filtered.json")
    print(f"🔄 数据刷新间隔: {REFRESH_INTERVAL} 秒")
    print(f"💾 数据存储: 内存（不写入文件）")
    print(f"\n按 Ctrl+C 停止服务器\n")
    
    server.serve_forever()


# ==================== 主函数 ====================

def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         DEX 费率对比系统 - Hyperliquid vs Ostium          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 1. 首次数据刷新
    refresh_data()
    
    # 2. 启动后台数据刷新线程
    refresh_thread = threading.Thread(target=data_refresh_loop, daemon=True)
    refresh_thread.start()
    print(f"\n⏰ 后台数据刷新线程已启动（每 {REFRESH_INTERVAL} 秒）")
    
    # 3. 启动 HTTP 服务器（阻塞）
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")


if __name__ == "__main__":
    main()
