/**
 * WebSocket 实时数据客户端
 * 连接后端 WebSocket 服务器，接收实时数据更新
 */

// WebSocket 配置
const WS_CONFIG = {
  url: 'http://localhost:5001',  // WebSocket 服务器地址
  reconnectDelay: 3000,           // 重连延迟
  pingInterval: 30000             // 心跳间隔
};

// Socket.IO 实例
let socket = null;

// 连接状态
let isConnected = false;

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
    handleDataUpdate(data);
  });
  
  // 接收实时数据更新
  socket.on('data_update', (update) => {
    console.log(`[WebSocket] 实时更新 [${update.platform}]:`, update.data);
    handlePlatformUpdate(update.platform, update.data);
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
 * 处理完整数据更新
 */
function handleDataUpdate(data) {
  if (data.hyperliquid) {
    updateHyperliquidData(data.hyperliquid);
  }
  if (data.ostium) {
    updateOstiumData(data.ostium);
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
  
  // 更新对比列表
  updateComparisonList();
}

/**
 * 更新 Hyperliquid 数据
 */
function updateHyperliquidData(data) {
  if (!data || !data.contracts) return;
  
  GLOBAL_HL_DATA = sortByPriority([...data.contracts], 'coin');
  
  const hlList = document.getElementById("hlList");
  if (hlList) {
    hlList.innerHTML = GLOBAL_HL_DATA.map(renderHLCard).join("");
  }
  
  const hlCount = document.getElementById("hlCount");
  if (hlCount) {
    hlCount.textContent = `${GLOBAL_HL_DATA.length} 合约`;
  }
  
  // 更新时间
  if (data.updated_at) {
    updateTimestamp('HL', data.updated_at);
  }
}

/**
 * 更新 Ostium 数据
 */
function updateOstiumData(data) {
  if (!data || !data.contracts) return;
  
  GLOBAL_OS_DATA = sortByPriority([...data.contracts], 'from');
  
  const osList = document.getElementById("osList");
  if (osList) {
    osList.innerHTML = GLOBAL_OS_DATA.map(renderOSCard).join("");
  }
  
  const osCount = document.getElementById("osCount");
  if (osCount) {
    osCount.textContent = `${GLOBAL_OS_DATA.length} 合约`;
  }
  
  // 更新时间
  if (data.updated_at) {
    updateTimestamp('OS', data.updated_at);
  }
}

/**
 * 更新对比列表
 */
function updateComparisonList() {
  if (GLOBAL_HL_DATA.length === 0 || GLOBAL_OS_DATA.length === 0) {
    return;
  }
  
  // 找出共同合约
  const commonPairs = [];
  const hlMap = {};

  GLOBAL_HL_DATA.forEach((c) => {
    const coin = c.coin.includes(":") ? c.coin.split(":")[1] : c.coin;
    hlMap[coin.toUpperCase()] = c;
  });

  GLOBAL_OS_DATA.forEach((osContract) => {
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

  // 保存到全局
  GLOBAL_COMMON_PAIRS = commonPairs;

  // 渲染
  const commonCount = document.getElementById("commonCount");
  const commonList = document.getElementById("commonList");
  
  if (commonCount) {
    commonCount.textContent = `${commonPairs.length} 对`;
  }

  if (commonList && commonPairs.length > 0) {
    // 排序
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
