# 📊 Signal Logger — Логирование сигналов для анализа

## 🎯 Назначение

Система сохраняет **все сигналы** с полными метриками для последующего анализа и улучшения стратегии.

---

## 📁 Файлы

| Файл | Описание |
|------|----------|
| `tk_signals_log.json` | Все сигналы с метриками (автосохранение) |
| `signals_analysis.csv` | Экспорт для анализа в Excel/Python |

---

## 📋 Что сохраняется для каждого сигнала:

### 1. Основная информация
- `signal_id` — уникальный ID
- `timestamp` — время сигнала (MSK)
- `symbol` — монета (например, STOUSDT)
- `type` — тип сигнала (long_tk, long_retest_1, short_retest_1)
- `confirmation` — confirmed / warning

### 2. Цены свечей
- `tk_open`, `tk_close`, `tk_high`, `tk_low` — ТК-свеча
- `test_open`, `test_close`, `test_high`, `test_low` — тестовая свеча

### 3. Уровни
- `high_level`, `low_level` — уровни за 10 свечей
- `zone_high`, `zone_low` — границы зоны
- `break_distance_pct` — % пробоя от цены

### 4. Метрики
- `body_size_pct` — % тела свечи от цены
- `body_ratio` — отношение к среднему телу
- `volume_ratio` — отношение к среднему объёму
- `atr_pct` — волатильность (ATR)

### 5. Контекст
- `candle_hour` — час свечи (0-23)
- `day_of_week` — день недели (0-6)
- `trend` — тренд (пока unknown)

### 6. Результат (заполняется через 3 часа)
- `success` — true/false
- `max_profit_pct` — максимальный профит %
- `max_loss_pct` — максимальный убыток %
- `exit_reason` — target / stoploss / timeout
- `exit_price` — цена выхода
- `exit_time` — время выхода

---

## 🚀 Использование

### Автоматическое логирование

Все сигналы **автоматически** записываются при работе бота.

### Команда /stats

Отправь боту `/stats` — получишь статистику:

```
📊 Статистика сигналов

📈 Всего: 150
✅ Завершено: 120
⏳ Ожидает: 30

✅ Win Rate: 45.0%
📊 Успешных: 54 | Неудач: 66

💰 Средний профит: +1.2%
📉 Средний убыток: -0.8%

🏆 Топ символы:
  SUIUSDT: 68.6% (24/35)
  SOLUSDT: 63.3% (19/30)
  BNBUSDT: 59.1% (13/22)
```

### Экспорт для анализа

Через 1-2 недели собери данные:

```bash
# На сервере
cd /home/ImpulsBot
python3 -c "from tk_scanner.signal_logger import SignalLogger; sl = SignalLogger(); sl.export_for_analysis()"
```

Получишь файл `signals_analysis.csv` — открой в Excel или Google Sheets.

---

## 📈 Анализ данных

### Что искать:

1. **Win Rate по типам сигналов**
   - `long_tk` vs `long_retest_1`
   - `short_tk` vs `short_retest_1`

2. **Win Rate по времени суток**
   - Какие часы лучшие?
   - Какие часы избегать?

3. **Win Rate по символам**
   - Какие монеты дают лучший %?
   - Какие монеты убыточны?

4. **Метрики успешных сигналов**
   - Какой средний `body_size_pct`?
   - Какой средний `volume_ratio`?
   - Какой средний `break_distance_pct`?

### Пример фильтрации:

```python
# В Excel или Python отфильтруй:
# Успешные LONG ретесты
type == "long_retest_1" AND success == True

# Найди общие паттерны:
# - body_size_pct в диапазоне?
# - volume_ratio > 1.5?
# - candle_hour в диапазоне?
```

---

## 🎯 План улучшения (через 2 недели):

1. **Собрать 500+ сигналов**
2. **Экспортировать в CSV**
3. **Найти паттерны успешных**
4. **Добавить фильтры в стратегию**
5. **Протестировать на истории**
6. **Залить на сервер**

---

## 📊 Пример JSON сигнала:

```json
{
  "signal_id": "STOUSDT_long_retest_1_20260320_1200",
  "timestamp": "2026-03-20T12:00:00+03:00",
  "symbol": "STOUSDT",
  "type": "long_retest_1",
  "confirmation": "confirmed",
  "tk_open": 0.5234,
  "tk_close": 0.5312,
  "body_size_pct": 1.49,
  "volume_ratio": 1.28,
  "atr_pct": 1.62,
  "break_distance_pct": 0.65,
  "candle_hour": 12,
  "result": {
    "success": true,
    "max_profit_pct": 1.2,
    "max_loss_pct": 0.3,
    "exit_reason": "target"
  }
}
```

---

## 🔧 Модификация

Если хочешь добавить свои метрики — редактируй `signal_logger.py`:

```python
# В методе log_signal добавить:
'your_metric': metrics.get('your_metric', 0),
```

Все данные сохраняются в `tk_signals_log.json` автоматически!
