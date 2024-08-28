import datetime
import os
from enum import Enum as PyEnum

import dotenv
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

dotenv.load_dotenv()

# === DATABASE Configuration ===
DATABASE_URL = os.getenv("MYSQL_CONN_STRING")
if not DATABASE_URL:
    raise ValueError("MYSQL_CONN_STRING is not set")
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+asyncmy://", 1)
# === DATABASE ===

# Set up SQLAlchemy
Base = declarative_base()  # 这里是一个基类，所有的 ORM 类都要继承这个类
engine = create_async_engine(DATABASE_URL, echo=True)  # 创建一个引擎
# noinspection PyTypeChecker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)  # 异步会话类


# 枚举类型定义
class SubChannelEnum(PyEnum):
    OLE_VOD = "ole_vod"


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, index=True)
    username = Column(String(32), unique=True, index=True)
    email = Column(String(128), unique=True)
    email_verified = Column(Boolean, default=False)
    avatar = Column(String(256), default="")
    is_active = Column(Boolean, default=True)
    oidc_sub = Column(String(64), default="")
    sub_limit = Column(Integer(), default=3)
    bark_token = Column(String(64), default="")
    sub = relationship("VodSub", back_populates="user")  # 修正: 使用 relationship 并 back_populates
    last_login = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))  # 使用 UTC 时间
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))  # 使用 UTC 时间

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active
        }


class VodSub(Base):
    __tablename__ = "vod_subs"

    id = Column(Integer(), primary_key=True, index=True, autoincrement=True)
    sub_id = Column(String(32), index=True, unique=True)
    sub_by = Column(String(36), ForeignKey('users.user_id'))
    sub_channel = Column(String(32), default=SubChannelEnum.OLE_VOD.value)  # 将 Enum 映射为字符串
    sub_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))  # 使用 UTC 时间

    # 外键关联到 VodInfo 表
    vod_info_id = Column(Integer, ForeignKey('vod_info.id'))
    vod_info = relationship("VodInfo", back_populates="subs")  # 使用 back_populates 创建双向关系
    user = relationship("User", back_populates="sub")

    def to_dict(self):
        return {
            "sub_id": self.sub_id,
            "sub_by": self.sub_by,
            "sub_channel": self.sub_channel,
            "sub_at": self.sub_at,
            "vod_info_id": self.vod_info_id
        }


class VodInfo(Base):
    __tablename__ = "vod_info"

    id = Column(Integer(), primary_key=True, index=True, autoincrement=True, unique=True)
    vod_id = Column(String(32), index=True, unique=True)
    vod_name = Column(String(32), index=True)
    vod_typeId = Column(Integer(), index=True)
    vod_typeId1 = Column(Integer(), index=True)
    vod_remarks = Column(String(24), default="")
    vod_is_vip = Column(Boolean, default=False)
    vod_episodes = Column(Integer(), default=0)
    vod_urls = Column(String(256), default="")
    # 添加 relationship，反向关系到 VodSub
    subs = relationship("VodSub", back_populates="vod_info")

    def to_dict(self):
        return {
            "vod_id": self.vod_id,
            "vod_name": self.vod_name,
            "vod_typeId": self.vod_typeId,
            "vod_typeId1": self.vod_typeId1,
            "vod_remarks": self.vod_remarks,
            "vod_is_vip": self.vod_is_vip,
            "vod_episodes": self.vod_episodes,
            "vod_urls": self.vod_urls
        }


# 创建或修改数据库中的表
async def init_db():
    async with engine.begin() as conn:
        # 执行创建表的命令
        await conn.run_sync(Base.metadata.create_all)
