"""
跨平台打包脚本 - DEX 费率对比系统
支持 Windows (.exe) 和 Mac (.app) 打包

使用方法:
    python build.py

输出目录:
    dist/DEX费率对比系统/  (Windows)
    dist/DEX费率对比系统.app  (Mac)
"""

import subprocess
import sys
import os
import shutil
import platform

# ==================== 配置 ====================
APP_NAME = 'DEX费率对比系统'
ENTRY_SCRIPT = 'launcher.py'
ICON_WINDOWS = None  # 可选: 'icon.ico'
ICON_MAC = None  # 可选: 'icon.icns'

# 需要打包的数据文件和目录
DATA_FILES = [
    # (源路径, 目标路径)
    ('comparison.html', '.'),
    ('comparison-http.html', '.'),
    ('css', 'css'),
    ('js', 'js'),
    ('config.example.py', '.'),
]

# 隐式导入 (PyInstaller 无法自动检测的模块)
HIDDEN_IMPORTS = [
    # Flask & SocketIO
    'flask',
    'flask_socketio',
    'flask_cors',
    'engineio.async_drivers.threading',
    'socketio',
    
    # SDK 模块
    'hyperliquid',
    'hyperliquid.info',
    'hyperliquid.utils',
    'ostium_python_sdk',
    
    # 项目模块
    'arbitrage',
    'arbitrage.arbitrage_engine',
    'arbitrage.arbitrage_calculator',
    'arbitrage.fee_calculator',
    'arbitrage.fee_config',
    'arbitrage.notifier',
    
    'trade_hyperliquid',
    'trade_hyperliquid.ws_client',
    'trade_hyperliquid.inspect_hyperliquid',
    'trade_hyperliquid.process_hyperliquid',
    
    'trade_ostium',
    'trade_ostium.async_poller',
    'trade_ostium.inspect_ostium',
    'trade_ostium.process_ostium',
    
    # 通知模块
    'plyer',
    'plyer.platforms.win.notification',
    'plyer.platforms.macosx.notification',
    
    # 异步支持
    'aiohttp',
    'asyncio',
    
    # 其他依赖
    'requests',
    'websockets',
    'gql',
    'gql.transport.aiohttp',
    
    # SSL 证书支持
    'certifi',
    'ssl',
]


def check_pyinstaller():
    """检查并安装 PyInstaller"""
    try:
        import PyInstaller
        print(f'✅ PyInstaller 版本: {PyInstaller.__version__}')
    except ImportError:
        print('📦 正在安装 PyInstaller...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller', '-q'])
        print('✅ PyInstaller 安装完成')


def clean_build():
    """清理旧的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = [f'{APP_NAME}.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f'🗑️  清理目录: {dir_name}')
            shutil.rmtree(dir_name)
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            print(f'🗑️  清理文件: {file_name}')
            os.remove(file_name)


def build_command():
    """构建 PyInstaller 命令"""
    current_os = platform.system()
    print(f'🖥️  当前系统: {current_os}')
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--noconfirm',  # 覆盖输出目录
        '--clean',  # 清理缓存
    ]
    
    # 平台特定配置
    if current_os == 'Windows':
        cmd.append('--console')  # 显示控制台窗口
        if ICON_WINDOWS and os.path.exists(ICON_WINDOWS):
            cmd.extend(['--icon', ICON_WINDOWS])
    elif current_os == 'Darwin':  # macOS
        cmd.append('--windowed')  # Mac 应用不显示终端
        cmd.append('--osx-bundle-identifier')
        cmd.append('com.dex.fee-comparison')
        if ICON_MAC and os.path.exists(ICON_MAC):
            cmd.extend(['--icon', ICON_MAC])
    else:  # Linux
        cmd.append('--console')
    
    # 添加数据文件
    separator = ';' if current_os == 'Windows' else ':'
    for src, dst in DATA_FILES:
        if os.path.exists(src):
            cmd.extend(['--add-data', f'{src}{separator}{dst}'])
        else:
            print(f'⚠️  警告: 文件不存在 {src}')
    
    # 添加隐式导入
    for module in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', module])
    
    # ⚠️ 安全：排除 config 模块，防止 API Key 被打包
    # 程序运行时会从输出目录读取用户创建的 config.py
    cmd.extend(['--exclude-module', 'config'])
    
    # 添加 certifi SSL 证书文件（修复 SSL 证书验证失败问题）
    try:
        import certifi
        cert_path = certifi.where()
        cert_dir = os.path.dirname(cert_path)
        cmd.extend(['--add-data', f'{cert_path}{separator}certifi'])
        print(f'📜 添加 SSL 证书: {cert_path}')
    except ImportError:
        print('⚠️  警告: certifi 未安装，SSL 可能无法正常工作')
    
    # 入口脚本
    cmd.append(ENTRY_SCRIPT)
    
    return cmd


def copy_config_files():
    """复制配置文件到输出目录"""
    current_os = platform.system()
    
    if current_os == 'Darwin':
        output_dir = f'dist'
    else:
        output_dir = f'dist/{APP_NAME}'
    
    if not os.path.exists(output_dir):
        print(f'⚠️  输出目录不存在: {output_dir}')
        return
    
    # 复制 config.example.py
    if os.path.exists('config.example.py'):
        shutil.copy('config.example.py', output_dir)
        print(f'📄 已复制: config.example.py -> {output_dir}')
    
    # 创建使用说明
    readme_content = f"""
{'='*50}
⚡ DEX 费率对比系统 - 使用说明
{'='*50}

📋 使用步骤:

1. 双击运行程序:
   - Windows: DEX费率对比系统.exe
   - Mac: DEX费率对比系统.app

2. 浏览器将自动打开 http://localhost:8080

🔧 配置 RPC (可选但推荐):

   不配置也能运行（使用公共节点），但建议配置私有 RPC 获得更稳定体验：
   
   1. 复制 config.example.py 为 config.py
   2. 编辑 config.py，填入您的 Arbitrum RPC URL
      - 推荐从 Alchemy 或 Infura 获取免费 API Key
      - 示例: https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY

⚠️ 注意事项:
- 确保网络连接正常
- 部分市场周末可能休市
- 按 Ctrl+C 可停止服务器

{'='*50}
"""
    
    readme_path = os.path.join(output_dir, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f'📄 已创建: README.txt -> {output_dir}')


def main():
    """主函数"""
    print('=' * 50)
    print('🔨 DEX 费率对比系统 - 打包工具')
    print('=' * 50)
    
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f'📁 工作目录: {script_dir}')
    
    # 检查入口脚本
    if not os.path.exists(ENTRY_SCRIPT):
        print(f'❌ 错误: 入口脚本不存在 {ENTRY_SCRIPT}')
        sys.exit(1)
    
    # 检查 PyInstaller
    check_pyinstaller()
    
    # 清理旧构建
    clean_build()
    
    # 构建命令
    cmd = build_command()
    print(f'\n📦 执行打包命令:')
    print(' '.join(cmd[:10]) + ' ...')
    
    # 执行打包
    print('\n' + '=' * 50)
    print('🚀 开始打包 (这可能需要几分钟)...')
    print('=' * 50 + '\n')
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f'\n❌ 打包失败: {e}')
        sys.exit(1)
    
    # 复制配置文件
    print('\n📋 复制配置文件...')
    copy_config_files()
    
    # 完成
    current_os = platform.system()
    if current_os == 'Darwin':
        output_path = f'dist/{APP_NAME}.app'
    else:
        output_path = f'dist/{APP_NAME}/{APP_NAME}.exe'
    
    print('\n' + '=' * 50)
    print('✅ 打包完成!')
    print('=' * 50)
    print(f'\n📂 输出路径: {output_path}')
    print(f'\n💡 使用方法:')
    print(f'   1. 进入 dist/{APP_NAME}/ 目录')
    print(f'   2. 复制 config.example.py 为 config.py')
    print(f'   3. 编辑 config.py 填入 RPC URL')
    print(f'   4. 双击运行 {APP_NAME}{".exe" if current_os == "Windows" else ".app"}')


if __name__ == '__main__':
    main()
