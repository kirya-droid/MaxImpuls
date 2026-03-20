# -*- coding: utf-8 -*-
"""
📡 Telegram — Утилиты (совместимость)
"""

import html
from datetime import datetime
from typing import Dict


def format_signal(sig: Dict, tf_name: str) -> str:
    """Сформатировать сообщение сигнала (для совместимости)"""
    sym = html.escape(sig['symbol'])
    direction = '🔵 LONG' if 'long' in sig['type'] else '🟠 SHORT'

    tko, tkc = sig.get('tk_open', 0), sig.get('tk_close', 0)
    tkto, tktc = sig.get('tk_time_open', 0), sig.get('tk_time_close', 0)
    tkod = datetime.fromtimestamp(tkto / 1000).strftime('%d.%m %H:%M') if tkto else "N/A"
    tkcd = datetime.fromtimestamp(tktc / 1000).strftime('%d.%m %H:%M') if tktc else "N/A"

    to, tc = sig.get('test_open', 0), sig.get('test_close', 0)
    tto, ttc = sig.get('test_time_open', 0), sig.get('test_time_close', 0)
    tod = datetime.fromtimestamp(tto / 1000).strftime('%d.%m %H:%M') if tto else "N/A"
    tcd = datetime.fromtimestamp(ttc / 1000).strftime('%d.%m %H:%M') if ttc else "N/A"

    conf = sig.get('confirmation', 'confirmed')
    retest_num = sig.get('retest_num', 1)
    retest_label = f"#{retest_num}" if retest_num > 1 else ""

    hdr, ftr = (
        ("🎯 <b>TK-PRO RETEST ✅ ПОДТВЕРЖДЁН</b>", "<i>✅ Сигнал подтверждён — можно входить!</i>")
        if conf == "confirmed"
        else ("⚠️ <b>TK-PRO RETEST ⚠️ ПРЕДУПРЕЖДЕНИЕ</b>", "<i>⚠️ Свеча закрылась против сигнала — будь осторожен!</i>")
    )

    header_with_num = f"{hdr.split(' ')[0]}{retest_label} {hdr.split(' ', 1)[1]}" if retest_num > 1 else hdr

    tk_range_info = ""
    if 'tk_high' in sig and 'tk_low' in sig:
        tk_range_info = f"📐 Диапазон ТК: H {sig['tk_high']:.4f} | L {sig['tk_low']:.4f}\n\n"

    return (
        f"{header_with_num}\n\n"
        f"🪙 <b>{sym}</b>\n"
        f"🧭 {direction}\n\n"
        f"📊 <b>ТК-свеча:</b>\nO: {tkod} {tko:.4f} | C: {tkcd} {tkc:.4f}\n"
        f"{tk_range_info}"
        f"📊 <b>Тестовая свеча:</b>\nO: {tod} {to:.4f} | C: {tcd} {tc:.4f}\n\n"
        f"{ftr}"
    )
