
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from database import get_db, init_db
from auth import validate_init_data
from models import User, Community, Template, ReplyRule, ScheduledPost


app = FastAPI(title="MarketPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup():
    init_db()


class CommunityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    username: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    community_type: str = "group"


class TemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ReplyRuleCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    response: str = Field(min_length=1)


class ScheduledPostCreate(BaseModel):
    content: str = Field(min_length=1)
    publish_at: datetime
    community_id: Optional[int] = None


def get_current_user(
    x_telegram_init_data: Optional[str] = Header(
        default=None,
        alias="X-Telegram-Init-Data"
    ),
    db: Session = Depends(get_db)
):
    telegram_user = validate_init_data(x_telegram_init_data or "")
    telegram_id = int(telegram_user["id"])

    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name")
        )
        db.add(user)
    else:
        user.username = telegram_user.get("username")
        user.first_name = telegram_user.get("first_name")

    db.commit()
    db.refresh(user)
    return user


@app.get("/")
def root():
    return {"name": "MarketPilot API", "status": "online"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "MarketPilot"}


@app.get("/api/me")
def get_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "created_at": user.created_at
    }


@app.get("/api/communities")
def get_communities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Community).filter(Community.owner_id == user.id).order_by(Community.id.desc()).all()
    return [
        {
            "id": x.id,
            "title": x.title,
            "username": x.username,
            "telegram_chat_id": x.telegram_chat_id,
            "community_type": x.community_type,
            "is_active": x.is_active,
            "created_at": x.created_at
        }
        for x in items
    ]


@app.post("/api/communities")
def create_community(data: CommunityCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = Community(owner_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "id": item.id, "title": item.title}


@app.delete("/api/communities/{community_id}")
def delete_community(community_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Community).filter(Community.id == community_id, Community.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Community not found")
    db.delete(item)
    db.commit()
    return {"success": True}


@app.get("/api/templates")
def get_templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Template).filter(Template.owner_id == user.id).order_by(Template.id.desc()).all()
    return [{"id": x.id, "title": x.title, "content": x.content, "created_at": x.created_at} for x in items]


@app.post("/api/templates")
def create_template(data: TemplateCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = Template(owner_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "id": item.id}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(Template).filter(Template.id == template_id, Template.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(item)
    db.commit()
    return {"success": True}


@app.get("/api/replies")
def get_replies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(ReplyRule).filter(ReplyRule.owner_id == user.id).order_by(ReplyRule.id.desc()).all()
    return [{"id": x.id, "keyword": x.keyword, "response": x.response, "is_active": x.is_active} for x in items]


@app.post("/api/replies")
def create_reply(data: ReplyRuleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = ReplyRule(owner_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "id": item.id}


@app.delete("/api/replies/{reply_id}")
def delete_reply(reply_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ReplyRule).filter(ReplyRule.id == reply_id, ReplyRule.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Reply rule not found")
    db.delete(item)
    db.commit()
    return {"success": True}


@app.get("/api/posts")
def get_posts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(ScheduledPost).filter(ScheduledPost.owner_id == user.id).order_by(ScheduledPost.publish_at.asc()).all()
    return [
        {
            "id": x.id,
            "content": x.content,
            "publish_at": x.publish_at,
            "community_id": x.community_id,
            "is_published": x.is_published
        }
        for x in items
    ]


@app.post("/api/posts")
def create_post(data: ScheduledPostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.community_id is not None:
        community = db.query(Community).filter(
            Community.id == data.community_id,
            Community.owner_id == user.id
        ).first()
        if not community:
            raise HTTPException(status_code=404, detail="Community not found")

    if data.publish_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Publication time must be in the future")

    item = ScheduledPost(owner_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "id": item.id, "publish_at": item.publish_at}


@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ScheduledPost).filter(ScheduledPost.id == post_id, ScheduledPost.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(item)
    db.commit()
    return {"success": True}
