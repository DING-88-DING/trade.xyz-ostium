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
      
      <!-- 价格行：独立显示 -->
      <div style="margin-bottom: 0.4rem; padding-bottom: 0.4rem; border-bottom: 1px dashed rgba(255, 255, 255, 0.05);">
        <span class="data-label" style="font-size: 0.6rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.4);">Bid / Mid / Ask</span>
        <div style="margin-top: 0.2rem; font-size: 0.75rem;">
          <span style="color: var(--neon-red);">$${formatPrice(contract.bid)}</span> / 
          <span style="color: #fff;">$${formatPrice(contract.mid)}</span> / 
          <span style="color: var(--neon-green);">$${formatPrice(contract.ask)}</span>
        </div>
      </div>
      
      <!-- 数据网格：2列布局 -->
      <div class="data-grid">
        <div class="data-item" style="align-items: flex-start;">
          <span class="data-label">1h Rate</span>
          <span class="data-value ${rateClass}">${formatRate(fundingHourly)}</span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">24h Vol</span>
          <span class="data-value">${formatVolume(contract.dayVolume_USD)}</span>
        </div>
        <div class="data-item" style="grid-column: span 2;">
          <span class="data-label">Taker/Maker Fee</span>
          <span class="data-value" style="color: var(--neon-yellow); font-size: 0.75rem;">
            ${formatFeeObj(feeObj)}
          </span>
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
      
      <!-- 价格行：独立显示 -->
      <div style="margin-bottom: 0.4rem; padding-bottom: 0.4rem; border-bottom: 1px dashed rgba(255, 255, 255, 0.05);">
        <span class="data-label" style="font-size: 0.6rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.4);">Bid / Mid / Ask</span>
        <div style="margin-top: 0.2rem; font-size: 0.75rem;">
          <span style="color: var(--neon-red);">$${formatPrice(contract.bid)}</span> / 
          <span style="color: #fff;">$${formatPrice(contract.mid)}</span> / 
          <span style="color: var(--neon-green);">$${formatPrice(contract.ask)}</span>
        </div>
      </div>
      
      <!-- 数据网格：2列布局 -->
      <div class="data-grid">
        <div class="data-item" style="align-items: flex-start;">
          <span class="data-label">${rateLabel}</span>
          <span class="data-value ${rateClass}">${formatRate(rate)}</span>
        </div>
        <div class="data-item" style="align-items: flex-end;">
          <span class="data-label">Total OI</span>
          <span class="data-value">${formatVolume(contract.totalOI_USD)}</span>
        </div>
        <div class="data-item" style="grid-column: span 2;">
          <span class="data-label">${feeLabel}</span>
          <span class="data-value" style="color: var(--neon-green); font-size: 0.7rem;">
            ${feeDisplay}
          </span>
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
  
  // 角标：任意方式能回本（Maker 或 Taker）
  const profitBadge = (arb.maker.anyCanProfit || arb.taker.anyCanProfit)
    ? `<span style="position: absolute; top: -5px; right: -5px; background: var(--neon-green); color: #000; padding: 2px 6px; border-radius: 10px; font-size: 0.65rem; font-weight: bold;">💰</span>`
    : '';

  // 格式化回本时间
  const formatHours = (h) => {
    if (h === null || h === Infinity) return '无';
    if (h < 1) return `${Math.round(h * 60)}m`;
    return `${h.toFixed(1)}h`;
  };
  
  // 格式化价差显示（当前价差 / 回本价差）
  const formatSpreadMaker = () => {
    const current = `$${arb.maker.currentSpreadUSD.toFixed(4)}`;
    const breakEven = `$${arb.maker.breakEvenSpreadUSD.toFixed(4)}`;
    return `${current} / ${breakEven}`;
  };

  const formatSpreadTaker = () => {
    const current = `$${arb.taker.currentSpreadUSD.toFixed(4)}`;
    const breakEven = `$${arb.taker.breakEvenSpreadUSD.toFixed(4)}`;
    return `${current} / ${breakEven}`;
  };

  return `
    <div class="comparison-card" style="position: relative;">
      ${profitBadge}
      <div class="comp-header">
        <span class="comp-name">${commonName}</span>
      </div>
      
      <!-- 价格行 (Bid/Mid/Ask) -->
      <div class="comp-row" style="grid-template-columns: 1fr; padding: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem;">
          <div style="text-align: left;">
            <span style="color: var(--text-dim); font-size: 0.6rem;">HL:</span>
            <span style="color: var(--neon-red);">$${formatPrice(hlContract.bid)}</span> / 
            <span style="color: #fff;">$${formatPrice(hlContract.mid)}</span> / 
            <span style="color: var(--neon-green);">$${formatPrice(hlContract.ask)}</span>
          </div>
          <span class="diff-tag ${priceDiffClass}" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">
            ${priceDiff >= 0 ? "+" : ""}${priceDiff.toFixed(3)}%
          </span>
          <div style="text-align: right;">
            <span style="color: var(--text-dim); font-size: 0.6rem;">OS:</span>
            <span style="color: var(--neon-red);">$${formatPrice(osContract.bid)}</span> / 
            <span style="color: #fff;">$${formatPrice(osContract.mid)}</span> / 
            <span style="color: var(--neon-green);">$${formatPrice(osContract.ask)}</span>
          </div>
        </div>
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
      
      <!-- 套利分析行 - Maker 方案 -->
      <div class="comp-row" style="background: rgba(74, 222, 128, 0.08); grid-template-columns: 1fr; padding: 6px;">
        <div style="font-size: 0.65rem; line-height: 1.3;">
          <div style="color: var(--text-dim); margin-bottom: 3px;">
            💚 Maker (${ARBITRAGE_CONFIG.positionSize}u) | 成本: $${arb.maker.totalCost.toFixed(2)} | 方向: ${directionText}
          </div>
          <div style="display: flex; justify-content: space-between; gap: 6px;">
            <span class="${arb.maker.spreadCanProfit ? 'val-pos' : ''}" title="当前价差 vs 回本价差">
              ①价差: ${formatSpreadMaker()}
            </span>
            <span class="${arb.maker.fundingValid ? 'val-pos' : ''}" title="资金费率回本时间">
              ②费率: ${formatHours(arb.maker.fundingHours)}
            </span>
            <span class="${arb.maker.comboValid ? 'val-pos' : ''}" title="综合回本时间">
              ③综合: ${formatHours(arb.maker.comboHours)}
            </span>
          </div>
        </div>
      </div>
      
      <!-- 套利分析行 - Taker 方案 -->
      <div class="comp-row" style="background: rgba(251, 191, 36, 0.08); grid-template-columns: 1fr; padding: 6px;">
        <div style="font-size: 0.65rem; line-height: 1.3;">
          <div style="color: var(--text-dim); margin-bottom: 3px;">
            🧡 Taker (${ARBITRAGE_CONFIG.positionSize}u) | 成本: $${arb.taker.totalCost.toFixed(2)} | 方向: ${directionText}
          </div>
          <div style="display: flex; justify-content: space-between; gap: 6px;">
            <span class="${arb.taker.spreadCanProfit ? 'val-pos' : ''}" title="当前价差 vs 回本价差">
              ①价差: ${formatSpreadTaker()}
            </span>
            <span class="${arb.taker.fundingValid ? 'val-pos' : ''}" title="资金费率回本时间">
              ②费率: ${formatHours(arb.taker.fundingHours)}
            </span>
            <span class="${arb.taker.comboValid ? 'val-pos' : ''}" title="综合回本时间">
              ③综合: ${formatHours(arb.taker.comboHours)}
            </span>
          </div>
        </div>
      </div>
    </div>
  `;
}
