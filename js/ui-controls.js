/**
 * UI 控制模块
 * 处理用户交互操作
 */

/**
 * 更新 Fee Tier
 * 当用户选择不同的费率等级时调用
 */
function updateTier() {
  const select = document.getElementById('tierSelect');
  CURRENT_TIER = parseInt(select.value);
  
  // 重新渲染所有列表以更新费率显示
  const hlList = document.getElementById("hlList");
  hlList.innerHTML = GLOBAL_HL_DATA.map(renderHLCard).join("");
  
  const commonList = document.getElementById("commonList");
  if (GLOBAL_COMMON_PAIRS.length > 0) {
    commonList.innerHTML = GLOBAL_COMMON_PAIRS
      .map((p) => renderComparisonCard(p.hl, p.os, p.name))
      .join("");
  }
}

/**
 * 列表过滤函数
 * 根据搜索框输入过滤卡片列表
 */
function filterList(input, listId) {
  const query = input.value.trim().toLowerCase();
  const list = document.getElementById(listId);
  const cardClass = listId === 'commonList' ? 'comparison-card' : 'contract-card';
  const cards = list.getElementsByClassName(cardClass);
  
  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? "" : "none";
  }
}
