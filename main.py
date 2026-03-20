#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 TK PRO Scanner — главная точка входа
"""

import sys
import os

# Добавляем текущую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tk_scanner.main import main

if __name__ == "__main__":
    main()
