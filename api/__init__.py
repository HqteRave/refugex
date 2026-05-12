"""
API модуль для работы с STALCRAFT API
Упрощённая версия без лишних обёрток
"""
from .stalcraft import get_price_history, calculate_price_stats

__all__ = ['get_price_history', 'calculate_price_stats']
