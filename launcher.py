"""
启动器 - DEX 费率对比系统
用于 PyInstaller 打包的入口脚本
自动打开浏览器访问前端页面

运行: python launcher.py
"""

import sys
import os
import webbrowser
import threading
import time

# ==================== 路径配置 ====================
def get_base_path():
    """
    获取基础路径
    PyInstaller 打包后 sys._MEIPASS 指向临时解压目录
    开发模式下使用当前脚本所在目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        return sys._MEIPASS
    else:
        # 开发模式
        return os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为基础路径
BASE_PATH = get_base_path()
os.chdir(BASE_PATH)

# 添加基础路径到 Python 路径
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# ==================== SSL 证书配置 ====================
# PyInstaller 打包后需要手动设置证书路径
def setup_ssl_certificates():
    """设置 SSL 证书路径，解决打包后 HTTPS 连接问题"""
    if getattr(sys, 'frozen', False):
        # 打包模式：查找打包的证书文件
        cert_path = os.path.join(BASE_PATH, 'certifi', 'cacert.pem')
        if os.path.exists(cert_path):
            os.environ['SSL_CERT_FILE'] = cert_path
            os.environ['REQUESTS_CA_BUNDLE'] = cert_path
            print(f'🔐 SSL 证书: {cert_path}')
        else:
            print('⚠️ 未找到 SSL 证书文件，HTTPS 可能无法正常工作')
    else:
        # 开发模式：使用 certifi 包
        try:
            import certifi
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        except ImportError:
            pass

# 初始化 SSL 证书
setup_ssl_certificates()


def open_browser_delayed(url, delay=2):
    """
    延迟打开浏览器
    等待服务器完全启动后再打开
    
    Args:
        url: 要打开的 URL
        delay: 延迟秒数
    """
    time.sleep(delay)
    print(f'\n🌐 正在打开浏览器: {url}')
    webbrowser.open(url)


def main():
    """主函数 - 启动服务器并打开浏览器"""
    print('=' * 50)
    print('⚡ DEX 费率对比系统')
    print('=' * 50)
    print(f'📁 基础路径: {BASE_PATH}')
    
    # 在后台线程中延迟打开浏览器
    browser_thread = threading.Thread(
        target=open_browser_delayed,
        args=('http://localhost:8080', 3),
        daemon=True
    )
    browser_thread.start()
    
    try:
        # 导入并运行 WebSocket 服务器
        from websocket_server import run_server
        run_server()
        
    except ImportError as e:
        print(f'\n❌ 导入错误: {e}')
        print('请确保所有依赖已正确安装')
        input('\n按回车键退出...')
        sys.exit(1)
        
    except KeyboardInterrupt:
        print('\n\n👋 服务器已停止')
        
    except Exception as e:
        print(f'\n❌ 运行错误: {e}')
        import traceback
        traceback.print_exc()
        input('\n按回车键退出...')
        sys.exit(1)


if __name__ == '__main__':
    main()
