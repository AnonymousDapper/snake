from sqlalchemy import ForeignKey, Integer, BigInteger, String, Date, Boolean, Column, create_engine

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Start mapping classes

class Tag(Base):
    __tablename__ = "tags"

    name = Column(String(50), primary_key=True)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="tags")
    content = Column(String(1500))
    uses = Column(Integer)
    timestamp = Column(String)

    def __repr__(self):
        return f"<Tag(name='{self.name}', author_id={self.author_id}, uses={self.uses}, timestamp='{self.timestamp}')>"

class Permission(Base):
    __tablename__ = "permissions"

    pk = Column(Integer, primary_key=True)
    server_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user = relationship("User", back_populates="permissions")
    user_id = Column(BigInteger, ForeignKey("users.id"))
    bits = Column(BigInteger)

    def __repr__(self):
        return f"<Permission(server_id={self.server_id}, channel_id={self.channel_id}, user_id={self.user_id}, bits={self.bits})>"

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(40))
    bot = Column(Boolean)
    discrim = Column(String(4))
    permissions = relationship("Permission", back_populates="user", cascade="all, delete, delete-orphan")
    messages = relationship("Message", back_populates="author", cascade="all, delete, delete-orphan")
    tags = relationship("Tag", back_populates="author", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', nick='{self.nick}', bot={self.bot}, discrim='{self.discrim}', permissions={self.permissions}, messages={self.messages}, tags={self.tags})>"

class Blacklist(Base):
    __tablename__ = "blacklist"

    pk = Column(Integer, primary_key=True)
    server_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user_id = Column(BigInteger)

    data = Column(String)

    def __repr__(self):
        return f"<Blacklist(server_id={self.server_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class Whitelist(Base):
    __tablename__ = "whitelist"

    pk = Column(Integer, primary_key=True)
    server_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user_id = Column(BigInteger)

    data = Column(String)

    def __repr__(self):
        return f"<Whitelist(server_id={self.server_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class TagVariable(Base):
    __tablename__ = "tag_values"

    tag_name = Column(String(50), primary_key=True)
    data = Column(JSONB) # JSONb as key:value pairs

    def __repr__(self):
        return f"<TagVariable(tag_name='{self.tag_name}, values={self.data})>"

class Message(Base):
    __tablename__ = "chat_logs"

    pk = Column(Integer, primary_key=True)
    id = Column(BigInteger)
    timestamp = Column(String)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="messages")
    channel_id = Column(BigInteger)
    server_id = Column(BigInteger)
    content = Column(String(2000))
    action = Column(String(15))

    def __repr__(self):
        return f"<Message(id={self.id}, timestamp='{self.timestamp}', author_id={self.author_id}, channel_id={self.channel_id}, server_id={self.server_id}, action='{self.action}')>"

class Command(Base):
    __tablename__ = "command_stats"

    command_name = Column(String(40), primary_key=True)
    uses = Column(Integer)

    def __repr__(self):
        return f"<Command(command_name='{self.command_name}', uses={self.uses})>"

class Prefix(Base):
    __tablename__ = "prefixes"

    server_id = Column(BigInteger, primary_key=True)
    prefix = Column(String(25))

    def __repr__(self):
        return f"<Prefix(server_id={self.server_id}, prefix='{self.prefix}')>"

# Actual adapter class

class SQL:
    def __init__(self, *args, **kwargs):
        self.db_name = kwargs.get("db_name")
        self.db_username = kwargs.get("db_username")
        self.db_password = kwargs.get("db_password")
        self.db_api = kwargs.get("db_api", "pypostgresql")
        self.engine = create_engine(f"postgresql+{self.db_api}://{self.db_username}:{self.db_password}@localhost:5432/{self.db_name}", echo=False)
        self.Session = sessionmaker(bind=self.engine)

        Base.metadata.create_all(self.engine)

    def flag(self, obj, type_):
        flag_modified(obj, type_)