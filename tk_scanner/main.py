#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Главная точка входа TK Bar Detector PRO
"""

import asyncio
import logging
import sys
import argparse
import os
from datetime import datetime, timedelta
from typing import Optional

from .config import Config, TIMEFRAME_TO_SECONDS, TIMEFRAME_NAMES
from .telegram_bot import TelegramBot
from .state import load_state, save_state
from .statistics import StatisticsTracker
from .scanner import scan_market_async
from .utils import seconds_to_next_candle
from .bybit_api import fetch_top_symbols_async
from .signal_logger import SignalLogger

logger = logging.getLogger(__name__)


async def get_current_prices(config: Config) -> dict:
    """Получить текущие цены для обновления результатов"""
    try:
        import aiohttp
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('retCode') == 0:
                        prices = {}
                        for ticker in data['result']['list']:
                            symbol = ticker['symbol']
                            if symbol.endswith('USDT'):
                                prices[symbol] = float(ticker['lastPrice'])
                        return prices
    except Exception as e:
        logger.debug("❌ Ошибка получения цен: %s", e)
    return {}


async def main_async(config: Config):
    """Основной цикл"""
    tf_name = TIMEFRAME_NAMES.get(config.timeframe)
    
    logger.info("\n" + "=" * 70)
    logger.info("🎯 TK BAR DETECTOR PRO v9.9 — Balanced Version")
    logger.info("=" * 70)
    logger.info("⏱ TF: %s (UTC) | 📊 Top-%d", tf_name, config.top_n_symbols)
    logger.info("📢 Фильтры: относительный объём | До 3 ретестов")
    logger.info("📊 Статистика: tk_statistics.json | Dashboard: tk_dashboard/")
    logger.info("=" * 70 + "\n")
    
    if not config.telegram_token:
        logger.warning("⚠️ TELEGRAM_TOKEN не задан — только консоль")
    
    # Инициализация статистики
    stats = StatisticsTracker(config.statistics_file)

    # Инициализация логгера сигналов
    signal_log = SignalLogger('tk_signals_log.json')
    logger.info("📊 Логгер сигналов инициализирован")

    # Инициализация Telegram бота
    tg = TelegramBot(config.telegram_token, config.telegram_chat_ids)
    await tg.init()

    # Запускаем поллинг в фоне
    polling_task = None
    if config.telegram_token and config.telegram_chat_ids:
        polling_task = asyncio.create_task(tg.start_polling())
        logger.info("🤖 Telegram бот запущен (polling)")

    interval = TIMEFRAME_TO_SECONDS.get(config.timeframe, 900)
    state_data = load_state(config.state_file)

    scan_count = 0
    last_report_time = datetime.now()
    report_interval = 15 * 60  # 15 минут в секундах
    last_scan_time = datetime.now()

    try:
        while True:
            logger.info("\n🔄 %s", datetime.now().strftime('%H:%M:%S'))

            # Сканирование
            state_data, stats_dict = await scan_market_async(state_data, config, tg, stats, signal_log)
            last_scan_time = datetime.now()

            # Отправка отчёта каждые 15 минут
            now = datetime.now()
            if (now - last_report_time).total_seconds() >= report_interval:
                last_report_time = now

                # Формируем сообщение
                tk_count = stats_dict.get('tk', 0) if stats_dict else 0
                retest_count = stats_dict.get('retest', 0) if stats_dict else 0
                total_count = stats_dict.get('total', 0) if stats_dict else 0

                await tg.send_report(tf_name, tk_count, retest_count, total_count, last_scan_time)

            # Обновление результатов каждые 5 сканов (~75 минут)
            scan_count += 1
            if scan_count % 5 == 0:
                logger.info("📊 Обновление результатов...")
                prices = await get_current_prices(config)
                if prices:
                    stats.update_results(prices)
                else:
                    logger.warning("⚠️ Не удалось получить цены для обновления")

            wait = seconds_to_next_candle(interval)
            logger.info("⏳ До скана: %d сек (%s)", wait, (datetime.now() + timedelta(seconds=wait)).strftime('%H:%M:%S'))

            await asyncio.sleep(wait)

    except KeyboardInterrupt:
        logger.info("\n🛑 Остановка...")
    finally:
        save_state(state_data, config.state_file)
        if stats:
            stats.save()
            stats.save_dashboard()
        if tg:
            await tg.close()
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass


def setup_logging(log_file: str, debug: bool = False):
    """Настройка логирования"""
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s UTC [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )
    logging.Formatter.converter = lambda *args: datetime.now().timetuple()


def parse_args():
    """Парсинг аргументов командной строки"""
    p = argparse.ArgumentParser(description='🎯 TK BAR DETECTOR PRO v9.9')
    p.add_argument('--debug', action='store_true', help='Включить отладку')
    p.add_argument('--timeframe', type=str, choices=['1', '3', '5', '15', '30', '60', '120', '240', 'D'], help='Таймфрейм')
    p.add_argument('--top', type=int, help='Количество монет (top N)')
    return p.parse_args()


def main():
    """Точка входа"""
    args = parse_args()
    overrides = {
        k: v for k, v in {
            'debug': args.debug,
            'timeframe': args.timeframe,
            'top_n_symbols': args.top
        }.items() if v is not None
    }
    
    config = Config.from_env(**overrides)
    setup_logging(config.log_file, debug=config.enable_debug_logging or args.debug)
    
    try:
        asyncio.run(main_async(config))
    except KeyboardInterrupt:
        logger.info("👋 Завершение...")
    except Exception as e:
        logger.error("❌ Фатальная ошибка: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
