#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Статистика сигналов — Полная версия (исправленная)
"""

import json
import os
import tempfile
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class StatisticsTracker:
    """Трекер статистики сигналов"""

    def __init__(self, statistics_file: str, dashboard_file: str = 'tk_dashboard/stats.json'):
        self.file = statistics_file
        self.dashboard_file = dashboard_file
        self.data = self._load()
        self.pending_signals = {}  # Сигналы для проверки результатов

    def _load(self) -> Dict[str, Any]:
        """Загрузить статистику из файла с нормализацией ключей"""
        if not os.path.exists(self.file):
            return self._empty_data()
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 🔧 НОРМАЛИЗАЦИЯ by_time: ключи к int, все 24 часа гарантированы
            if 'by_time' in data:
                normalized = {}
                for k, v in data['by_time'].items():
                    try:
                        hour_key = int(k)  # "16" -> 16, или 16 -> 16
                        normalized[hour_key] = v
                    except (ValueError, TypeError):
                        continue
                # Гарантируем все 24 часа
                for h in range(24):
                    if h not in normalized:
                        normalized[h] = {'total': 0, 'success': 0, 'fail': 0}
                data['by_time'] = normalized
            else:
                data['by_time'] = {hour: {'total': 0, 'success': 0, 'fail': 0} for hour in range(24)}

            # by_retest_num
            if 'by_retest_num' not in data:
                data['by_retest_num'] = {
                    '1': {'total': 0, 'success': 0, 'fail': 0},
                    '2': {'total': 0, 'success': 0, 'fail': 0},
                    '3': {'total': 0, 'success': 0, 'fail': 0}
                }

            # by_metric
            if 'by_metric' not in data:
                data['by_metric'] = {
                    'volume_high': {'total': 0, 'success': 0, 'fail': 0},
                    'volume_low': {'total': 0, 'success': 0, 'fail': 0},
                    'body_high': {'total': 0, 'success': 0, 'fail': 0},
                    'body_low': {'total': 0, 'success': 0, 'fail': 0},
                }

            # by_direction
            if 'by_direction' not in data:
                data['by_direction'] = {
                    'LONG': {'total': 0, 'success': 0, 'fail': 0},
                    'SHORT': {'total': 0, 'success': 0, 'fail': 0}
                }

            # by_symbol
            if 'by_symbol' not in data:
                data['by_symbol'] = {}

            # today
            if 'today' not in data or not isinstance(data['today'], dict):
                data['today'] = self._empty_day()

            # history
            if 'history' not in data:
                data['history'] = []

            return data
        except Exception as e:
            logger.error("❌ Ошибка загрузки statistics: %s", e)
            return self._empty_data()

    def _empty_data(self) -> Dict[str, Any]:
        """Пустая структура данных"""
        return {
            'today': self._empty_day(),
            'by_retest_num': {
                '1': {'total': 0, 'success': 0, 'fail': 0},
                '2': {'total': 0, 'success': 0, 'fail': 0},
                '3': {'total': 0, 'success': 0, 'fail': 0}
            },
            'by_metric': {
                'volume_high': {'total': 0, 'success': 0, 'fail': 0},
                'volume_low': {'total': 0, 'success': 0, 'fail': 0},
                'body_high': {'total': 0, 'success': 0, 'fail': 0},
                'body_low': {'total': 0, 'success': 0, 'fail': 0},
            },
            'by_time': {hour: {'total': 0, 'success': 0, 'fail': 0} for hour in range(24)},
            'by_direction': {'LONG': {'total': 0, 'success': 0, 'fail': 0},
                             'SHORT': {'total': 0, 'success': 0, 'fail': 0}},
            'by_symbol': {},
            'history': []
        }

    def _empty_day(self) -> Dict[str, Any]:
        """Пустая статистика за день"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'tk_proboy': 0,
            'retests': {'total': 0, 'retest_1': 0, 'retest_2': 0, 'retest_3': 0},
            'results': {'success': 0, 'fail': 0, 'pending': 0},
            'signals': []
        }

    def _get_hour_stats(self, hour: int) -> Dict[str, int]:
        """Безопасное получение статистики по часу"""
        # Поддержка и int, и str ключей
        if hour in self.data['by_time']:
            return self.data['by_time'][hour]
        elif str(hour) in self.data['by_time']:
            return self.data['by_time'][str(hour)]
        else:
            # Создаём если нет
            self.data['by_time'][hour] = {'total': 0, 'success': 0, 'fail': 0}
            return self.data['by_time'][hour]

    def record_signal(self, signal: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Записать сигнал в статистику

        metrics: {
            'volume': float,
            'volume_ratio': float,
            'body_ratio': float,
        }
        """
        today = datetime.now().strftime('%Y-%m-%d')

        # Проверка на новый день
        if self.data['today']['date'] != today:
            # Сохраняем старый день в историю
            if self.data['today']['signals']:
                self.data['history'].append(self.data['today'])
                # Храним только последние 100 дней
                self.data['history'] = self.data['history'][-100:]
            self.data['today'] = self._empty_day()

        sig_type = signal.get('type', '')
        symbol = signal.get('symbol', '')
        direction = 'LONG' if 'long' in sig_type else 'SHORT'
        retest_num = signal.get('retest_num', 1) if 'retest' in sig_type else None

        # TK-пробой (не ретест)
        if 'tk' in sig_type and 'retest' not in sig_type:
            self.data['today']['tk_proboy'] += 1
            return

        # Ретест
        if 'retest' in sig_type and retest_num:
            self.data['today']['retests']['total'] += 1
            self.data['today']['retests'][f'retest_{retest_num}'] += 1

            # Статистика по номерам ретестов
            key = str(retest_num)
            if key in self.data['by_retest_num']:
                self.data['by_retest_num'][key]['total'] += 1
                self.data['by_retest_num'][key]['pending'] = (
                        self.data['by_retest_num'][key]['total'] -
                        self.data['by_retest_num'][key]['success'] -
                        self.data['by_retest_num'][key]['fail']
                )

            # Статистика по направлению
            self.data['by_direction'][direction]['total'] += 1

            # Статистика по времени
            sig_time = signal.get('time')
            if isinstance(sig_time, datetime):
                hour = sig_time.hour
            elif isinstance(sig_time, str):
                try:
                    hour = datetime.strptime(sig_time, '%Y-%m-%d %H:%M').hour
                except:
                    hour = datetime.now().hour
            else:
                hour = datetime.now().hour

            # 🔧 Безопасное обновление по часу
            if 0 <= hour < 24:
                hour_stats = self._get_hour_stats(hour)
                hour_stats['total'] += 1

            # Статистика по метрикам
            if metrics:
                vol_ratio = metrics.get('volume_ratio', 0)
                body_ratio = metrics.get('body_ratio', 0)

                if vol_ratio >= 2.0:
                    self.data['by_metric']['volume_high']['total'] += 1
                else:
                    self.data['by_metric']['volume_low']['total'] += 1

                if body_ratio >= 1.5:
                    self.data['by_metric']['body_high']['total'] += 1
                else:
                    self.data['by_metric']['body_low']['total'] += 1

            # Статистика по монетам
            if symbol not in self.data['by_symbol']:
                self.data['by_symbol'][symbol] = {'total': 0, 'success': 0, 'fail': 0, 'pending': 0}
            self.data['by_symbol'][symbol]['total'] += 1
            self.data['by_symbol'][symbol]['pending'] += 1

            # Сохраняем сигнал для последующей проверки
            signal_record = {
                'id': f"{symbol}_{signal.get('time', datetime.now()).strftime('%Y%m%d_%H%M')}_{sig_type}",
                'symbol': symbol,
                'type': sig_type,
                'time': signal.get('time', datetime.now()).strftime('%Y-%m-%d %H:%M') if isinstance(signal.get('time'),
                                                                                                    datetime) else str(
                    signal.get('time')),
                'tk_open': signal.get('tk_open', 0),
                'entry_price': signal.get('test_close', 0),
                'direction': direction,
                'retest_num': retest_num,
                'confirmation': signal.get('confirmation', 'confirmed'),
                'volume_ratio': metrics.get('volume_ratio', 0) if metrics else 0,
                'body_ratio': metrics.get('body_ratio', 0) if metrics else 0,
                'result': 'pending',
                'exit_price': 0,
                'move_percent': 0.0,
                'candles_passed': 0
            }
            self.data['today']['signals'].append(signal_record)
            self.data['today']['results']['pending'] += 1

            # Добавляем в pending для проверки
            self.pending_signals[signal_record['id']] = {
                'symbol': symbol,
                'entry_price': signal_record['entry_price'],
                'direction': direction,
                'time': datetime.now(),
                'candles_to_check': 3
            }

        self.save()
        self.save_dashboard()

    def update_results(self, current_prices: Dict[str, float]) -> None:
        """
        Обновить результаты сигналов на основе текущих цен

        current_prices: {'BTCUSDT': 101.50, 'ETHUSDT': 3200.00, ...}
        """
        updated = 0

        for signal in self.data['today']['signals']:
            if signal['result'] != 'pending':
                continue

            symbol = signal['symbol']
            if symbol not in current_prices:
                continue

            # Проверяем сколько свечей прошло
            pending_id = signal['id']
            if pending_id not in self.pending_signals:
                continue

            pending = self.pending_signals[pending_id]
            entry_price = pending['entry_price']
            direction = pending['direction']
            current_price = current_prices.get(symbol, entry_price)

            # Считаем движение
            if direction == 'LONG':
                move_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                move_percent = ((entry_price - current_price) / entry_price) * 100

            # Обновляем сигнал
            signal['exit_price'] = current_price
            signal['move_percent'] = round(move_percent, 2)
            signal['candles_passed'] += 1

            # Проверяем результат через 3 свечи
            if signal['candles_passed'] >= 3 and signal['result'] == 'pending':
                if move_percent > 0:
                    signal['result'] = 'success'
                    self._update_stats(symbol, direction, signal['retest_num'],
                                       signal.get('volume_ratio', 0), signal.get('body_ratio', 0), True)
                else:
                    signal['result'] = 'fail'
                    self._update_stats(symbol, direction, signal['retest_num'],
                                       signal.get('volume_ratio', 0), signal.get('body_ratio', 0), False)

                self.data['today']['results']['pending'] -= 1
                if signal['result'] == 'success':
                    self.data['today']['results']['success'] += 1
                else:
                    self.data['today']['results']['fail'] += 1

                # Удаляем из pending
                del self.pending_signals[pending_id]
                updated += 1

        if updated > 0:
            self.save()
            self.save_dashboard()

    def _update_stats(self, symbol: str, direction: str, retest_num: int,
                      volume_ratio: float, body_ratio: float, success: bool) -> None:
        """Обновить статистику после получения результата"""
        key = str(retest_num)

        # По номерам ретестов
        if key in self.data['by_retest_num']:
            if success:
                self.data['by_retest_num'][key]['success'] += 1
            else:
                self.data['by_retest_num'][key]['fail'] += 1

        # По направлению
        if success:
            self.data['by_direction'][direction]['success'] += 1
        else:
            self.data['by_direction'][direction]['fail'] += 1

        # 🔧 По времени — безопасно
        hour = datetime.now().hour
        hour_stats = self._get_hour_stats(hour)
        if success:
            hour_stats['success'] += 1
        else:
            hour_stats['fail'] += 1

        # По монетам
        if symbol in self.data['by_symbol']:
            if success:
                self.data['by_symbol'][symbol]['success'] += 1
            else:
                self.data['by_symbol'][symbol]['fail'] += 1
            if self.data['by_symbol'][symbol]['pending'] > 0:
                self.data['by_symbol'][symbol]['pending'] -= 1

        # По метрикам
        if volume_ratio >= 2.0:
            if success:
                self.data['by_metric']['volume_high']['success'] += 1
            else:
                self.data['by_metric']['volume_high']['fail'] += 1
        else:
            if success:
                self.data['by_metric']['volume_low']['success'] += 1
            else:
                self.data['by_metric']['volume_low']['fail'] += 1

        if body_ratio >= 1.5:
            if success:
                self.data['by_metric']['body_high']['success'] += 1
            else:
                self.data['by_metric']['body_high']['fail'] += 1
        else:
            if success:
                self.data['by_metric']['body_low']['success'] += 1
            else:
                self.data['by_metric']['body_low']['fail'] += 1

    def get_success_rate(self, category: str = 'total') -> float:
        """Получить процент успеха"""
        if category == 'total':
            total = self.data['today']['results']['success'] + self.data['today']['results']['fail']
            if total == 0:
                return 0.0
            return (self.data['today']['results']['success'] / total) * 100
        elif category in self.data['by_retest_num']:
            data = self.data['by_retest_num'][category]
            total = data['success'] + data['fail']
            if total == 0:
                return 0.0
            return (data['success'] / total) * 100
        return 0.0

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Получить данные для дашборда"""
        today = self.data['today']

        # Рассчитываем проценты
        by_retest_percent = {}
        for key, data in self.data['by_retest_num'].items():
            total = data['success'] + data['fail']
            by_retest_percent[key] = {
                'total': data['total'],
                'success': data['success'],
                'fail': data['fail'],
                'percent': round((data['success'] / total) * 100, 1) if total > 0 else 0
            }

        by_metric_percent = {}
        for key, data in self.data['by_metric'].items():
            total = data['success'] + data['fail']
            by_metric_percent[key] = {
                'total': data['total'],
                'success': data['success'],
                'fail': data['fail'],
                'percent': round((data['success'] / total) * 100, 1) if total > 0 else 0
            }

        # Топ монет
        top_symbols = sorted(
            [(k, v) for k, v in self.data['by_symbol'].items() if v['success'] + v['fail'] > 0],
            key=lambda x: x[1]['success'] / (x[1]['success'] + x[1]['fail']) if (x[1]['success'] + x[1][
                'fail']) > 0 else 0,
            reverse=True
        )[:10]

        return {
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': today['date'],
            'summary': {
                'tk_proboy': today['tk_proboy'],
                'retests_total': today['retests']['total'],
                'retest_1': today['retests']['retest_1'],
                'retest_2': today['retests']['retest_2'],
                'retest_3': today['retests']['retest_3'],
                'success': today['results']['success'],
                'fail': today['results']['fail'],
                'pending': today['results']['pending'],
                'success_rate': round(self.get_success_rate('total'), 1)
            },
            'by_retest_num': by_retest_percent,
            'by_metric': by_metric_percent,
            'by_direction': {
                'LONG': self.data['by_direction']['LONG'],
                'SHORT': self.data['by_direction']['SHORT']
            },
            'top_symbols': [
                {
                    'symbol': sym,
                    'total': data['total'],
                    'success': data['success'],
                    'fail': data['fail'],
                    'percent': round((data['success'] / (data['success'] + data['fail'])) * 100, 1) if (data[
                                                                                                            'success'] +
                                                                                                        data[
                                                                                                            'fail']) > 0 else 0
                }
                for sym, data in top_symbols
            ],
            'recent_signals': today['signals'][-20:]  # Последние 20 сигналов
        }

    def save(self) -> bool:
        """Сохранить статистику в файл"""
        try:
            save_data = {
                'today': self.data['today'],
                'by_retest_num': self.data['by_retest_num'],
                'by_metric': self.data['by_metric'],
                'by_direction': self.data['by_direction'],
                'by_time': self.data['by_time'],  # ключи уже int, JSON сериализует их как строки — это ок
                'by_symbol': self.data['by_symbol'],
                'history': self.data['history']
            }
            with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.tmp') as tmp:
                json.dump(save_data, tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            shutil.move(tmp_path, self.file)
            return True
        except Exception as e:
            logger.error("❌ Ошибка сохранения statistics: %s", e)
            return False

    def save_dashboard(self) -> bool:
        """Сохранить данные для дашборда"""
        try:
            # Создаём папку если нет
            dashboard_dir = os.path.dirname(self.dashboard_file)
            if dashboard_dir and not os.path.exists(dashboard_dir):
                os.makedirs(dashboard_dir, exist_ok=True)

            data = self.get_dashboard_data()
            with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.tmp') as tmp:
                json.dump(data, tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            shutil.move(tmp_path, self.dashboard_file)
            return True
        except Exception as e:
            logger.error("❌ Ошибка сохранения dashboard: %s", e)
            return False