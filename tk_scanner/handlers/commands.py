# -*- coding: utf-8 -*-
"""
📡 Обработчики команд Telegram бота
"""

import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

# Часовой пояс Москвы (UTC+3)
MSK = timezone(timedelta(hours=3))

logger = logging.getLogger(__name__)

router = Router()

# Глобальная ссылка на admin chat_ids (устанавливается из telegram_bot.py)
_admin_chat_ids: set = set()


def set_admin_chat_ids(chat_ids: list[str]) -> None:
    """Установить разрешённые chat_ids"""
    global _admin_chat_ids
    _admin_chat_ids = set(str(cid) for cid in chat_ids)


def is_admin(message: Message) -> bool:
    """Проверить что пользователь админ"""
    return str(message.from_user.id) in _admin_chat_ids


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    if not is_admin(message):
        return
    await message.answer(
        "🚀 <b>TK PRO Scanner запущен!</b>\n\n"
        "📊 Сканирую рынок каждые 15 мин\n"
        "🔍 TK-PROBOY | TK-RETEST\n\n"
        "<b>Команды:</b>\n"
        "/ping — проверить связь\n"
        "/status — статус бота\n"
        "/help — помощь",
        parse_mode='HTML'
    )
    logger.info("📩 /start → %s", message.from_user.id)


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    """Обработчик команды /ping"""
    if not is_admin(message):
        return
    import time
    ms = int(time.time() * 1000)
    await message.answer(
        f"🟢 <b>Бот работает!</b>\n\n"
        f"⏱ Пинг: <code>{ms}</code> ms",
        parse_mode='HTML'
    )
    logger.info("📩 /ping → %s", message.from_user.id)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Обработчик команды /status"""
    if not is_admin(message):
        return
    now = datetime.now(MSK).strftime('%d.%m.%Y %H:%M:%S')
    await message.answer(
        "🟢 <b>TK PRO Бот активен</b>\n\n"
        "✅ Все системы в норме\n"
        f"🕒 Время: <code>{now}</code>",
        parse_mode='HTML'
    )
    logger.info("📩 /status → %s", message.from_user.id)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help"""
    if not is_admin(message):
        return
    await message.answer(
        "ℹ️ <b>Помощь TK PRO Scanner</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — запустить бота\n"
        "/ping — проверить связь\n"
        "/status — статус бота\n"
        "/stats — статистика сигналов\n"
        "/help — эта справка\n\n"
        "<b>О боте:</b>\n"
        "Сканирует топ-200 монет Bybit\n"
        "Ищет ТК-бары (пробойные свечи)\n"
        "Отправляет сигналы о ретестах\n\n"
        "⏱ Таймфрейм: 15м\n"
        "📊 Обновление: каждые 15 мин",
        parse_mode='HTML'
    )
    logger.info("📩 /help → %s", message.from_user.id)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Обработчик команды /stats"""
    if not is_admin(message):
        return
    
    from tk_scanner.signal_logger import SignalLogger
    signal_log = SignalLogger('tk_signals_log.json')
    stats = signal_log.get_statistics()
    
    if stats.get('total', 0) == 0:
        await message.answer("📊 Нет данных для статистики")
        return
    
    msg = (
        f"📊 <b>Статистика сигналов</b>\n\n"
        f"📈 Всего: {stats['total']}\n"
        f"✅ Завершено: {stats['completed']}\n"
        f"⏳ Ожидает: {stats['pending']}\n\n"
    )
    
    if stats.get('win_rate'):
        success_emoji = "✅" if stats['win_rate'] >= 50 else "⚠️"
        msg += f"{success_emoji} <b>Win Rate:</b> {stats['win_rate']}%\n"
        msg += f"📊 Успешных: {stats['success']} | Неудач: {stats['fail']}\n\n"
    
    if stats.get('avg_profit'):
        msg += f"💰 Средний профит: +{stats['avg_profit']}%\n"
        msg += f"📉 Средний убыток: -{stats['avg_loss']}%\n\n"
    
    # Топ 3 символа
    if stats.get('by_symbol'):
        top_symbols = sorted(
            stats['by_symbol'].items(),
            key=lambda x: x[1]['win_rate'],
            reverse=True
        )[:3]
        
        msg += "🏆 <b>Топ символы:</b>\n"
        for symbol, data in top_symbols:
            msg += f"  {symbol}: {data['win_rate']}% ({data['success']}/{data['total']})\n"
    
    await message.answer(msg, parse_mode='HTML')
    logger.info("📩 /stats → %s", message.from_user.id)
