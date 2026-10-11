# -*- coding: utf-8 -*-
"""空投雷达 - 数据源层（多源降级）

主源：DefiLlama /protocols（免费、无需 Key）
- 融资数据：DefiLlama /raises 已改付费，改用本地 FUNDED_PROJECTS 名单维护
- 任务数据：Galxe GraphQL 在部分网络不可达，改用本地 TASK_HINTS 规则表维护
全部失效时返回 []，由主程序优雅降级。
"""
import math
import time

import requests

import config


def _get(url, times=config.RETRY_TIMES):
    """带重试的 GET，失败返回 None（不抛异常，保证优雅降级）"""
    for i in range(times):
        try:
            r = requests.get(url, timeout=config.REQUEST_TIMEOUT,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(2 * (i + 1))   # 退避重试：2s / 4s / 6s
    return None


def _match_any(name, names):
    """名称模糊匹配（不区分大小写，子串命中即算）"""
    low = name.lower()
    return any(n.lower() in low or low in n.lower() for n in names)


def fetch_defillama():
    """主源：筛出「未发币 + 高 TVL」的潜在空投协议"""
    data = _get("https://api.llama.fi/protocols")
    if not data:
        return None

    now = time.time()
    out = []
    for p in data:
        # 1) 未发币：无市值、无 CoinGecko 报价
        if p.get("mcap") is not None or p.get("gecko_id"):
            continue
        # 2) 类别与黑名单过滤
        if p.get("category") in config.CATEGORY_EXCLUDE:
            continue
        name = p.get("name", "")
        if _match_any(name, config.BLOCKLIST):
            continue
        # 3) TVL 门槛
        tvl = p.get("tvl") or 0
        if tvl < config.MIN_TVL_USD:
            continue
        # 4) 链过滤（如配置了 CHAIN_FOCUS）
        chains = p.get("chains") or []
        if config.CHAIN_FOCUS and not config.CHAIN_FOCUS.intersection(chains):
            continue

        listed_at = p.get("listedAt") or 0
        age_days = (now - listed_at) / 86400 if listed_at else 9999

        out.append({
            "id": str(p.get("id")),
            "name": name,
            "category": p.get("category", ""),
            "tvl": tvl,
            "chains": chains,
            "url": p.get("url", ""),
            "twitter": p.get("twitter", ""),
            "audited": bool(p.get("audits") and str(p.get("audits")) != "0"),
            "age_days": age_days,
            "listed_at": listed_at,
            "description": (p.get("description") or "").strip()[:100],
        })
    return out


# ==================== 打分模型（v2：倒U型规模分 + 融资 + 老项目扣分）====================

# 最可能发空投的 TVL 区间（百万美元）：太高=已成熟/早发币，太低=没实力
TVL_SWEET_LOW = 50.0      # 5000 万
TVL_SWEET_HIGH = 1000.0   # 10 亿


def _size_score(tvl_m):
    """倒 U 型规模分：5000万~10亿 最高 4 分，两端递减"""
    if tvl_m <= 0:
        return 0.0
    if tvl_m < TVL_SWEET_LOW:                     # 太小：线性上升
        return round(4.0 * (tvl_m / TVL_SWEET_LOW), 2)
    if tvl_m <= TVL_SWEET_HIGH:                   # 甜区：满分
        return 4.0
    # 超过 10 亿：头部项目，空投概率反而下降（多数早已发币或有代币计划）
    over = math.log10(tvl_m / TVL_SWEET_HIGH)
    return round(max(4.0 - over * 2.0, 0.5), 2)


def _cost_penalty(chains):
    """高成本环境：只在以太坊主网的协议，交互 Gas 贵"""
    if chains and all(c in ("Ethereum",) for c in chains):
        return 2.0
    return 0.0


def score(item):
    s = _size_score(item["tvl"] / 1e6)

    # 时间维度
    if item["age_days"] <= 180:
        s += 2.0                                  # 半年内新项目：空投预期最强
    elif item["age_days"] <= 365:
        s += 1.0
    elif item["age_days"] >= 9000:
        s -= 3.0                                  # listedAt 缺失 = 老牌项目，兑现概率低

    # 融资背景：有知名 VC 投资 → 必须发币回报投资人
    if item.get("funded"):
        s += 2.0

    # 零本金项目：无需投入本金即可参与，性价比最高
    if item.get("zero_cost"):
        s += 3.0

    if item["audited"]:
        s += 1.0                                  # 已审计：安全加成
    if not item["twitter"]:
        s -= 1.0                                  # 无社交账号：风险扣分

    s -= _cost_penalty(item["chains"])
    return round(s, 1)


def enrich(items):
    """补充融资/任务/零本金字段并计算综合分"""
    for it in items:
        it["funded"] = _match_any(it["name"], config.FUNDED_PROJECTS)
        it["zero_cost"] = _match_any(it["name"], config.ZERO_COST_PROJECTS)
        it["task_url"] = _task_url(it)
        it["score"] = score(it)
        it["source"] = "DefiLlama"
    return items


def _task_url(item):
    """任务链接：优先本地任务规则表，其次项目官网"""
    for hint in config.TASK_HINTS:
        if _match_any(item["name"], [hint["name"]]):
            return hint["url"]
    return ""


def fetch_all():
    """多源降级入口：依次尝试各数据源，全部失败返回 []"""
    for src_name, src_fn in [("DefiLlama", fetch_defillama)]:
        items = src_fn()
        if items is not None:
            return enrich(items)
    return []   # 全源失效：优雅降级，由主程序决定提示
