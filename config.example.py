"""
配置文件模板
使用方法: 复制此文件为 config.py, 并填入你的实际配置
注意: 请勿将 config.py 提交到公共代码仓库!
"""

# ========== 基础配置 ==========

# Arbitrum RPC URL (用于 Ostium SDK)
# 推荐从 Alchemy 或 Infura 获取免费 API Key
# Alchemy: https://www.alchemy.com/
# Infura: https://www.infura.io/
ARBITRUM_RPC_URL = "https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY"

# 默认公共 RPC (兜底用)
DEFAULT_ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

# Hyperliquid API URL
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"

# Ostium REST API URL
OSTIUM_REST_API_URL = "https://metadata-backend.ostium.io"


# ========== 自动交易配置 ==========
# ⚠️ 警告: 自动交易涉及真实资金风险,请充分测试后再启用!

# 总开关 (默认关闭,需要手动开启)
AUTO_TRADING_ENABLED = False

# Hyperliquid 交易配置
# 获取方式: 在 Hyperliquid 网站创建 API Key (需要交易权限)
# 注意: 私钥泄露将导致资金损失,请妥善保管!
HYPERLIQUID_WALLET_ADDRESS = ""  # 你的钱包地址 (0x...)
HYPERLIQUID_PRIVATE_KEY = ""     # 私钥 (用于签名交易)

# Ostium 交易配置  
# 使用你的 Arbitrum 钱包私钥
OSTIUM_WALLET_ADDRESS = ""  # 你的钱包地址 (0x...)
OSTIUM_PRIVATE_KEY = ""     # 私钥 (用于签名交易)

# 交易参数配置
TRADING_CONFIG = {
    # ========== 资金配置 ==========
    'margin_size': 100,              # 每次交易保证金 (USD), 默认 $100
                                     # 建议从小额开始测试 (如 $10-$50)
    
    'use_max_leverage': True,        # 是否使用最大杠杆 (默认 true)
                                     # 系统会自动查询该币种的最大杠杆
    
    'leverage_multiplier': 1.0,      # 杠杆乘数 (调整实际使用的杠杆比例)
                                     # 1.0 = 100% 最大杠杆
                                     # 0.5 = 50% 最大杠杆 (更保守)
                                     # 0.2 = 20% 最大杠杆
                                     # 示例: 如果 GOLD 最大杠杆 50x
                                     #       multiplier=0.2 → 实际使用 10x
    
    # ========== 监控资产 ==========
    'monitored_assets': ['GOLD', 'SILVER', 'COPPER', 'XYZ100'],
                                     # 只有这些资产会触发自动交易
                                     # 对应关系:
                                     # GOLD → XAU (黄金)
                                     # SILVER → XAG (白银)
                                     # COPPER → HG (铜)
                                     # XYZ100 → NDX (纳斯达克100)
    
    # ========== 风控参数 ==========
    'trade_cooldown': 0,             # 交易冷却时间 (秒, 0=不限制)
                                     # 套利机会转瞬即逝,默认不设冷却
                                     # 系统会通过检查持仓避免重复下单
                                     # 如需额外保护,可设为 30-60 秒
                                     # 
                                     # 示例:
                                     # 0: 不限制 (推荐)
                                     # 30: 同一资产30秒内不重复交易
                                     # 300: 5分钟冷却 (过于保守)
    
    'max_slippage': 0.005,           # 最大滑点容忍 (百分比)
                                     # 0.005 = 0.5%
                                     # 市价单实际成交价可能偏离当前价
                                     # 滑点过大会拒绝下单
    
    'max_daily_trades': 20,          # 每日最大交易次数 (每个资产)
                                     # 防止异常情况下频繁交易
                                     # 达到上限后当天不再交易该资产
    
    # ========== 测试模式 ==========
    'simulation_mode': True,         # 模拟模式 (默认开启)
                                     # True: 只记录交易计划,不真实下单
                                     # False: 真实下单 (⚠️ 有资金风险!)
                                     # 
                                     # ⚠️ 重要提示:
                                     # 1. 首次使用请保持 True,运行至少 24 小时
                                     # 2. 确认逻辑正确后,改为 False 并用小额测试
                                     # 3. 从 margin_size=10 开始,逐步增加
}


# ========== 配置说明 ==========
"""
快速开始步骤:

1. 复制此文件
   cp config.example.py config.py

2. 填写 API 配置
   - ARBITRUM_RPC_URL: 从 Alchemy 获取
   - HYPERLIQUID_WALLET_ADDRESS / PRIVATE_KEY: Hyperliquid 账户
   - OSTIUM_WALLET_ADDRESS / PRIVATE_KEY: Arbitrum 钱包

3. 保持模拟模式
   simulation_mode = True

4. 运行系统观察
   python websocket_server.py

5. 检查交易记录
   查看 trading/trade_history.jsonl

6. 确认无误后谨慎启用真实交易
   simulation_mode = False
   margin_size = 10  # 从小额开始!

风险提示:
- 密钥泄露会导致资金损失
- 市场波动可能导致滑点超出预期
- Hyperliquid 成交但 Ostium 失败会产生单边持仓
- 高杠杆放大盈亏,谨慎使用

建议:
- 先用模拟模式运行一周
- 用小额测试至少一周  
- 设置合理的风控参数
- 定期检查持仓和交易记录
"""
