import os
import dotenv
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Boolean, create_engine, Column, Integer, String

dotenv.load_dotenv()

# === DATABASE Configuration ===
enableMySQL = os.environ.get("ENABLE_MYSQL", "false")
if not enableMySQL.lower() in ["true", "false"]:
    raise RuntimeError("ENABLE_MYSQL must be either 'true' or 'false'")
if enableMySQL.lower() == "true":
    DATABASE_URL = os.environ.get("MYSQL_CONN_STRING")
else:
    DATABASE_URL = f"sqlite:///./test.db"
# === DATABASE ===

# Set up SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency to get the SQLAlchemy session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def testSQL():
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Error connecting to SQL: {e}")
        return False


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    oidc_sub = Column(String, unique=True, index=True)
    username = Column(String)
    email = Column(String)
    email_verified = Column(Boolean, default=False)
    avatar = Column(String, nullable=True)
    has_subscribe = Column(Boolean, default=False)
    sub_vod = Column(String, default="[]")
    sub_tv = Column(String, default="[]")
    sub_live = Column(String, default="[]")
    sub_overseas = Column(String, default="[]")
    last_login = Column(String, default="")

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'email_verified': self.email_verified,
            'avatar': self.avatar,
            'has_subscribe': self.has_subscribe,
            'sub_vod': self.sub_vod,
            'sub_tv': self.sub_tv,
            'sub_live': self.sub_live,
            'sub_overseas': self.sub_overseas,
            'last_login': self.last_login,
        }


# Create the database tables
Base.metadata.create_all(bind=engine)
