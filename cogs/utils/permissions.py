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

from . import sql

"""
Permission system is as follows:


Bit Value | Permission Name

0x00      | Send embeds

0x01      | Queue songs

0x02      | Queue streams

0x03      | Edit music queue

0x04      | Skip songs

0x05      | Adjust music volume

0x06      | Control music playback

0x07      | Join/leave voice channel

0x08      | View music queue

0x09      | Create/Edit/Delete tags

0x0A      | View tags

0x0B      | View analytics data

0x0C      | Manage analytics data

0x0D      | Remove bot's messages

0x0E      | Use calc command
"""

USE_EMBEDS       = 1 << 0x00
QUEUE_SONGS      = 1 << 0x01
QUEUE_STREAMS    = 1 << 0x02
EDIT_QUEUE       = 1 << 0x03
SKIP_SONGS       = 1 << 0x04
MUSIC_VOLUME     = 1 << 0x05
MUSIC_PLAYBACK   = 1 << 0x06
MANAGE_VOICE     = 1 << 0x07
VIEW_QUEUE       = 1 << 0x08
MANAGE_TAGS      = 1 << 0x09
VIEW_TAGS        = 1 << 0x0A
VIEW_ANALYTICS   = 1 << 0x0B
MANAGE_ANALYTICS = 1 << 0x0C
CLEAN_BOT        = 1 << 0x0D
RUN_CALC         = 1 << 0x0E

DEFAULT = USE_EMBEDS | QUEUE_SONGS | QUEUE_STREAMS | EDIT_QUEUE | SKIP_SONGS \
    | MUSIC_VOLUME | MUSIC_PLAYBACK | MANAGE_VOICE | VIEW_QUEUE | MANAGE_TAGS \
    | VIEW_TAGS | CLEAN_BOT | RUN_CALC

class Permissions:
    default_permissions = DEFAULT
    db = None

    @classmethod
    def _init_database(cls, db):
        cls.db = db