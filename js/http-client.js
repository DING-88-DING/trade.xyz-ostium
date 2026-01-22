/**
 * HTTP 轮询数据客户端
 * 用于 main.py 启动的 HTTP 服务器模式
 * 定时轮询获取数据更新
 */

// HTTP 配置
const HTTP_CONFIG = {
  baseUrl: '',  // 空字符串表示使用当前域名
  pollInterval: 5000,  // 轮询间隔 5 秒
  endpoints: {
    hyperliquid: '/hyperliquid_filtered.json',
    ostium: '/ostium_filtered.json',
    commonPairs: '/common_pairs.json'
  }
};

// 全局套利数据缓存（从后端接收）
let GLOBAL_COMMON_PAIRS_DATA = null;

// 是否正在轮询
let isPolling = false;

/**
 * 初始化 HTTP 轮询
 */
function initHttpPolling() {
  console.log('[HTTP] 🚀 启动 HTTP 轮询模式');
  console.log(`[HTTP] 轮询间隔: ${HTTP_CONFIG.pollInterval / 1000} 秒`);
  
  // 首次获取数据
  fetchAllData();
  
  // 启动定时轮询
  setInterval(fetchAllData, HTTP_CONFIG.pollInterval);
  
  // 更新连接状态显示
  updateConnectionStatus(true);
}

/**
 * 获取所有数据
 */
async function fetchAllData() {
  if (isPolling) return;  // 防止重复请求
  isPolling = true;
  
  try {
    // 并行获取所有数据
    const [hlRes, osRes, pairsRes] = await Promise.all([
      fetch(HTTP_CONFIG.endpoints.hyperliquid),
      fetch(HTTP_CONFIG.endpoints.ostium),
      fetch(HTTP_CONFIG.endpoints.commonPairs)
    ]);
    
    // 解析 JSON
    const [hlData, osData, pairsData] = await Promise.all([
      hlRes.ok ? hlRes.json() : null,
      osRes.ok ? osRes.json() : null,
      pairsRes.ok ? pairsRes.json() : null
    ]);
    
    // 更新界面
    if (hlData) updateHyperliquidData(hlData);
    if (osData) updateOstiumData(osData);
    if (pairsData) handleCommonPairsUpdate(pairsData);
    
    console.log('[HTTP] ✓ 数据更新完成');
  } catch (error) {
    console.error('[HTTP] 数据获取失败:', error);
    updateConnectionStatus(false);
  } finally {
    isPolling = false;
  }
}

/**
 * 更新连接状态显示
 */
function updateConnectionStatus(connected) {
  const statusEl = document.getElementById('ws-status');
  if (statusEl) {
    if (connected) {
      statusEl.textContent = '🟢 轮询';
      statusEl.style.color = 'var(--neon-green)';
      statusEl.style.background = 'rgba(0, 255, 100, 0.1)';
    } else {
      statusEl.textContent = '🔴 离线';
      statusEl.style.color = 'var(--neon-red)';
      statusEl.style.background = 'rgba(255, 0, 0, 0.1)';
    }
  }
}

/**
 * 处理套利数据更新（从后端接收计算结果）
 */
function handleCommonPairsUpdate(data) {
  if (!data || !data.pairs) return;
  
  // 缓存套利数据
  GLOBAL_COMMON_PAIRS_DATA = data;
  
  const pairs = data.pairs;
  const vipTier = data.vip_tier;
  
  // 更新计数
  const commonCount = document.getElementById("commonCount");
  if (commonCount) {
    commonCount.textContent = `${pairs.length} 对`;
  }
  
  // 渲染套利列表
  const commonList = document.getElementById("commonList");
  if (commonList) {
    if (pairs.length > 0) {
      commonList.innerHTML = pairs
        .map((p) => renderComparisonCardWithArbitrage(p))
        .join("");
      reapplyFilter('commonList');
    } else {
      commonList.innerHTML = `
        <div class="empty-state">
          <div class="emoji">🔍</div>
          <p>暂无共同合约</p>
          <p style="font-size: 0.8rem">请确保两个数据源都已连接</p>
        </div>
      `;
    }
  }
  
  // 更新时间
  if (data.updated_at) {
    updateTimestamp('ARB', data.updated_at);
  }
}

/**
 * 更新 Hyperliquid 数据
 */
function updateHyperliquidData(data) {
  if (!data || !data.contracts) return;
  
  // 后端已经排序，直接使用
  GLOBAL_HL_DATA = [...data.contracts];
  
  const hlList = document.getElementById("hlList");
  if (hlList) {
    hlList.innerHTML = GLOBAL_HL_DATA.map(renderHLCard).join("");
    reapplyFilter('hlList');
  }
  
  const hlCount = document.getElementById("hlCount");
  if (hlCount) {
    hlCount.textContent = `${GLOBAL_HL_DATA.length} 合约`;
  }
  
  if (data.updated_at) {
    updateTimestamp('HL', data.updated_at);
  }
}

/**
 * 更新 Ostium 数据
 */
function updateOstiumData(data) {
  if (!data || !data.contracts) return;
  
  // 后端已经排序，直接使用
  GLOBAL_OS_DATA = [...data.contracts];
  
  const osList = document.getElementById("osList");
  if (osList) {
    osList.innerHTML = GLOBAL_OS_DATA.map(renderOSCard).join("");
    reapplyFilter('osList');
  }
  
  const osCount = document.getElementById("osCount");
  if (osCount) {
    osCount.textContent = `${GLOBAL_OS_DATA.length} 合约`;
  }
  
  if (data.updated_at) {
    updateTimestamp('OS', data.updated_at);
  }
}

/**
 * 更新时间戳显示
 */
function updateTimestamp(platform, timestamp) {
  const updateTime = document.getElementById("updateTime");
  if (updateTime) {
    updateTime.textContent = `UPDATED: ${timestamp} [${platform}]`;
  }
}

/**
 * VIP 等级变更时调用
 * HTTP 模式下只能等待下次轮询刷新
 * （因为 main.py 不支持动态 VIP 变更）
 */
function updateTier() {
  const tierSelect = document.getElementById('tierSelect');
  if (tierSelect) {
    const tier = parseInt(tierSelect.value);
    console.log('[HTTP] VIP 等级变更:', tier);
    console.log('[HTTP] ⚠️ HTTP 模式不支持实时 VIP 变更，请重启后端');
    
    // 提示用户
    alert(`HTTP 模式不支持实时 VIP 变更。\n\n请修改 main.py 中的 vip_tier 参数后重启服务。\n\n或使用 websocket_server.py 启动，支持实时 VIP 切换。`);
  }
}
