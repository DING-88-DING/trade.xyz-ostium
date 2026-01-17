/**
 * 主入口和初始化脚本
 * 启动应用程序并设置定时刷新
 */

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", loadData);

// 定时刷新
setInterval(loadData, TIMER_REFRESH_INTERVAL);
