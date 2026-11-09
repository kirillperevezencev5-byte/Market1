import hashlib
import hmac
import json
import time

from urllib.parse import parse_qsl

from fastapi import HTTPException

from app.config import settings


def validate_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(
            status_code=401,
            detail="Telegram authorization data is missing"
        )

    if settings.allow_dev_user:
        return {
            "id": 0,
            "first_name": "Development User",
            "username": "developer"
        }

    if not settings.bot_token:
        raise HTTPException(
            status_code=500,
            detail="Bot token is not configured"
        )

    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram authorization data"
        )

    received_hash = parsed_data.pop("hash", None)

    if not received_hash:
        raise HTTPException(
            status_code=401,
            detail="Telegram hash is missing"
        )

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed_data.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=401,
            detail="Telegram authorization signature is invalid"
        )

    auth_date = parsed_data.get("auth_date")

    if not auth_date:
        raise HTTPException(
            status_code=401,
            detail="Authorization date is missing"
        )

    try:
        auth_timestamp = int(auth_date)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization date"
        )

    if time.time() - auth_timestamp > 86400:
        raise HTTPException(
            status_code=401,
            detail="Telegram authorization data has expired"
        )

    user_data = parsed_data.get("user")

    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Telegram user data is missing"
        )

    try:
        user = json.loads(user_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram user data"
        )

    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(
            status_code=401,
            detail="Telegram user ID is missing"
        )

    return user