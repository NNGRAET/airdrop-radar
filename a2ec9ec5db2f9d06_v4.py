# -*- coding: utf-8 -*-
"""空投雷达 - 配置文件（按需修改）"""

# ========== 推送配置（二选一或都填，都为空则只打印不推送）==========
# 本地跑：直接填在引号里；云端跑：留空，在 GitHub Secrets 里配置同名变量
import os as _os
# Server酱 Turbo 版 SendKey，申请：https://sct.ftqq.com （微信扫码即可）
SERVERCHAN_SENDKEY = _os.environ.get("SERVERCHAN_SENDKEY", "")
# PushPlus token（备用推送），申请：http://www.pushplus.plus
PUSHPLUS_TOKEN = _os.environ.get("PUSHPLUS_TOKEN", "")

# ========== 筛选参数 ==========
MIN_TVL_USD = 10_000_000      # 最低 TVL（美元），低于此值不关注
TOP_N_PUSH = 5                # 每次最多推送几条新机会
CATEGORY_EXCLUDE = {"CEX", "Chain", "Foundation"}   # 不关注的类别

# 已发币/不可能空投的协议黑名单（会持续补充，可自行添加）
BLOCKLIST = {
    "Aave", "WBTC", "Sky Lending", "Binance staked ETH", "Coinbase Bridge",
    "Hyperliquid Bridge", "JustLend", "Spark", "Fluid", "Venus", "Compound",
    "Curve", "Uniswap", "Maker", "Lido", "EigenLayer", "ether.fi",
    "Chainlink", "CCIP", "Bittensor", "dTAO", "Morpho", "Pendle", "Ethena",
}

# 只关注这些链（留空 = 全部链）。例：CHAIN_FOCUS = {"Base", "Arbitrum", "Solana"}
CHAIN_FOCUS = set()

# ========== 网络 ==========
REQUEST_TIMEOUT = 20          # 单次请求超时（秒）
RETRY_TIMES = 3               # 失败重试次数
# 如需代理，设置系统环境变量 HTTPS_PROXY 即可，requests 会自动识别
