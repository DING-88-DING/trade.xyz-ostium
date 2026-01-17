/**
 * 费率计算模块
 * 负责计算 Hyperliquid 和 Ostium 的交易费率
 */

/**
 * 获取 Hyperliquid 费率对象 {t, m} (已应用 Referral 折扣)
 * 费率类别基于 dex 字段自动判断:
 * - "main": 主流加密货币 (perps_base)
 * - "xyz": HIP-3 资产 (hip3_growth 或 hip3_standard)
 */
function getHLFeeRate(contract) {
  const name = contract.coin;
  const dex = contract.dex || 'main';
  const tier = CURRENT_TIER;
  const discountMultiplier = 1 - (REFERRAL_DISCOUNT / 100);
  
  let baseFee;
  
  // 基于 dex 字段判断
  if (dex === 'xyz') {
    // HIP-3 资产
    // GOLD 使用 hip3_standard (因为 PAXG-USDC 已跟踪金价，不适用 Growth Mode)
    if (name === 'GOLD' || name.includes('GOLD')) {
      baseFee = FEE_SCHEDULE.hip3_standard[tier];
    } else {
      // 其他 HIP-3 资产使用 hip3_growth
      baseFee = FEE_SCHEDULE.hip3_growth[tier];
    }
  } else {
    // 主流加密货币 (dex = "main")
    baseFee = FEE_SCHEDULE.perps_base[tier];
  }

  // 应用 Referral 折扣
  return {
    t: baseFee.t * discountMultiplier,
    m: baseFee.m * discountMultiplier
  };
}

/**
 * 获取 Ostium 费率
 * 基于 contract.group 字段自动判断费率类别
 * 返回: 传统资产返回数字(百分比), 加密货币返回对象 {t, m}
 */
function getOSFeeRate(contract) {
  const from = contract.from || '';
  const group = (contract.group || '').toLowerCase();
  
  // 1. 检查是否有特定资产的费率 (XAU, XAG, CL 等)
  if (OSTIUM_FEE_SCHEDULE.traditional[from]) {
    return OSTIUM_FEE_SCHEDULE.traditional[from];
  }
  
  // 2. 根据 group 字段判断类型
  if (group === 'forex' || group.includes('fx')) {
    return OSTIUM_FEE_SCHEDULE.traditional.forex;
  }
  if (group === 'indices' || group === 'index') {
    return OSTIUM_FEE_SCHEDULE.traditional.indices;
  }
  if (group === 'stocks' || group === 'stock' || group === 'equities') {
    return OSTIUM_FEE_SCHEDULE.traditional.stocks;
  }
  if (group === 'commodities' || group === 'commodity') {
    return 0.05; // 5 bps 默认大宗商品费率
  }
  
  // 3. 加密货币 - 返回 Maker/Taker 对象
  if (group === 'crypto' || group === 'cryptocurrency') {
    return {
      t: OSTIUM_FEE_SCHEDULE.crypto.taker,
      m: OSTIUM_FEE_SCHEDULE.crypto.maker
    };
  }
  
  // 默认返回 6 bps
  return 0.06;
}
