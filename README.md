# 合约价格和资金费率对比工具

一个用于对比 Ostium 和 Trade.xyz 两个加密货币交易平台合约数据的自动化工具。

## 功能特性

- 📊 自动从两个平台获取合约数据
- 🔍 过滤 24 小时交易量大于 1M 的合约
- 💱 对比价格和资金费率差异
- 💾 保存数据到 JSON 文件
- 🌐 美观的 Web 界面展示对比结果
- ⚡ 实时数据更新(每 30 秒自动刷新)
- 🎯 自动识别套利机会

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行主程序:

```bash
python main.py
```

2. 程序会自动:

   - 从 Ostium 获取数据并保存到 `ostium_data.json`
   - 从 Trade.xyz 获取数据并保存到 `tradexyz_data.json`
   - 对比数据并保存结果到 `comparison_result.json`
   - 启动 Web 服务器(默认端口 8000)
   - 自动打开浏览器显示对比结果

3. 在浏览器中访问 `http://localhost:8000` 查看对比数据

## 文件说明

- `fetch_data.py` - 数据获取模块
- `compare_data.py` - 数据对比模块
- `main.py` - 主程序
- `index.html` - Web 展示页面
- `requirements.txt` - 依赖库列表

## 数据文件

程序运行后会生成以下 JSON 文件:

- `ostium_data.json` - Ostium 平台的合约数据
- `tradexyz_data.json` - Trade.xyz 平台的合约数据
- `comparison_result.json` - 对比结果

## 注意事项

- 首次运行可能需要较长时间来获取所有数据
- 确保网络连接稳定
- Trade.xyz 使用 WebSocket 连接,如果连接超时请重试
- 数据每 30 秒自动刷新一次

## 技术栈

- Python 3.x
- requests - HTTP 请求
- websocket-client - WebSocket 连接
- 原生 HTML/CSS/JavaScript - Web 展示

## 许可证

MIT License
