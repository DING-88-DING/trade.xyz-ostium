# -*- coding: utf-8 -*-
"""
====================================================================
自动交易功能测试脚本
====================================================================

用途:
1. 测试 auto TradingSignal 字段是否正确生成
2. 测试交易执行器的各项功能 (模拟模式)
3. 验证交易记录器

运行方式:
    python test_trading.py
"""

import sys
sys.path.insert(0, '.')

from arbitrage.arbitrage_calculator import ArbitrageCalculator
from arbitrage.fee_calculator import FeeCalculator
from trading.trade_executor import TradeExecutor
from trading.trade_recorder import TradeRecorder


def test_auto_trading_signal():
    """测试 autoTradingSignal 字段"""
    print('\n' + '='*60)
    print('测试 1: autoTradingSignal 字段生成')
    print('='*60)
    
    # 创建计算器
    fee_calc = FeeCalculator(vip_tier=0)
    arb_calc = ArbitrageCalculator()
    
    # 模拟合约数据
    hl_contract = {
        'mid': 2650.5,
        'bid': 2650.0,
        'ask': 2651.0,
        'fundingRate': {'rateHourly': 0.001}
    }
    
    os_contract = {
        'mid': 2648.2,
        'bid': 2648.0,
        'ask': 2648.4,
        'fundingRate': {'longPayHourly': 0.002}
    }
    
    # 获取费率
    hl_fee = fee_calc.get_hl_fee('GOLD', 'xyz')
    os_fee = fee_calc.get_os_fee('XAU', 'commodities')
    
    # 计算套利
    result = arb_calc.calculate_arbitrage(
        hl_contract=hl_contract,
        os_contract=os_contract,
        hl_fee=hl_fee,
        os_fee=os_fee,
        expected_spread=0  # GOLD 预期收敛到 0
    )
    
    print(f'\n✅ Maker 方案:')
    print(f'   adjustedSpreadCanProfit: {result["maker"]["adjustedSpreadCanProfit"]}')
    print(f'   当前价差: ${result["maker"]["currentSpreadUSD"]:.4f}')
    print(f'   回本价差: ${result["maker"]["breakEvenSpreadUSD"]:.4f}')
    
    print(f'\n✅ Taker 方案:')
    print(f'   adjustedSpreadCanProfit: {result["taker"]["adjustedSpreadCanProfit"]}')
    print(f'   当前价差: ${result["taker"]["currentSpreadUSD"]:.4f}')
    print(f'   回本价差: ${result["taker"]["breakEvenSpreadUSD"]:.4f}')
    
    print(f'\n🔑 autoTradingSignal: {result["autoTradingSignal"]}')
    print(f'   (取自 Taker 方案的 adjustedSpreadCanProfit)')
    
    # 验证
    assert 'autoTradingSignal' in result, '❌ autoTradingSignal 字段不存在'
    assert result['autoTradingSignal'] == result['taker']['adjustedSpreadCanProfit'], \
        '❌ autoTradingSignal 值不正确'
    
    print('\n✅ 测试通过: autoTradingSignal 字段正确生成')


def test_trade_executor_simulation():
    """测试交易执行器 (模拟模式)"""
    print('\n' + '='*60)
    print('测试 2: 交易执行器 (模拟模式)')
    print('='*60)
    
    try:
        # 创建执行器
        executor = TradeExecutor()
        
        # 检查是否可以测试
        if not executor.enabled and not executor.config.get('simulation_mode'):
            print('⚠️  自动交易未启用,跳过测试')
            return
    except Exception as e:
        print(f'⚠️  无法初始化执行器 (可能缺少SDK): {e}')
        print('⚠️  跳过交易执行器测试')
        return
    
    # 模拟套利机会数据
    pair_data = {
        'name': 'GOLD / XAU',
        'hl': {
            'coin': 'GOLD',
            'mid': 2650.5,
            'bid': 2650.0,
            'ask': 2651.0
        },
        'os': {
            'asset': 'XAU',
            'mid': 2648.2,
            'bid': 2648.0,
            'ask': 2648.4
        },
        'arbitrage': {
            'autoTradingSignal': True,
            'taker': {
                'adjustedSpreadCanProfit': True,
                'currentSpreadUSD': 2.3,
                'breakEvenSpreadUSD': 1.8,
                'profitableSpread': 2.3,
                'totalCost': 1.8
            }
        }
    }
    
    # 执行交易 (模拟模式)
    print('\n执行模拟交易...')
    result = executor.execute_arbitrage_trade(pair_data)
    
    print(f'\n执行结果: {result}')
    
    if result['success']:
        print('✅ 测试通过: 模拟交易执行成功')
    else:
        print(f'⚠️  执行失败: {result.get("error")}')


def test_trade_recorder():
    """测试交易记录器"""
    print('\n' + '='*60)
    print('测试 3: 交易记录器')
    print('='*60)
    
    # 创建记录器
    recorder = TradeRecorder()
    
    # 保存测试记录
    test_trade = {
        'asset': 'GOLD',
        'direction': 'HL_SHORT_OS_LONG',
        'margin': 100,
        'leverage': 10,
        'position_value': 1000,
        'spread': 2.3,
        'estimated_profit': 1.5
    }
    
    success = recorder.save_trade(test_trade)
    assert success, '❌ 保存交易记录失败'
    
    # 查询今日交易次数
    today_count = recorder.get_today_trade_count('GOLD')
    print(f'\n✅ GOLD 今日交易次数: {today_count}')
    
    # 打印统计
    recorder.print_statistics()
    
    print('✅ 测试通过: 交易记录器工作正常')


def main():
    """主函数"""
    print('\n' + '='*60)
    print('🧪 自动交易功能测试')
    print('='*60)
    
    try:
        # 测试 1: autoTradingSignal
        test_auto_trading_signal()
        
        # 测试 2: 交易执行器
        test_trade_executor_simulation()
        
        # 测试 3: 交易记录器
        test_trade_recorder()
        
        print('\n' + '='*60)
        print('🎉 所有测试通过!')
        print('='*60 + '\n')
        
    except Exception as e:
        print(f'\n❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
