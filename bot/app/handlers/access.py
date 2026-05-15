from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Router
from aiogram.types import Message


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, whitelist_tg_id: int) -> None:
        self.whitelist_tg_id = whitelist_tg_id

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is None or event.from_user.id != self.whitelist_tg_id:
            await event.answer("Access denied")
            return None
        return await handler(event, data)


def setup_whitelist(router: Router, whitelist_tg_id: int) -> None:
    router.message.middleware(WhitelistMiddleware(whitelist_tg_id))
