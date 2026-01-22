/**
 * 主入口和初始化脚本 - HTTP 轮询模式
 * 用于 main.py 启动的服务器
 */

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", () => {
  console.log('[Main] 🚀 应用启动 (HTTP 轮询模式)');
  
  // 启动 HTTP 轮询
  initHttpPolling();
});
