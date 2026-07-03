"""
Этот файл — не для Render, а для ТВОЕГО Heroku-юзербота
(репозиторий Sabackeny/Heroku).

Добавляет в существующий aiohttp Web-сервер юзербота роут
POST /send_message, который принимает запрос от telegram-bridge-mcp
и реально отправляет сообщение через клиент юзербота (Telethon).

Как встроить:
1. Найди файл, где у Heroku поднимается aiohttp `Web` (там же, где ты
   раньше пытался добавить claude_bridge.py — судя по прошлому опыту,
   проще всего искать через GitHub code search в репозитории, а не
   через gc/рефлексию по объектам в рантайме).
2. Импортни setup_bridge_routes(app, client) и вызови её там, где
   Web-приложение создаётся и где уже доступен активный TelegramClient.
3. В Render/окружении юзербота задай переменную BRIDGE_SECRET —
   такую же, как у MCP-сервера на втором аккаунте.

Пример интеграции (примерно, зависит от структуры форка Heroku):

    from heroku_side_bridge import setup_bridge_routes
    ...
    app = web.Application()
    setup_bridge_routes(app, self.client)  # self.client — TelegramClient
"""

import os
import logging
from aiohttp import web

logger = logging.getLogger("heroku.bridge")

BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "")


def setup_bridge_routes(app: web.Application, telegram_client) -> None:
    async def send_message(request: web.Request) -> web.Response:
        # Проверка секрета — чтобы левые запросы не могли слать
        # сообщения от твоего имени
        if BRIDGE_SECRET and request.headers.get("X-Bridge-Secret") != BRIDGE_SECRET:
            return web.json_response({"error": "unauthorized"}, status=401)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        chat = data.get("chat")
        text = data.get("text")
        if not chat or not text:
            return web.json_response({"error": "chat and text are required"}, status=400)

        try:
            entity = await telegram_client.get_entity(chat)
            await telegram_client.send_message(entity, text)
        except Exception as e:
            logger.exception("Failed to send message")
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response({"status": "ok", "chat": chat})

    app.router.add_post("/send_message", send_message)
