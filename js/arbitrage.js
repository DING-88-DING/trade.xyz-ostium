/**
 * 套利计算模块
 * 计算价差套利、资金费率套利和综合套利的回本时间
 */

/**
 * 计算单一方案的套利数据
 * @param {Number} hlCost - HL 成本
 * @param {Number} osCost - OS 成本
 * @param {Number} size - 仓位大小
 * @param {Number} maxHours - 最大回本小时数
 * @param {Object} hlContract - HL 合约
 * @param {Object} osContract - OS 合约
 * @returns {Object} 套利结果
 */
function calculateSingleArbitrage(hlCost, osCost, size, maxHours, hlContract, osContract) {
  const totalCost = hlCost + osCost;
  
  // 1. 价差回本：需要多大价格差（美元）才能覆盖成本
  const breakEvenSpreadUSD = totalCost * osContract.mid / size;
  
  // 2. 资金费率回本
  const hlFunding = hlContract.fundingRate?.rateHourly || 0;
  const osFunding = osContract.fundingRate?.longPayHourly || osContract.rolloverRate?.hourly || 0;
  const fundingDiff = Math.abs(hlFunding - osFunding);
  const fundingPerHour = size * (fundingDiff / 100);
  const fundingHours = fundingPerHour > 0 ? totalCost / fundingPerHour : Infinity;
  const fundingValid = fundingHours <= maxHours && fundingHours > 0;
  
  // 3. 当前价差（美元）
  const currentSpreadUSD = Math.abs(hlContract.mid - osContract.mid);
  const spreadProfit = currentSpreadUSD * size / osContract.mid;
  
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

/**
 * 计算套利成本和回本（同时计算 Maker 和 Taker 两种方案）
 * @param {Object} hlContract - Hyperliquid 合约数据
 * @param {Object} osContract - Ostium 合约数据
 * @param {Object} hlFee - Hyperliquid 费率对象 {t, m}
 * @param {Object|Number} osFee - Ostium 费率（对象或数字）
 * @param {Number} oracleFee - Ostium 预言机费用
 * @returns {Object} 包含 maker 和 taker 两种方案的套利分析结果
 */
function calculateArbitrage(hlContract, osContract, hlFee, osFee, oracleFee) {
  const size = ARBITRAGE_CONFIG.positionSize;
  const maxHours = ARBITRAGE_CONFIG.maxFundingHours;
  
  // === 方案1: Maker 费率 ===
  const osOpenFeeRateMaker = typeof osFee === 'object' ? osFee.m : osFee;
  const hlCostMaker = size * (hlFee.m / 100) * 2;  // HL 开平都用 Maker
  const osCostMaker = size * (osOpenFeeRateMaker / 100) + oracleFee;
  const maker = calculateSingleArbitrage(hlCostMaker, osCostMaker, size, maxHours, hlContract, osContract);
  
  // === 方案2: Taker 费率 ===
  const osOpenFeeRateTaker = typeof osFee === 'object' ? osFee.t : osFee;  // 加密货币用 Taker，传统资产不变
  const hlCostTaker = size * (hlFee.t / 100) * 2;  // HL 开平都用 Taker
  const osCostTaker = size * (osOpenFeeRateTaker / 100) + oracleFee;
  const taker = calculateSingleArbitrage(hlCostTaker, osCostTaker, size, maxHours, hlContract, osContract);
  
  return {
    maker,
    taker
  };
}
