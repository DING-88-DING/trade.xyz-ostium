# Ostium 数据结构说明

本文档说明 Ostium 相关 JSON 文件的字段含义。

---

## ostium_response.json

原始 SDK 响应数据，由 `inspect_ostium.py` 生成。

```jsonc
{
  "pairs": [               // 所有交易对列表
    {
      "id": "0",           // 交易对 ID
      "from": "BTC",       // 基础资产
      "to": "USD",         // 报价资产
      "feed": "0x00039d...", // Pyth 价格预言机 Feed ID

      // === 资产分类 ===
      "group": {
        "id": "0",
        "name": "crypto",      // 资产类别（crypto/forex/commodities/stocks/indices）
        "minLeverage": "100",  // 最小杠杆（除以 100，如 100 = 1x）
        "maxLeverage": "10000" // 最大杠杆（除以 100，如 10000 = 100x）
      },

      // === 持仓量（原始值，需除以 1e18）===
      "longOI": "16190118096356189197",   // 多头持仓量（币数量 × 1e18）
      "shortOI": "19987432486160506187",  // 空头持仓量（币数量 × 1e18）
      "maxOI": "10000000000000",          // 最大持仓量上限

      // === 资金费率（仅 crypto 资产）===
      "curFundingLong": "2973925102",    // 多头每秒费率（正数 = 多头付费）
      "curFundingShort": "-2416694579",  // 空头每秒费率（负数 = 空头收费）
      "maxFundingFeePerBlock": "7610350000", // 最大资金费率
      "lastFundingRate": "740836496",    // 上次结算的费率
      "lastFundingBlock": "419641384",   // 上次结算的区块

      // === 隔夜费率（非 crypto 资产）===
      "rolloverFeePerBlock": "0",        // 每区块隔夜费（crypto 为 0）
      "curRollover": "0",                // 当前累积隔夜费
      "lastRolloverBlock": "390299858",  // 上次结算的区块

      // === 手续费（基点，需除以 1e6）===
      "makerFeeP": "30000",   // Maker 手续费（30000 = 0.03%）
      "takerFeeP": "100000",  // Taker 手续费（100000 = 0.1%）

      // === 其他 ===
      "overnightMaxLeverage": "0",  // 隔夜最大杠杆（0 = 无限制）
      "totalOpenTrades": "182",     // 当前开仓数量
      "lastTradePrice": "90312375737906340000000" // 最后成交价格（原始值）
    }
  ],

  "prices": [              // 实时价格列表
    {
      "from": "BTC",
      "to": "USD",
      "bid": 94939.15,     // 买一价
      "ask": 94947.61,     // 卖一价
      "mid": 94943.38,     // 中间价
      "isMarketOpen": true // 市场是否开放（股票等有交易时间）
    }
  ],

  "analysis": {...}        // 分析结果（分类统计等）
}
```

---

## ostium_filtered.json

过滤并处理后的数据，由 `process_ostium.py` 生成。

```jsonc
{
  "total_filtered": 13, // 符合条件的合约数量
  "filter_criteria": "Total OI > $2,000,000", // 过滤条件
  "updated_at": "2026-01-14 19:34:00", // 更新时间

  "contracts": [
    // 过滤后的合约列表（按 OI 降序）
    {
      "pair": "BTC/USD", // 交易对名称
      "from": "BTC", // 基础资产
      "to": "USD", // 报价资产
      "group": "crypto", // 资产类别

      // === 价格数据 ===
      "bid": 94939.15, // 买一价
      "mid": 94943.38, // 中间价
      "ask": 94947.61, // 卖一价
      "isMarketOpen": true, // 市场是否开放

      // === 持仓量 ===
      "totalOI_USD": 3434819.22, // 总持仓量（USD）
      "longOI": "16190118096356189197", // 多头原始值
      "shortOI": "19987432486160506187", // 空头原始值

      // === 资金费率（仅 crypto 资产）===
      "fundingRate": {
        "longPayHourly": 0.001071, // 多头每小时费率（%）
        "shortPayHourly": 0.00087, // 空头每小时费率（%）
        "longPay8h": 0.008565, // 多头 8 小时费率（%）
        "shortPay8h": 0.00696 // 空头 8 小时费率（%）
      },

      // === 隔夜费率（非 crypto 资产）===
      "rolloverRate": {
        "hourly": 0.000138, // 每小时费率（%）
        "daily": 0.003316 // 每日费率（%）
      },

      // === 原始数据（用于调试）===
      "_raw": {
        "curFundingLong": 2973925102,
        "curFundingShort": -2416694579,
        "rolloverFeePerBlock": 0
      }
    }
  ]
}
```

---

## 费率类型说明

| 资产类别                         | 费率类型 | 字段           | 说明             |
| -------------------------------- | -------- | -------------- | ---------------- |
| crypto                           | 资金费率 | `fundingRate`  | 多空双方浮动费率 |
| forex/stocks/commodities/indices | 隔夜费率 | `rolloverRate` | 固定费率         |

---

## 资金费率计算公式（crypto）

```
原始值 curFundingLong = 2973925102  // 每秒费率

每小时费率 (%) = |curFundingLong| × 3600 / 1e18 × 100
              = 2973925102 × 3600 / 1e18 × 100
              = 0.00107%

8小时费率 (%) = 每小时费率 × 8 = 0.00856%
```

---

## 隔夜费率计算公式（非 crypto）

```
原始值 rolloverFeePerBlock = 383765040  // 每区块费率

Arbitrum 约 4 块/秒，每小时 = 3600 × 4 = 14400 块

每小时费率 (%) = rolloverFeePerBlock × 14400 / 1e18 × 100 = 0.000138%
每日费率 (%) = 每小时费率 × 24 = 0.00331%
```

---

## OI 计算公式

```
totalOI (币) = (longOI + shortOI) / 1e18
             = (16190... + 19987...) / 1e18
             = 36.17 BTC

totalOI (USD) = totalOI (币) × mid 价格
              = 36.17 × 94943.38
              = $3,434,819
```

---

## 资产类别 (group) 对照表

| group.name  | 说明     | 费率类型 | 示例                                 |
| ----------- | -------- | -------- | ------------------------------------ |
| crypto      | 加密货币 | 资金费率 | BTC, ETH                             |
| forex       | 外汇     | 隔夜费率 | EUR/USD, GBP/USD                     |
| commodities | 大宗商品 | 隔夜费率 | XAU（黄金）, XAG（白银）, CL（原油） |
| stocks      | 股票     | 隔夜费率 | TSLA, AAPL, NVDA                     |
| indices     | 指数     | 隔夜费率 | SPX, NDX, DJI                        |
