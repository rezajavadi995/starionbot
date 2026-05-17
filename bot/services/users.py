from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    full_name: str,
    username: str | None,
    language: str = "fa",
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is not None:
        return user
    user = User(telegram_id=telegram_id, full_name=full_name, username=username, language=language)
    session.add(user)
    await session.flush()
    return user
