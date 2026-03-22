# -*- coding: utf-8 -*-
"""
🤖 Telegram бот на aiogram 3.x
"""

import logging
from typing import List, Optional
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from .handlers import router as commands_router
from .handlers.commands import set_admin_chat_ids

logger = logging.getLogger(__name__)


class TelegramBot:
    """TK PRO Telegram бот на aiogram"""

    def __init__(self, token: str, chat_ids: List[str]):
        self.token = token
        self.chat_ids = [str(cid) for cid in chat_ids]
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._admin_chat_ids: set = set()

    async def init(self) -> None:
        """Инициализация бота"""
        if not self.token:
            logger.warning("⚠️ Telegram токен не задан — бот не будет запущен")
            return

        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()

        # Регистрируем роутеры
        self.dp.include_router(commands_router)

        # Сохраняем admin chat_ids и устанавливаем в хендлеры
        for cid in self.chat_ids:
            self._admin_chat_ids.add(cid)
        set_admin_chat_ids(self.chat_ids)

        logger.info("🤖 Telegram бот инициализирован (chat_ids: %d)", len(self._admin_chat_ids))

    async def start_polling(self) -> None:
        """Запуск поллинга"""
        if not self.bot:
            return

        try:
            # Запускаем поллинг
            await self.dp.start_polling(self.bot, allowed_updates=['message'])
        except Exception as e:
            logger.error("❌ Ошибка поллинга: %s", e)

    async def send_to_all(self, message: str, parse_mode: str = 'HTML') -> int:
        """
        Отправить сообщение всем админам
        Returns: количество успешных отправок
        """
        if not self.bot:
            return 0

        success_count = 0
        for chat_id in self._admin_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                success_count += 1
                logger.info("📤 TG → %s", chat_id)
            except Exception as e:
                logger.error("❌ Ошибка отправки в %s: %s", chat_id, e)

        return success_count

    async def send_report(
        self,
        tf_name: str,
        tk_count: int,
        retest_count: int,
        total_count: int,
        last_scan_time: datetime
    ) -> int:
        """Отправить отчёт за 15 минут"""
        # Добавляем +2 часа к времени сервера
        msk_time = last_scan_time + timedelta(hours=2)
        
        now = datetime.now() + timedelta(hours=2)
        time_since_scan = (now - msk_time).total_seconds()
        status = "🟢 Бот активен" if time_since_scan < 120 else "🟡 Задержка скана"

        msg = (
            f"📊 <b>TK PRO — Отчёт за 15 мин</b>\n"
            f"{status}\n\n"
            f"⏱ TF: <b>{tf_name}</b>\n"
            f"🔍 TK-PROBOY: <b>{tk_count}</b>\n"
            f"🎯 TK-RETEST: <b>{retest_count}</b>\n"
            f"📈 Всего: <b>{total_count}</b>\n\n"
            f"🕒 Последнее сканирование: {msk_time.strftime('%H:%M:%S')}"
        )

        return await self.send_to_all(msg)

    async def send_signal(self, signal: dict, tf_name: str) -> int:
        """Отправить сигнал о ретесте"""
        sym = signal.get('symbol', 'UNKNOWN')
        direction = '🔵 LONG' if 'long' in signal.get('type', '') else '🟠 SHORT'
        retest_num = signal.get('retest_num', 1)
        conf = signal.get('confirmation', 'confirmed')

        tko = signal.get('tk_open', 0)
        tkc = signal.get('tk_close', 0)
        to = signal.get('test_open', 0)
        tc = signal.get('test_close', 0)

        # Текущее московское время
        now_msk = datetime.now().strftime('%d.%m %H:%M')

        retest_label = f"#{retest_num}" if retest_num > 1 else ""

        if conf == 'confirmed':
            header = f"🎯 <b>TK-PRO RETEST{retest_label} ✅ ПОДТВЕРЖДЁН</b>"
            footer = "<i>✅ Сигнал подтверждён — можно входить!</i>"
        else:
            header = f"🎯 <b>TK-PRO RETEST{retest_label} ⚠️ ПРЕДУПРЕЖДЕНИЕ</b>"
            footer = "<i>⚠️ Свеча закрылась против сигнала — будь осторожен!</i>"

        msg = (
            f"{header}\n\n"
            f"🕒 <b>Время сигнала:</b> {now_msk}\n\n"
            f"🪙 <b>{sym}</b>\n"
            f"🧭 {direction}\n\n"
            f"📊 <b>ТК-свеча:</b>\n"
            f"O: {tko:.4f} | C: {tkc:.4f}\n\n"
            f"📊 <b>Тестовая свеча:</b>\n"
            f"O: {to:.4f} | C: {tc:.4f}\n\n"
            f"{footer}"
        )

        return await self.send_to_all(msg)

    async def close(self) -> None:
        """Закрытие бота"""
        if self.bot:
            await self.bot.session.close()
            logger.info("🔴 Telegram бот остановлен")
