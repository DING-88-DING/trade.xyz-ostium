# -*- coding: utf-8 -*-
"""
====================================================================
Hyperliquid 过滤规则模块 (filters.py)
====================================================================

这个文件的作用：
- 存放 Hyperliquid 数据接入层的过滤配置
- 负责判断某个 HL 资产是否需要被排除
- 支持从根目录 config.py 覆盖默认过滤配置

说明：
- 这里的职责是“数据过滤”，不是“费率配置”
- 因此放在 trade_hyperliquid 模块下比放在 arbitrage/fee_config.py 更合适
"""

import os
import sys


# 将项目根目录加入 sys.path，方便读取根目录 config.py。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


# Hyperliquid 默认过滤配置。
# 当前需求只需要按资产名过滤，因此默认只保留 excluded_assets。
HYPERLIQUID_FILTER_CONFIG = {
    'excluded_assets': ['SPX'],
}


def normalize_hyperliquid_asset_name(coin):
    """将 Hyperliquid 资产名称标准化，便于统一做过滤判断。"""
    if not coin:
        return ''

    normalized_coin = str(coin).strip()
    if ':' in normalized_coin:
        normalized_coin = normalized_coin.split(':')[-1]

    return normalized_coin.upper()


def _load_user_filter_config():
    """从根目录 config.py 读取用户自定义过滤配置。"""
    try:
        import config as _user_config
    except Exception:
        return

    user_filter_config = getattr(_user_config, 'HYPERLIQUID_FILTER_CONFIG', None)
    if not isinstance(user_filter_config, dict):
        return

    # 这里只做浅覆盖，当前配置结构已经足够简单。
    HYPERLIQUID_FILTER_CONFIG.update(user_filter_config)


def is_hyperliquid_asset_excluded(coin):
    """判断某个 Hyperliquid 合约是否命中过滤配置。"""
    normalized_coin = normalize_hyperliquid_asset_name(coin)

    excluded_assets = {
        normalize_hyperliquid_asset_name(asset)
        for asset in HYPERLIQUID_FILTER_CONFIG.get('excluded_assets', [])
        if asset
    }

    return normalized_coin in excluded_assets


# 模块加载时立即尝试读取用户配置，保证调用方拿到的是最终生效配置。
_load_user_filter_config()
