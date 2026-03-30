#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧮 Логика TK Bar — Стратегия с поддержкой нескольких уровней
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any
from .config import Config, get_adaptive_params, TIMEFRAME_TO_SECONDS

logger = logging.getLogger(__name__)


def calculate_tk_pro_signals(
        candles: List[List[str]],
        symbol: str,
        state: Dict[str, Any],
        sent_signals: Dict[str, Any],
        config: Config
) -> Tuple[List[Dict], Dict[str, Any], Dict[str, Any]]:
    """Рассчитать сигналы TK-PRO с поддержкой нескольких уровней"""
    if len(candles) < config.lookback + 10:
        return [], state, sent_signals

    signals = []
    tf_params = get_adaptive_params(config.timeframe, config)
    zone_pct = tf_params['zone_percent']
    body_mult = tf_params['body_multiplier']
    break_thresh = tf_params['break_threshold']
    interval_ms = TIMEFRAME_TO_SECONDS.get(config.timeframe, 900) * 1000

    # Преобразуем свечи в DataFrame
    df = {
        'open': [float(c[1]) for c in candles],
        'high': [float(c[2]) for c in candles],
        'low': [float(c[3]) for c in candles],
        'close': [float(c[4]) for c in candles],
        'volume': [float(c[5]) for c in candles],
        'time': [int(c[0]) for c in candles]
    }

    n = len(df['close'])
    idx = n - 2  # Предпоследняя свеча (точно закрыта)

    if idx < config.lookback + 5 or idx < 1:
        return [], state, sent_signals

    if int(time.time() * 1000) < df['time'][idx + 1]:
        return [], state, sent_signals

    candle_time = datetime.fromtimestamp(df['time'][idx] / 1000)

    # === 1. Уровни и зона ===
    high_level = max(df['high'][idx - config.lookback:idx])
    low_level = min(df['low'][idx - config.lookback:idx])
    zone_high = high_level * (1 + zone_pct / 100)
    zone_low = low_level * (1 - zone_pct / 100)

    # === 2. Тело свечи ===
    body = abs(df['close'][idx] - df['open'][idx])
    avg_body = sum(abs(df['close'][i] - df['open'][i]) for i in range(max(0, idx - 19), idx + 1)) / min(20, idx + 1)
    strong_body = body > avg_body * body_mult

    # === 3. Объём ===
    avg_vol = sum(df['volume'][max(0, idx - 19):idx + 1]) / min(20, idx + 1)
    volume_ok = df['volume'][idx] >= avg_vol * tf_params['min_volume_mult']

    # === 4. Условия TK-баров ===
    break_long = df['close'][idx] - high_level
    break_short = low_level - df['close'][idx]
    long_tk = (df['close'][idx] > zone_high) and strong_body and (break_long > body * break_thresh) and volume_ok
    short_tk = (df['close'][idx] < zone_low) and strong_body and (break_short > body * break_thresh) and volume_ok

    # === 5. Состояние ===
    key = f"{symbol}"

    def already_sent(sig_type: str, ts: int) -> bool:
        return f"{symbol}_{sig_type}" in sent_signals and sent_signals[f"{symbol}_{sig_type}"] == ts

    def mark_sent(sig_type: str, ts: int):
        sent_signals[f"{symbol}_{sig_type}"] = ts

    if key not in state or not isinstance(state[key], dict):
        state[key] = {}

    st = state[key]

    # === 6. Новый ТК-бар (поддержка нескольких уровней) ===
    if 'tk_levels' not in st:
        st['tk_levels'] = []

    tk_levels = st['tk_levels']
    max_levels = 10  # Максимум активных уровней на символ
    max_retests = 1  # Максимум ретестов на уровень

    # Проверка cooldown: сколько баров прошло с последнего ТК-бара (отдельно для LONG и SHORT)
    last_long_tk_bar = st.get('last_long_tk_bar', -100)
    last_short_tk_bar = st.get('last_short_tk_bar', -100)
    bars_since_last_long = idx - last_long_tk_bar
    bars_since_last_short = idx - last_short_tk_bar
    long_cooldown_active = bars_since_last_long < config.min_bars_between
    short_cooldown_active = bars_since_last_short < config.min_bars_between

    if long_tk:
        # Проверка: не активен ли ещё cooldown после предыдущего LONG ТК-бара
        if long_cooldown_active:
            logger.debug("🔍 %s | Пропуск LONG ТК-бара — cooldown (баров после последнего LONG: %d)", symbol, bars_since_last_long)
        # Добавляем новый уровень если есть место и нет cooldown
        elif len(tk_levels) < max_levels:
            tko, tkc = df['time'][idx], df['time'][idx] + interval_ms
            new_level = {
                'tk_open': df['open'][idx],
                'tk_close': df['close'][idx],
                'tk_high': df['high'][idx],  # ← добавлено
                'tk_low': df['low'][idx],  # ← добавлено
                'tk_time_open': tko,
                'tk_time_close': tkc,
                'tk_dir': 1,
                'retest_count': 0,
                'bar_idx': idx
            }
            tk_levels.append(new_level)

            if not already_sent('long_tk', df['time'][idx]):
                signals.append({
                    'type': 'long_tk', 'symbol': symbol, 'price': df['close'][idx],
                    'open': df['open'][idx], 'time': candle_time, 'send_telegram': False
                })
                mark_sent('long_tk', df['time'][idx])
                # Сохраняем индекс последнего LONG ТК-бара
                st['last_long_tk_bar'] = idx
        else:
            logger.debug("🔍 %s | Пропуск нового LONG ТК-бара — достигнут лимит уровней (%d)", symbol, len(tk_levels))

    if short_tk:
        # Проверка: не активен ли ещё cooldown после предыдущего SHORT ТК-бара
        if short_cooldown_active:
            logger.debug("🔍 %s | Пропуск SHORT ТК-бара — cooldown (баров после последнего SHORT: %d)", symbol, bars_since_last_short)
        # Добавляем новый уровень если есть место и нет cooldown
        elif len(tk_levels) < max_levels:
            tko, tkc = df['time'][idx], df['time'][idx] + interval_ms
            new_level = {
                'tk_open': df['open'][idx],
                'tk_close': df['close'][idx],
                'tk_high': df['high'][idx],  # ← добавлено
                'tk_low': df['low'][idx],  # ← добавлено
                'tk_time_open': tko,
                'tk_time_close': tkc,
                'tk_dir': -1,
                'retest_count': 0,
                'bar_idx': idx
            }
            tk_levels.append(new_level)

            if not already_sent('short_tk', df['time'][idx]):
                signals.append({
                    'type': 'short_tk', 'symbol': symbol, 'price': df['close'][idx],
                    'open': df['open'][idx], 'time': candle_time, 'send_telegram': False
                })
                mark_sent('short_tk', df['time'][idx])
                # Сохраняем индекс последнего SHORT ТК-бара
                st['last_short_tk_bar'] = idx
        else:
            logger.debug("🔍 %s | Пропуск нового SHORT ТК-бара — достигнут лимит уровней (%d)", symbol, len(tk_levels))

    # === 7. Ретест (проверяем все активные уровни) ===
    levels_to_remove = []

    for level_idx, level in enumerate(tk_levels):
        tk_open = level.get('tk_open')
        tk_high = level.get('tk_high', tk_open)  # ← fallback на open для безопасности
        tk_low = level.get('tk_low', tk_open)  # ← fallback на open для безопасности
        tk_dir = level.get('tk_dir', 0)
        retest_count = level.get('retest_count', 0)
        bar_idx = level.get('bar_idx')

        if tk_open and tk_dir != 0 and retest_count < max_retests and idx > 0:
            # Касание: цена тестовой свечи пересекает уровень открытия ТК-бара
            touch = df['low'][idx] <= tk_open <= df['high'][idx]

            # ✅ НОВАЯ ЛОГИКА: подтверждение по диапазону ТК-бара
            # LONG: закрытие тестовой свечи >= tk_low (даже если ниже tk_open, но выше low — всё равно подтверждение)
            # SHORT: закрытие тестовой свечи <= tk_high (даже если выше tk_open, но ниже high — всё равно подтверждение)
            if tk_dir == 1:
                correct = df['close'][idx - 1] >= tk_low
            else:  # tk_dir == -1
                correct = df['close'][idx - 1] <= tk_high

            not_new_tk = not long_tk and not short_tk
            retest = touch and correct and not_new_tk

            if retest:
                level['retest_count'] = retest_count + 1

                to, tc, tto = df['open'][idx], df['close'][idx], df['time'][idx]

                # Определение конфирмации: сравниваем с tk_open для визуального статуса
                conf, vs = (
                    ("confirmed", "выше") if (tk_dir == 1 and tc > tk_open) or (tk_dir == -1 and tc < tk_open)
                    else ("warning", "ниже" if tk_dir == 1 else "выше")
                )

                retest_num = retest_count + 1
                sig_type = f'long_retest_{retest_num}' if tk_dir == 1 else f'short_retest_{retest_num}'

                if not already_sent(sig_type, tto):
                    signals.append({
                        'type': sig_type, 'symbol': symbol, 'price': tc,
                        'tk_open': tk_open, 'tk_close': level.get('tk_close', tk_open),
                        'tk_high': tk_high, 'tk_low': tk_low,  # ← добавлено в сигнал для отладки
                        'tk_time_open': level.get('tk_time_open', tto),
                        'tk_time_close': level.get('tk_time_close', tto),
                        'test_open': to, 'test_close': tc, 'test_time_open': tto,
                        'test_time_close': tto + interval_ms,
                        'time': candle_time, 'close_vs_level': vs, 'confirmation': conf,
                        'send_telegram': True, 'retest_num': retest_num
                    })
                    mark_sent(sig_type, tto)
                    logger.info("🎯 %s | TK-RETEST #%d %s @ %.4f — ОТПРАВЛЕНО В TG", symbol, retest_num, conf, tc)

                # Если достигнут максимум ретестов — помечаем уровень на удаление
                if level['retest_count'] >= max_retests:
                    levels_to_remove.append(level_idx)

    # Удаляем уровни с максимальным количеством ретестов
    for level_idx in sorted(levels_to_remove, reverse=True):
        tk_levels.pop(level_idx)

    # === 8. Очистка старых состояний ===
    # Очищаем уровни старше cleanup_bars свечей
    if tk_levels:
        oldest_bar_idx = min(lvl.get('bar_idx', idx) for lvl in tk_levels)
        if (idx - oldest_bar_idx) > config.state_cleanup_bars:
            state[key] = {'tk_levels': []}

    return signals, state, sent_signals