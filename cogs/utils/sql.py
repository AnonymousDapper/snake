# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ["Tag", "Permission", "User", "Blacklist", "Whitelist", "TagVariable", "Message", "MessageChange", "Command", "ErrorLog", "Prefix", "SQL"]

import traceback
from contextlib import contextmanager

from sqlalchemy import ForeignKey, Integer, BigInteger, String, DateTime, Boolean, Column, create_engine

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.attributes import flag_modified

# Can't import logger here because logger:PostgresHandler refers to ErrorLog and causes import loop

Base = declarative_base()

# Class -> table mappings

class Tag(Base):
    __tablename__ = "tags"

    name = Column(String(50), primary_key=True, unique=True)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="tags")
    content = Column(String(2000))
    uses = Column(Integer)
    timestamp = Column(DateTime)

    def __repr__(self):
        return f"<Tag(name='{self.name}', author_id={self.author_id}, uses={self.uses}, timestamp='{self.timestamp}')>"

class Permission(Base):
    __tablename__ = "permissions"

    pk = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user = relationship("User", back_populates="permissions")
    user_id = Column(BigInteger, ForeignKey("users.id"))
    bits = Column(BigInteger)

    def __repr__(self):
        return f"<Permission(guild_id={self.guild_id}, channel_id={self.channel_id}, user_id={self.user_id}, bits={self.bits})>"

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, unique=True)
    name = Column(String(40))
    bot = Column(Boolean)
    discrim = Column(String(4))
    permissions = relationship("Permission", back_populates="user", cascade="all, delete, delete-orphan")
    messages = relationship("Message", back_populates="author", cascade="all, delete, delete-orphan")
    tags = relationship("Tag", back_populates="author", cascade="all, delete, delete-orphan")
    commands = relationship("Command", back_populates="user", cascade="all, delete, delete-orphan")
    changed_messages = relationship("MessageChange", back_populates="author", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', bot={self.bot}, discrim='{self.discrim}', permissions={self.permissions}, messages={self.messages}, tags={self.tags})>"

class Blacklist(Base):
    __tablename__ = "blacklist"

    pk = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user_id = Column(BigInteger)

    data = Column(String)

    def __repr__(self):
        return f"<Blacklist(guild_id={self.guild_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class Whitelist(Base):
    __tablename__ = "whitelist"

    pk = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    role_id = Column(BigInteger)
    user_id = Column(BigInteger)

    data = Column(String)

    def __repr__(self):
        return f"<Whitelist(guild_id={self.guild_id}, channel_id={self.channel_id}, role_id={self.role_id}, user_id={self.user_id})>"

class TagVariable(Base):
    __tablename__ = "tag_values"

    tag_name = Column(String(50), primary_key=True, unique=True)
    data = Column(JSONB) # JSONb as key:value pairs

    def __repr__(self):
        return f"<TagVariable(tag_name='{self.tag_name}, values={self.data})>"

class Message(Base):
    __tablename__ = "chat_logs"

    id = Column(BigInteger, primary_key=True, unique=True)
    timestamp = Column(DateTime)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="messages")
    command = relationship("Command", back_populates="message")
    channel_id = Column(BigInteger)
    guild_id = Column(BigInteger)
    content = Column(String(2000))

    def __repr__(self):
        return f"<Message(id={self.id}, timestamp='{self.timestamp}', author_id={self.author_id}, channel_id={self.channel_id}, guild_id={self.guild_id})>"

class MessageChange(Base):
    __tablename__ = "chat_updates"

    pk = Column(Integer, primary_key=True)
    id = Column(BigInteger)
    timestamp = Column(DateTime)
    author_id = Column(BigInteger, ForeignKey("users.id"))
    author = relationship("User", back_populates="changed_messages")
    channel_id = Column(BigInteger)
    guild_id = Column(BigInteger)
    content = Column(String(2000))
    deleted = Column(Boolean)

    def __repr__(self):
        return f"<Message(id={self.id}, timestamp='{self.timestamp}', author_id={self.author_id}, channel_id={self.channel_id}, guild_id={self.guild_id}, deleted={self.deleted})>"

class Command(Base):
    __tablename__ = "command_stats"

    pk = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, ForeignKey("chat_logs.id"))
    message = relationship("Message", back_populates="command", uselist=False)
    command_name = Column(String(40))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    user = relationship("User", back_populates="commands")
    timestamp = Column(DateTime)
    args = Column(String(2000))
    errored = Column(Boolean)

    def __repr__(self):
        return f"<Command(name='{self.command_name}', errored={self.errored}, message_id={self.message_id})>"

class ErrorLog(Base):
    __tablename__ = "logged_errors"
    pk = Column(Integer, primary_key=True, unique=True)
    level = Column(String)
    module = Column(String)
    function = Column(String)
    filename = Column(String)
    line_number = Column(Integer)
    message = Column(String)
    timestamp = Column(DateTime)

    def __repr__(self):
        return f"<ErrorLog(level='{self.level}', function='{self.function}', filename='{self.filename}', lineno={self.line_number})>"

class Prefix(Base):
    __tablename__ = "prefixes"

    guild_id = Column(BigInteger, primary_key=True)
    prefix = Column(String(25))

    def __repr__(self):
        return f"<Prefix(guild_id={self.guild_id}, prefix='{self.prefix}')>"




# Actual adapter class

class SQL:
    def __init__(self, *args, **kwargs):
        do_echo = kwargs.get("echo", False)
        self.db_name = kwargs.get("db_name")
        self.db_username = kwargs.get("db_username")
        self.db_password = kwargs.get("db_password")
        self.db_api = kwargs.get("db_api", "pypostgresql")
        self.engine = create_engine(f"postgresql+{self.db_api}://{self.db_username}:{self.db_password}@localhost:5432/{self.db_name}", echo=do_echo)
        self.Session = sessionmaker(bind=self.engine)

        Base.metadata.create_all(self.engine)

    # Helper method to flag an obect as modified to re-commit
    @staticmethod
    def flag(obj, type_):
        flag_modified(obj, type_)

    # Session context manager
    @contextmanager
    def session(self):
        session = self.Session()

        try:
            yield session
            session.commit()

        except:
            traceback.print_exc()
            session.rollback()

        finally:
            session.close()
