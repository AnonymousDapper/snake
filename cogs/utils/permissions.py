from . import sql

"""
Permissions system is as follows..

+-----------+-----------------+
| Bit Value | Permission Name |
+===========+=================+
| 0x01      | Use chat        |
+-----------+-----------------+
| 0x02      | XKCD command    |
+-----------+-----------------+
| 0x03      | Retro command   |
+-----------+-----------------+
| 0x04      | Queue songs     |
+-----------+-----------------+
| 0x05      | Queue streams   |
+-----------+-----------------+
| 0x06      | Edit music      |
|           | queue           |
+-----------+-----------------+
| 0x07      | Skip songs      |
+-----------+-----------------+
| 0x08      | Adjust volume   |
+-----------+-----------------+
| 0x09      | Pause/resume    |
|           | music           |
+-----------+-----------------+
| 0x0A      | Control voice   |
|           | channels        |
+-----------+-----------------+
| 0x0B      | Play/stop music |
+-----------+-----------------+
| 0x0C      | View queue      |
|           | contents        |
+-----------+-----------------+
| 0x0D      | Manage tags     |
+-----------+-----------------+
| 0x0E      | View tags       |
+-----------+-----------------+
| 0x0F      | Emoji command   |
+-----------+-----------------+
| 0x10      | Change prefix   |
+-----------+-----------------+

"""

CHAT         = 1 << 0x01
XKCD         = 1 << 0x02
RETRO        = 1 << 0x03
QUEUE_MUSIC  = 1 << 0x04
QUEUE_STREAM = 1 << 0x05
EDIT_QUEUE   = 1 << 0x06
SKIP_SONG    = 1 << 0x07
ADJ_VOL      = 1 << 0x08
PR_MUSIC     = 1 << 0x09
VOICE_CHAN   = 1 << 0x0A
PS_MUSIC     = 1 << 0x0B
VIEW_QUEUE   = 1 << 0x0C
MANAGE_TAG   = 1 << 0x0D
VIEW_TAG     = 1 << 0x0E
EMOJI        = 1 << 0x0F
CHANGE_PFX   = 1 << 0x10

DEFAULT = CHAT | XKCD | RETRO | QUEUE_MUSIC | QUEUE_STREAM | EDIT_QUEUE | SKIP_SONG | ADJ_VOL | PR_MUSIC \
    | VOICE_CHAN | PS_MUSIC | VIEW_QUEUE | MANAGE_TAG | VIEW_TAG | EMOJI # default permissions includes all but change prefix

class Permissions:
    bot = None
    default_permissions = DEFAULT

    def __init__(self, user, **kwargs):
        self.user = user
        self.args = kwargs
        self._value = self._get_permissions()
        self.value = self._value

    def __del__(self):
        self._update_permissions(**self.args)

    def __repr__(self):
        return f"<Permissions(value={self.value})>"

    def _get_permissions(self, **kwargs):
        with self.bot.db_scope() as session:
            kwargs.update({"user_id":int(self.user.id)})
            kwargs.update(self.args)

            permission_entry = session.query(sql.Permission).filter_by(**kwargs).first()
            if permission_entry is None:
                self.value = self.default_permissions
            else:
                self.value = permission_entry.bits

        return self.value

    def _update_permissions(self, **kwargs):
        if self._value == self.value:
            return

        with self.bot.db_scope() as session:
            kwargs.update({"user_id":int(self.user.id)})
            kwargs.update(self.args)

            permission_entry = session.query(sql.Permission).filter_by(**kwargs).first()

            if permission_entry is None:
                permission_user = session.query(sql.User).filter_by(id=int(self.user.id)).first()

                if permission_user is None:
                    permission_user = sql.User(
                        id=int(self.user.id),
                        name=user.name,
                        bot=user.bot,
                        discrim=user.discriminator
                    )
                    session.add(permission_user)

                permission_entry = sql.Permission(user=permission_user, bits=self.value, **kwargs)
                session.add(permission_entry)
            else:
                permission_entry.bits = self.value

        self._value = self.value

    async def get(self, **kwargs):
        return self._get_permissions(**kwargs)

    async def set(self, **kwargs):
        return self._update_permissions(**kwargs)

    def _bit(self, index):
        return bool((self.value >> index) & 1)

    def _set(self, index, value):
        if value == True:
            self.value |= (1 << index)
        elif value == False:
            self.value &= ~(1 << index)
        else:
            raise TypeError("Set value must be bool")

    def _iterator(self):
        for attr in dir(self):
            if isinstance(getattr(self.__class__, attr), property):
                yield (attr, getattr(self, attr))

    def __iter__(self):
        return self._iterator()

    @property
    def use_chat(self):
        return self._bit(0x01)

    @use_chat.setter
    def use_chat(self, value):
        self._set(0x01, value)

    @property
    def use_xkcd(self):
        return self._bit(0x02)

    @use_xkcd.setter
    def use_xkcd(self, value):
        self._set(0x02, value)

    @property
    def use_retro(self):
        return self._bit(0x03)

    @use_retro.setter
    def use_retro(self, value):
        self._set(0x03, value)

    @property
    def queue_music(self):
        return self._bit(0x04)

    @queue_music.setter
    def queue_music(self, value):
        self._set(0x04, value)

    @property
    def queue_stream(self):
        return self._bit(0x05)

    @queue_stream.setter
    def queue_stream(self, value):
        self._set(0x05, value)

    @property
    def edit_queue(self):
        return self._bit(0x06)

    @edit_queue.setter
    def edit_queue(self, value):
        self._set(0x06, value)

    @property
    def skip_music(self):
        return self._bit(0x07)

    @skip_music.setter
    def skip_music(self, value):
        self._set(0x07, value)

    @property
    def adjust_volume(self):
        return self._bit(0x08)

    @adjust_volume.setter
    def adjust_volume(self, value):
        self._set(0x08, value)

    @property
    def pause_music(self):
        return self._bit(0x09)

    @pause_music.setter
    def pause_music(self, value):
        self._set(0x09, value)

    @property
    def control_voice(self):
        return self._bit(0x0A)

    @control_voice.setter
    def control_voice(self, value):
        self._set(0x0A, value)

    @property
    def play_music(self):
        return self._bit(0x0B)

    @play_music.setter
    def play_music(self, value):
        self._set(0x0B, value)

    @property
    def view_queue(self):
        return self._bit(0x0C)

    @view_queue.setter
    def view_queue(self, value):
        self._set(0x0C, value)

    @property
    def manage_tag(self):
        return self._bit(0x0D)

    @manage_tag.setter
    def manage_tag(self, value):
        self._set(0x0D, value)

    @property
    def view_tag(self):
        return self._bit(0x0E)

    @view_tag.setter
    def view_tag(self, value):
        self._set(0x0E, value)

    @property
    def use_emoji(self):
        return self._bit(0x0F)

    @use_emoji.setter
    def use_emoji(self, value):
        self._set(0x0F, value)

    @property
    def change_pfx(self):
        return self._bit(0x10)

    @change_pfx.setter
    def change_pfx(self, value):
        self._set(0x10, value)