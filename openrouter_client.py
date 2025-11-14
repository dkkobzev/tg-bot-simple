from __future__ import annotations
import os
import time
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')


@dataclass
class OpenRouterError(Exception):
    status: int
    msg: str

    def __str__(self) -> str:
        return f"[{self.status}] {self.msg}"


def _friendly_status(status: int) -> str:
    return {
        400: 'Неверный формат запроса.',
        401: 'Ключ OpenRouter отклонён. Проверьте OPENROUTER_API_KEY.',
        403: 'Нет прав доступа к модели.',
        404: 'Эндпоинт не найден. Проверьте URL /api/v1/chat/completions.',
        405: 'Превышен лимит бесплатной модели. Попробуйте позднее.',
        500: 'Внутренняя ошибка сервера OpenRouter. Попробуйте позже.',
        502: 'Плохой шлюз. Сервер OpenRouter временно недоступен.',
        503: 'Сервис OpenRouter временно недоступен. Попробуйте позже.',
        504: 'Таймаут шлюза. Сервер OpenRouter не ответил вовремя.',
    }.get(status, 'Сервис недоступен. Повторите попытку позже.')


class OpenRouterClient:
    """
    Клиент для работы с OpenRouter API.

    Почему отдельный класс для клиента?

    1. Единая точка интеграции.
       Заголовки, базовый URL, таймауты, формат payload, разбор 
       ответа — в одном месте.

    2. Если что-то поменяется у OpenRouter, правим один файл, 
       а не весь проект.

    3. Валидируем и нормализуем.
       Проверяем наличие ключа, модели, формируем 
       «дружественные» сообщения об ошибках (401/404/429/5xx), 
       гарантируем одинаковый тип возврата (text: str, latency, ms: int).
    """

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY не найден в переменных окружения")

        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_API
        self.timeout = 30

    def chat_once(self, messages: List[dict], model: str, temperature: float = 0.7, max_tokens: int = 1000) -> tuple:
        """
        Отправляет запрос к модели и возвращает ответ и время выполнения.

        Args:
            messages: Список сообщений в формате OpenAI
            model: Идентификатор модели
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            tuple: (текст ответа, время выполнения в мс)

        Raises:
            OpenRouterError: При ошибках API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.time()

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            # Обработка HTTP ошибок
            if response.status_code != 200:
                friendly_msg = _friendly_status(response.status_code)
                raise OpenRouterError(response.status_code, friendly_msg)

            data = response.json()

            # Извлечение текста ответа
            if "choices" not in data or not data["choices"]:
                raise OpenRouterError(500, "Пустой ответ от модели")

            text = data["choices"][0]["message"]["content"]
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            return text, latency_ms

        except requests.exceptions.Timeout:
            raise OpenRouterError(504, "Таймаут запроса к OpenRouter")
        except requests.exceptions.ConnectionError:
            raise OpenRouterError(503, "Ошибка соединения с OpenRouter")
        except Exception as e:
            raise OpenRouterError(500, f"Неизвестная ошибка: {str(e)}")