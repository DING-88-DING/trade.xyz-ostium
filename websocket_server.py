"""
WebSocket 服务器
实时推送 Hyperliquid 和 Ostium 数据给前端
集成套利引擎，在后端完成套利计算

运行: python websocket_server.py
"""

import sys
import subprocess

# 检查并安装依赖
def check_and_install_dependencies():
    """检查必需的依赖，如果缺失则自动安装"""
    # 包名 -> 导入名映射 (有些包的安装名和导入名不同)
    required_packages = {
        # WebSocket 服务器依赖
        'flask': 'flask',
        'flask-socketio': 'flask_socketio',
        'python-socketio': 'socketio',  # 注意：安装名是 python-socketio，但导入名是 socketio
        'flask-cors': 'flask_cors',
        # 数据源 SDK
        'hyperliquid-python-sdk': 'hyperliquid',
        'ostium-python-sdk': 'ostium_python_sdk',
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f'\n⚠️  缺少依赖包: {", ".join(missing_packages)}')
        print('📦 正在自动安装...\n')
        
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            *missing_packages, '-q'
        ])
        
        print('✅ 依赖安装完成！\n')

# 运行依赖检查
check_and_install_dependencies()

# ==================== 配置加载 ====================
# 尝试从 config.py 加载配置并注入环境变量
try:
    import os
    import config
    if hasattr(config, 'ARBITRUM_RPC_URL') and config.ARBITRUM_RPC_URL:
        os.environ['ARBITRUM_RPC_URL'] = config.ARBITRUM_RPC_URL
        print(f'[Config] 已加载 ARBITRUM_RPC_URL: {config.ARBITRUM_RPC_URL[:20]}...')
except ImportError:
    print("警告: 未找到 config.py，将使用默认 RPC")

# 导入依赖
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import asyncio
from threading import Thread, Lock
import time
import json
import os

# 导入套利引擎
from arbitrage import ArbitrageEngine

# 创建 Flask 应用，配置静态文件服务
app = Flask(__name__, 
            static_folder='.',  # 当前目录为静态文件根目录
            static_url_path='')
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)  # 允许跨域

# 创建 Socket.IO 实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 首页路由
@app.route('/')
def index():
    """返回首页"""
    return send_from_directory('.', 'comparison.html')

# ==================== 套利引擎实例 ====================
# 创建全局套利引擎实例
arbitrage_engine = ArbitrageEngine(vip_tier=0)
engine_lock = Lock()  # 线程锁，保证数据一致性

# 全局数据存储（保持兼容性）
DATA_STORE = {
    'hyperliquid': {'contracts': [], 'updated_at': ''},
    'ostium': {'contracts': [], 'updated_at': ''}
}

# 连接的客户端数量
connected_clients = 0


@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    global connected_clients
    connected_clients += 1
    print(f'[WebSocket] 客户端已连接，当前连接数: {connected_clients}')
    
    # 发送当前数据（包含套利计算结果）
    with engine_lock:
        initial_data = {
            'hyperliquid': arbitrage_engine.get_hl_data(),
            'ostium': arbitrage_engine.get_os_data(),
            'common_pairs': arbitrage_engine.get_common_pairs()
        }
    emit('initial_data', initial_data)


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    global connected_clients
    connected_clients -= 1
    print(f'[WebSocket] 客户端已断开，当前连接数: {connected_clients}')


@socketio.on('ping')
def handle_ping():
    """心跳检测"""
    emit('pong')


@socketio.on('set_vip_tier')
def handle_set_vip_tier(data):
    """
    处理前端发送的 VIP 等级变更
    
    Args:
        data: {'tier': int} VIP 等级 (0-6)
    """
    tier = data.get('tier', 0)
    print(f'[WebSocket] 收到 VIP 等级变更请求: {tier}')
    
    with engine_lock:
        arbitrage_engine.set_vip_tier(tier)
        # 重新广播套利数据
        common_pairs_data = arbitrage_engine.get_common_pairs()
    
    # 广播更新后的套利数据给所有客户端
    socketio.emit('common_pairs_update', common_pairs_data)
    print(f'[WebSocket] VIP 等级已更新为 {tier}，已重新广播套利数据')


def broadcast_data(platform, data):
    """
    广播数据给所有连接的客户端
    集成套利引擎进行计算
    """
    global DATA_STORE
    
    contracts = data.get('contracts', [])
    
    with engine_lock:
        # 更新套利引擎数据（会添加费率信息）
        if platform == 'hyperliquid':
            arbitrage_engine.update_hl_data(contracts)
            # 获取处理后的数据（包含费率和排序）
            platform_data = arbitrage_engine.get_hl_data()
        elif platform == 'ostium':
            arbitrage_engine.update_os_data(contracts)
            # 获取处理后的数据（包含费率和排序）
            platform_data = arbitrage_engine.get_os_data()
        else:
            platform_data = {
                'contracts': contracts,
                'updated_at': data.get('updated_at', '')
            }
        
        DATA_STORE[platform] = platform_data
        
        # 获取套利计算结果
        common_pairs_data = arbitrage_engine.get_common_pairs()
    
    # 广播平台数据
    socketio.emit('data_update', {
        'platform': platform,
        'data': platform_data
    })
    
    # 广播套利数据（每次数据更新都推送最新套利结果）
    socketio.emit('common_pairs_update', common_pairs_data)
    
    print(f'[WebSocket] 已广播 {platform} 数据和套利结果给 {connected_clients} 个客户端')


def start_hyperliquid_ws():
    """启动 Hyperliquid WebSocket 订阅"""
    from trade_hyperliquid.ws_client import start_hl_ws_client
    print('[HL WebSocket] 启动 Hyperliquid WebSocket 客户端...')
    
    def callback(data):
        """HL 数据回调"""
        broadcast_data('hyperliquid', data)
    
    # 在新线程中运行异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_hl_ws_client(callback))


def start_ostium_poller():
    """启动 Ostium 2秒轮询"""
    from trade_ostium.async_poller import start_os_poller
    print('[OS Poller] 启动 Ostium 轮询器...')
    
    def callback(data):
        """OS 数据回调"""
        broadcast_data('ostium', data)
    
    # 在新线程中运行异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_os_poller(callback, interval=2))


if __name__ == '__main__':
    print('=' * 50)
    print('🚀 启动实时数据服务器 (带套利引擎)')
    print('=' * 50)
    
    # 在后台线程启动数据源
    Thread(target=start_hyperliquid_ws, daemon=True).start()
    Thread(target=start_ostium_poller, daemon=True).start()
    
    # 等待数据源启动
    time.sleep(2)
    
    # 启动服务器
    print(f'\n✅ 服务器已启动!')
    print(f'✅ WebSocket: ws://localhost:8080')
    print(f'✅ 前端页面: http://localhost:8080')
    print(f'✅ 套利引擎: 已启用')
    print(f'\n📱 在浏览器打开: http://localhost:8080')
    print('\n按 Ctrl+C 停止服务器\n')
    
    # 启动 Flask + WebSocket 服务器
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
