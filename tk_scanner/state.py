#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 Управление состоянием
"""

import json
import os
import tempfile
import shutil
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_state(state_file: str) -> Dict[str, Any]:
    """Загрузить состояние из файла"""
    if not os.path.exists(state_file):
        return {'states': {}, 'sent_signals': {}}
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'sent_signals' not in data:
            data['sent_signals'] = {}
        if not isinstance(data.get('states'), dict):
            data['states'] = {}
        return data
    except Exception as e:
        logger.error("❌ Ошибка загрузки state: %s", e)
    return {'states': {}, 'sent_signals': {}}


def save_state(state: Dict[str, Any], state_file: str) -> bool:
    """Сохранить состояние в файл"""
    try:
        save_data = {
            'states': state.get('states', {}),
            'sent_signals': dict(state.get('sent_signals', {}))
        }
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.tmp') as tmp:
            json.dump(save_data, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name
        shutil.move(tmp_path, state_file)
        return True
    except Exception as e:
        logger.error("❌ Ошибка сохранения state: %s", e)
        return False


def cleanup_sent_signals(sent_signals: Dict, max_age_hours: int) -> Dict:
    """Очистить старые отправленные сигналы"""
    cutoff = time.time() * 1000 - max_age_hours * 3600 * 1000
    to_remove = [k for k, v in sent_signals.items() if isinstance(v, (int, float)) and v < cutoff]
    for k in to_remove:
        del sent_signals[k]
    return sent_signals
