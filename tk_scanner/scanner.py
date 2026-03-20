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

logger = logging.getLogger(__name__)


async def scan_market_async(
    state_data: Dict[str, Any],
    config: Config,
    tg: Optional[TelegramBot],
    stats: Optional[StatisticsTracker]
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
