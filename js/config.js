/**
 * DEX 费率对比系统配置文件
 *
 * 用户可以根据自己的情况修改这些配置值
 */

// ============ 用户配置 ============

// Referral 折扣 (默认 4%)，范围 0-100
// 可以在 Hyperliquid 交易界面查看你的 Referral 折扣比例
const REFERRAL_DISCOUNT = 4;

// ============ 费率表 ============
// 数据来源: Hyperliquid 交易界面 Fee Schedule
// 单位: % (例如 0.045 = 0.045%)

const FEE_SCHEDULE = {
  // 主流加密货币永续合约 (Perps Base)
  // 适用于: BTC, ETH, SOL 等主流加密资产
  perps_base: {
    0: { t: 0.045, m: 0.015 },
    1: { t: 0.04, m: 0.012 },
    2: { t: 0.035, m: 0.008 },
    3: { t: 0.03, m: 0.004 },
    4: { t: 0.028, m: 0.0 },
    5: { t: 0.026, m: 0.0 },
    6: { t: 0.024, m: 0.0 },
  },

  // HIP-3 Growth Mode (90%+ 折扣)
  // 适用于: 外汇, 股票, SILVER, COPPER 等 (不包括 GOLD)
  hip3_growth: {
    0: { t: 0.009, m: 0.003 },
    1: { t: 0.008, m: 0.0024 },
    2: { t: 0.007, m: 0.0016 },
    3: { t: 0.006, m: 0.0008 },
    4: { t: 0.0056, m: 0.0 },
    5: { t: 0.0052, m: 0.0 },
    6: { t: 0.0048, m: 0.0 },
  },

  // HIP-3 Standard (2x 标准费率, 无 Growth Mode)
  // 适用于: GOLD (因为 PAXG-USDC 已跟踪金价，不适用 Growth Mode)
  hip3_standard: {
    0: { t: 0.090, m: 0.030 },
    1: { t: 0.080, m: 0.024 },
    2: { t: 0.070, m: 0.016 },
    3: { t: 0.060, m: 0.008 },
    4: { t: 0.056, m: 0.0 },
    5: { t: 0.052, m: 0.0 },
    6: { t: 0.048, m: 0.0 },
  },
};

// ============ Ostium 费率表 ============
// 数据来源: https://ostium-labs.gitbook.io/ostium-docs/trading/fees
// 单位: bps (基点), 1 bps = 0.01%

const OSTIUM_FEE_SCHEDULE = {
  // 传统资产 (只收开仓费，无 Maker/Taker 区分)
  traditional: {
    // 外汇
    forex: 0.03,      // 3 bps
    // 指数
    indices: 0.05,    // 5 bps
    // 股票
    stocks: 0.05,     // 5 bps
    // 贵金属
    XAU: 0.03,        // 黄金 3 bps
    XAG: 0.15,        // 白银 15 bps
    XPT: 0.20,        // 铂金 20 bps
    XPD: 0.20,        // 钯金 20 bps
    // 能源
    CL: 0.10,         // 原油 10 bps
  },
  
  // 加密货币 (Maker/Taker 模型)
  crypto: {
    maker: 0.03,      // 3 bps (杠杆 ≤ 20x 且 减少OI不平衡)
    taker: 0.10,      // 10 bps (杠杆 > 20x 或 增加OI不平衡)
  },
  
  // 其他费用 (固定费用，单位: USD)
  other: {
    oracleFee: 0.10,        // 预言机费: $0.10 (手动平仓时收取)
    closeFee: 0,            // 平仓费: $0 (通常免费)
    // 注意: 自动止盈止损 (SL/TP) 不收取预言机费
  }
};

// ============ 名称映射 ============
// Ostium 名称 -> Hyperliquid 名称（仅名称不同的资产需要映射）
const NAME_MAPPING = {
  XAU: "GOLD", // 黄金
  XAG: "SILVER", // 白银
  HG: "COPPER", // 铜
  NDX: "XYZ100", // 纳斯达克100指数
};

// ============ 优先显示资产 ============
// 这些资产将在列表顶部优先显示
const PRIORITY_ASSETS = [
  // Hyperliquid 资产名
  "GOLD", "SILVER", "COPPER", "XYZ100",
  // Ostium 资产名
  "XAU", "XAG", "HG", "NDX"
];

// ============ 过滤设置 ============
// 最小成交量阈值 (USD)
const MIN_VOLUME_THRESHOLD = 2000000;

// ============ 自动刷新设置 ============
// 自动刷新间隔 (毫秒)
const AUTO_REFRESH_INTERVAL = 5000;

// 定时刷新间隔 (毫秒)
const TIMER_REFRESH_INTERVAL = 60000;
