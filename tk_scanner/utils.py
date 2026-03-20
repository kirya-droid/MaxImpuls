#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ Утилиты
"""

import time
from datetime import datetime, timedelta


def seconds_to_next_candle(interval_seconds: int) -> int:
    """Рассчитать секунды до следующей свечи"""
    now = datetime.now()
    if interval_seconds >= 86400:
        nxt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        now_ts = time.time()
        nxt = datetime.fromtimestamp(now_ts + (interval_seconds - now_ts % interval_seconds))
    return max(1, int((nxt - now).total_seconds()) + 2)
