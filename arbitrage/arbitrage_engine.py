# -*- coding: utf-8 -*-
"""
====================================================================
套利引擎模块 (arbitrage_engine.py)
====================================================================

这个文件的作用：
- 这是套利模块的"总入口"和"控制中心"
- 整合数据采集和套利计算
- 被 websocket_server.py 直接调用

工作流程：
1. 接收 Hyperliquid 和 Ostium 的原始数据
2. 自动匹配两个平台的共同资产
3. 调用 FeeCalculator 计算费率
4. 调用 ArbitrageCalculator 计算套利
5. 返回完整的分析结果给前端

核心概念 - 共同资产 (Common Pairs)：
- 只有两个平台都有的资产才能进行套利
- 例如: BTC 在 HL 和 OS 都有 → 可以套利
- 例如: SHIB 只在 HL 有 → 无法套利

关于类型提示:
- Dict[str, Any]: 字典类型，键是字符串，值可以是任何类型
- List[Dict]: 列表类型，每个元素是字典
- Optional[T]: 可选类型，可以是 T 类型或 None
"""

# ==================== 导入依赖 ====================
from typing import Dict, List, Any, Optional
from datetime import datetime  # 用于生成时间戳

# 从同目录的其他模块导入
from .fee_config import NAME_MAPPING, REVERSE_NAME_MAPPING, PRIORITY_ASSETS
from .fee_calculator import FeeCalculator
from .arbitrage_calculator import ArbitrageCalculator


class ArbitrageEngine:
    """
    套利引擎 - 整合数据与计算的核心类
    
    这个类是整个套利模块的"大脑"，负责协调各个组件工作
    
    使用示例:
        # 创建引擎实例 (VIP 0 等级)
        engine = ArbitrageEngine(vip_tier=0)
        
        # 更新数据 (通常由 WebSocket 回调触发)
        engine.update_hl_data(hl_contracts)
        engine.update_os_data(os_contracts)
        
        # 获取套利分析结果
        result = engine.get_common_pairs()
        print(result['pairs'])  # 共同资产列表，每个都包含套利分析
        
        # 用户切换 VIP 等级时
        engine.set_vip_tier(3)  # 自动重新计算所有套利数据
    """
    
    def __init__(self, vip_tier: int = 0):
        """
        初始化套利引擎
        
        Args:
            vip_tier (int): 初始 VIP 等级 (0-6)
                           影响费率计算，进而影响套利分析结果
        
        创建引擎时会自动创建:
        - fee_calculator: 费率计算器实例
        - arbitrage_calculator: 套利计算器实例
        - 三个数据缓存列表
        """
        # 保存 VIP 等级
        self.vip_tier = vip_tier
        
        # 创建费率计算器 (传入 VIP 等级)
        self.fee_calculator = FeeCalculator(vip_tier)
        
        # 创建套利计算器 (使用默认配置)
        self.arbitrage_calculator = ArbitrageCalculator()
        
        # ==================== 数据缓存 ====================
        # 这些列表用于存储最新的数据
        # List[Dict] 表示"字典列表"，即 [{...}, {...}, ...]
        
        # Hyperliquid 合约列表
        # 格式: [{'coin': 'BTC', 'mid': 100000, 'bid': ..., 'fundingRate': {...}}, ...]
        self.hl_contracts: List[Dict] = []
        
        # Ostium 合约列表
        # 格式: [{'from': 'BTC', 'to': 'USD', 'group': 'crypto', 'mid': ..., ...}, ...]
        self.os_contracts: List[Dict] = []
        
        # 共同资产列表 (计算后的结果)
        # 格式: [{'name': 'BTC', 'hl': {...}, 'os': {...}, 'arbitrage': {...}}, ...]
        self.common_pairs: List[Dict] = []
        
        # 打印初始化日志
        print(f'[ArbitrageEngine] 初始化完成，VIP 等级: {vip_tier}')
    
    def set_vip_tier(self, tier: int):
        """
        更新 VIP 等级
        
        当用户在前端切换 VIP 等级时，会调用此方法
        更新后会自动重新计算所有套利数据
        
        Args:
            tier (int): 新的 VIP 等级 (0-6)
        """
        # 限制范围在 0-6
        self.vip_tier = min(max(tier, 0), 6)
        
        # 同步更新费率计算器的 VIP 等级
        self.fee_calculator.set_vip_tier(self.vip_tier)
        
        print(f'[ArbitrageEngine] VIP 等级更新为: {self.vip_tier}')
        
        # 如果有数据，重新计算套利
        # 使用 and 确保两个列表都有数据
        if self.hl_contracts and self.os_contracts:
            self._calculate_common_pairs()
    
    def update_hl_data(self, contracts: List[Dict]):
        """
        更新 Hyperliquid 数据
        
        当后端收到 Hyperliquid 的新数据时调用此方法
        会为每个合约计算并添加费率信息
        
        Args:
            contracts (List[Dict]): Hyperliquid 合约数据列表
        """
        # 为每个合约添加费率信息
        for contract in contracts:
            coin = contract.get('coin', '')
            dex = contract.get('dex', 'main')
            fee = self.fee_calculator.get_hl_fee(coin, dex)
            # 添加费率到合约数据中
            # 使用 round(..., 6) 保留完整精度，如 0.00768%
            contract['fee'] = {
                't': round(fee['t'], 6),
                'm': round(fee['m'], 6)
            }
        
        self.hl_contracts = contracts
        self._calculate_common_pairs()
    
    def update_os_data(self, contracts: List[Dict]):
        """
        更新 Ostium 数据
        
        当后端收到 Ostium 的新数据时调用此方法
        会为每个合约计算并添加费率信息
        
        Args:
            contracts (List[Dict]): Ostium 合约数据列表
        """
        # 为每个合约添加费率信息
        for contract in contracts:
            asset = contract.get('from', '')
            group = contract.get('group', 'crypto')
            fee = self.fee_calculator.get_os_fee(asset, group)
            # 添加费率到合约数据中
            contract['fee'] = fee  # 包含 rate/t/m 和 oracle
        
        self.os_contracts = contracts
        self._calculate_common_pairs()
    
    def _normalize_coin_name(self, coin: str) -> str:
        """
        标准化币种名称
        
        不同数据源的币种名可能有前缀，比如 'xyz:GOLD'
        这个方法去除前缀，只保留纯币种名
        
        Args:
            coin (str): 原始币种名，可能包含前缀
        
        Returns:
            str: 标准化后的大写币种名
        
        示例:
            _normalize_coin_name('xyz:GOLD') → 'GOLD'
            _normalize_coin_name('BTC') → 'BTC'
            _normalize_coin_name('btc') → 'BTC'
        
        注意: 方法名以单下划线 _ 开头表示这是"内部方法"
              虽然外部也能调用，但按惯例不应该在类外部使用
        """
        # 如果包含冒号，按冒号分割，取最后一部分
        # split(':') 将 'xyz:GOLD' 变成 ['xyz', 'GOLD']
        # [-1] 取最后一个元素 'GOLD'
        if ':' in coin:
            return coin.split(':')[-1].upper()
        return coin.upper()
    
    def _calculate_common_pairs(self):
        """
        计算共同资产的套利数据
        
        这是引擎的核心私有方法，执行以下步骤:
        1. 检查是否有足够的数据
        2. 构建 Hyperliquid 的资产映射表
        3. 遍历 Ostium 资产，查找匹配的 HL 资产
        4. 对每个配对计算套利数据
        5. 按优先级排序
        6. 保存到 self.common_pairs
        """
        # ---- 步骤1: 检查数据 ----
        # 如果任一列表为空，直接返回
        if not self.hl_contracts or not self.os_contracts:
            return
        
        # ---- 步骤2: 构建 Hyperliquid 映射表 ----
        # 将 HL 合约列表转换为字典，方便快速查找
        # 格式: {'BTC': {合约数据}, 'ETH': {合约数据}, ...}
        hl_map = {}
        for contract in self.hl_contracts:
            coin = contract.get('coin', '')
            normalized = self._normalize_coin_name(coin)
            hl_map[normalized] = contract
        
        # ---- 步骤3 & 4: 匹配共同资产并计算套利 ----
        common_pairs = []
        
        for os_contract in self.os_contracts:
            # 获取 Ostium 资产名称 (大写)
            os_name = os_contract.get('from', '').upper()
            
            # 尝试通过名称映射找到对应的 HL 资产名
            # 例如: OS 叫 'XAU' → HL 叫 'GOLD'
            # NAME_MAPPING.get(os_name, os_name) 的意思是:
            #   如果 os_name 在映射表中，返回映射后的名称
            #   否则返回原名称 (即两边名称相同)
            hl_name = NAME_MAPPING.get(os_name, os_name)
            
            # 检查 HL 是否有这个资产
            if hl_name in hl_map:
                # 找到匹配! 获取 HL 合约数据
                hl_contract = hl_map[hl_name]
                
                # 计算这个配对的套利数据
                arbitrage_result = self._calculate_pair_arbitrage(hl_contract, os_contract)
                
                # 构建配对数据结构
                pair_data = {
                    # 显示名称: 如果名称相同就用一个，否则显示 "HL名/OS名"
                    'name': os_name if os_name == hl_name else f'{hl_name} / {os_name}',
                    'hl': hl_contract,              # Hyperliquid 原始数据
                    'os': os_contract,              # Ostium 原始数据
                    'arbitrage': arbitrage_result   # 套利分析结果
                }
                common_pairs.append(pair_data)
        
        # ---- 步骤5: 按优先级排序 ----
        common_pairs = self._sort_by_priority(common_pairs)
        
        # ---- 步骤6: 保存结果 ----
        self.common_pairs = common_pairs
    
    def _calculate_pair_arbitrage(
        self, 
        hl_contract: Dict[str, Any], 
        os_contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算单个交易对的套利数据
        
        这个方法协调 FeeCalculator 和 ArbitrageCalculator 完成计算
        
        Args:
            hl_contract (dict): Hyperliquid 合约数据
            os_contract (dict): Ostium 合约数据
        
        Returns:
            dict: 套利分析结果，包含 maker 和 taker 两种方案
        """
        # ---- 获取 HL 费率 ----
        coin = hl_contract.get('coin', '')
        dex = hl_contract.get('dex', 'main')  # 'main' 或 'xyz'
        hl_fee = self.fee_calculator.get_hl_fee(coin, dex)
        
        # ---- 获取 OS 费率 ----
        os_asset = os_contract.get('from', '')
        os_group = os_contract.get('group', 'crypto')
        os_fee = self.fee_calculator.get_os_fee(os_asset, os_group)
        
        # ---- 调用套利计算器 ----
        return self.arbitrage_calculator.calculate_arbitrage(
            hl_contract, os_contract, hl_fee, os_fee
        )
    
    def _sort_by_priority(self, pairs: List[Dict]) -> List[Dict]:
        """
        按优先级排序共同资产
        
        PRIORITY_ASSETS 中的资产会排在前面
        这样用户最关心的资产（如黄金、白银）总是显示在顶部
        
        Args:
            pairs (List[Dict]): 交易对列表
        
        Returns:
            List[Dict]: 排序后的列表
        """
        def get_priority(pair):
            """
            获取单个配对的优先级
            
            这是一个内部函数，只在 _sort_by_priority 内部使用
            返回值越小，排序越靠前
            """
            os_name = pair['os'].get('from', '').upper()
            hl_name = self._normalize_coin_name(pair['hl'].get('coin', ''))
            
            # 检查是否在优先资产列表中
            for i, asset in enumerate(PRIORITY_ASSETS):
                if os_name == asset or hl_name == asset:
                    return i  # 返回在列表中的位置作为优先级
            
            # 不在优先列表中的资产，排在最后
            return len(PRIORITY_ASSETS)
        
        # sorted() 函数按 key 返回值排序
        # key=get_priority 表示用 get_priority 函数的返回值作为排序依据
        return sorted(pairs, key=get_priority)
    
    # ==================== 数据获取方法 ====================
    # 以下方法用于获取处理后的数据，供外部 (如 websocket_server.py) 调用
    
    def get_hl_data(self) -> Dict[str, Any]:
        """
        获取处理后的 Hyperliquid 数据
        
        返回排序后的数据包，可以直接发送给前端
        
        Returns:
            dict: {
                'contracts': [...],  # 合约列表 (已排序)
                'updated_at': '2024-01-20 12:00:00'
            }
        """
        # 按优先级排序
        sorted_contracts = self._sort_hl_contracts(self.hl_contracts)
        return {
            'contracts': sorted_contracts,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_os_data(self) -> Dict[str, Any]:
        """
        获取处理后的 Ostium 数据
        
        返回排序后的数据包
        
        Returns:
            dict: {'contracts': [...], 'updated_at': '...'}
        """
        # 按优先级排序
        sorted_contracts = self._sort_os_contracts(self.os_contracts)
        return {
            'contracts': sorted_contracts,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _sort_hl_contracts(self, contracts: List[Dict]) -> List[Dict]:
        """按优先级排序 HL 合约"""
        def get_priority(contract):
            coin = self._normalize_coin_name(contract.get('coin', ''))
            for i, asset in enumerate(PRIORITY_ASSETS):
                if coin == asset:
                    return i
            return len(PRIORITY_ASSETS)
        return sorted(contracts, key=get_priority)
    
    def _sort_os_contracts(self, contracts: List[Dict]) -> List[Dict]:
        """按优先级排序 OS 合约"""
        def get_priority(contract):
            asset = contract.get('from', '').upper()
            for i, priority_asset in enumerate(PRIORITY_ASSETS):
                if asset == priority_asset:
                    return i
            return len(PRIORITY_ASSETS)
        return sorted(contracts, key=get_priority)
    
    def get_common_pairs(self) -> Dict[str, Any]:
        """
        获取共同资产的套利分析数据
        
        这是前端 Arbitrage Monitor 面板需要的数据
        
        Returns:
            dict: {
                'pairs': [...],  # 配对列表，每个都包含套利分析
                'vip_tier': 0,   # 当前 VIP 等级
                'updated_at': '...'
            }
        """
        return {
            'pairs': self.common_pairs,
            'vip_tier': self.vip_tier,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_full_data(self) -> Dict[str, Any]:
        """
        获取完整数据
        
        一次性返回所有数据，包含 HL、OS 和套利分析
        适合初始化连接时一次性发送所有数据
        
        Returns:
            dict: {
                'hyperliquid': {...},  # HL 数据
                'ostium': {...},       # OS 数据
                'common_pairs': {...}  # 套利分析
            }
        """
        return {
            'hyperliquid': self.get_hl_data(),
            'ostium': self.get_os_data(),
            'common_pairs': self.get_common_pairs()
        }
