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
 * @param {String} orderType - 订单类型: 'maker' 或 'taker'
 * @returns {Object} 套利结果
 */
function calculateSingleArbitrage(hlCost, osCost, size, maxHours, hlContract, osContract, orderType = 'maker') {
  const totalCost = hlCost + osCost;
  
  // 根据订单类型计算实际价差
  let currentSpreadUSD;
  let breakEvenSpreadUSD;
  let avgPrice;  // 参考价格（用于价差和收益的转换）
  
  if (orderType === 'taker') {
    // Taker: 使用 bid/ask 价格（反映市价单真实成交价）
    // 判断套利方向: HL 价格 > OS 价格 → HL 做空(bid), OS 做多(ask)
    //              HL 价格 < OS 价格 → HL 做多(ask), OS 做空(bid)
    let hlPrice, osPrice;  // 实际成交价格
    
    if (hlContract.mid > osContract.mid) {
      // HL 做空用 bid, OS 做多用 ask
      hlPrice = hlContract.bid;
      osPrice = osContract.ask;
      currentSpreadUSD = hlPrice - osPrice;
    } else {
      // HL 做多用 ask, OS 做空用 bid
      hlPrice = hlContract.ask;
      osPrice = osContract.bid;
      currentSpreadUSD = osPrice - hlPrice;
    }
    
    // 价差可能为负（交叉盘口），这意味着没有套利空间
    currentSpreadUSD = Math.max(0, currentSpreadUSD);
    
    // 回本价差也基于实际成交价计算（使用实际成交价的平均值）
    avgPrice = (hlPrice + osPrice) / 2;
    breakEvenSpreadUSD = totalCost * avgPrice / size;
  } else {
    // Maker: 使用 mid 价格（挂单可以在接近 mid 的价格成交）
    currentSpreadUSD = Math.abs(hlContract.mid - osContract.mid);
    avgPrice = (hlContract.mid + osContract.mid) / 2;
    breakEvenSpreadUSD = totalCost * avgPrice / size;
  }
  
  // 2. 资金费率回本
  const hlFunding = hlContract.fundingRate?.rateHourly || 0;
  const osFunding = osContract.fundingRate?.longPayHourly || osContract.rolloverRate?.hourly || 0;
  const fundingDiff = Math.abs(hlFunding - osFunding);
  const fundingPerHour = size * (fundingDiff / 100);
  const fundingHours = fundingPerHour > 0 ? totalCost / fundingPerHour : Infinity;
  const fundingValid = fundingHours <= maxHours && fundingHours > 0;
  
  // 3. 价差收益（使用与回本价差计算相同的参考价格）
  const spreadProfit = currentSpreadUSD * size / avgPrice;
  
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
  const maker = calculateSingleArbitrage(hlCostMaker, osCostMaker, size, maxHours, hlContract, osContract, 'maker');
  
  // === 方案2: Taker 费率 ===
  const osOpenFeeRateTaker = typeof osFee === 'object' ? osFee.t : osFee;  // 加密货币用 Taker，传统资产不变
  const hlCostTaker = size * (hlFee.t / 100) * 2;  // HL 开平都用 Taker
  const osCostTaker = size * (osOpenFeeRateTaker / 100) + oracleFee;
  const taker = calculateSingleArbitrage(hlCostTaker, osCostTaker, size, maxHours, hlContract, osContract, 'taker');
  
  return {
    maker,
    taker
  };
}
