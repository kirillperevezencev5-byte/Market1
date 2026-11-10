import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    """Validate Telegram Mini App initData using Telegram's HMAC validation scheme."""
    if not init_data or not bot_token:
        raise ValueError("Missing initData or bot token")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing Telegram hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid Telegram signature")
    auth_date = int(pairs.get("auth_date", "0"))
    if auth_date <= 0 or time.time() - auth_date > max_age_seconds:
        raise ValueError("Expired Telegram initData")
    user_raw = pairs.get("user")
    if not user_raw:
        raise ValueError("Telegram user data is missing")
    return json.loads(user_raw)


def current_user(
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Telegram authentication required")
    try:
        tg_user = validate_init_data(x_telegram_init_data, settings.bot_token)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired Telegram authentication")
    telegram_id = int(tg_user["id"])
    user = db.query(User).filter(User.telegram_id == telegram_id).one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=tg_user.get("username"), first_name=tg_user.get("first_name"))
        db.add(user)
    else:
        user.username = tg_user.get("username")
        user.first_name = tg_user.get("first_name")
    db.commit()
    db.refresh(user)
    return user
