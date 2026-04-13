"""
Ostium filtering helpers.
"""

# Ostium 真实 24h 成交量阈值（USD）
OSTIUM_MIN_VOLUME_USD = 1_000_000

# Ostium 总 OI 阈值（USD）
OSTIUM_MIN_OI_USD = 1_000_000


def passes_ostium_liquidity_filter(
    day_volume_usd: float,
    total_oi_usd: float,
    min_volume_usd: float = OSTIUM_MIN_VOLUME_USD,
    min_oi_usd: float = OSTIUM_MIN_OI_USD,
) -> bool:
    """
    只要 24h 成交量或总 OI 任一达到阈值，就保留该合约。
    """
    return day_volume_usd >= min_volume_usd or total_oi_usd >= min_oi_usd


def format_ostium_filter_criteria(
    min_volume_usd: float = OSTIUM_MIN_VOLUME_USD,
    min_oi_usd: float = OSTIUM_MIN_OI_USD,
) -> str:
    """
    生成统一的过滤条件说明文案。
    """
    return f"24h Volume > ${min_volume_usd:,.0f} OR Total OI > ${min_oi_usd:,.0f}"
