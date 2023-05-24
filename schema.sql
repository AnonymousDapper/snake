CREATE TABLE boards (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER UNIQUE NOT NULL,
    threshold INTEGER NOT NULL,
    name TEXT NOT NULL,
    emote TEXT NOT NULL
);

CREATE TABLE board_messages (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    reacts INTEGER NOT NULL,
    emote INTEGER NOT NULL,

    FOREIGN KEY(emote) REFERENCES boards(id)
        ON DELETE CASCADE ON UPDATE NO ACTION
);

CREATE TABLE autoroles (
    role_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    emote TEXT NOT NULL
);

CREATE TABLE posted_board_messages (
    message_id INTEGER PRIMARY KEY,
    board_message_id INTEGER NOT NULL,

    FOREIGN KEY(message_id) REFERENCES board_messages(message_id)
        ON DELETE CASCADE ON UPDATE NO ACTION
);
