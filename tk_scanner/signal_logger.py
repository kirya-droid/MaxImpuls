#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Signal Logger — Логирование сигналов для анализа
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
logger = logging.getLogger(__name__)


class SignalLogger:
    """Логгер сигналов для последующего анализа"""

    def __init__(self, log_file: str = 'tk_signals_log.json'):
        self.log_file = log_file
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Загрузить существующие данные"""
        if not os.path.exists(self.log_file):
            return {'signals': [], 'metadata': {'created': datetime.now().isoformat()}}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("❌ Ошибка загрузки логов: %s", e)
            return {'signals': [], 'metadata': {'created': datetime.now().isoformat()}}

    def _save(self) -> None:
        """Сохранить данные"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("❌ Ошибка сохранения логов: %s", e)

    def log_signal(
        self,
        symbol: str,
        sig_type: str,
        tk_candle: Dict[str, float],
        test_candle: Optional[Dict[str, float]],
        levels: Dict[str, float],
        metrics: Dict[str, float],
        context: Dict[str, Any],
        confirmation: str = 'unknown'
    ) -> str:
        """
        Записать новый сигнал
        
        Returns:
            signal_id: уникальный ID сигнала
        """
        signal_id = f"{symbol}_{sig_type}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        signal = {
            'signal_id': signal_id,
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'type': sig_type,
            'confirmation': confirmation,
            
            # ТК-свеча
            'tk_open': tk_candle.get('open', 0),
            'tk_close': tk_candle.get('close', 0),
            'tk_high': tk_candle.get('high', 0),
            'tk_low': tk_candle.get('low', 0),
            
            # Тестовая свеча (если есть)
            'test_open': test_candle.get('open', 0) if test_candle else 0,
            'test_close': test_candle.get('close', 0) if test_candle else 0,
            'test_high': test_candle.get('high', 0) if test_candle else 0,
            'test_low': test_candle.get('low', 0) if test_candle else 0,
            
            # Уровни
            'high_level': levels.get('high_level', 0),
            'low_level': levels.get('low_level', 0),
            'zone_high': levels.get('zone_high', 0),
            'zone_low': levels.get('zone_low', 0),
            'break_distance_pct': levels.get('break_distance_pct', 0),
            
            # Метрики
            'body_size': metrics.get('body_size', 0),
            'body_size_pct': metrics.get('body_size_pct', 0),
            'avg_body': metrics.get('avg_body', 0),
            'body_ratio': metrics.get('body_ratio', 0),
            'volume': metrics.get('volume', 0),
            'avg_volume': metrics.get('avg_volume', 0),
            'volume_ratio': metrics.get('volume_ratio', 0),
            'atr': metrics.get('atr', 0),
            'atr_pct': metrics.get('atr_pct', 0),
            
            # Контекст
            'candle_hour': context.get('candle_hour', 0),
            'day_of_week': context.get('day_of_week', 0),
            'price_vs_ma50_pct': context.get('price_vs_ma50_pct', 0),
            'price_vs_ma200_pct': context.get('price_vs_ma200_pct', 0),
            'trend': context.get('trend', 'unknown'),
            
            # Результат (заполняется позже)
            'result': {
                'success': None,
                'max_profit_pct': 0,
                'max_loss_pct': 0,
                'exit_reason': 'pending',
                'exit_price': 0,
                'exit_time': None
            },
            
            # Статус
            'status': 'pending'
        }
        
        self.data['signals'].append(signal)
        self._save()
        
        logger.info("📝 Сигнал записан: %s", signal_id)
        return signal_id

    def update_result(
        self,
        signal_id: str,
        success: bool,
        max_profit_pct: float,
        max_loss_pct: float,
        exit_reason: str,
        exit_price: float = 0,
        exit_time: Optional[datetime] = None
    ) -> bool:
        """Обновить результат сигнала"""
        for signal in self.data['signals']:
            if signal['signal_id'] == signal_id:
                signal['result'] = {
                    'success': success,
                    'max_profit_pct': round(max_profit_pct, 3),
                    'max_loss_pct': round(max_loss_pct, 3),
                    'exit_reason': exit_reason,
                    'exit_price': exit_price,
                    'exit_time': exit_time.isoformat() if exit_time else None
                }
                signal['status'] = 'completed' if exit_reason != 'pending' else 'active'
                self._save()
                logger.info("✅ Результат обновлён: %s", signal_id)
                return True
        
        logger.warning("⚠️ Сигнал не найден: %s", signal_id)
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по всем сигналам"""
        signals = self.data['signals']
        
        if not signals:
            return {'total': 0}
        
        completed = [s for s in signals if s['status'] == 'completed']
        pending = [s for s in signals if s['status'] == 'pending']
        
        total = len(completed)
        if total == 0:
            return {
                'total': len(signals),
                'completed': 0,
                'pending': len(pending)
            }
        
        success = [s for s in completed if s['result']['success']]
        fail = [s for s in completed if not s['result']['success']]
        
        # По типам сигналов
        by_type = {}
        for sig_type in set(s['type'] for s in completed):
            type_signals = [s for s in completed if s['type'] == sig_type]
            type_success = [s for s in type_signals if s['result']['success']]
            by_type[sig_type] = {
                'total': len(type_signals),
                'success': len(type_success),
                'win_rate': round(len(type_success) / len(type_signals) * 100, 1) if type_signals else 0
            }
        
        # По символам
        by_symbol = {}
        for symbol in set(s['symbol'] for s in completed):
            sym_signals = [s for s in completed if s['symbol'] == symbol]
            sym_success = [s for s in sym_signals if s['result']['success']]
            if len(sym_signals) >= 3:  # Минимум 3 сигнала
                by_symbol[symbol] = {
                    'total': len(sym_signals),
                    'success': len(sym_success),
                    'win_rate': round(len(sym_success) / len(sym_signals) * 100, 1)
                }
        
        # По времени суток
        by_hour = {}
        for hour in range(24):
            hour_signals = [s for s in completed if s['candle_hour'] == hour]
            hour_success = [s for s in hour_signals if s['result']['success']]
            if hour_signals:
                by_hour[hour] = {
                    'total': len(hour_signals),
                    'success': len(hour_success),
                    'win_rate': round(len(hour_success) / len(hour_signals) * 100, 1)
                }
        
        # Средние значения
        avg_profit = sum(s['result']['max_profit_pct'] for s in completed) / total
        avg_loss = sum(s['result']['max_loss_pct'] for s in completed) / total
        
        return {
            'total': len(signals),
            'completed': total,
            'pending': len(pending),
            'success': len(success),
            'fail': len(fail),
            'win_rate': round(len(success) / total * 100, 1),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'by_type': by_type,
            'by_symbol': by_symbol,
            'by_hour': by_hour
        }

    def export_for_analysis(self, output_file: str = 'signals_analysis.csv') -> str:
        """Экспорт данных для анализа (CSV)"""
        import csv
        
        signals = self.data['signals']
        if not signals:
            return "Нет данных для экспорта"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'signal_id', 'timestamp', 'symbol', 'type', 'confirmation',
                'tk_open', 'tk_close', 'tk_high', 'tk_low',
                'body_size_pct', 'volume_ratio', 'atr_pct',
                'break_distance_pct', 'candle_hour', 'trend',
                'price_vs_ma50_pct',
                'success', 'max_profit_pct', 'max_loss_pct', 'exit_reason'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for s in signals:
                writer.writerow({
                    'signal_id': s['signal_id'],
                    'timestamp': s['timestamp'],
                    'symbol': s['symbol'],
                    'type': s['type'],
                    'confirmation': s['confirmation'],
                    'tk_open': s['tk_open'],
                    'tk_close': s['tk_close'],
                    'tk_high': s['tk_high'],
                    'tk_low': s['tk_low'],
                    'body_size_pct': s['body_size_pct'],
                    'volume_ratio': s['volume_ratio'],
                    'atr_pct': s['atr_pct'],
                    'break_distance_pct': s['break_distance_pct'],
                    'candle_hour': s['candle_hour'],
                    'trend': s['trend'],
                    'price_vs_ma50_pct': s['price_vs_ma50_pct'],
                    'success': s['result']['success'],
                    'max_profit_pct': s['result']['max_profit_pct'],
                    'max_loss_pct': s['result']['max_loss_pct'],
                    'exit_reason': s['result']['exit_reason']
                })
        
        return f"✅ Экспортировано {len(signals)} сигналов в {output_file}"
