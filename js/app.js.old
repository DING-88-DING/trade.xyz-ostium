/**
 * DEX 费率对比系统 - 主应用脚本
 * 依赖: config.js (需要先加载)
 */

// ==================== 全局状态 ====================
let CURRENT_TIER = 0;
let GLOBAL_HL_DATA = [];
let GLOBAL_OS_DATA = [];
let GLOBAL_COMMON_PAIRS = [];

// 反向名称映射
const REVERSE_MAPPING = {};
for (const [os, hl] of Object.entries(NAME_MAPPING)) {
  REVERSE_MAPPING[hl] = os;
}

// ==================== 费率计算函数 ====================

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

// ==================== 格式化函数 ====================

// 格式化 Ostium 费率 (支持单一费率和 Maker/Taker 对象)
function formatOSFee(fee) {
  if (!fee && fee !== 0) return "N/A";
  // 如果是对象 (加密货币 Maker/Taker)
  if (typeof fee === 'object' && fee.t !== undefined) {
    return `T:${fee.t.toFixed(2)}% / M:${fee.m.toFixed(2)}%`;
  }
  // 单一费率 (传统资产)
  return `${fee.toFixed(2)}%`;
}

// 格式化手续费 (Taker / Maker)
function formatFeeObj(feeObj) {
  if (!feeObj) return "N/A";
  return `T:${feeObj.t.toFixed(5)}% / M:${feeObj.m.toFixed(5)}%`;
}

// 格式化价格
function formatPrice(price) {
  if (!price && price !== 0) return "N/A";
  const num = parseFloat(price);
  if (num >= 1000)
    return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (num >= 1) return num.toFixed(4);
  return num.toFixed(6);
}

// 格式化费率
function formatRate(rate) {
  if (!rate && rate !== 0) return "N/A";
  const num = parseFloat(rate);
  return (num >= 0 ? "+" : "") + num.toFixed(4) + "%";
}

// 格式化成交量
function formatVolume(vol) {
  if (!vol && vol !== 0) return "N/A";
  const num = parseFloat(vol);
  if (num >= 1e9) return "$" + (num / 1e9).toFixed(2) + "B";
  if (num >= 1e6) return "$" + (num / 1e6).toFixed(2) + "M";
  if (num >= 1e3) return "$" + (num / 1e3).toFixed(2) + "K";
  return "$" + num.toFixed(0);
}

// 根据数值返回颜色类
function getValClass(val) {
  if (!val && val !== 0) return "val-neu";
  return val > 0 ? "val-pos" : val < 0 ? "val-neg" : "val-neu";
}

// ==================== UI 控制函数 ====================

// 更新 Fee Tier
function updateTier() {
  const select = document.getElementById('tierSelect');
  CURRENT_TIER = parseInt(select.value);
  
  // 重新渲染所有列表以更新费率显示
  const hlList = document.getElementById("hlList");
  hlList.innerHTML = GLOBAL_HL_DATA.map(renderHLCard).join("");
  
  const commonList = document.getElementById("commonList");
  if (GLOBAL_COMMON_PAIRS.length > 0) {
    commonList.innerHTML = GLOBAL_COMMON_PAIRS
      .map((p) => renderComparisonCard(p.hl, p.os, p.name))
      .join("");
  }
}

// 列表过滤函数
function filterList(input, listId) {
  const query = input.value.trim().toLowerCase();
  const list = document.getElementById(listId);
  const cardClass = listId === 'commonList' ? 'comparison-card' : 'contract-card';
  const cards = list.getElementsByClassName(cardClass);
  
  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? "" : "none";
  }
}

// ==================== 卡片渲染函数 ====================

// 渲染 Hyperliquid 合约卡片
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

// 渲染 Ostium 合约卡片
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

// 计算套利成本和回本
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

// 渲染共同合约对比卡片
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

// ==================== 数据加载函数 ====================

// 排序函数：优先资产排在前面
function sortByPriority(contracts, nameField) {
  return contracts.sort((a, b) => {
    const aName = (a[nameField] || '').toUpperCase();
    const bName = (b[nameField] || '').toUpperCase();
    const aIsPriority = PRIORITY_ASSETS.some(p => aName.includes(p));
    const bIsPriority = PRIORITY_ASSETS.some(p => bName.includes(p));
    
    if (aIsPriority && !bIsPriority) return -1;
    if (!aIsPriority && bIsPriority) return 1;
    if (aIsPriority && bIsPriority) {
      const aIdx = PRIORITY_ASSETS.findIndex(p => aName.includes(p));
      const bIdx = PRIORITY_ASSETS.findIndex(p => bName.includes(p));
      return aIdx - bIdx;
    }
    return 0;
  });
}

// 主函数: 加载数据
async function loadData() {
  try {
    const timestamp = Date.now();

    const [hlRes, osRes] = await Promise.all([
      fetch(`hyperliquid_filtered.json?t=${timestamp}`),
      fetch(`ostium_filtered.json?t=${timestamp}`),
    ]);

    const hlData = await hlRes.json();
    const osData = await osRes.json();

    const hlContracts = hlData.contracts || [];
    const osContracts = osData.contracts || [];

    // 排序后保存到全局变量
    GLOBAL_HL_DATA = sortByPriority([...hlContracts], 'coin');
    GLOBAL_OS_DATA = sortByPriority([...osContracts], 'from');

    // 更新计数
    document.getElementById("hlCount").textContent = `${GLOBAL_HL_DATA.length} 合约`;
    document.getElementById("osCount").textContent = `${GLOBAL_OS_DATA.length} 合约`;

    // 渲染列表
    document.getElementById("hlList").innerHTML = GLOBAL_HL_DATA.map(renderHLCard).join("");
    document.getElementById("osList").innerHTML = GLOBAL_OS_DATA.map(renderOSCard).join("");

    // 找出共同合约
    const commonPairs = [];
    const hlMap = {};

    hlContracts.forEach((c) => {
      const coin = c.coin.includes(":") ? c.coin.split(":")[1] : c.coin;
      hlMap[coin.toUpperCase()] = c;
    });

    osContracts.forEach((osContract) => {
      const osName = osContract.from.toUpperCase();
      const hlName = NAME_MAPPING[osName] || osName;

      if (hlMap[hlName]) {
        commonPairs.push({
          hl: hlMap[hlName],
          os: osContract,
          name: osName === hlName ? osName : `${hlName} / ${osName}`,
        });
      }
    });

    // 保存共同合约到全局变量
    GLOBAL_COMMON_PAIRS = commonPairs;

    // 渲染共同合约
    document.getElementById("commonCount").textContent = `${commonPairs.length} 对`;
    const commonList = document.getElementById("commonList");

    if (commonPairs.length > 0) {
      // 使用 PRIORITY_ASSETS 排序
      commonPairs.sort((a, b) => {
        const aName = a.os.from.toUpperCase();
        const bName = b.os.from.toUpperCase();
        const aIsPriority = PRIORITY_ASSETS.some(p => aName.includes(p));
        const bIsPriority = PRIORITY_ASSETS.some(p => bName.includes(p));
        
        if (aIsPriority && !bIsPriority) return -1;
        if (!aIsPriority && bIsPriority) return 1;
        if (aIsPriority && bIsPriority) {
          const aIdx = PRIORITY_ASSETS.findIndex(p => aName.includes(p));
          const bIdx = PRIORITY_ASSETS.findIndex(p => bName.includes(p));
          return aIdx - bIdx;
        }
        return 0;
      });
      
      commonList.innerHTML = commonPairs
        .map((p) => renderComparisonCard(p.hl, p.os, p.name))
        .join("");
    } else {
      commonList.innerHTML = `
        <div class="empty-state">
          <div class="emoji">🔍</div>
          <p>暂无共同合约</p>
          <p style="font-size: 0.8rem">请确保两个数据文件都已更新</p>
        </div>
      `;
    }

    // 更新时间
    const dataTime = hlData.updated_at || osData.updated_at || new Date().toLocaleString("zh-CN");
    document.getElementById("updateTime").textContent = `UPDATED: ${dataTime}`;
    
    return true;
  } catch (error) {
    console.error("加载数据失败:", error);
    document.getElementById("commonList").innerHTML = `
      <div class="empty-state">
        <div class="emoji">⚠️</div>
        <p>加载数据失败</p>
        <p style="font-size: 0.8rem">${error.message}</p>
      </div>
    `;
    return false;
  }
}

// ==================== 初始化 ====================

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", loadData);

// 定时刷新
setInterval(loadData, TIMER_REFRESH_INTERVAL);
