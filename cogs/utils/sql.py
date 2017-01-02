from sqlalchemy import ForeignKey, Integer, BigInteger, String, Date, Boolean, Column, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Start mapping classes

class Tag(Base):

    __tablename__ = "tags"

    name = Column(String(50), primary_key=True)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="tags")
    content = Column(String(1000))
    uses = Column(Integer)
    timestamp = Column(String)

    def __repr__(self):
        return "<Tag(name='{0.name}', author_id={0.author_id}, uses={0.uses}, timestamp='{0.timestamp}')>".format(self)

class Permission(Base):

    __tablename__ = "permissions"

    pk = Column(Integer, primary_key=True)
    server_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    user = relationship("User", back_populates="permissions")
    user_id = Column(BigInteger, ForeignKey("users.id"))
    p_string = Column(String)

    def __repr__(self):
        return "<Permission(server_id={0.server_id}, channel_id={0.channel_id}, user_id={0.user_id})>".format(self)

class User(Base):

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(40))
    nick = Column(String(40))
    bot = Column(Boolean)
    discrim = Column(String(4))
    permissions = relationship("Permission", back_populates="user", cascade="all, delete, delete-orphan")
    messages = relationship("Message", back_populates="author", cascade="all, delete, delete-orphan")
    tags = relationship("Tag", back_populates="author", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<User(id={0.id}, name='{0.name}', nick='{0.nick}', bot={0.bot}, discrim='{0.discrim}', permissions={0.permissions}, messages={0.messages}, tags={0.tags})>".format(self)

class Blacklist(Base):

    __tablename__ = "blacklist"

    server_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, primary_key=True)
    data = Column(String)

    def __repr__(self):
        return "<Blacklist(server_id={0.server_id}, channel_id={0.channel_id})>".format(self)

class Whitelist(Base):

    __tablename__ = "whitelist"

    server_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, primary_key=True)
    data = Column(String)

    def __repr__(self):
        return "<Whitelist(server_id={0.server_id}, channel_id={0.channel_id})>".format(self)

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
        return "<Message(id={0.id}, timestamp='{0.timestamp}', author_id={0.author_id}, channel_id={0.channel_id}, server_id={0.server_id}, action='{0.action}')>".format(self)

class CommandStat(Base):

    __tablename__ = "command_stats"

    command_name = Column(String(40), primary_key=True)
    uses = Column(Integer)

    def __repr__(self):
        return "<CommandStat(command_name='{0.command_name}', uses={0.uses})>".format(self)

class Prefix(Base):

    __tablename__ = "prefixes"

    server_id = Column(BigInteger, primary_key=True)
    prefix = Column(String(25))

    def __repr__(self):
        return "<Prefix(server_id={0.server_id}, prefix='{0.prefix}')>".format(self)

# Actual adapter class

class SQL:
    def __init__(self, *args, **kwargs):
        self.db_name = kwargs.get("db_name")
        self.db_username = kwargs.get("db_username")
        self.db_password = kwargs.get("db_password")
        self.db_api = kwargs.get("db_api", "pypostgresql")
        self.engine = create_engine("postgresql+{0.db_api}://{0.db_username}:{0.db_password}@localhost:5432/{0.db_name}".format(self), echo=False)
        self.Session = sessionmaker(bind=self.engine)

        Base.metadata.create_all(self.engine)