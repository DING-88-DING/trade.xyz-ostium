/**
 * 调试工具 - 轮询模式
 * 帮助排查轮询为什么不刷新
 */

console.log('='.repeat(50));
console.log('轮询模式调试信息');
console.log('='.repeat(50));

// 检查配置
console.log('1. 配置检查:');
console.log(`   - TIMER_REFRESH_INTERVAL: ${TIMER_REFRESH_INTERVAL}ms (${TIMER_REFRESH_INTERVAL/1000}秒)`);

// 检查函数是否存在
console.log('\n2. 函数检查:');
console.log(`   - loadData 函数存在: ${typeof loadData === 'function'}`);

// 监听 loadData 调用
if (typeof loadData === 'function') {
  const originalLoadData = loadData;
  window.loadData = async function() {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`\n[${timestamp}] ⏰ loadData() 被调用`);
    
    try {
      const result = await originalLoadData();
      console.log(`[${timestamp}] ✅ loadData() 执行成功`, result);
    } catch (error) {
      console.error(`[${timestamp}] ❌ loadData() 执行失败:`, error);
    }
  };
  console.log('   - 已安装 loadData 监听器');
}

// 检查定时器
console.log('\n3. 定时器状态:');
let callCount = 0;
const checkInterval = setInterval(() => {
  callCount++;
  console.log(`   - 定时器运行中... (${callCount * 3}秒)`);
  if (callCount >= 5) {
    clearInterval(checkInterval);
    console.log('   - 定时器检查完成');
  }
}, 3000);

console.log('='.repeat(50));
console.log('提示: 打开浏览器控制台查看 loadData() 调用日志');
console.log('预期: 每60秒应该看到一次 "loadData() 被调用"');
console.log('='.repeat(50));
