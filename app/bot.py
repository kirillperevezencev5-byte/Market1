from aiogram import Bot, Dispatcher
from aiogram.enums import ChatMemberStatus
from aiogram.types import Update, ChatMemberUpdated
from sqlalchemy.orm import Session
from .config import get_settings
from .database import SessionLocal
from .models import Community, User, AuditEvent

settings = get_settings()
bot = Bot(token=settings.bot_token) if settings.bot_token else None
dp = Dispatcher()


@dp.my_chat_member()
async def bot_membership_changed(event: ChatMemberUpdated):
    """Track a group/channel when an admin adds the bot with admin rights."""
    db: Session = SessionLocal()
    try:
        community = db.query(Community).filter(Community.telegram_chat_id == event.chat.id).one_or_none()
        if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            actor = event.from_user
            owner = db.query(User).filter(User.telegram_id == actor.id).one_or_none()
            kind = "channel" if event.chat.type == "channel" else "group"
            if community is None:
                community = Community(
                    telegram_chat_id=event.chat.id,
                    title=event.chat.title or "Без названия",
                    kind=kind,
                    bot_is_admin=True,
                    owner_id=owner.id if owner else None,
                    added_by_telegram_id=actor.id,
                )
                db.add(community)
            else:
                community.title = event.chat.title or community.title
                community.kind = kind
                community.bot_is_admin = True
                community.added_by_telegram_id = actor.id
                if owner:
                    community.owner_id = owner.id
            db.add(AuditEvent(owner_id=owner.id if owner else None, event_type="community_connected",
                              description=f"Бот получил права администратора: {event.chat.title or event.chat.id}"))
            db.commit()
        elif event.new_chat_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
            if community:
                community.bot_is_admin = False
                db.add(AuditEvent(owner_id=community.owner_id, community_id=community.id,
                                  event_type="bot_permissions_lost", description="Бот удалён или потерял права администратора"))
                db.commit()
    finally:
        db.close()


async def process_update(payload: dict):
    if bot is None:
        raise RuntimeError("BOT_TOKEN is not configured")
    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)
