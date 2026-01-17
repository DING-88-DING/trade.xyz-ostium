/**
 * 数据加载模块
 * 负责从 API 加载数据、排序和匹配
 */

/**
 * 排序函数：优先资产排在前面
 */
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

/**
 * 主数据加载函数
 * 从服务器获取 Hyperliquid 和 Ostium 数据，进行处理和渲染
 */
async function loadData() {
  try {
    const timestamp = Date.now();

    const [hlRes, osRes] = await Promise.all([
      fetch(`hyperliquid_filtered.json?t=${timestamp}`),
      fetch(`ostium_filtered.json?t=${ timestamp}`),
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
