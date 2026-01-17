/**
 * 格式化函数模块
 * 负责将数据格式化为用户友好的显示格式
 */

// 格式化 Ostium 费率 (支持单一费率和 Maker/Taker 对象)
function formatOSFee(fee) {
  if (!fee && fee !== 0) return "N/A";
  // 如果是对象 (加密货币 Maker/Taker)
  if (typeof fee === 'object' && fee.t !== undefined) {
    return `T:${fee.t.toFixed(2)}% / M:${fee.m.toFixed(2)}%`;
  }
  // 单一费率 (传统资产)
  return `${fee.toFixed(2)}%`;
}

// 格式化手续费 (Taker / Maker)
function formatFeeObj(feeObj) {
  if (!feeObj) return "N/A";
  return `T:${feeObj.t.toFixed(5)}% / M:${feeObj.m.toFixed(5)}%`;
}

// 格式化价格
function formatPrice(price) {
  if (!price && price !== 0) return "N/A";
  const num = parseFloat(price);
  if (num >= 1000)
    return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (num >= 1) return num.toFixed(4);
  return num.toFixed(6);
}

// 格式化费率
function formatRate(rate) {
  if (!rate && rate !== 0) return "N/A";
  const num = parseFloat(rate);
  return (num >= 0 ? "+" : "") + num.toFixed(4) + "%";
}

// 格式化成交量
function formatVolume(vol) {
  if (!vol && vol !== 0) return "N/A";
  const num = parseFloat(vol);
  if (num >= 1e9) return "$" + (num / 1e9).toFixed(2) + "B";
  if (num >= 1e6) return "$" + (num / 1e6).toFixed(2) + "M";
  if (num >= 1e3) return "$" + (num / 1e3).toFixed(2) + "K";
  return "$" + num.toFixed(0);
}

// 根据数值返回颜色类
function getValClass(val) {
  if (!val && val !== 0) return "val-neu";
  return val > 0 ? "val-pos" : val < 0 ? "val-neg" : "val-neu";
}
