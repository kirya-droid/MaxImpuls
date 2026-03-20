#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Конфигурация TK Bar Detector PRO
"""

import os
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv
from typing import List, Optional

# =======================
# 🔧 КОНСТАНТЫ
# =======================
VALID_TIMEFRAMES = {"1", "3", "5", "15", "30", "60", "120", "240", "D"}

TIMEFRAME_ADJUSTMENTS = {
    "1": (2.0, 0.7, 0.7, 2.0), "3": (1.5, 0.8, 0.8, 1.5), "5": (1.2, 0.9, 0.9, 1.2),
    "15": (1.0, 1.0, 1.0, 1.0), "30": (0.8, 1.1, 1.1, 0.9), "60": (0.6, 1.3, 1.3, 0.8),
    "120": (0.5, 1.4, 1.4, 0.7), "240": (0.4, 1.5, 1.5, 0.6), "D": (0.3, 1.6, 1.6, 0.5),
}

TIMEFRAME_TO_SECONDS = {
    "1": 60, "3": 180, "5": 300, "15": 900, "30": 1800,
    "60": 3600, "120": 7200, "240": 14400, "D": 86400
}

TIMEFRAME_NAMES = {
    "1": "1м", "3": "3м", "5": "5м", "15": "15м", "30": "30м",
    "60": "1ч", "120": "2ч", "240": "4ч", "D": "1д"
}

MOTIVATION_PHRASES = [
    "💎 Дисциплина > Эмоции. Следуй плану!", "🚀 Каждый сигнал — шаг к цели. Действуй!",
    "🎯 Терпение + Точность = Прибыль", "📈 Рынок вознаграждает тех, кто ждёт подтверждения",
    "🔥 Не гонись за каждой свечой — лови качественные!", "💪 Один хороший вход лучше десяти сомнительных",
    "🧘 Сохраняй хладнокровие — рынок всегда даст шанс", "⭐ Твой план — твоя защита. Доверяй системе!",
]


# =======================
# 🔧 КОНФИГУРАЦИЯ
# =======================
@dataclass(frozen=True)
class Config:
    """Конфигурация приложения"""
    # Базовые настройки
    lookback: int = 100  # Сколько последних свечей анализировать для обнаружения TK-баров
    timeframe: str = "15"  # Таймфрейм свечей в минутах (1, 3, 5, 15, 30, 60, 120, 240) или "D" для дневного
    symbol_filter: str = "USDT"  # Фильтр символов — сканировать только пары с этим суффиксом
    top_n_symbols: int = 200  # Сколько лучших символов отбирать для анализа (по объёму/активности)

    # Сетевые настройки
    max_concurrent_requests: int = 20  # Максимальное количество одновременных запросов к API биржи
    request_timeout: int = 10  # Таймаут одного запроса в секундах
    max_retries: int = 2  # Количество повторных попыток при ошибке запроса

    # Параметры стратегии
    base_zone_percent: float = 0.6  # Базовый процент зоны интереса — насколько цена должна измениться, чтобы свеча считалась значимой (0.2 = 20%)
    base_body_multiplier: float = 1.6  # Множитель размера тела свечи для определения аномалий (1.3 = тело на 30% больше среднего)
    base_break_threshold: float = 0.3  # Порог пробоя — минимальная доля пробоя относительно диапазона свечи (0.3 = 30%)

    # Окна расчётов
    body_window: int = 20  # Количество свечей для расчёта среднего размера тела свечи
    volume_window: int = 20  # Количество свечей для расчёта среднего объёма
    state_cleanup_bars: int = 100  # Через сколько баров выполнять очистку устаревших данных состояния
    sent_signals_max_age_hours: int = 24  # Максимальный возраст отправленных сигналов в часах (старые удаляются)

    # Файлы
    state_file: str = 'tk_pro_state_2.json'  # Файл для сохранения состояния сканера
    log_file: str = 'tk_pro_2.log'  # Файл логов
    statistics_file: str = 'tk_statistics.json'  # Файл статистики работы сканера

    # Telegram
    telegram_token: Optional[str] = None  # Токен Telegram-бота для отправки уведомлений
    telegram_chat_ids: List[str] = field(default_factory=list)  # Список ID чатов для рассылки сигналов

    # Отладка
    enable_debug_logging: bool = False  # Включить подробное логирование для отладки
    
    def __post_init__(self):
        if self.timeframe not in VALID_TIMEFRAMES:
            raise ValueError(f"❌ Неверный таймфрейм: {self.timeframe}")
    
    @classmethod
    def from_env(cls, **overrides) -> 'Config':
        load_dotenv()
        chat_ids_raw = os.getenv('TELEGRAM_CHAT_ID_2', '')
        chat_ids = [cid.strip() for cid in chat_ids_raw.split(',') if cid.strip()] if chat_ids_raw else []
        
        # Преобразуем overrides: debug -> enable_debug_logging
        converted_overrides = {}
        if 'debug' in overrides:
            converted_overrides['enable_debug_logging'] = overrides.pop('debug')
        
        config = cls(
            timeframe=os.getenv('TIMEFRAME', '15'),
            top_n_symbols=int(os.getenv('TOP_N_SYMBOLS', '200')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '20')),
            telegram_token=os.getenv('TELEGRAM_BOT_TOKEN_2'),
            telegram_chat_ids=chat_ids,
            enable_debug_logging=os.getenv('DEBUG_LOGGING', 'false').lower() == 'true',
        )
        # Применяем только валидные параметры Config
        valid_params = {f.name for f in cls.__dataclass_fields__.values()}
        if overrides:
            valid_overrides = {k: v for k, v in overrides.items() if k in valid_params}
            if valid_overrides:
                config = cls(**{**asdict(config), **valid_overrides})
        return config


def get_adaptive_params(tf: str, config: Config) -> dict:
    """Получить адаптивные параметры для таймфрейма"""
    zone_mult, body_mult, break_mult, vol_mult = TIMEFRAME_ADJUSTMENTS.get(tf, (1.0, 1.0, 1.0, 1.0))
    return {
        'zone_percent': config.base_zone_percent * zone_mult,
        'body_multiplier': config.base_body_multiplier * body_mult,
        'break_threshold': config.base_break_threshold * break_mult,
        'min_volume_mult': vol_mult,
    }
