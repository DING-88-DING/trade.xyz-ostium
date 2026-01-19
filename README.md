# ⚡ DEX 费率对比系统 (Hyperliquid vs Ostium)

这是一个用于实时监控和对比 **Hyperliquid** 与 **Ostium** 两个去中心化交易所（DEX）永续合约费率、持仓量（OI）及资金费率的系统。该工具旨在帮助交易员发现套利机会，监控市场热度，并优化资金费率策略。

## 🌟 核心功能

- **实时数据监控**：
  - **Hyperliquid**：监控 24小时成交量大于设定阈值（默认 $1M）的合约。
  - **Ostium**：监控总持仓量（Total OI）大于设定阈值（默认 $1M）的合约。
- **智能跨平台对比**：
  - 自动识别两个平台的共有资产（如 BTC, ETH 等）。
  - **套利监控 (Arbitrage Monitor)**：并排显示同一种资产在两个平台的资金费率，方便发现 Funding Rate Arbitrage 机会。
- **多模式运行**：
  - **WebSocket 实时模式**：基于 `Flask-SocketIO`，实现毫秒级数据推送。
  - **HTTP 轮询模式**：基于 Python 原生 `http.server`，轻量级，适合低配置环境。
- **交互式前端 UI**：
  - **VIP 费率等级调整**：支持动态切换 VIP 0 - VIP 6 费率层级，实时重新计算预估收益。
  - **自动依赖管理**：无需手动安装繁杂依赖，启动脚本会自动检测并安装 python 库。
  - **排序与过滤**：支持按字母、成交量、OI、资金费率等多种维度排序。

## 🛠️ 安装与运行

### 1. 环境准备

确保您的系统环境满足以下要求：

- **操作系统**: Windows / macOS / Linux
- **Python 版本**: Python 3.8 或更高版本
  - 可以在终端输入 `python --version` 检查版本
- **包管理工具**: pip
  - 可以在终端输入 `pip --version` 检查

### 2. 安装依赖

本项目包含 `requirements.txt` 文件，您可以一键安装所有必需的依赖包。

**手动安装（推荐）：**
打开命令行终端（Terminal / CMD / PowerShell），进入项目根目录，运行：

```bash
pip install -r requirements.txt
```

**依赖包说明**：

- `flask`, `flask-socketio`, `python-socketio`, `flask-cors`: 用于构建 WebSocket 后端服务器。
- `hyperliquid-python-sdk`: 官方 Hyperliquid 交易与数据接口 SDK。
- `ostium-python-sdk`: 官方 Ostium 数据接口 SDK。
- `aiohttp`: 用于异步 HTTP 请求。
- `requests`: 用于同步 HTTP 请求。

### 3. 运行方式

#### A. 实时模式 (推荐 - WebSocket)

这是最佳体验模式，支持毫秒级数据推送。

1.  **启动服务器**：

    ```bash
    python websocket_server.py
    ```

    > **提示**：该脚本在启动时也会自动检查依赖，如果发现缺失会尝试自动安装。

2.  **访问页面**：
    打开浏览器访问：[http://localhost:8080](http://localhost:8080)

#### B. 轮询模式 (备选 - HTTP)

如果您只需要简单的静态展示，或者服务器资源非常有限（不支持 WebSocket），可以使用此模式。

1.  **启动脚本**：

    ```bash
    python main.py
    ```

2.  **访问页面**：
    访问：[http://localhost:8080/comparison.html](http://localhost:8080/comparison.html)
    - 该模式下数据每 **30秒** 自动刷新一次。

## 📂 项目结构

```
trade.xyz-ostium/
├── main.py                 # HTTP 轮询模式启动脚本 (轻量)
├── websocket_server.py     # WebSocket 实时模式启动脚本 (推荐)
├── comparison.html         # 前端主页面
├── config.py               # 配置文件 (API URL 等)
├── js/                     # 前端逻辑
│   ├── websocket-client.js # WebSocket 客户端逻辑
│   ├── data-loader.js      # HTTP 轮询数据加载逻辑
│   ├── arbitrage.js        # 套利计算逻辑
│   ├── fee-calculator.js   # 费率计算核心算法
│   └── ...
├── trade_hyperliquid/      # Hyperliquid 数据源模块
└── trade_ostium/           # Ostium 数据源模块
```

## ⚙️ 配置说明

您可以在 `main.py` 或 `config.py` 中修改以下参数来调整监控灵敏度：

- `HL_MIN_VOLUME`: Hyperliquid 最小 24h 成交量过滤阈值 (默认 1,000,000 USD)。
- `OS_MIN_OI`: Ostium 最小持仓量过滤阈值 (默认 1,000,000 USD)。
- `REFRESH_INTERVAL`: HTTP 轮询模式下的刷新间隔 (默认 30 秒)。

## 🧩 架构设计

- **后端**:
  - 采用 **Flask + Socket.IO** 构建实时推送服务。
  - 利用 `asyncio` 和 `threading` 实现多数据源并发采集，互不阻塞。
  - **Hyperliquid** 数据通过 WebSocket 订阅实现实时更新。
  - **Ostium** 数据通过高频轮询 (每 2 秒) 模拟实时更新。
- **前端**:
  - 原生 JavaScript (Vanilla JS) 实现，无复杂的构建流程，修改即生效。
  - CSS 变量实现深色模式和响应式布局。

## ⚠️ 注意事项

- 因为 Ostium 涉及外汇(Forex)和大宗商品(Commodities)交易，部分市场在周末可能会休市。
- 显示的资金费率已年化处理，方便直观对比。
- 本工具仅供参考，不构成投资建议。

---

_Built with ❤️ for generic trading._
