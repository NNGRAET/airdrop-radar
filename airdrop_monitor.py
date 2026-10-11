# -*- coding: utf-8 -*-
"""空投雷达 - 主程序

流程：抓取 → 打分 → 状态变化检测 → 微信推送 → 落盘日志
用法：python airdrop_monitor.py
"""
import json
import os
import sys

import requests

import common
import config
import sources

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen.json")
LOG_DIR = os.path.join(BASE_DIR, "log")
os.makedirs(LOG_DIR, exist_ok=True)


def log(msg):
    line = "[%s] %s" % (common.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    with open(os.path.join(LOG_DIR, common.now().strftime("%Y%m%d") + ".log"),
              "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_seen():
    """读取状态库，自动兼容旧格式（旧：{id: ts}）"""
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    seen = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            seen[k] = v
        else:                                   # 旧格式迁移
            seen[k] = {"ts": v, "tvl": 0, "audited": False, "days": 9999}
    return seen


def save_seen(seen):
    if len(seen) > 3000:                        # 防止无限膨胀
        seen = dict(sorted(seen.items(), key=lambda kv: kv[1].get("ts", 0))[-3000:])
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=1)


# ==================== 推送 ====================

def push_serverchan(title, content):
    if not config.SERVERCHAN_SENDKEY:
        return False, "未配置"
    try:
        url = "https://sctapi.ftqq.com/%s.send" % config.SERVERCHAN_SENDKEY
        r = requests.post(url, data={"title": title, "desp": content},
                          timeout=config.REQUEST_TIMEOUT)
        if r.status_code == 200:
            # 解析返回体，Server酱 即使 200 也可能 code!=0
            try:
                j = r.json()
                if j.get("code") not in (0, None):
                    return False, "接口返回 %s：%s" % (j.get("code"), j.get("message", ""))
            except Exception:
                pass
            return True, "成功"
        return False, "HTTP %s" % r.status_code
    except Exception as e:
        return False, "%s" % type(e).__name__


def push_pushplus(title, content):
    if not config.PUSHPLUS_TOKEN:
        return False, "未配置"
    try:
        r = requests.post("http://www.pushplus.plus/send", json={
            "token": config.PUSHPLUS_TOKEN, "title": title,
            "content": content, "template": "markdown",
        }, timeout=config.REQUEST_TIMEOUT)
        if r.status_code == 200:
            try:
                if r.json().get("code") != 200:
                    return False, "接口返回 %s" % r.json().get("msg", "")
            except Exception:
                pass
            return True, "成功"
        return False, "HTTP %s" % r.status_code
    except Exception as e:
        return False, "%s" % type(e).__name__


def push(title, content):
    """推送降级链：Server酱 → PushPlus，返回详细原因便于排查"""
    ok, why = push_serverchan(title, content)
    log("Server酱 推送：%s（%s）" % ("成功" if ok else "失败", why))
    if ok:
        return
    ok2, why2 = push_pushplus(title, content)
    log("PushPlus 推送：%s（%s）" % ("成功" if ok2 else "失败", why2))
    if not ok2:
        log("⚠️ 所有推送渠道均失败，请检查 SendKey 是否正确")


# ==================== 报告 ====================

def fmt_money(v):
    return "$%.0fM" % (v / 1e6) if v >= 1e6 else "$%.0fK" % (v / 1e3)


def _item_lines(it):
    chains = ", ".join(it["chains"][:3]) or "-"
    audit = "已审计" if it["audited"] else "未审计"
    age = "上线%d天" % it["age_days"] if it["age_days"] < 9000 else "老项目"
    lines = [
        "### %s（评分 %.1f）" % (it["name"], it["score"]),
        "- 类别：%s｜TVL：%s｜%s" % (it["category"], fmt_money(it["tvl"]), age),
        "- 链：%s｜%s%s" % (chains, audit, "｜有融资" if it.get("funded") else ""),
    ]
    if it.get("description"):
        lines.append("- 说明：%s" % it["description"])
    if it["url"]:
        lines.append("- 官网：%s" % it["url"])
    if it.get("task_url"):
        lines.append("- 🎯 任务入口：%s" % it["task_url"])
    if it["twitter"]:
        lines.append("- 推特：https://x.com/%s" % it["twitter"])
    lines.append("")
    return lines


def build_report(new_items, changes, total):
    now = common.now().strftime("%m-%d %H:%M")
    lines = ["## 空投雷达 %s" % now,
             "> 新增 **%d** 个｜状态变化 **%d** 个｜监控池 %d 个未发币协议"
             % (len(new_items), len(changes), total), ""]

    if new_items:
        lines += ["## 🆕 新发现机会", ""]
        for it in new_items:
            lines += _item_lines(it)

    if changes:
        lines += ["## ⚡ 状态变化（值得留意）", ""]
        for it, why in changes:
            lines.append("- **%s**：%s" % (it["name"], why))

    lines += ["---", "提示：交互请用小额钱包，只授权必要额度，谨防钓鱼网站。"]
    return "\n".join(lines)


# ==================== 主流程 ====================

def detect_changes(items, seen):
    """检测状态变化：TVL 暴涨 / 审计状态变化"""
    changes = []
    for it in items:
        old = seen.get(it["id"])
        if not old:
            continue
        old_tvl = old.get("tvl") or 0
        # TVL 暴涨（要求基数 ≥100 万，避免小基数噪声）
        if old_tvl >= 1_000_000 and it["tvl"] >= old_tvl * config.TVL_SURGE_RATIO:
            changes.append((it, "TVL 从 %s 涨到 %s（+%.0f%%）" % (
                fmt_money(old_tvl), fmt_money(it["tvl"]),
                (it["tvl"] / old_tvl - 1) * 100)))
        # 审计状态从无到有
        elif it["audited"] and not old.get("audited"):
            changes.append((it, "已完成审计，项目推进中"))
    return changes


def main():
    log("==== 开始抓取 ====")
    items = sources.fetch_all()

    if not items:
        log("数据源暂不可用，本次跳过")
        push("空投雷达：数据源暂不可用",
             "本次抓取失败（境外源网络波动），下个周期自动重试。")
        return

    items.sort(key=lambda x: -x["score"])
    seen = load_seen()
    now_ts = common.now().timestamp()

    new_items = [it for it in items if it["id"] not in seen]
    changes = detect_changes(items, seen)

    # 更新状态库
    for it in items:
        seen[it["id"]] = {"ts": now_ts, "tvl": it["tvl"],
                          "audited": it["audited"], "days": it["age_days"]}
    save_seen(seen)

    log("监控池 %d 个，新增 %d 个，状态变化 %d 个"
        % (len(items), len(new_items), len(changes)))

    if not new_items and not changes:
        log("无新增、无变化，不推送")
        return

    report = build_report(new_items[:config.TOP_N_PUSH], changes[:10], len(items))
    push("空投雷达：新增 %d｜变化 %d" % (len(new_items), len(changes)), report)
    log("==== 完成 ====")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("运行异常：%s" % e)
        sys.exit(0)
