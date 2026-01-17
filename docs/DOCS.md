# 项目参考文档

本文档记录了 DEX 费率对比系统所使用的外部 API、SDK 和参考资料。

---

## 📦 SDK 依赖

### Hyperliquid Python SDK

- **PyPI**: [hyperliquid-python-sdk](https://pypi.org/project/hyperliquid-python-sdk/)
- **GitHub**: [https://github.com/hyperliquid-dex/hyperliquid-python-sdk](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)
- **安装**: `pip install hyperliquid-python-sdk`

### Ostium Python SDK

- **GitHub**: [https://github.com/0xOstium/ostium-python-sdk](https://github.com/0xOstium/ostium-python-sdk)
- **安装**: `pip install ostium-python-sdk`

---

## 📚 API 文档

### Hyperliquid

| 类型             | 链接                                                                                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **官方文档**     | [https://hyperliquid.gitbook.io/hyperliquid-docs](https://hyperliquid.gitbook.io/hyperliquid-docs)                                                                   |
| **Info API**     | [https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) |
| **API Base URL** | `https://api.hyperliquid.xyz`                                                                                                                                        |

#### 常用 API 端点

```
POST /info
{
  "type": "meta"           # 获取所有永续合约元数据
  "type": "allMids"        # 获取所有合约中间价
  "type": "metaAndAssetCtxs" # 获取合约元数据和上下文（含资金费率）
  "type": "spotMeta"       # 获取现货元数据
  "type": "perpDexs"       # 获取 Builder DEX 列表
}
```

### Ostium

| 类型           | 链接                                                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **官方网站**   | [https://ostium.io](https://ostium.io)                                                                                               |
| **官方文档**   | [https://ostium-labs.gitbook.io/ostium-docs](https://ostium-labs.gitbook.io/ostium-docs)                                             |
| **API & SDK**  | [https://ostium-labs.gitbook.io/ostium-docs/developer/api-and-sdk](https://ostium-labs.gitbook.io/ostium-docs/developer/api-and-sdk) |
| **SDK GitHub** | [https://github.com/0xOstium/ostium-python-sdk](https://github.com/0xOstium/ostium-python-sdk)                                       |
| **网络配置**   | Arbitrum Mainnet                                                                                                                     |

#### SDK 使用示例

```python
from ostium_python_sdk import OstiumSDK
from ostium_python_sdk.config import NetworkConfig

config = NetworkConfig.mainnet()
sdk = OstiumSDK(config, rpc_url="YOUR_ARBITRUM_RPC_URL")

# 获取所有交易对
pairs = await sdk.get_pairs()

# 获取价格
prices = await sdk.get_prices()
```

---

## 🔧 其他依赖

| 包名           | 用途       | 链接                                                                   |
| -------------- | ---------- | ---------------------------------------------------------------------- |
| `requests`     | HTTP 请求  | [https://docs.python-requests.org](https://docs.python-requests.org)   |
| `Flask` (可选) | Web 服务器 | [https://flask.palletsprojects.com](https://flask.palletsprojects.com) |

---

## 🌐 RPC 节点

项目需要 Arbitrum RPC 节点来连接 Ostium 合约：

| 提供商        | 链接                                                   |
| ------------- | ------------------------------------------------------ |
| **Alchemy**   | [https://www.alchemy.com](https://www.alchemy.com)     |
| **Infura**    | [https://infura.io](https://infura.io)                 |
| **QuickNode** | [https://www.quicknode.com](https://www.quicknode.com) |
| **公共节点**  | `https://arb1.arbitrum.io/rpc` (有速率限制)            |

---

## 📁 项目结构

```
trade.xyz-ostium/
├── main.py                    # 主程序入口
├── comparison.html            # 前端对比界面
├── config.py                  # 配置文件 (API Key 等)
├── requirements.txt           # Python 依赖
├── DOCS.md                    # 本文档
│
├── hyperliquid/               # Hyperliquid 数据模块
│   ├── inspect_hyperliquid.py # 数据获取
│   └── process_hyperliquid.py # 数据处理
│
└── ostium/                    # Ostium 数据模块
    ├── inspect_ostium.py      # 数据获取
    ├── process_ostium.py      # 数据处理
    └── DATA_SCHEMA.md         # 数据结构文档
```

---

## 📝 更新日志

- **2026-01-17**: 初始版本
