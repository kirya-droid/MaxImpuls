#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Сканирование рынка
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .config import Config, get_adaptive_params, TIMEFRAME_TO_SECONDS, TIMEFRAME_NAMES
from .bybit_api import fetch_all_klines_async
from .strategy import calculate_tk_pro_signals
from .telegram_bot import TelegramBot
from .state import load_state, save_state, cleanup_sent_signals
from .statistics import StatisticsTracker
from .signal_logger import SignalLogger

logger = logging.getLogger(__name__)


async def scan_market_async(
    state_data: Dict[str, Any],
    config: Config,
    tg: Optional[TelegramBot],
    stats: Optional[StatisticsTracker],
    signal_log: Optional[SignalLogger] = None
) -> tuple[Dict[str, Any], dict]:
    """Сканировать рынок"""
    tf_name = TIMEFRAME_NAMES.get(config.timeframe)
    tf_params = get_adaptive_params(config.timeframe, config)
    
    logger.info("\n🔍 %s | TF: %s", datetime.now().strftime('%H:%M:%S'), tf_name)
    logger.info("📐 Зона: ±%.2f%% | Тело: ×%.2f", tf_params['zone_percent'], tf_params['body_multiplier'])
    
    state = state_data.get('states', {})
    sent_signals = state_data.get('sent_signals', {})
    sent_signals = cleanup_sent_signals(sent_signals, config.sent_signals_max_age_hours)
    
    klines = await fetch_all_klines_async([], config)
    signals_count = tk_count = retest_count = 0
    
    for symbol, candles in klines.items():
        if not candles or len(candles) < config.lookback + 10:
            continue
        
        signals, state, sent_signals = calculate_tk_pro_signals(
            candles, symbol, state, sent_signals, config
        )
        
        for sig in signals:
            signals_count += 1
            if 'tk' in sig['type']:
                tk_count += 1
                logger.info("🚀 %s | TK-PROBOY %s @ %.4f", symbol, sig['type'], sig['price'])
            else:
                retest_count += 1
                cfm = "✅" if sig.get('confirmation') == "confirmed" else "⚠️"
                retest_num = sig.get('retest_num', 1)
                retest_label = f"#{retest_num}" if retest_num > 1 else ""
                logger.info("🎯 %s | TK-RETEST%s %s @ %.4f", symbol, retest_label, cfm, sig['price'])

            # Отправка в Telegram
            if sig.get('send_telegram') and 'retest' in sig['type'] and tg:
                try:
                    await tg.send_signal(sig, tf_name)
                except Exception as e:
                    logger.error("❌ TG send: %s", e)

            # Запись в лог сигналов (для анализа)
            if signal_log and ('tk' in sig['type'] or 'retest' in sig['type']):
                try:
                    # Считаем метрики
                    df = {
                        'open': [float(c[1]) for c in candles],
                        'high': [float(c[2]) for c in candles],
                        'low': [float(c[3]) for c in candles],
                        'close': [float(c[4]) for c in candles],
                        'volume': [float(c[5]) for c in candles],
                    }
                    idx = len(df['close']) - 2
                    
                    # Тело свечи
                    body = abs(df['close'][idx] - df['open'][idx])
                    avg_body = sum(abs(df['close'][i] - df['open'][i]) for i in range(max(0, idx-19), idx+1)) / min(20, idx+1)
                    
                    # Объём
                    avg_vol = sum(df['volume'][max(0, idx-19):idx+1]) / min(20, idx+1)
                    volume_ratio = df['volume'][idx] / avg_vol if avg_vol > 0 else 0
                    
                    # ATR (упрощённо)
                    tr_values = []
                    for i in range(1, min(14, len(candles))):
                        high = candles[i][2]
                        low = candles[i][3]
                        prev_close = candles[i-1][4]
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        tr_values.append(tr)
                    atr = sum(tr_values) / len(tr_values) if tr_values else 0
                    
                    # Уровни
                    lookback = config.lookback
                    high_level = max(df['high'][idx-lookback:idx])
                    low_level = min(df['low'][idx-lookback:idx])
                    break_dist = abs(df['close'][idx] - (high_level if 'long' in sig['type'] else low_level))
                    break_dist_pct = (break_dist / df['close'][idx]) * 100 if df['close'][idx] > 0 else 0

                    # Контекст
                    candle_hour = datetime.fromtimestamp(df['time'][idx] / 1000).hour

                    signal_log.log_signal(
                        symbol=symbol,
                        sig_type=sig['type'],
                        tk_candle={
                            'open': sig.get('tk_open', df['open'][idx]),
                            'close': sig.get('price', df['close'][idx]),
                            'high': df['high'][idx],
                            'low': df['low'][idx]
                        },
                        test_candle={
                            'open': sig.get('test_open', 0),
                            'close': sig.get('test_close', 0),
                            'high': df['high'][idx],
                            'low': df['low'][idx]
                        } if 'retest' in sig['type'] else None,
                        levels={
                            'high_level': high_level,
                            'low_level': low_level,
                            'break_distance_pct': round(break_dist_pct, 2)
                        },
                        metrics={
                            'body_size': body,
                            'body_size_pct': round((body / df['close'][idx]) * 100, 2),
                            'avg_body': avg_body,
                            'body_ratio': round(body / avg_body, 2) if avg_body > 0 else 0,
                            'volume': df['volume'][idx],
                            'avg_volume': avg_vol,
                            'volume_ratio': round(volume_ratio, 2),
                            'atr': atr,
                            'atr_pct': round((atr / df['close'][idx]) * 100, 2) if df['close'][idx] > 0 else 0
                        },
                        context={
                            'candle_hour': candle_hour,
                            'day_of_week': datetime.fromtimestamp(df['time'][idx] / 1000).weekday(),
                            'trend': 'unknown'
                        },
                        confirmation=sig.get('confirmation', 'unknown')
                    )
                except Exception as e:
                    logger.debug("⚠️ Ошибка логгирования сигнала: %s", e)

            # Запись в статистику с метриками
            if stats and 'retest' in sig['type']:
                # Считаем метрики
                df = {
                    'close': [float(c[4]) for c in candles],
                    'volume': [float(c[5]) for c in candles],
                }
                idx = len(df['close']) - 2

                # Объём
                avg_vol = sum(df['volume'][max(0, idx-19):idx+1]) / min(20, idx+1)
                volume_ratio = df['volume'][idx] / avg_vol if avg_vol > 0 else 0
                volume_usd = df['volume'][idx] * df['close'][idx]

                # Тело свечи
                body = abs(df['close'][idx] - df['open'][idx]) if 'open' in df else 0
                avg_body = sum(abs(df['close'][i] - df['open'][i]) for i in range(max(0, idx-19), idx+1)) / min(20, idx+1) if 'open' in df else 0
                body_ratio = body / avg_body if avg_body > 0 else 0

                metrics = {
                    'volume': volume_usd,
                    'volume_ratio': round(volume_ratio, 2),
                    'body_ratio': round(body_ratio, 2),
                }

                stats.record_signal(sig, metrics)
    
    logger.info("📊 Сигналы: TK-PROBOY: %d | TK-RETEST: %d | Всего: %d", tk_count, retest_count, signals_count)

    state_data['states'], state_data['sent_signals'] = state, sent_signals
    save_state(state_data, config.state_file)

    return state_data, {'tk': tk_count, 'retest': retest_count, 'total': signals_count}
