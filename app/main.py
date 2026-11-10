from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, engine, get_db
from .models import User, Community, Template, AuditEvent
from .schemas import UserOut, CommunityOut, TemplateCreate, TemplateOut
from .telegram_auth import current_user
from . import bot as bot_module

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    if bot_module.bot:
        await bot_module.bot.session.close()


app = FastAPI(title="MarketPilot API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/communities", response_model=list[CommunityOut])
def list_communities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Community).filter(Community.owner_id == user.id).order_by(Community.created_at.desc()).all()


@app.get("/api/templates", response_model=list[TemplateOut])
def list_templates(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Template).filter(Template.owner_id == user.id).order_by(Template.created_at.desc()).all()


@app.post("/api/templates", response_model=TemplateOut, status_code=201)
def create_template(payload: TemplateCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    template = Template(owner_id=user.id, name=payload.name.strip(), body=payload.body)
    db.add(template)
    db.commit()
    db.refresh(template)
    db.add(AuditEvent(owner_id=user.id, event_type="template_created", description=f"Создан шаблон «{template.name}»"))
    db.commit()
    return template


@app.delete("/api/templates/{template_id}", status_code=204)
def delete_template(template_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id, Template.owner_id == user.id).one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return Response(status_code=204)


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if not settings.telegram_webhook_secret:
        raise HTTPException(status_code=503, detail="Telegram webhook is not configured")
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    if not bot_module.bot:
        raise HTTPException(status_code=503, detail="Bot token is not configured")
    await bot_module.process_update(await request.json())
    return {"ok": True}
