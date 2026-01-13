# -*- coding: utf-8 -*-
"""
主程序
整合数据获取、对比和展示功能
"""

import json
import time
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

from fetch_data import OstiumFetcher, TradeXYZFetcher, filter_by_volume, save_to_json
from compare_data import match_contracts, generate_comparison_report, save_comparison_result


class ComparisonHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP处理器,用于提供API接口"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/comparison':
            # 返回对比数据的API
            try:
                with open('comparison_result.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Comparison data not found')
        else:
            # 其他请求使用默认处理
            super().do_GET()
    
    def log_message(self, format, *args):
        """禁用日志输出"""
        pass


def fetch_all_data():
    """获取所有平台的数据"""
    print("=" * 60)
    print("开始获取数据...")
    print("=" * 60)
    
    # 获取 Ostium 数据
    print("\n[1/2] 从 Ostium 获取数据")
    ostium_fetcher = OstiumFetcher()
    ostium_data = ostium_fetcher.fetch()
    # 先保存原始数据到JSON
    save_to_json(ostium_data, "ostium_data.json")
    # 再进行过滤用于对比
    ostium_filtered = filter_by_volume(ostium_data, min_volume=1000000)
    
    # 获取 Trade.xyz 数据
    print("\n[2/2] 从 Trade.xyz 获取数据")
    tradexyz_fetcher = TradeXYZFetcher()
    tradexyz_data = tradexyz_fetcher.fetch(timeout=15)
    # 先保存原始数据到JSON
    save_to_json(tradexyz_data, "tradexyz_data.json")
    # 再进行过滤用于对比
    tradexyz_filtered = filter_by_volume(tradexyz_data, min_volume=1000000)
    
    return ostium_filtered, tradexyz_filtered


def compare_data(ostium_data, tradexyz_data):
    """对比数据"""
    print("\n" + "=" * 60)
    print("开始对比数据...")
    print("=" * 60)
    
    # 匹配合约
    matched = match_contracts(ostium_data, tradexyz_data)
    
    # 生成报告
    report = generate_comparison_report(matched)
    
    print(f"\n对比完成!")
    print(f"- 匹配成功: {report['total_matched']} 个合约")
    print(f"- 套利机会: {report['arbitrage_opportunities']} 个")
    
    # 保存结果
    save_comparison_result(report)
    
    return report


def start_web_server(port=8000):
    """启动Web服务器"""
    try:
        handler = ComparisonHTTPHandler
        httpd = socketserver.TCPServer(("", port), handler)
        
        print(f"\n" + "=" * 60)
        print(f"Web服务器已启动: http://localhost:{port}")
        print(f"=" * 60)
        print(f"\n请在浏览器中访问 http://localhost:{port} 查看对比结果")
        print("按 Ctrl+C 停止服务器\n")
        
        # 自动打开浏览器
        threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{port}')).start()
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        httpd.shutdown()
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"\n错误: 端口 {port} 已被占用,请关闭占用该端口的程序或使用其他端口")
        else:
            print(f"\n启动服务器失败: {e}")


def main():
    """主函数"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "合约价格和资金费率对比工具" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    
    try:
        # 1. 获取数据
        ostium_data, tradexyz_data = fetch_all_data()
        
        if not ostium_data or not tradexyz_data:
            print("\n警告: 某些平台的数据获取失败,结果可能不完整")
        
        # 2. 对比数据
        report = compare_data(list(ostium_data), tradexyz_data)
        
        # 3. 启动Web服务器
        start_web_server(port=8000)
        
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
