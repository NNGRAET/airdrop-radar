# -*- coding: utf-8 -*-
"""空投雷达 - 配置文件（按需修改）

提示：本地跑可直接把 SendKey 填在引号里；云端跑保持留空，用 GitHub Secrets 注入。
"""
import os as _os

# ========== 推送配置 ==========
SERVERCHAN_SENDKEY = _os.environ.get("SERVERCHAN_SENDKEY", "")
PUSHPLUS_TOKEN = _os.environ.get("PUSHPLUS_TOKEN", "")

# ========== 筛选参数 ==========
MIN_TVL_USD = 10_000_000      # 最低 TVL（美元）
TOP_N_PUSH = 5                # 微信单次最多推送几条新机会
CATEGORY_EXCLUDE = {"CEX", "Chain", "Foundation"}

# 已发币/不可能空投的协议黑名单（名字含以下即可，可持续补充）
BLOCKLIST = {
    "Aave", "WBTC", "Sky Lending", "Binance staked ETH", "Coinbase Bridge",
    "Hyperliquid Bridge", "JustLend", "Spark", "Fluid", "Venus", "Compound",
    "Curve", "Uniswap", "Maker", "Lido", "EigenLayer", "ether.fi",
    "Chainlink", "CCIP", "Bittensor", "dTAO", "Morpho", "Pendle", "Ethena",
    "Maple", "PancakeSwap", "Alchemix",
}

# ========== 融资背景名单（有知名 VC 投资 → 发币概率大增，+2 分）==========
# DefiLlama 融资接口已付费，改为人工维护。名称子串匹配，可随时补充。
FUNDED_PROJECTS = {
    # 公链 / 基础设施
    "Monad", "Berachain", "Story", "Movement", "Fuel", "Linea", "Scroll",
    "zkSync", "Starknet", "Aleo", "Celestia", "Eclipse", "MegaETH",
    # DeFi
    "Ethena", "Pendle", "EigenLayer", "Babylon", "Symbiotic", "Karak",
    "Morpho", "Spark", "Fluid", "Ondo", "Ethena", "Drift", "Kamino",
    "Marginfi", "Jupiter", "Sanctum", "Zeta", "Parcl", "Tensor",
    # L2 / Rollup 相关
    "Taiko", "Manta", "Blast", "Mode", "Zora", "Base",
    # 新兴热点
    "Hyperliquid", "Sonic", "Plasma", "Boundless", "Union", "Nexus",
    "Irys", "Fogo", "DoubleZero", "Solayer", "Reya", "Corn", "Swell",
}

# ========== 任务提示规则表（协议名子串 -> 任务/活动入口）==========
# Galxe 接口在部分网络不可达，改为人工维护常用任务入口。
TASK_HINTS = [
    {"name": "Binance", "url": "https://www.binance.com/zh-CN/activity"},
    {"name": "Monad", "url": "https://app.galxe.com/quest/monad"},
    {"name": "Linea", "url": "https://app.galxe.com/quest/Linea"},
    {"name": "Scroll", "url": "https://app.galxe.com/quest/Scroll"},
    {"name": "Base", "url": "https://app.galxe.com/quest/Base"},
    {"name": "Manta", "url": "https://app.galxe.com/quest/MantaNetwork"},
]

# ========== 状态变化检测阈值 ==========
TVL_SURGE_RATIO = 1.5    # TVL 较上次上涨超 50% → 推送（可能有动作）
FRESH_DAYS = 30          # 上线 ≤30 天视为「新上线」，必推

# ========== 零本金项目名单（免费可参与，无需投入本金，+3 分）==========
# 挂机型 DePIN / 测试网 / 纯积分任务：只用时间或闲置资源，不花本金
ZERO_COST_PROJECTS = {
    # 挂机型（DePIN，共享带宽/算力）
    "Grass", "Nodepay", "Network3", "Teneo", "Dawn", "Blockless",
    "Gradient", "Proxypal", "Nesa", "Hyperbolic", "Koii",
    # 测试网型
    "Canton", "DogeOS", "Chikyū", "TitanX",
    # 纯积分/社交任务型
    "June", "Rainbow", "Wormhole", "Zealy", "Galxe", "Layer3",
}

# ========== 网络 ==========
REQUEST_TIMEOUT = 20
RETRY_TIMES = 3
CHAIN_FOCUS = set()      # 留空 = 全部链。例：{"Base", "Solana"}
