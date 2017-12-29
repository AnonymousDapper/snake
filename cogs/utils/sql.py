from sqlalchemy import ForeignKey, INTEGER, TEXT, BOOLEAN, Column, create_engine

from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Start mapping classesS

class Tag(Base):
    __tablename__ = "tags"

    name = Column(TEXT, primary_key=True) # limit of 50
    author_id = Column(INTEGER, ForeignKey("users.id"))
    author = relationship("User", back_populates="tags")
    content = Column(TEXT) # limit of 1500
    uses = Column(INTEGER)
    timestamp = Column(TEXT)

    def __repr__(self):
        return f"<Tag(name='{self.name}', author_id={self.author_id}, uses={self.uses}, timestamp='{self.timestamp}')>"

class Permission(Base):
    __tablename__ = "permissions"

    pk = Column(INTEGER, primary_key=True)
    guild_id = Column(INTEGER)
    channel_id = Column(INTEGER)
    role_id = Column(INTEGER)
    user = relationship("User", back_populates="permissions")
    user_id = Column(INTEGER, ForeignKey("users.id"))
    bits = Column(INTEGER)

    def __repr__(self):
        return f"<Permission(guild_id={self.guild_id}, channel_id={self.channel_id}, user_id={self.user_id}, bits={self.bits})>"

class User(Base):
    __tablename__ = "users"

    id = Column(INTEGER, primary_key=True)
    name = Column(TEXT) # limit of 40
    bot = Column(BOOLEAN)
    discrim = Column(TEXT) # limit of 4
    permissions = relationship("Permission", back_populates="user", cascade="all, delete, delete-orphan")
    messages = relationship("Message", back_populates="author", cascade="all, delete, delete-orphan")
    tags = relationship("Tag", back_populates="author", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', bot={self.bot}, discrim='{self.discrim}', permissions={self.permissions}, messages={self.messages}, tags={self.tags})>"

class Blacklist(Base):
    __tablename__ = "blacklist"

    pk = Column(INTEGER, primary_key=True)
    guild_id = Column(INTEGER)
    channel_id = Column(INTEGER)
    role_id = Column(INTEGER)
    user_id = Column(INTEGER)

    data = Column(TEXT)

    def __repr__(self):
        return f"<Blacklist(guild_id={self.guild_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class Whitelist(Base):
    __tablename__ = "whitelist"

    pk = Column(INTEGER, primary_key=True)
    guild_id = Column(INTEGER)
    channel_id = Column(INTEGER)
    role_id = Column(INTEGER)
    user_id = Column(INTEGER)

    data = Column(TEXT)

    def __repr__(self):
        return f"<Whitelist(guild_id={self.guild_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class TagVariable(Base):
    __tablename__ = "tag_values"

    tag_name = Column(TEXT, primary_key=True) # limit of 50
    data = Column(TEXT)

    def __repr__(self):
        return f"<TagVariable(tag_name='{self.tag_name}, values={self.data})>"

class Message(Base):
    __tablename__ = "chat_logs"

    pk = Column(INTEGER, primary_key=True)
    id = Column(INTEGER)
    timestamp = Column(TEXT)
    author_id = Column(INTEGER, ForeignKey("users.id"))
    author = relationship("User", back_populates="messages")
    channel_id = Column(INTEGER)
    guild_id = Column(INTEGER)
    content = Column(TEXT) # limit of 2000
    action = Column(TEXT) # limit of 15

    def __repr__(self):
        return f"<Message(id={self.id}, timestamp='{self.timestamp}', author_id={self.author_id}, channel_id={self.channel_id}, guild_id={self.guild_id}, action='{self.action}')>"

class Command(Base):
    __tablename__ = "command_stats"

    command_name = Column(TEXT, primary_key=True) # limit of 40
    uses = Column(INTEGER)

    def __repr__(self):
        return f"<Command(command_name='{self.command_name}', uses={self.uses})>"

class Prefix(Base):
    __tablename__ = "prefixes"

    guild_id = Column(INTEGER, primary_key=True)
    prefix = Column(TEXT) # limit of 25

    def __repr__(self):
        return f"<Prefix(guild_id={self.guild_id}, prefix='{self.prefix}')>"

# Actual adapter class

class SQL:
    def __init__(self, *args, **kwargs):
        self.db_name = kwargs.get("db_name")
        self.db_api = kwargs.get("db_api", "pysqlite")
        self.engine = create_engine(f"sqlite+{self.db_api}:///{self.db_name}.db?check_same_thread=False", echo=False)
        self.Session = sessionmaker(bind=self.engine)

        Base.metadata.create_all(self.engine)

    def flag(self, obj, type_):
        flag_modified(obj, type_)