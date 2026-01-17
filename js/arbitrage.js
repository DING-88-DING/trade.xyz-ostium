/**
 * 套利计算模块
 * 计算价差套利、资金费率套利和综合套利的回本时间
 */

/**
 * 计算套利成本和回本
 * @param {Object} hlContract - Hyperliquid 合约数据
 * @param {Object} osContract - Ostium 合约数据
 * @param {Object} hlFee - Hyperliquid 费率对象 {t, m}
 * @param {Object|Number} osFee - Ostium 费率（对象或数字）
 * @param {Number} oracleFee - Ostium 预言机费用
 * @returns {Object} 套利分析结果
 */
function calculateArbitrage(hlContract, osContract, hlFee, osFee, oracleFee) {
  const size = ARBITRAGE_CONFIG.positionSize;
  const maxHours = ARBITRAGE_CONFIG.maxFundingHours;
  
  // 获取 Ostium 开仓费率 (统一使用 Maker 挂单价)
  const osOpenFeeRate = typeof osFee === 'object' ? osFee.m : osFee;
  
  // 计算总成本 (百分比 -> 小数)
  // HL: 开仓 Maker + 平仓 Maker
  // OS: 开仓 Maker + 开仓预言机费 (预言机费在开仓时收取)
  const hlCost = size * (hlFee.m / 100) * 2;  // HL 开平都用 Maker
  const osCost = size * (osOpenFeeRate / 100) + oracleFee;  // OS 开仓 Maker + 预言机费
  const totalCost = hlCost + osCost;
  
  // 1. 价差回本：需要多大价格差（美元）才能覆盖成本
  // 回本价格差 = 总成本 / 仓位数量 = 总成本 * 价格 / 仓位金额
  const breakEvenSpreadUSD = totalCost * osContract.mid / size;
  
  // 2. 资金费率回本
  const hlFunding = hlContract.fundingRate?.rateHourly || 0;
  const osFunding = osContract.fundingRate?.longPayHourly || osContract.rolloverRate?.hourly || 0;
  const fundingDiff = Math.abs(hlFunding - osFunding);  // 每小时费率差 (百分比)
  const fundingPerHour = size * (fundingDiff / 100);  // 每小时收益 (USD)
  const fundingHours = fundingPerHour > 0 ? totalCost / fundingPerHour : Infinity;
  const fundingValid = fundingHours <= maxHours && fundingHours > 0;
  
  // 3. 当前价差（美元）
  const currentSpreadUSD = Math.abs(hlContract.mid - osContract.mid);  // 价格差（美元）
  const spreadProfit = currentSpreadUSD * size / osContract.mid;  // 当前价差收益（考虑仓位大小）
  
  // 4. 综合回本：当前价差收益 + 资金费率收益
  const remainingCost = totalCost - spreadProfit;
  const comboHours = remainingCost > 0 && fundingPerHour > 0 
    ? remainingCost / fundingPerHour 
    : (remainingCost <= 0 ? 0 : Infinity);
  const comboValid = comboHours <= maxHours;
  
  // 判断是否能回本
  const spreadCanProfit = currentSpreadUSD >= breakEvenSpreadUSD;
  const anyCanProfit = spreadCanProfit || fundingValid || comboValid;
  
  return {
    totalCost,
    breakEvenSpreadUSD,
    currentSpreadUSD,
    spreadCanProfit,
    fundingDiff,
    fundingHours: fundingValid ? fundingHours : null,
    fundingValid,
    comboHours: comboValid ? comboHours : null,
    comboValid,
    anyCanProfit
  };
}
