/**
 * 主入口和初始化脚本 - WebSocket 实时模式
 * 使用 WebSocket 实时推送数据，失败则降级到轮询
 */

// 数据模式
let DATA_MODE = 'websocket';  // 'websocket' 或 'polling'
let pollingInterval = null;

/**
 * 尝试连接 WebSocket
 */
function tryWebSocket() {
  console.log('[Main] 尝试连接 WebSocket...');
  
  // 检查 WebSocket 客户端是否加载
  if (typeof initWebSocket !== 'function') {
    console.log('[Main] ⚠️ WebSocket 客户端未加载');
    fallbackToPolling();
    return;
  }
  
  // 尝试连接
  const testSocket = io(WS_CONFIG.url, {
    reconnection: false,
    timeout: 3000
  });
  
  testSocket.on('connect', () => {
    console.log('[Main] ✅ WebSocket 可用，使用实时模式');
    DATA_MODE = 'websocket';
    testSocket.disconnect();
    
    // 启动 WebSocket 模式
    initWebSocket();
  });
  
  testSocket.on('connect_error', (error) => {
    console.log('[Main] ❌ WebSocket 连接失败:', error.message);
    testSocket.disconnect();
    fallbackToPolling();
  });
}

/**
 * 降级到轮询模式
 */
function fallbackToPolling() {
  console.log('[Main] 📊 使用轮询模式 (每60秒)');
  DATA_MODE = 'polling';
  
  // 更新状态显示
  const statusEl = document.getElementById('ws-status');
  if (statusEl) {
    statusEl.textContent = '🔵 轮询';
    statusEl.style.background = 'rgba(0,123,255,0.1)';
    statusEl.title = '使用JSON文件轮询模式（60秒）';
  }
  
  // 立即加载一次
  loadData();
  
  // 启动定时轮询
  if (pollingInterval) {
    clearInterval(pollingInterval);
  }
  pollingInterval = setInterval(loadData, TIMER_REFRESH_INTERVAL);
}

/**
 * 手动切换到轮询模式
 */
function switchToPolling() {
  if (DATA_MODE === 'polling') {
    console.log('[Main] 已经是轮询模式');
    return;
  }
  
  console.log('[Main] 手动切换到轮询模式');
  
  // 断开 WebSocket
  if (socket && socket.connected) {
    socket.disconnect();
  }
  
  fallbackToPolling();
}

/**
 * 手动切换到 WebSocket 模式
 */
function switchToWebSocket() {
  if (DATA_MODE === 'websocket') {
    console.log('[Main] 已经是WebSocket模式');
    return;
  }
  
  console.log('[Main] 手动切换到WebSocket模式');
  
  // 停止轮询
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
  
  tryWebSocket();
}

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", () => {
  console.log('[Main] 🚀 应用启动 (WebSocket 模式)');
  
  // 优先尝试 WebSocket，失败则降级到轮询
  tryWebSocket();
});
