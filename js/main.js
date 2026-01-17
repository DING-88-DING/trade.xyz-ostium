/**
 * 主入口和初始化脚本 - 轮询模式
 * 
 * 工作流程：
 * 1. 定时调用 loadData() 刷新前端数据
 * 2. loadData() fetch HTTP API 路径（如 /hyperliquid_filtered.json）
 * 3. main.py 的 HTTP 服务器接收请求
 * 4. 服务器从内存 DATA_STORE（Python字典）读取数据
 * 5. 转换为 JSON 格式返回给前端
 * 
 * 注意：磁盘上没有 .json 文件，数据全部在 main.py 的内存中！
 */

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", loadData);

// 定时刷新
setInterval(loadData, TIMER_REFRESH_INTERVAL);
