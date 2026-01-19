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

/**
 * 重新应用搜索过滤器
 * 在数据刷新后调用，保持搜索状态
 */
function reapplyFilter(listId) {
  // 根据 listId 找到对应的搜索框
  const list = document.getElementById(listId);
  if (!list) return;
  
  // 找到搜索框（在同一个 column 下）
  const column = list.closest('.column');
  if (!column) return;
  
  const searchInput = column.querySelector('.search-input');
  if (!searchInput) return;
  
  // 如果有搜索内容，重新应用过滤
  const query = searchInput.value.trim();
  if (query) {
    filterList(searchInput, listId);
  }
}
