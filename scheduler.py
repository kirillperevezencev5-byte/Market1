
import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import ScheduledPost, Community


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MarketPilot.Scheduler")

CHECK_INTERVAL = 10


async def publish_due_posts(bot: Bot):
    db = SessionLocal()

    try:
        now = datetime.utcnow()

        posts = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.is_published == False,
                ScheduledPost.publish_at <= now,
                ScheduledPost.community_id.isnot(None)
            )
            .order_by(ScheduledPost.publish_at.asc())
            .all()
        )

        for post in posts:
            community = db.query(Community).filter(
                Community.id == post.community_id,
                Community.owner_id == post.owner_id
            ).first()

            if not community:
                logger.warning(
                    "Post %s skipped: community not found",
                    post.id
                )
                continue

            if not community.telegram_chat_id:
                logger.warning(
                    "Post %s skipped: Telegram chat ID is missing",
                    post.id
                )
                continue

            try:
                await bot.send_message(
                    chat_id=community.telegram_chat_id,
                    text=post.content
                )

                post.is_published = True
                db.commit()

                logger.info(
                    "Post %s published to %s",
                    post.id,
                    community.title
                )

            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to publish post %s",
                    post.id
                )

    finally:
        db.close()


async def main():
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN не указан в файле .env"
        )

    bot = Bot(token=settings.bot_token)

    logger.info("MarketPilot Scheduler started")

    try:
        while True:
            await publish_due_posts(bot)
            await asyncio.sleep(CHECK_INTERVAL)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
