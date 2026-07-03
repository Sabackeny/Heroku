import os
import logging
from aiohttp import web

logger = logging.getLogger("heroku.bridge")

BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "")


def setup_bridge_routes(web_instance) -> None:
    """
    web_instance — это self из heroku/web/core.py (класс Web),
    у него есть .app (aiohttp Application) и .client_data
    (словарь tg_id -> (loader, client, db)).
    """

    async def send_message(request: web.Request) -> web.Response:
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

        if not web_instance.client_data:
            return web.json_response({"error": "no telegram client ready yet"}, status=503)

        # Берём первого (обычно единственного) залогиненного клиента
        _, client, _ = next(iter(web_instance.client_data.values()))

        try:
            entity = await client.get_entity(chat)
            await client.send_message(entity, text)
        except Exception as e:
            logger.exception("Failed to send message")
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response({"status": "ok", "chat": chat})

    web_instance.app.router.add_post("/send_message", send_message)
