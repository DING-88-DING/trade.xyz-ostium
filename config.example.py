"""
配置文件示例
复制此文件为 config.py 并填入你的 API 密钥

注意：请勿将 config.py 提交到公共代码仓库！
"""

# Arbitrum RPC URL（用于 Ostium SDK）
# 从 Alchemy 免费获取: https://www.alchemy.com/
# 1. 注册 Alchemy 账号
# 2. 创建 App，选择 Arbitrum One 网络
# 3. 复制 API Key 填入下方
ARBITRUM_RPC_URL = "https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY"

# 默认公共 RPC（兜底用）
# 当上面的 ARBITRUM_RPC_URL 未配置或无效时使用
DEFAULT_ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

# Hyperliquid API URL
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"

# Ostium REST API URL
OSTIUM_REST_API_URL = "https://metadata-backend.ostium.io"

