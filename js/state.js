/**
 * 全局状态管理
 * 存储应用程序的全局变量和状态
 */

// 当前选择的 Fee Tier
let CURRENT_TIER = 0;

// 全局数据存储
let GLOBAL_HL_DATA = [];
let GLOBAL_OS_DATA = [];
let GLOBAL_COMMON_PAIRS = [];

// 反向名称映射 (Hyperliquid -> Ostium)
const REVERSE_MAPPING = {};
for (const [os, hl] of Object.entries(NAME_MAPPING)) {
  REVERSE_MAPPING[hl] = os;
}
