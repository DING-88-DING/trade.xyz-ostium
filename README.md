# ⚡ DEX 费率对比系统 (Hyperliquid vs Ostium)

这是一个用于实时监控和对比 **Hyperliquid** 与 **Ostium** 两个去中心化交易所（DEX）永续合约费率、持仓量（OI）及资金费率的系统。该工具旨在帮助交易员发现套利机会，监控市场热度，并优化资金费率策略。

## 🌟 核心功能

- **实时数据监控**：
  - **Hyperliquid**：监控 24小时成交量大于设定阈值（默认 $1M）的合约。
  - **Ostium**：监控总持仓量（Total OI）大于设定阈值（默认 $1M）的合约。
- **智能跨平台对比**：
  - 自动识别两个平台的共有资产（如 BTC, ETH, GOLD 等）。
  - **套利监控 (Arbitrage Monitor)**：并排显示同一种资产在两个平台的资金费率，方便发现 Funding Rate Arbitrage 机会。
- **多模式运行**：
  - **WebSocket 实时模式**：基于 `Flask-SocketIO`，实现毫秒级数据推送。
  - **HTTP 轮询模式**：基于 Python 原生 `http.server`，轻量级，适合低配置环境。
- **交互式前端 UI**：
  - **VIP 费率等级调整**：支持动态切换 VIP 0 - VIP 6 费率层级，实时重新计算预估收益。
  - **自动依赖管理**：无需手动安装繁杂依赖，启动脚本会自动检测并安装 python 库。
  - **排序与过滤**：支持按字母、成交量、OI、资金费率等多种维度排序。

## 🏗️ 项目架构

```
trade.xyz-ostium/
├── main.py                    # HTTP 轮询模式启动脚本 (每5秒刷新)
├── websocket_server.py        # WebSocket 实时模式启动脚本 (推荐，毫秒级推送)
├── comparison.html            # 前端主页面 - WebSocket 模式
├── comparison-http.html       # 前端主页面 - HTTP 轮询模式
├── config.py                  # 配置文件 (RPC URL 等)
├── config.example.py          # 配置文件模板
├── requirements.txt           # Python 依赖列表
│
├── arbitrage/                 # 🆕 套利引擎模块 (后端计算)
│   ├── __init__.py            # 模块入口
│   ├── arbitrage_engine.py    # 套利引擎核心类
│   ├── arbitrage_calculator.py# 套利计算器
│   ├── fee_calculator.py      # 费率计算器
│   ├── fee_config.py          # 费率配置表 (VIP 0-6, 预期收敛价差)
│   └── notifier.py            # 🆕 桌面通知模块 (plyer)
│
├── trade_hyperliquid/         # Hyperliquid 数据源模块
│   ├── ws_client.py           # WebSocket 实时订阅客户端
│   ├── inspect_hyperliquid.py # REST API 数据获取
│   ├── process_hyperliquid.py # 数据处理逻辑
│   └── DATA_SCHEMA.md         # 数据结构文档
│
├── trade_ostium/              # Ostium 数据源模块
│   ├── async_poller.py        # 异步轮询器（每2秒）
│   ├── inspect_ostium.py      # Subgraph 数据获取
│   ├── process_ostium.py      # 数据处理逻辑
│   └── DATA_SCHEMA.md         # 数据结构文档
│
├── js/                        # 前端逻辑模块
│   ├── state.js               # 全局状态管理
│   ├── formatters.js          # 数据格式化工具
│   ├── renderers.js           # UI 渲染
│   ├── ui-controls.js         # 用户交互控制
│   ├── websocket-client.js    # WebSocket 客户端
│   ├── http-client.js         # HTTP 轮询客户端
│   ├── main-websocket.js      # WebSocket 模式入口
│   └── main-http.js           # HTTP 模式入口
│
└── css/                       # 样式文件
    └── comparison.css         # 主页面样式（深色模式）
```

## 🔧 技术栈

| 组件           | 技术                                           |
| -------------- | ---------------------------------------------- |
| **后端**       | Python 3.8+, Flask + Flask-SocketIO            |
| **数据源 SDK** | `hyperliquid-python-sdk`, `ostium-python-sdk`  |
| **异步处理**   | `asyncio`, `threading`, `websockets`           |
| **前端**       | 原生 JavaScript (Vanilla JS)，CSS 变量深色模式 |
| **区块链 RPC** | Arbitrum Mainnet（用于 Ostium SDK）            |

## 📡 数据流设计

```
┌─────────────────────────────────────────────────────────────────┐
│                          数据源层                                │
├─────────────────────────────┬───────────────────────────────────┤
│   Hyperliquid API           │   Ostium Subgraph (Arbitrum)      │
│   (WebSocket 订阅)           │   (每2秒轮询)                      │
└─────────────┬───────────────┴───────────────┬───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          后端处理层                              │
├─────────────────────────────┬───────────────────────────────────┤
│   ws_client.py              │   async_poller.py                 │
│   (Hyperliquid WebSocket)   │   (Ostium 异步轮询器)              │
└─────────────┬───────────────┴───────────────┬───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              websocket_server.py (Flask-SocketIO)               │
│              数据聚合 + 实时广播                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼ Socket.IO 推送
┌─────────────────────────────────────────────────────────────────┐
│                          前端展示层                              │
├─────────────────────────────────────────────────────────────────┤
│   comparison.html                                               │
│   ├── Hyperliquid 列表 (左栏)                                    │
│   ├── Arbitrage Monitor (中栏) - 共有资产对比                     │
│   └── Ostium 列表 (右栏)                                         │
└─────────────────────────────────────────────────────────────────┘
```

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

| 包名                                    | 用途                         |
| --------------------------------------- | ---------------------------- |
| `flask`, `flask-socketio`, `flask-cors` | WebSocket 后端服务器         |
| `python-socketio`                       | Socket.IO 协议支持           |
| `hyperliquid-python-sdk`                | Hyperliquid 官方数据接口 SDK |
| `ostium-python-sdk`                     | Ostium 官方数据接口 SDK      |
| `aiohttp`                               | 异步 HTTP 请求               |
| `requests`                              | 同步 HTTP 请求               |
| `websockets`                            | WebSocket 客户端             |

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
    访问：[http://localhost:8080/](http://localhost:8080/)
    - 该模式下数据每 **5秒** 自动刷新一次。
    - 注意：HTTP 模式不支持实时 VIP 等级切换，需修改 `main.py` 后重启。

## ⚙️ 配置说明

在使用本系统之前，**您必须配置 Arbitrum RPC URL**，因为 Ostium SDK 依赖链上数据。

### 1. 复制配置模板

将 `config.example.py` 复制为 `config.py` (如果尚未存在)。

### 2. 编辑配置文件 (`config.py`)

```python
# Arbitrum RPC URL（用于 Ostium SDK）
# 推荐从 Alchemy 或 Infura 获取免费的 API Key
ARBITRUM_RPC_URL = "https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY"

# Hyperliquid API URL
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"
```

> **重要**: 如果不配置有效的 `ARBITRUM_RPC_URL`，Ostium 数据将无法加载！

### 3. 可选参数调整

您还可以修改以下参数来调整监控灵敏度（在对应文件中）：

| 参数               | 文件                             | 默认值        | 说明                                |
| ------------------ | -------------------------------- | ------------- | ----------------------------------- |
| `HL_MIN_VOLUME`    | `main.py`                        | 1,000,000 USD | Hyperliquid 最小 24h 成交量过滤阈值 |
| `OS_MIN_OI`        | `main.py`                        | 1,000,000 USD | Ostium 最小持仓量过滤阈值           |
| `REFRESH_INTERVAL` | `main.py`                        | 5 秒          | HTTP 轮询模式下后端刷新间隔         |
| `pollInterval`     | `js/http-client.js`              | 5000 ms       | HTTP 轮询模式下前端刷新间隔         |
| `MIN_VOLUME_USD`   | `trade_hyperliquid/ws_client.py` | 1,000,000 USD | WebSocket 模式下的过滤阈值          |
| `MIN_OI_USD`       | `trade_ostium/async_poller.py`   | 1,000,000 USD | Ostium 轮询器的过滤阈值             |

### 4. RPC 连接优先级

系统按照以下优先级连接 Arbitrum RPC 节点：

1.  **环境变量** (`ARBITRUM_RPC_URL`)：优先级最高。
2.  **配置文件** (`config.py`)：如果环境变量未设置，尝试读取此文件。
3.  **默认公用节点**：如果以上均未配置，使用默认公共节点：
    ```
    https://arb1.arbitrum.io/rpc
    ```
    > ⚠️ 该公共节点可能不稳定，请求频率高时可能会被限流，建议配置私有 RPC。

> **修复日志 (2026-01-20)**: 修复了 `websocket_server.py` 未正确加载 `config.py` 导致 `async_poller.py` 无法获取私有 RPC 节点的问题。现在程序会自动将配置注入环境变量。

## 📊 数据逻辑与费率说明

### 1. 资产匹配 (Name Mapping)

系统会自动处理不同交易所的命名差异，以确保正确对比：

| 资产 | Hyperliquid 名称 | Ostium 名称 |
| ---- | ---------------- | ----------- |
| 黄金 | GOLD             | XAU         |
| 白银 | SILVER           | XAG         |
| 铜   | COPPER           | HG          |
| 纳指 | XYZ100           | NDX         |

### 2. 费率计算 (Fee Schedule)

本系统内置了详细的费率表（可在 `js/config.js` 中查看和修改）：

**Hyperliquid**:

- 区分 **VIP 0 - VIP 6** 等级
- 区分 **Taker** 和 **Maker** 费率
- 区分 **Main** (Crypto) 和 **HIP-3** (High Impact Perps - Forex/Commodities) 资产类别
- _默认配置_: 包含了 4% 的 Referral 折扣

**Ostium**:

- **Crypto**: 采用 Maker/Taker 机制 (Maker 3bps, Taker 10bps)
- **Forex/Commodities**: 采用固定开仓费
  - Forex: 3 bps
  - Gold (XAU): 3 bps
  - Silver (XAG): 15 bps
  - Oil (CL): 10 bps
- **其他费用**: 包含 $0.10 的预言机费用 (Oracle Fee)

### 3. 套利计算逻辑

套利计算模块 (`js/arbitrage.js`) 支持两种费率模式：

| 模式      | 说明                                      |
| --------- | ----------------------------------------- |
| **Maker** | 使用 mid 价格计算，假设挂单成交           |
| **Taker** | 使用 bid/ask 价格计算，反映市价单真实成本 |

计算内容包括：

- **价差套利**：当前价差 vs 回本所需价差
- **资金费率套利**：根据费率差异计算回本时间
- **综合套利**：价差收益 + 资金费率收益的组合计算

> 🆕 **后端套利计算**：套利逻辑已迁移到后端 `arbitrage/` 模块，确保费率计算精度 (支持 0.00768% 精度显示)。

**默认假设**（可在 `js/config.js` 中修改）：

- **仓位大小**: $1,000 USD
- **资金费率**: 假设当前费率在未来 12 小时内保持不变

## 💡 核心模块说明

### trade_hyperliquid 模块

| 文件                     | 功能                                                   |
| ------------------------ | ------------------------------------------------------ |
| `ws_client.py`           | WebSocket 客户端，订阅 `allDexsAssetCtxs` 获取实时数据 |
| `inspect_hyperliquid.py` | REST API 调用，获取合约元数据                          |
| `process_hyperliquid.py` | 数据处理和格式化                                       |

**数据特点**：

- 支持主站加密货币 + xyz DEX（外汇/大宗商品）
- WebSocket 订阅实现毫秒级更新

### trade_ostium 模块

| 文件                | 功能                            |
| ------------------- | ------------------------------- |
| `async_poller.py`   | 异步轮询器，每 2 秒获取一次数据 |
| `inspect_ostium.py` | Subgraph 查询接口               |
| `process_ostium.py` | 数据处理和格式化                |

**数据特点**：

- 通过 `ostium-python-sdk` 连接 Subgraph
- 支持 Crypto、Forex、Commodities、Stocks、Indices 五大类资产
- 区分资金费率（Crypto）和隔夜费率（传统资产）

## 🧩 前端模块说明

| 文件                  | 功能                               |
| --------------------- | ---------------------------------- |
| `state.js`            | 全局状态管理（数据缓存）           |
| `formatters.js`       | 数字格式化、时间格式化等工具函数   |
| `renderers.js`        | UI 渲染逻辑（卡片、列表渲染）      |
| `ui-controls.js`      | 用户交互控制（搜索过滤等）         |
| `websocket-client.js` | WebSocket 客户端，处理实时数据推送 |
| `http-client.js`      | HTTP 轮询客户端，定时获取数据      |
| `main-websocket.js`   | WebSocket 模式入口                 |
| `main-http.js`        | HTTP 模式入口                      |

> 📝 **注意**：套利计算和费率计算已迁移到后端 `arbitrage/` 模块。

### arbitrage 模块 (🆕 后端套利引擎)

| 文件                      | 功能                                        |
| ------------------------- | ------------------------------------------- |
| `arbitrage_engine.py`     | 套利引擎核心类，整合数据采集和套利计算      |
| `arbitrage_calculator.py` | 套利计算器，计算价差/费率/综合套利          |
| `fee_calculator.py`       | 费率计算器，根据 VIP 等级和资产类型计算费率 |
| `fee_config.py`           | 费率配置表 (VIP 0-6, Referral 折扣等)       |

## ⚠️ 注意事项

1. **RPC 配置必须**：需要配置有效的 `ARBITRUM_RPC_URL`（从 Alchemy/Infura 获取），否则 Ostium 数据无法加载
2. **市场休市**：因为 Ostium 涉及外汇 (Forex) 和大宗商品 (Commodities) 交易，部分市场在周末可能会休市
3. **费率已年化**：显示的资金费率已年化处理，方便直观对比
4. **仅供参考**：本工具仅供参考，不构成投资建议

## 📝 更新日志

### 2026-01-22

- 🆕 **后端套利引擎**：新增 `arbitrage/` 模块，将套利计算逻辑迁移到后端
- 🆕 **HTTP 轮询模式完善**：`main.py` 现已集成 ArbitrageEngine，支持套利数据
- 🆕 **前端 HTTP 客户端**：新增 `http-client.js` 和 `comparison-http.html`
- 🆕 **桌面通知功能**：新增 `arbitrage/notifier.py` 模块
  - 使用 `plyer` 库实现跨平台桌面通知（Windows Toast / Mac Notification Center）
  - 监控资产：GOLD、SILVER、COPPER、XYZ100
  - 1 分钟冷却防重复通知
  - Windows 平台支持音效提示
- 🆕 **预期收敛价差 (Expected Spread)**：
  - 配置位置：`arbitrage/fee_config.py` → `ARBITRAGE_CONFIG['expected_spread']`
  - COPPER: $0.002，XYZ100: $10（价差通常不会收敛到 0）
  - 新增字段：`profitableSpread = 当前价差 - 预期收敛价差`
- 🆕 **调整后判断（严格模式）**：
  - `adjustedSpreadCanProfit`：可盈利价差 ≥ 回本价差
  - 盈利图标 💰 和桌面通知仅在 `adjustedSpreadCanProfit = true` 时触发
  - 前端显示格式：`$22.38/$16.79($26.79)` = 当前/回本(预期+回本)
- 修复 HL 费率精度问题：`round(fee, 4)` 改为 `round(fee, 6)`，确保能显示 0.00768% 等精度
- 前端费率显示精度优化：`toFixed(3)` 改为 `toFixed(5)`
- 统一前后端轮询间隔为 5 秒

### 2026-01-20

- 修复 `websocket_server.py` 未正确加载 `config.py` 的问题
- 优化 `async_poller.py` RPC 配置读取逻辑
- 更新 README 文档结构

---

_Built with ❤️ for crypto trading._
