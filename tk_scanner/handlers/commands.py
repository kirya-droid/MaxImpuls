# -*- coding: utf-8 -*-
"""
📡 Обработчики команд Telegram бота
"""

import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

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
    now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
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
