# -*- coding: utf-8 -*-
"""空投雷达 - 每日网页报告生成器

生成 report.html（iPad 自适应）+ report.md（供知识库保存）
用法：python daily_report.py [输出目录]
"""
import json
import os
import sys

import common
import config
import sources

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen.json")


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fmt_money(v):
    if v >= 1e9:
        return "$%.1fB" % (v / 1e9)
    if v >= 1e6:
        return "$%.0fM" % (v / 1e6)
    return "$%.0fK" % (v / 1e3)


def score_badge(s, funded):
    fire = "🔥" if s >= 5 else ""
    cls = "hot" if s >= 5 else ("mid" if s >= 3 else "low")
    fund = ' <span class="fund">💰</span>' if funded else ""
    return '<span class="badge %s">%s %.1f</span>%s' % (cls, fire, s, fund)


def row(it, is_new=False):
    chains = ", ".join(it["chains"][:3]) or "-"
    audit = '<span class="ok">已审计</span>' if it["audited"] else '<span class="warn">未审计</span>'
    new_tag = ' <span class="new">NEW</span>' if is_new else ""
    link = it["url"] or ("https://x.com/%s" % it["twitter"] if it["twitter"] else "#")
    listed = common.ts_to_str(it.get("listed_at"))
    age = it["age_days"]
    fresh = '<span class="fresh">⚡新上线</span>' if age <= config.FRESH_DAYS else ""
    zero = '<span class="zero">💸零本金</span>' if it.get("zero_cost") else ""
    desc = ('<br><small class="desc">📝 %s</small>' % it["description"]) if it.get("description") else ""
    task = ('<br><small class="task">🎯 <a href="%s" onclick="event.stopPropagation()">任务入口</a></small>'
            % it["task_url"]) if it.get("task_url") else ""
    return """<tr onclick="window.open('%s')" class="clickable">
<td class="name">%s%s%s%s<br><small>%s · 上线 %s（%d天）%s</small>%s</td>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td>
</tr>""" % (link, it["name"], new_tag, fresh, zero, it["category"], listed, age, desc, task,
            fmt_money(it["tvl"]), chains, audit, score_badge(it["score"], it.get("funded")))


HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>空投雷达日报 {date}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  background:#0d1117; color:#e6edf3; padding:16px; max-width:960px; margin:0 auto; }}
h1 {{ font-size:22px; margin-bottom:4px; }}
.sub {{ color:#8b949e; font-size:13px; margin-bottom:16px; }}
.cards {{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }}
.card {{ flex:1; min-width:100px; background:#161b22; border:1px solid #30363d;
  border-radius:10px; padding:12px; text-align:center; }}
.card .num {{ font-size:24px; font-weight:700; color:#58a6ff; }}
.card .lbl {{ font-size:12px; color:#8b949e; margin-top:2px; }}
h2 {{ font-size:16px; margin:18px 0 8px; color:#58a6ff; }}
table {{ width:100%; border-collapse:collapse; background:#161b22;
  border-radius:10px; overflow:hidden; font-size:14px; }}
th {{ background:#21262d; color:#8b949e; font-weight:500; font-size:12px;
  padding:8px 10px; text-align:left; }}
td {{ padding:10px; border-top:1px solid #21262d; vertical-align:top; }}
.clickable {{ cursor:pointer; }} .clickable:active {{ background:#21262d; }}
.name {{ font-weight:600; }} small {{ color:#8b949e; font-weight:400; }}
.desc {{ display:block; margin-top:3px; color:#9aa4b2; }}
.task a {{ color:#58a6ff; text-decoration:none; }}
.badge {{ padding:2px 8px; border-radius:10px; font-size:13px; font-weight:600; }}
.badge.hot {{ background:#f8514926; color:#f85149; }}
.badge.mid {{ background:#d2992226; color:#d29922; }}
.badge.low {{ background:#8b949e26; color:#8b949e; }}
.fund {{ font-size:12px; }}
.ok {{ color:#3fb950; }} .warn {{ color:#d29922; }}
.new {{ background:#3fb950; color:#0d1117; font-size:10px; padding:1px 5px;
  border-radius:4px; font-weight:700; }}
.fresh {{ background:#a371f7; color:#fff; font-size:10px; padding:1px 5px;
  border-radius:4px; font-weight:700; margin-left:4px; }}
.zero {{ background:#3fb950; color:#0d1117; font-size:10px; padding:1px 5px;
  border-radius:4px; font-weight:700; margin-left:4px; }}
.tip {{ margin-top:20px; padding:12px; background:#d2992214; border:1px solid #d2992244;
  border-radius:10px; font-size:13px; color:#d29922; }}
.legend {{ font-size:12px; color:#8b949e; margin:8px 0 0; }}
.footer {{ margin-top:14px; text-align:center; color:#484f58; font-size:12px; }}
</style></head><body>
<h1>🪂 空投雷达日报</h1>
<div class="sub">{date}（北京时间）生成 · 数据源 DefiLlama · 云端每小时更新</div>
<div class="cards">
  <div class="card"><div class="num">{total}</div><div class="lbl">监控池</div></div>
  <div class="card"><div class="num">{new_cnt}</div><div class="lbl">今日新增</div></div>
  <div class="card"><div class="num">{fresh_cnt}</div><div class="lbl">30天内上线</div></div>
  <div class="card"><div class="num">{funded_cnt}</div><div class="lbl">有融资</div></div>
</div>
{fresh_block}
<h2>🏆 综合评分 Top 10</h2>
<table><tr><th>项目</th><th>TVL</th><th>链</th><th>审计</th><th>评分</th></tr>
{top_rows}
</table>
<p class="legend">🔥 高分 ｜ 💰 有知名 VC 融资 ｜ 💸 零本金可参与 ｜ ⚡ 上线 30 天内 ｜ 点行跳官网，🎯 可直达任务</p>
<div class="tip">⚠️ 交互请用小额专用钱包，只从官网/官推进入，不点陌生链接，定期清理授权。</div>
<div class="footer">空投雷达 · 仅供信息参考，不构成投资建议</div>
</body></html>"""


def build_fresh_block(items):
    """新上线速览（30 天内）—— 空投预期最强的窗口"""
    fresh = [it for it in items if it["age_days"] <= config.FRESH_DAYS]
    if not fresh:
        return ""
    rows = "".join(row(it, True) for it in fresh[:8])
    return ("<h2>⚡ 新上线速览（30 天内，空投预期最强）</h2>"
            "<table><tr><th>项目</th><th>TVL</th><th>链</th><th>审计</th><th>评分</th></tr>"
            "%s</table>" % rows)


def _md_item(it):
    listed = common.ts_to_str(it.get("listed_at"))
    tags = []
    if it["age_days"] <= config.FRESH_DAYS:
        tags.append("⚡新上线")
    if it.get("zero_cost"):
        tags.append("💸零本金")
    if it.get("funded"):
        tags.append("💰有融资")
    if not it["audited"]:
        tags.append("⚠未审计")
    lines = ["### %s（评分 %.1f）%s" % (it["name"], it["score"], " ".join(tags)),
             "- 类别：%s｜TVL：%s｜上线：%s（%d天）" % (
                 it["category"], fmt_money(it["tvl"]), listed, it["age_days"]),
             "- 链：%s" % (", ".join(it["chains"][:3]) or "-")]
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


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR
    os.makedirs(out_dir, exist_ok=True)

    items = sources.fetch_all()
    if not items:
        print("数据源暂不可用，本次跳过")
        return

    items.sort(key=lambda x: -x["score"])
    seen = load_seen()
    today0 = common.today_start_ts()

    new_items = []
    for it in items:
        v = seen.get(it["id"])
        ts = v.get("ts", 0) if isinstance(v, dict) else (v or 0)
        if ts >= today0:
            new_items.append(it)
    new_ids = {it["id"] for it in new_items}
    fresh_cnt = sum(1 for it in items if it["age_days"] <= config.FRESH_DAYS)
    funded_cnt = sum(1 for it in items if it.get("funded"))

    html = HTML_TMPL.format(
        date=common.now().strftime("%Y-%m-%d %H:%M"),
        total=len(items),
        new_cnt=len(new_items),
        fresh_cnt=fresh_cnt,
        funded_cnt=funded_cnt,
        fresh_block=build_fresh_block(items),
        top_rows="".join(row(it, it["id"] in new_ids) for it in items[:10]),
    )
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # Markdown 版（供 WorkBuddy / IMA 知识库存档）
    md = ["# 🪂 空投雷达日报 %s" % common.now().strftime("%Y-%m-%d"), "",
          "监控池 **%d** 个未发币协议｜今日新增 **%d** 个｜30天内上线 %d 个｜有融资 %d 个"
          % (len(items), len(new_items), fresh_cnt, funded_cnt), ""]
    fresh = [it for it in items if it["age_days"] <= config.FRESH_DAYS]
    if fresh:
        md += ["## ⚡ 新上线速览（30 天内）", ""]
        for it in fresh[:8]:
            md += _md_item(it)
    md += ["## 🏆 综合评分 Top 10", ""]
    for it in items[:10]:
        md += _md_item(it)
    md += ["---",
           "⚠️ 交互请用小额专用钱包，只从官网/官推进入，不点陌生链接。"
           "数据源 DefiLlama，仅供信息参考，不构成投资建议。"]
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("报告已生成：%s" % os.path.join(out_dir, "report.html"))


if __name__ == "__main__":
    main()
