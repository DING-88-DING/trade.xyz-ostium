/**
 * 卡片渲染模块
 * 负责渲染 Hyperliquid、Ostium 和对比卡片
 * 
 * 注意: 所有数据（包括费率）都从后端下发
 */

/**
 * 渲染 Hyperliquid 合约卡片
 * @param {Object} contract - 合约数据（包含后端计算的 fee 字段）
 */
function renderHLCard(contract) {
  const fundingHourly = contract.fundingRate?.rateHourly;
  const rateClass = getValClass(fundingHourly);
  
  // 使用后端下发的费率数据
  const fee = contract.fee || { t: 0, m: 0 };
  // 使用 toFixed(5) 确保能显示完整精度, 如 0.00768%
  const feeDisplay = `${fee.t.toFixed(5)}% / ${fee.m.toFixed(5)}%`;

  return `
    <div class="contract-card">
      <div class="contract-header">
        <span class="contract-name">${contract.coin}</span>
        <span class="contract-group">PERP</span>
      </div>
      
      <!-- 价格行 -->
      <div style="margin-bottom: 0.4rem; padding-bottom: 0.4rem; border-bottom: 1px dashed rgba(255, 255, 255, 0.05);">
        <span class="data-label" style="font-size: 0.6rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.4);">Bid / Mid / Ask</span>
        <div style="margin-top: 0.2rem; font-size: 0.75rem;">
          <span style="color: var(--neon-red);">$${formatPrice(contract.bid)}</span> / 
          <span style="color: #fff;">$${formatPrice(contract.mid)}</span> / 
          <span style="color: var(--neon-green);">$${formatPrice(contract.ask)}</span>
        </div>
      </div>
      
      <!-- 数据网格 -->
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
            ${feeDisplay}
          </span>
        </div>
      </div>
    </div>
  `;
}

/**
 * 渲染 Ostium 合约卡片
 * @param {Object} contract - 合约数据（包含后端计算的 fee 字段）
 */
function renderOSCard(contract) {
  const hasFunding = contract.fundingRate?.longPayHourly;
  const rate = hasFunding
    ? contract.fundingRate.longPayHourly
    : contract.rolloverRate?.hourly;
  const rateLabel = hasFunding ? "Fund/h" : "Roll/h";
  const rateClass = getValClass(hasFunding ? rate : -rate);
  const group = (contract.group || '').toLowerCase();
  
  // 使用后端下发的费率数据
  const fee = contract.fee || {};
  const oracleFee = fee.oracle || 0.10;
  const isCrypto = group === 'crypto' || group === 'cryptocurrency';
  
  let feeLabel, feeDisplay;
  if (isCrypto) {
    // 加密货币显示 Taker/Maker
    const t = fee.t || 0;
    const m = fee.m || 0;
    feeLabel = "Taker/Maker Fee";
    feeDisplay = `${t.toFixed(2)}% / ${m.toFixed(2)}%`;
  } else {
    // 传统资产显示 Open Fee + Oracle
    const openFee = fee.rate || 0;
    feeLabel = "Fees (Open/Oracle)";
    feeDisplay = `${openFee.toFixed(2)}% / $${oracleFee.toFixed(2)}`;
  }

  return `
    <div class="contract-card">
      <div class="contract-header">
        <span class="contract-name">${contract.pair}</span>
        <span class="contract-group">${contract.group || "N/A"}</span>
      </div>
      
      <!-- 价格行 -->
      <div style="margin-bottom: 0.4rem; padding-bottom: 0.4rem; border-bottom: 1px dashed rgba(255, 255, 255, 0.05);">
        <span class="data-label" style="font-size: 0.6rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.4);">Bid / Mid / Ask</span>
        <div style="margin-top: 0.2rem; font-size: 0.75rem;">
          <span style="color: var(--neon-red);">$${formatPrice(contract.bid)}</span> / 
          <span style="color: #fff;">$${formatPrice(contract.mid)}</span> / 
          <span style="color: var(--neon-green);">$${formatPrice(contract.ask)}</span>
        </div>
      </div>
      
      <!-- 数据网格 -->
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
 * 渲染共同合约对比卡片（使用后端计算的套利数据）
 * @param {Object} pairData - 包含 hl, os, name, arbitrage 的数据对象
 */
function renderComparisonCardWithArbitrage(pairData) {
  const hlContract = pairData.hl;
  const osContract = pairData.os;
  const commonName = pairData.name;
  const arb = pairData.arbitrage;
  
  // 如果没有套利数据，显示加载中
  if (!arb) {
    return `
      <div class="comparison-card" style="position: relative;">
        <div class="comp-header">
          <span class="comp-name">${commonName}</span>
        </div>
        <div style="padding: 1rem; text-align: center; color: var(--text-dim);">
          ⏳ 计算中...
        </div>
      </div>
    `;
  }
  
  const hlFunding = hlContract.fundingRate?.rateHourly;
  const osFunding =
    osContract.fundingRate?.longPayHourly ||
    osContract.rolloverRate?.hourly;
    
  const priceDiff =
    ((hlContract.mid - osContract.mid) / osContract.mid) * 100;

  const priceDiffClass = priceDiff >= 0 ? "bg-pos" : "bg-neg";

  // 使用后端下发的费率（用于显示）
  const hlFee = hlContract.fee || { t: 0, m: 0 };
  const osFee = osContract.fee || {};
  const oracleFee = osFee.oracle || 0.10;
  
  // 格式化 HL 费率显示
  // 使用 toFixed(5) 确保能显示完整精度, 如 0.00768%
  const hlFeeDisplay = `${hlFee.t.toFixed(5)}%/${hlFee.m.toFixed(5)}%`;
  
  // 格式化 OS 费率显示
  const osFeeDisplay = osFee.rate !== undefined 
    ? `${osFee.rate.toFixed(2)}%` 
    : `${(osFee.t || 0).toFixed(2)}%/${(osFee.m || 0).toFixed(2)}%`;

  // 确定开仓方向
  const hlDir = hlContract.mid > osContract.mid ? '空' : '多';
  const osDir = hlContract.mid > osContract.mid ? '多' : '空';
  const directionText = `HL:${hlDir} OS:${osDir}`;
  
  // 角标：价差能够盈利（严格模式，只检查价差，不含费率和综合回本）
  const profitBadge = (arb.maker?.adjustedSpreadCanProfit || arb.taker?.adjustedSpreadCanProfit)
    ? `<span style="position: absolute; top: -5px; right: -5px; background: var(--neon-green); color: #000; padding: 2px 6px; border-radius: 10px; font-size: 0.65rem; font-weight: bold;">💰</span>`
    : '';

  // 格式化回本时间
  const formatHours = (h) => {
    if (h === null || h === undefined || h === Infinity) return '无';
    if (h < 1) return `${Math.round(h * 60)}m`;
    return `${h.toFixed(1)}h`;
  };
  
  // 格式化价差显示
  // 格式: 当前价差 / 回本价差 (预期+回本)
  const formatSpread = (arbResult) => {
    if (!arbResult) return '-';
    const current = arbResult.currentSpreadUSD || 0;
    const breakEven = arbResult.breakEvenSpreadUSD || 0;
    const expected = arbResult.expectedSpread || 0;
    
    // 基础显示：当前价差 / 回本价差
    let result = `$${current.toFixed(4)}/$${breakEven.toFixed(4)}`;
    
    // 如果有预期收敛价差，添加 (预期+回本) 到后面
    if (expected > 0) {
      const expectedPlusBreakEven = expected + breakEven;
      result += `($${expectedPlusBreakEven.toFixed(4)})`;
    }
    
    return result;
  };

  const makerData = arb.maker || {};
  const takerData = arb.taker || {};
  
  // 仓位大小（从后端套利数据获取，或使用默认值）
  const positionSize = 1000;

  return `
    <div class="comparison-card" style="position: relative;">
      ${profitBadge}
      <div class="comp-header">
        <span class="comp-name">${commonName}</span>
      </div>
      
      <!-- 价格行 -->
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
          <span style="color: var(--neon-yellow)">HL: ${hlFeeDisplay}</span>
          <span style="color: var(--neon-green)">OS: ${osFeeDisplay} +$${oracleFee.toFixed(2)}</span>
        </div>
      </div>
      
      <!-- Maker 方案 -->
      <div class="comp-row" style="background: rgba(74, 222, 128, 0.08); grid-template-columns: 1fr; padding: 6px;">
        <div style="font-size: 0.65rem; line-height: 1.3;">
          <div style="color: var(--text-dim); margin-bottom: 3px;">
            💚 Maker (${positionSize}u) | 成本: $${(makerData.totalCost || 0).toFixed(2)} | 方向: ${directionText}
          </div>
          <div style="display: flex; justify-content: space-between; gap: 6px;">
            <span class="${makerData.spreadCanProfit ? 'val-pos' : ''}" title="当前价差 vs 回本价差">
              ①价差: ${formatSpread(makerData)}
            </span>
            <span class="${makerData.fundingValid ? 'val-pos' : ''}" title="资金费率回本时间">
              ②费率: ${formatHours(makerData.fundingHours)}
            </span>
            <span class="${makerData.comboValid ? 'val-pos' : ''}" title="综合回本时间">
              ③综合: ${formatHours(makerData.comboHours)}
            </span>
          </div>
        </div>
      </div>
      
      <!-- Taker 方案 -->
      <div class="comp-row" style="background: rgba(251, 191, 36, 0.08); grid-template-columns: 1fr; padding: 6px;">
        <div style="font-size: 0.65rem; line-height: 1.3;">
          <div style="color: var(--text-dim); margin-bottom: 3px;">
            🧡 Taker (${positionSize}u) | 成本: $${(takerData.totalCost || 0).toFixed(2)} | 方向: ${directionText}
          </div>
          <div style="display: flex; justify-content: space-between; gap: 6px;">
            <span class="${takerData.spreadCanProfit ? 'val-pos' : ''}" title="当前价差 vs 回本价差">
              ①价差: ${formatSpread(takerData)}
            </span>
            <span class="${takerData.fundingValid ? 'val-pos' : ''}" title="资金费率回本时间">
              ②费率: ${formatHours(takerData.fundingHours)}
            </span>
            <span class="${takerData.comboValid ? 'val-pos' : ''}" title="综合回本时间">
              ③综合: ${formatHours(takerData.comboHours)}
            </span>
          </div>
        </div>
      </div>
    </div>
  `;
}
