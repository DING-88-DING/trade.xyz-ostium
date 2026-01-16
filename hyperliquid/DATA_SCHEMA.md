# Hyperliquid 数据结构说明

本文档说明 Hyperliquid 相关 JSON 文件的字段含义。

---

## hyperliquid_response.json

原始 API 响应数据，由 `inspect_hyperliquid.py` 生成。

```jsonc
{
  "perpetuals": [          // 所有永续合约列表
    {
      "index": 0,          // 合约在 DEX 中的索引位置
      "coin": "BTC",       // 合约名称（如 "BTC", "xyz:GOLD"）
      "dex": "main",       // 所属 DEX（"main" = 主 DEX，"xyz" = Builder DEX）
      "szDecimals": 5,     // 数量精度（下单数量的小数位数）
      "maxLeverage": 40,   // 最大杠杆倍数

      // === 资金费率 ===
      "funding": "0.0000125",  // 每小时资金费率（正数 = 多头付费，负数 = 空头付费）

      // === 持仓量与成交量 ===
      "openInterest": "28990.05256",       // 持仓量（币数量）
      "dayNtlVlm": "3195422735.3928818703", // 24小时成交量（USD）
      "prevDayPx": "96428.0",              // 前一天收盘价（USD）

      // === 价格数据 ===
      "oraclePx": "95650.0",   // Oracle 预言机价格（外部数据源，用于计算资金费率）
      "markPx": "95637.0",     // 标记价格（用于计算未实现盈亏和强平）
      "midPx": "95636.5",      // 中间价（买一价和卖一价的平均值）
      "premium": "-0.0001359122", // 溢价率 = (markPx - oraclePx) / oraclePx
      "impactPxs": [           // 冲击价格（大单模拟成交价格）
        "95623.9",             // 买入冲击价（模拟大额买入的成交价）
        "95637.0"              // 卖出冲击价（模拟大额卖出的成交价）
      ]
    }
  ],
  "perp_meta": {           // 各 DEX 的元数据配置
    "main": {              // 主 DEX 配置
      "universe": [...],   // 合约配置列表
      "marginTables": [...], // 保证金层级表
      "collateralToken": 0   // 抵押品代币索引
    },
    "xyz": {...}           // xyz DEX 配置
  }
}
```

---

## hyperliquid_filtered.json

过滤并处理后的数据，由 `process_hyperliquid.py` 生成。

```jsonc
{
  "total_filtered": 66, // 符合条件的合约数量
  "filter_criteria": "24h Volume > $2,000,000", // 过滤条件

  "contracts": [
    // 过滤后的合约列表（按成交量降序）
    {
      "coin": "BTC", // 合约名称
      "pair": "BTC/USD", // 交易对名称

      // === 价格数据 ===
      "bid": 95623.9, // 买一价（最高买价）
      "mid": 95636.5, // 中间价
      "ask": 95637.0, // 卖一价（最低卖价）
      "markPx": 95637.0, // 标记价格
      "oraclePx": 95650.0, // Oracle 价格

      // === 成交量与持仓量 ===
      "dayVolume_USD": 3195422735.39, // 24小时成交量（USD）
      "openInterest": "28990.05256", // 持仓量（币数量）

      // === 资金费率（已转换） ===
      "fundingRate": {
        "rate8h": 0.01, // 8小时费率（%），大多数交易所使用此周期
        "rateHourly": 0.00125, // 每小时费率（%）
        "rateAnnualized": 10.95 // 年化费率（%）= 每小时费率 × 24 × 365
      },

      // === 其他 ===
      "premium": "-0.0001359122", // 溢价率
      "maxLeverage": 40 // 最大杠杆
    }
  ]
}
```

---

## 资金费率计算公式

```
原始值 funding = "0.0000125"  // 每小时费率（小数形式）

每小时费率 (%) = funding × 100 = 0.00125%
8小时费率 (%) = 每小时费率 × 8 = 0.01%
年化费率 (%) = 每小时费率 × 24 × 365 = 10.95%
```

---

## 特殊字段说明

| 字段        | 可能的值                | 说明                           |
| ----------- | ----------------------- | ------------------------------ |
| `dex`       | `"main"`, `"xyz"`       | 主 DEX 或 Builder-Deployed DEX |
| `coin`      | `"BTC"`, `"xyz:GOLD"`   | Builder DEX 合约带有前缀       |
| `impactPxs` | `null` / `[买价, 卖价]` | 无流动性时为 null              |
| `premium`   | 正数/负数               | 正 = 现货溢价，负 = 期货溢价   |
