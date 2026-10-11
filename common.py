# -*- coding: utf-8 -*-
"""空投雷达 - 时区与公共工具

统一使用北京时间（Asia/Shanghai），避免云端（UTC）与本地时间混用。
"""
from datetime import datetime, timezone, timedelta

# 北京时间：UTC+8（用固定偏移，不依赖系统 tzdata，最稳）
CST = timezone(timedelta(hours=8))


def now():
    """当前北京时间"""
    return datetime.now(CST)


def today_start_ts():
    """今天（北京时间）零点的 Unix 时间戳"""
    n = now()
    return n.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def ts_to_str(ts, fmt="%Y-%m-%d"):
    """时间戳 -> 北京时间字符串，0 返回「未知」"""
    if not ts:
        return "未知"
    return datetime.fromtimestamp(ts, CST).strftime(fmt)
