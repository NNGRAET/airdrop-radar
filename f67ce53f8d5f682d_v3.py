# -*- coding: utf-8 -*-
"""空投雷达 - 每日网页报告生成器

生成 report.html（手机/iPad 自适应），配合 GitHub Pages 固定网址访问。
用法：python daily_report.py [输出目录]
"""
import json
import os
import sys
from datetime import datetime

import config
import sources

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen.json")


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def fmt_money(v):
    return "$%.1fB" % (v / 1e9) if v >= 1e9 else ("$%.0fM" % (v / 1e6) if v >= 1e6 else "$%.0fK" % (v / 1e3))


def score_badge(s):
    if s >= 5:
        return '<span class="badge hot">🔥 %.1f</span>' % s
    if s >= 3:
        return '<span class="badge mid">%.1f</span>' % s
    return '<span class="badge low">%.1f</span>' % s


def row(it, is_new):
    chains = ", ".join(it["chains"][:3]) or "-"
    audit = '<span class="ok">已审计</span>' if it["audited"] else '<span class="warn">未审计</span>'
    new_tag = ' <span class="new">NEW</span>' if is_new else ""
    link = it["url"] or ("https://x.com/%s" % it["twitter"] if it["twitter"] else "#")
    age = "%d天" % it["age_days"] if it["age_days"] < 9000 else "老项目"
    return """<tr onclick="window.open('%s')" class="clickable">
<td class="name">%s%s<br><small>%s · %s</small></td>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td>
</tr>""" % (link, it["name"], new_tag, it["category"], age,
            fmt_money(it["tvl"]), chains, audit, score_badge(it["score"]))


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
.badge {{ padding:2px 8px; border-radius:10px; font-size:13px; font-weight:600; }}
.badge.hot {{ background:#f8514926; color:#f85149; }}
.badge.mid {{ background:#d2992226; color:#d29922; }}
.badge.low {{ background:#8b949e26; color:#8b949e; }}
.ok {{ color:#3fb950; }} .warn {{ color:#d29922; }}
.new {{ background:#3fb950; color:#0d1117; font-size:10px; padding:1px 5px;
  border-radius:4px; font-weight:700; }}
.tip {{ margin-top:20px; padding:12px; background:#d2992214; border:1px solid #d2992244;
  border-radius:10px; font-size:13px; color:#d29922; }}
.footer {{ margin-top:14px; text-align:center; color:#484f58; font-size:12px; }}
</style></head><body>
<h1>🪂 空投雷达日报</h1>
<div class="sub">{date} 生成 · 数据源 DefiLlama · 每小时自动更新监控池</div>
<div class="cards">
  <div class="card"><div class="num">{total}</div><div class="lbl">监控池</div></div>
  <div class="card"><div class="num">{new_cnt}</div><div class="lbl">今日新增</div></div>
  <div class="card"><div class="num">{audited}</div><div class="lbl">已审计</div></div>
  <div class="card"><div class="num">{fresh}</div><div class="lbl">半年内上线</div></div>
</div>
<h2>🆕 今日新增机会</h2>
<table><tr><th>项目</th><th>TVL</th><th>链</th><th>审计</th><th>评分</th></tr>
{new_rows}
</table>
<h2>🏆 高分候选 Top 10</h2>
<table><tr><th>项目</th><th>TVL</th><th>链</th><th>审计</th><th>评分</th></tr>
{top_rows}
</table>
<div class="tip">⚠️ 交互请用小额专用钱包，只从官网/官推进入，不点陌生链接，定期清理授权。点任意行可跳转官网。</div>
<div class="footer">空投雷达 · 仅供信息参考，不构成投资建议</div>
</body></html>"""


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR
    os.makedirs(out_dir, exist_ok=True)

    items = sources.fetch_all()
    if not items:
        print("数据源暂不可用，本次跳过")
        return

    items.sort(key=lambda x: -x["score"])
    seen = load_seen()
    today0 = datetime.now().replace(hour=0, minute=0, second=0).timestamp()

    new_items = [it for it in items if seen.get(it["id"], 0) >= today0]
    new_ids = {it["id"] for it in new_items}

    html = HTML_TMPL.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(items),
        new_cnt=len(new_items),
        audited=sum(1 for it in items if it["audited"]),
        fresh=sum(1 for it in items if it["age_days"] <= 180),
        new_rows="".join(row(it, True) for it in new_items[:15])
                 or '<tr><td colspan="5" style="color:#8b949e">今日暂无新增</td></tr>',
        top_rows="".join(row(it, it["id"] in new_ids) for it in items[:10]),
    )

    path = os.path.join(out_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("报告已生成：%s" % path)


if __name__ == "__main__":
    main()
