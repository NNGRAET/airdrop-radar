# -*- coding: utf-8 -*-
"""空投雷达 - 数据源层（多源降级）

主源：DefiLlama /protocols（免费、无需 Key、国内一般可直连）
备源：预留接口位，主源全部失败时优雅降级（返回空列表，不抛异常）
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


def fetch_defillama():
    """主源：DefiLlama 协议列表 → 筛出「未发币 + 高 TVL」的潜在空投协议"""
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
        if any(b.lower() in name.lower() for b in config.BLOCKLIST):
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
        })
    return out


# ---- 打分逻辑：综合分 = 规模分 + 新上线加成 + 审计加成 - 成本扣分 ----

# 高成本环境：只在以太坊主网的协议，交互 Gas 贵
def _cost_penalty(chains):
    if chains and all(c in ("Ethereum",) for c in chains):
        return 2.0
    return 0.0


def score(item):
    s = min(math.log10(max(item["tvl"], 1) / 1e6), 4.0)   # 规模分 0~4
    if item["age_days"] <= 180:
        s += 2.0                                          # 上线半年内：新项目加成
    elif item["age_days"] <= 365:
        s += 1.0
    if item["audited"]:
        s += 1.0                                          # 已审计：安全加成
    if not item["twitter"]:
        s -= 1.0                                          # 无社交账号：风险扣分
    s -= _cost_penalty(item["chains"])                    # 主网高 Gas 扣分
    return round(s, 1)


def fetch_all():
    """多源降级入口：依次尝试各数据源，全部失败返回 []"""
    for src_name, src_fn in [("DefiLlama", fetch_defillama)]:
        items = src_fn()
        if items is not None:
            for it in items:
                it["score"] = score(it)
                it["source"] = src_name
            return items
    return []   # 全源失效：优雅降级，由主程序决定提示
