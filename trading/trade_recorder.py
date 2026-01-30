# -*- coding: utf-8 -*-
"""
====================================================================
交易记录器 (trade_recorder.py)
====================================================================

功能:
1. 记录所有交易历史到本地文件
2. 查询历史交易记录
3. 统计交易数据

存储格式: JSONL (每行一个 JSON 对象)
存储位置: trading/trade_history.jsonl
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class TradeRecorder:
    """交易记录器"""
    
    def __init__(self, history_file: str = None):
        """
        初始化交易记录器
        
        Args:
            history_file: 历史记录文件路径,默认为 trading/trade_history.jsonl
        """
        if history_file is None:
            # 默认保存在 trading 目录下
            current_dir = os.path.dirname(os.path.abspath(__file__))
            history_file = os.path.join(current_dir, 'trade_history.jsonl')
        
        self.history_file = history_file
        
        # 确保文件存在
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                pass
            print(f'[TradeRecorder] 📝 创建历史记录文件: {self.history_file}')
        else:
            print(f'[TradeRecorder] 📝 使用历史记录文件: {self.history_file}')
    
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        保存交易记录
        
        Args:
            trade_data: 交易数据字典,包含:
                - asset: 资产名称
                - direction: 交易方向 (HL_LONG_OS_SHORT / HL_SHORT_OS_LONG)
                - margin: 保证金
                - leverage: 杠杆
                - position_value: 持仓价值
                - hl_order: HL订单信息
                - os_order: OS订单信息
                - spread: 价差
                - estimated_profit: 预计盈利
                - total_cost: 总成本
        
        Returns:
            是否保存成功
        """
        try:
            # 添加时间戳
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.now().isoformat()
            
            # 写入文件 (追加模式)
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trade_data, ensure_ascii=False) + '\n')
            
            print(f'[TradeRecorder] ✅ 交易记录已保存: {trade_data.get("asset")} @ {trade_data.get("timestamp")}')
            return True
        
        except Exception as e:
            print(f'[TradeRecorder] ❌ 保存交易记录失败: {e}')
            return False
    
    def get_all_trades(self) -> List[Dict[str, Any]]:
        """
        获取所有交易记录
        
        Returns:
            交易记录列表
        """
        trades = []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        trades.append(json.loads(line))
            
            return trades
        
        except Exception as e:
            print(f'[TradeRecorder] 读取交易记录失败: {e}')
            return []
    
    def get_trades_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        获取某个资产的所有交易记录
        
        Args:
            asset: 资产名称 (如 'GOLD')
        
        Returns:
            该资产的交易记录列表
        """
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.get('asset') == asset]
    
    def get_trades_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        获取某一天的所有交易记录
        
        Args:
            date: 日期字符串 (格式: 'YYYY-MM-DD')
        
        Returns:
            该日期的交易记录列表
        """
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.get('timestamp', '').startswith(date)]
    
    def get_today_trade_count(self, asset: Optional[str] = None) -> int:
        """
        获取今天的交易次数
        
        Args:
            asset: 资产名称,如果指定则只统计该资产
        
        Returns:
            交易次数
        """
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = self.get_trades_by_date(today)
        
        if asset:
            today_trades = [t for t in today_trades if t.get('asset') == asset]
        
        return len(today_trades)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取交易统计数据
        
        Returns:
            统计数据字典,包含:
                - total_trades: 总交易次数
                - assets: 各资产交易统计
                - total_profit: 总盈亏 (预计)
        """
        all_trades = self.get_all_trades()
        
        stats = {
            'total_trades': len(all_trades),
            'assets': {},
            'total_profit': 0
        }
        
        # 按资产统计
        for trade in all_trades:
            asset = trade.get('asset', 'UNKNOWN')
            
            if asset not in stats['assets']:
                stats['assets'][asset] = {
                    'count': 0,
                    'total_margin': 0,
                    'total_position_value': 0,
                    'estimated_profit': 0
                }
            
            stats['assets'][asset]['count'] += 1
            stats['assets'][asset]['total_margin'] += trade.get('margin', 0)
            stats['assets'][asset]['total_position_value'] += trade.get('position_value', 0)
            stats['assets'][asset]['estimated_profit'] += trade.get('estimated_profit', 0)
            
            stats['total_profit'] += trade.get('estimated_profit', 0)
        
        return stats
    
    def print_statistics(self):
        """打印交易统计信息"""
        stats = self.get_statistics()
        
        print('\n' + '='*60)
        print('📊 交易统计数据')
        print('='*60)
        print(f'总交易次数: {stats["total_trades"]}')
        print(f'预计总盈亏: ${stats["total_profit"]:.2f}')
        print('\n各资产统计:')
        
        for asset, data in stats['assets'].items():
            print(f'\n  {asset}:')
            print(f'    交易次数: {data["count"]}')
            print(f'    累计保证金: ${data["total_margin"]:.2f}')
            print(f'    累计持仓: ${data["total_position_value"]:.2f}')
            print(f'    预计盈亏: ${data["estimated_profit"]:.2f}')
        
        print('='*60 + '\n')
