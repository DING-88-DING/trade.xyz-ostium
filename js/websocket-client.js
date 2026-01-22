/**
 * WebSocket 实时数据客户端
 * 连接后端 WebSocket 服务器，接收实时数据更新
 * 支持 VIP 等级同步和后端套利计算结果展示
 */

// WebSocket 配置
const WS_CONFIG = {
  url: 'http://localhost:8080',  // WebSocket 服务器地址
  reconnectDelay: 3000,           // 重连延迟
  pingInterval: 30000             // 心跳间隔
};

// Socket.IO 实例
let socket = null;

// 连接状态
let isConnected = false;

// 全局套利数据缓存（从后端接收）
let GLOBAL_COMMON_PAIRS_DATA = null;

/**
 * 初始化 WebSocket 连接
 */
function initWebSocket() {
  console.log('[WebSocket] 正在连接到:', WS_CONFIG.url);
  
  // 创建 Socket.IO 连接
  socket = io(WS_CONFIG.url, {
    reconnection: true,
    reconnectionDelay: WS_CONFIG.reconnectDelay,
    reconnectionAttempts: Infinity
  });
  
  // 连接成功
  socket.on('connect', () => {
    console.log('[WebSocket] ✅ 已连接');
    isConnected = true;
    updateConnectionStatus(true);
    
    // 连接成功后，发送当前 VIP 等级
    const tierSelect = document.getElementById('tierSelect');
    if (tierSelect) {
      sendVipTier(parseInt(tierSelect.value));
    }
  });
  
  // 断开连接
  socket.on('disconnect', () => {
    console.log('[WebSocket] ❌ 已断开');
    isConnected = false;
    updateConnectionStatus(false);
  });
  
  // 接收初始数据
  socket.on('initial_data', (data) => {
    console.log('[WebSocket] 接收初始数据:', data);
    handleInitialData(data);
  });
  
  // 接收实时数据更新
  socket.on('data_update', (update) => {
    console.log(`[WebSocket] 实时更新 [${update.platform}]:`, update.data);
    handlePlatformUpdate(update.platform, update.data);
  });
  
  // 接收套利数据更新（新增）
  socket.on('common_pairs_update', (data) => {
    console.log('[WebSocket] 接收套利数据更新:', data);
    handleCommonPairsUpdate(data);
  });
  
  // 心跳响应
  socket.on('pong', () => {
    // console.log('[WebSocket] 心跳响应');
  });
  
  // 连接错误
  socket.on('connect_error', (error) => {
    console.error('[WebSocket] 连接错误:', error.message);
  });
  
  // 启动心跳
  startHeartbeat();
}

/**
 * 发送 VIP 等级给后端
 * @param {number} tier - VIP 等级 (0-6)
 */
function sendVipTier(tier) {
  if (socket && isConnected) {
    console.log('[WebSocket] 发送 VIP 等级:', tier);
    socket.emit('set_vip_tier', { tier: tier });
  }
}

/**
 * 启动心跳检测
 */
function startHeartbeat() {
  setInterval(() => {
    if (socket && isConnected) {
      socket.emit('ping');
    }
  }, WS_CONFIG.pingInterval);
}

/**
 * 更新连接状态显示
 */
function updateConnectionStatus(connected) {
  const statusEl = document.getElementById('ws-status');
  if (statusEl) {
    if (connected) {
      statusEl.textContent = '🟢 实时';
      statusEl.style.color = 'var(--neon-green)';
    } else {
      statusEl.textContent = '🔴 离线';
      statusEl.style.color = 'var(--neon-red)';
    }
  }
}

/**
 * 处理初始数据（包含套利计算结果）
 */
function handleInitialData(data) {
  // 处理 Hyperliquid 数据
  if (data.hyperliquid) {
    updateHyperliquidData(data.hyperliquid);
  }
  // 处理 Ostium 数据
  if (data.ostium) {
    updateOstiumData(data.ostium);
  }
  // 处理套利数据（新增）
  if (data.common_pairs) {
    handleCommonPairsUpdate(data.common_pairs);
  }
}

/**
 * 处理单个平台的数据更新
 */
function handlePlatformUpdate(platform, data) {
  if (platform === 'hyperliquid') {
    updateHyperliquidData(data);
  } else if (platform === 'ostium') {
    updateOstiumData(data);
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
 * VIP 等级变更时调用（绑定到 UI 控件）
 */
function updateTier() {
  const tierSelect = document.getElementById('tierSelect');
  if (tierSelect) {
    const tier = parseInt(tierSelect.value);
    console.log('[UI] VIP 等级变更:', tier);
    
    // 发送给后端重新计算
    sendVipTier(tier);
  }
}
