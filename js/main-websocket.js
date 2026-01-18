/**
 * 主入口和初始化脚本 - WebSocket 实时模式
 * 纯 WebSocket 实时推送数据
 */

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", () => {
  console.log('[Main] 🚀 应用启动 (WebSocket 模式)');
  
  // 启动 WebSocket 连接
  initWebSocket();
});
