# -*- coding: utf-8 -*-
"""
====================================================================
套利通知模块 (notifier.py)
====================================================================

这个文件的作用：
- 检测监控资产的套利机会
- 发送 Windows 桌面通知
- 防重复通知（1分钟冷却）

使用示例:
    from arbitrage.notifier import ArbitrageNotifier
    
    notifier = ArbitrageNotifier()
    notifier.check_and_notify(common_pairs)
"""

import time
from datetime import datetime
from typing import Dict, List, Any

# ==================== 配置 ====================

# 从配置文件导入
from .fee_config import ARBITRAGE_CONFIG

# 监控的资产列表（HL 名称）
MONITORED_ASSETS = ARBITRAGE_CONFIG.get('monitored_assets', ['GOLD', 'SILVER', 'COPPER', 'XYZ100'])
MONITORED_ASSET_SET = {
    str(asset).strip().upper()
    for asset in MONITORED_ASSETS
    if str(asset).strip()
}

# 通知冷却时间（秒）- 同一资产在此时间内不重复通知
NOTIFICATION_COOLDOWN = ARBITRAGE_CONFIG.get('notification_cooldown', 60)


class ArbitrageNotifier:
    """
    套利通知器
    
    负责检测监控资产的套利机会并发送桌面通知
    """
    
    def __init__(self, cooldown: int = NOTIFICATION_COOLDOWN):
        """
        初始化通知器
        
        Args:
            cooldown: 通知冷却时间（秒）
        """
        self.cooldown = cooldown
        # 上次通知时间记录 {'GOLD': 1234567890, ...}
        self.last_notification_time: Dict[str, float] = {}
        # 通知功能是否可用
        self.notification_available = False
        
        # 尝试导入 plyer
        try:
            from plyer import notification
            self._notification = notification
            self.notification_available = True
            print('[Notifier] ✅ 桌面通知功能已启用')
            print(f'[Notifier] 监控资产: {", ".join(MONITORED_ASSETS)}')
        except ImportError:
            print('[Notifier] ⚠️ plyer 未安装，桌面通知功能不可用')
            print('[Notifier] 请运行: pip install plyer')
            self._notification = None
    
    def send_notification(self, title: str, message: str, timeout: int = 10):
        """
        发送桌面通知
        
        Args:
            title: 通知标题
            message: 通知内容
            timeout: 通知显示时间（秒）
        """
        # 播放提示音
        self._play_sound()
        
        if not self.notification_available:
            # 降级到终端输出
            print(f'\n{"="*50}')
            print(f'🔔 {title}')
            print(f'{message}')
            print(f'{"="*50}\n')
            return
        
        try:
            self._notification.notify(
                title=title,
                message=message,
                app_name='DEX Arbitrage Monitor',
                timeout=timeout
            )
            print(f'[Notifier] 📢 已发送通知: {title}')
        except Exception as e:
            print(f'[Notifier] 发送通知失败: {e}')
            # 降级到终端输出
            print(f'\n🔔 {title}\n{message}\n')
    
    def _play_sound(self):
        """
        播放提示音
        Windows: 使用 winsound 播放系统声音
        """
        try:
            import winsound
            # MB_ICONEXCLAMATION = 0x30 (惊叹号提示音)
            # MB_ICONASTERISK = 0x40 (星号提示音，更柔和)
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except ImportError:
            # 非 Windows 系统，尝试使用终端铃声
            print('\a', end='', flush=True)
        except Exception as e:
            print(f'[Notifier] 播放音效失败: {e}')
    
    def check_and_notify(self, common_pairs: List[Dict[str, Any]]):
        """
        检查套利机会并发送通知
        
        Args:
            common_pairs: 共同资产配对列表
        """
        if not common_pairs:
            return
        
        now = time.time()
        
        for pair in common_pairs:
            # 获取资产名称
            name = pair.get('name', '')
            hl_contract = pair.get('hl', {})
            hl_coin = hl_contract.get('coin', '')
            normalized_hl_coin = hl_coin.split(':')[-1].upper() if hl_coin else ''
            
            # 检查是否在监控列表中
            is_monitored = normalized_hl_coin in MONITORED_ASSET_SET
            
            if not is_monitored:
                continue
            
            # 获取套利数据
            arb = pair.get('arbitrage')
            if not arb:
                continue
            
            # 检查是否有套利机会（使用调整后的判断，考虑预期收敛价差）
            maker_spread_profit = arb.get('maker', {}).get('adjustedSpreadCanProfit', False)
            taker_spread_profit = arb.get('taker', {}).get('adjustedSpreadCanProfit', False)
            
            if not (maker_spread_profit or taker_spread_profit):
                continue
            
            # 提取资产标识（用于防重复）
            asset_key = normalized_hl_coin or name.split(' ')[0]
            
            # 检查冷却时间
            last_time = self.last_notification_time.get(asset_key, 0)
            if now - last_time < self.cooldown:
                continue
            
            # 更新上次通知时间
            self.last_notification_time[asset_key] = now
            
            # 构建通知内容
            profit_type = 'Maker' if maker_spread_profit else 'Taker'
            arb_data = arb.get('maker' if maker_spread_profit else 'taker', {})
            
            current_spread = arb_data.get('currentSpreadUSD', 0)
            break_even_spread = arb_data.get('breakEvenSpreadUSD', 0)
            total_cost = arb_data.get('totalCost', 0)
            
            title = f'💰 {name} 发现套利机会!'
            message = (
                f'{profit_type} 方案可盈利\n'
                f'当前价差: ${current_spread:.4f}\n'
                f'回本价差: ${break_even_spread:.4f}\n'
                f'开仓成本: ${total_cost:.2f}'
            )
            
            # 发送通知
            self.send_notification(title, message)
    
    def test_notification(self):
        """发送测试通知"""
        self.send_notification(
            title='🚀 套利监控已启动',
            message=f'正在监控: {", ".join(MONITORED_ASSETS)}'
        )


# 全局通知器实例
_notifier_instance = None


def get_notifier() -> ArbitrageNotifier:
    """获取全局通知器实例（单例模式）"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = ArbitrageNotifier()
    return _notifier_instance
