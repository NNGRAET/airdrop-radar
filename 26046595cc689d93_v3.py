# -*- coding: utf-8 -*-
"""空投雷达 - 主程序（Windows 任务计划程序每小时跑一次）

流程：抓取 → 打分 → 去重（只推新增）→ 推送微信 → 落盘日志
用法：python airdrop_monitor.py
"""
import json
import os
import sys
from datetime import datetime

import requests

import config
import sources

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen.json")
LOG_DIR = os.path.join(BASE_DIR, "log")
os.makedirs(LOG_DIR, exist_ok=True)


def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    with open(os.path.join(LOG_DIR, datetime.now().strftime("%Y%m%d") + ".log"),
              "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_seen(seen):
    # 只保留最近 2000 条，防止文件无限膨胀
    if len(seen) > 2000:
        seen = dict(sorted(seen.items(), key=lambda kv: kv[1])[-2000:])
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=1)


def push_serverchan(title, content):
    if not config.SERVERCHAN_SENDKEY:
        return False
    try:
        url = "https://sctapi.ftqq.com/%s.send" % config.SERVERCHAN_SENDKEY
        r = requests.post(url, data={"title": title, "desp": content},
                          timeout=config.REQUEST_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def push_pushplus(title, content):
    if not config.PUSHPLUS_TOKEN:
        return False
    try:
        r = requests.post("http://www.pushplus.plus/send", json={
            "token": config.PUSHPLUS_TOKEN, "title": title,
            "content": content, "template": "markdown",
        }, timeout=config.REQUEST_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def push(title, content):
    """推送降级链：Server酱 → PushPlus → 仅日志"""
    if push_serverchan(title, content):
        log("推送成功：Server酱")
    elif push_pushplus(title, content):
        log("推送成功：PushPlus")
    else:
        log("推送渠道未配置或均失败，仅记录日志")


def fmt_money(v):
    return "$%.0fM" % (v / 1e6) if v >= 1e6 else "$%.0fK" % (v / 1e3)


def build_report(new_items, total):
    now = datetime.now().strftime("%m-%d %H:%M")
    lines = ["## 空投雷达 %s" % now,
             "> 新增候选 **%d** 个｜监控池共 %d 个未发币协议" % (len(new_items), total), ""]
    for i, it in enumerate(new_items, 1):
        chains = ", ".join(it["chains"][:3]) or "-"
        audit = "已审计" if it["audited"] else "未审计"
        age = "上线%d天" % it["age_days"] if it["age_days"] < 9000 else "老项目"
        lines += [
            "### %d. %s（评分 %.1f）" % (i, it["name"], it["score"]),
            "- 类别：%s｜TVL：%s｜%s" % (it["category"], fmt_money(it["tvl"]), age),
            "- 链：%s｜%s" % (chains, audit),
        ]
        if it["url"]:
            lines.append("- 官网：%s" % it["url"])
        if it["twitter"]:
            lines.append("- 推特：https://x.com/%s" % it["twitter"])
        lines.append("")
    lines += ["---", "提示：交互请用小额钱包，只授权必要额度，谨防钓鱼网站。"]
    return "\n".join(lines)


def main():
    log("==== 开始抓取 ====")
    items = sources.fetch_all()

    if not items:
        # 数据源全部失效：优雅降级，只发一条简洁提示
        log("数据源暂不可用，本次跳过")
        push("空投雷达：数据源暂不可用", "本次抓取失败（境外源网络波动），下个周期自动重试。")
        return

    items.sort(key=lambda x: -x["score"])
    seen = load_seen()
    now_ts = datetime.now().timestamp()

    new_items = [it for it in items if it["id"] not in seen]
    for it in new_items:
        seen[it["id"]] = now_ts
    save_seen(seen)

    log("监控池 %d 个，新增 %d 个" % (len(items), len(new_items)))

    if not new_items:
        log("无新增机会，不推送")
        return

    report = build_report(new_items[:config.TOP_N_PUSH], len(items))
    push("空投雷达：发现 %d 个新机会" % len(new_items), report)
    log("==== 完成 ====")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 兜底：任何未预期错误都不让程序崩出报错刷屏
        log("运行异常：%s" % e)
        sys.exit(0)
