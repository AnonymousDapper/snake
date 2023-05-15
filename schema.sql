CREATE TABLE boards (
    guild_id INTEGER NOT NULL,
    board_channel_id INTEGER UNIQUE NOT NULL,
    emote TEXT(64) NOT NULL,

    PRIMARY KEY (guild_id, emote);
);

CREATE TABLE board_messages (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    reacts INTEGER NOT NULL,
    emote INTEGER NOT NULL

    FOREIGN KEY(emote) REFERENCES boards(id)
        ON DELETE CASCADE ON UPDATE NO ACTION
);