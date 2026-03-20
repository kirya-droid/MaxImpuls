#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Bybit API — Запрос данных
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Tuple, Optional
from .config import Config

logger = logging.getLogger(__name__)


def validate_candle_data(candles: List[List[str]]) -> bool:
    """Проверить корректность данных свечи"""
    if not candles:
        return False
    for c in candles:
        if len(c) < 6:
            return False
        try:
            for i in range(1, 6):
                float(c[i])
        except:
            return False
    return True


async def fetch_klines_async(
    session: aiohttp.ClientSession,
    symbol: str,
    interval: str,
    limit: int,
    config: Config
) -> Tuple[str, List[List[str]]]:
    """Получить свечи для символа"""
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}
    
    for attempt in range(config.max_retries + 1):
        try:
            async with session.get(url, params=params, timeout=config.request_timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('retCode') == 0:
                        candles = data['result']['list']
                        if validate_candle_data(candles):
                            return symbol, list(reversed(candles)) if candles else []
        except Exception:
            pass
        if attempt < config.max_retries:
            await asyncio.sleep(1)
    
    return symbol, []


async def fetch_top_symbols_async(session: aiohttp.ClientSession, config: Config) -> List[str]:
    """Получить топ символов по объёму в долларах (turnover24h)"""
    url = "https://api.bybit.com/v5/market/tickers?category=linear"
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('retCode') == 0:
                    # Фильтруем USDT пары с положительным оборотом
                    tickers = [
                        t for t in data['result']['list']
                        if t['symbol'].endswith(config.symbol_filter) and float(t.get('turnover24h', 0)) > 0
                    ]
                    # Сортируем по turnover24h (оборот в долларах), а не volume24h
                    sorted_by_turnover = sorted(tickers, key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
                    return [t['symbol'] for t in sorted_by_turnover[:config.top_n_symbols]]
    except Exception:
        pass
    return []


async def fetch_all_klines_async(
    symbols: Optional[List[str]],
    config: Config
) -> Dict[str, List[List[str]]]:
    """Получить свечи для всех символов"""
    if not symbols:
        async with aiohttp.ClientSession() as session:
            symbols = await fetch_top_symbols_async(session, config)
    
    if not symbols:
        return {}
    
    results = {}
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_klines_async(session, s, config.timeframe, config.lookback + 25, config)
            for s in symbols
        ]
        for coro in asyncio.as_completed(tasks):
            symbol, candles = await coro
            if candles:
                results[symbol] = candles
    
    logger.info("✅ Данные: %d/%d символов", len(results), len(symbols))
    return results
