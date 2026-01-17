/**
 * 卡片渲染模块
 * 负责渲染 Hyperliquid、Ostium 和对比卡片
 */

/**
 * 渲染 Hyperliquid 合约卡片
 */
function renderHLCard(contract) {
  const fundingHourly = contract.fundingRate?.rateHourly;
  const rateClass = getValClass(fundingHourly);
  const feeObj = getHLFeeRate(contract);

  return `
    <div class="contract-card">
      <div class="contract-header">
        <span class="contract-name">${contract.coin}</span>
        <span class="contract-group">PERP</span>
      </div>
      
      <div class="data-grid">
        <div class="data-item">
          <span class="data-label">Price</span>
          <span class="data-value">$${formatPrice(contract.mid)}</span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">1h Rate</span>
          <span class="data-value ${rateClass}">${formatRate(fundingHourly)}</span>
        </div>
        <div class="data-item">
          <span class="data-label">Taker/Maker Fee</span>
          <span class="data-value" style="color: var(--neon-yellow); font-size: 0.8rem;">
            ${formatFeeObj(feeObj)}
          </span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">24h Vol</span>
          <span class="data-value">${formatVolume(contract.dayVolume_USD)}</span>
        </div>
      </div>
    </div>
  `;
}

/**
 * 渲染 Ostium 合约卡片
 */
function renderOSCard(contract) {
  const hasFunding = contract.fundingRate?.longPayHourly;
  const rate = hasFunding
    ? contract.fundingRate.longPayHourly
    : contract.rolloverRate?.hourly;
  const rateLabel = hasFunding ? "Fund/h" : "Roll/h";
  const rateClass = getValClass(hasFunding ? rate : -rate);
  const group = (contract.group || '').toLowerCase();
  
  // 计算 Ostium 交易费
  const osFee = getOSFeeRate(contract);
  const oracleFee = OSTIUM_FEE_SCHEDULE.other.oracleFee;
  
  // 加密货币显示 Maker/Taker，传统资产显示 Open Fee + Oracle Fee
  const isCrypto = group === 'crypto' || group === 'cryptocurrency';
  const feeLabel = isCrypto ? "Taker/Maker Fee" : "Fees (Open/Oracle)";
  const feeDisplay = isCrypto 
    ? formatOSFee(osFee)
    : `${formatOSFee(osFee)} / $${oracleFee.toFixed(2)}`;

  return `
    <div class="contract-card">
      <div class="contract-header">
        <span class="contract-name">${contract.pair}</span>
        <span class="contract-group">${contract.group || "N/A"}</span>
      </div>
      
      <div class="data-grid">
        <div class="data-item">
          <span class="data-label">Price</span>
          <span class="data-value">$${formatPrice(contract.mid)}</span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">${rateLabel}</span>
          <span class="data-value ${rateClass}">${formatRate(rate)}</span>
        </div>
        <div class="data-item">
          <span class="data-label">${feeLabel}</span>
          <span class="data-value" style="color: var(--neon-green); font-size: 0.75rem;">
            ${feeDisplay}
          </span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">Total OI</span>
          <span class="data-value">${formatVolume(contract.totalOI_USD)}</span>
        </div>
      </div>
    </div>
  `;
}

/**
 * 渲染共同合约对比卡片
 */
function renderComparisonCard(hlContract, osContract, commonName) {
  const hlFunding = hlContract.fundingRate?.rateHourly;
  const osFunding =
    osContract.fundingRate?.longPayHourly ||
    osContract.rolloverRate?.hourly;
    
  const priceDiff =
    ((hlContract.mid - osContract.mid) / osContract.mid) * 100;

  const feeObj = getHLFeeRate(hlContract);
  const osFee = getOSFeeRate(osContract);
  const oracleFee = OSTIUM_FEE_SCHEDULE.other.oracleFee;
  const priceDiffClass = priceDiff >= 0 ? "bg-pos" : "bg-neg";

  // 计算套利
  const arb = calculateArbitrage(hlContract, osContract, feeObj, osFee, oracleFee);
  
  // 确定开仓方向
  // HL价格 > OS价格 → HL开空，OS开多（做空贵的，做多便宜的）
  // HL价格 < OS价格 → HL开多，OS开空
  const hlDir = hlContract.mid > osContract.mid ? '空' : '多';
  const osDir = hlContract.mid > osContract.mid ? '多' : '空';
  const directionText = `HL:${hlDir} OS:${osDir}`;
  
  // 角标：任意方式能回本
  const profitBadge = arb.anyCanProfit 
    ? `<span style="position: absolute; top: -5px; right: -5px; background: var(--neon-green); color: #000; padding: 2px 6px; border-radius: 10px; font-size: 0.65rem; font-weight: bold;">💰</span>`
    : '';

  // 格式化回本时间
  const formatHours = (h) => {
    if (h === null || h === Infinity) return '无';
    if (h < 1) return `${Math.round(h * 60)}m`;
    return `${h.toFixed(1)}h`;
  };
  
  // 格式化价差显示（当前价差 / 回本价差）
  const formatSpread = () => {
    const current = `$${arb.currentSpreadUSD.toFixed(4)}`;
    const breakEven = `$${arb.breakEvenSpreadUSD.toFixed(4)}`;
    return `${current} / ${breakEven}`;
  };

  return `
    <div class="comparison-card" style="position: relative;">
      ${profitBadge}
      <div class="comp-header">
        <span class="comp-name">${commonName}</span>
      </div>
      
      <!-- 价格行 -->
      <div class="comp-row">
        <span class="comp-cell-left">$${formatPrice(hlContract.mid)}</span>
        <div class="comp-cell-mid">
          <span class="diff-tag ${priceDiffClass}">
            ${priceDiff >= 0 ? "+" : ""}${priceDiff.toFixed(3)}%
          </span>
        </div>
        <span class="comp-cell-right">$${formatPrice(osContract.mid)}</span>
      </div>
      
      <!-- 费率行 -->
      <div class="comp-row">
        <span class="comp-cell-left comp-val-hl">${formatRate(hlFunding)}</span>
        <div class="comp-cell-mid">
          <span style="opacity: 0.5">Rate/1h</span>
        </div>
        <span class="comp-cell-right comp-val-os">${formatRate(osFunding)}</span>
      </div>
      
      <!-- 交易费行 -->
      <div class="comp-row" style="background: rgba(255, 238, 0, 0.05); grid-template-columns: 1fr;">
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
          <span style="color: var(--neon-yellow)">HL: ${formatFeeObj(feeObj)}</span>
          <span style="color: var(--neon-green)">OS: ${formatOSFee(osFee)} +$${oracleFee.toFixed(2)}</span>
        </div>
      </div>
      
      <!-- 套利分析行 -->
      <div class="comp-row" style="background: rgba(147, 51, 234, 0.1); grid-template-columns: 1fr; padding: 8px;">
        <div style="font-size: 0.7rem; line-height: 1.4;">
          <div style="color: var(--text-dim); margin-bottom: 4px;">
            📊 套利分析 (${ARBITRAGE_CONFIG.positionSize}u) | 成本: $${arb.totalCost.toFixed(2)} | 方向: ${directionText}
          </div>
          <div style="display: flex; justify-content: space-between; gap: 8px;">
            <span class="${arb.spreadCanProfit ? 'val-pos' : ''}" title="当前价差（能否回本）">
              ①价差: ${formatSpread()}
            </span>
            <span class="${arb.fundingValid ? 'val-pos' : ''}" title="通过资金费率回本时间">
              ②费率: ${formatHours(arb.fundingHours)}
            </span>
            <span class="${arb.comboValid ? 'val-pos' : ''}" title="价差+资金费率综合回本时间">
              ③综合: ${formatHours(arb.comboHours)}
            </span>
          </div>
        </div>
      </div>
    </div>
  `;
}
