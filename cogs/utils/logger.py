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

__all__ = ["get_logger", "set_level"]

import inspect
import logging
import os

from logging import handlers

# Make sure the log directory exists (and create it if not)
if not os.path.exists("logs"):
    os.makedirs("logs")

LOG_LEVEL = logging.INFO

# Handlers
FILE_HANDLER = handlers.RotatingFileHandler(filename="logs/snake.log", maxBytes=5 * 1024 * 1024, backupCount=3) # Max size of 5Mb per-file, with 3 past files
LOG_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s | [In module %(module)s -> function %(funcName)s] (%(filename)s:%(lineno)s) | %(message)s")

FILE_HANDLER.setLevel(logging.NOTSET)
FILE_HANDLER.setFormatter(LOG_FORMATTER)

# Set log level according to debug status (call once at init)
def set_level(debug=False):
    LOG_LEVEL = logging.DEBUG if debug else logging.INFO

# Special logger that runs for each module it's called in
def get_logger():
    # Get name of calling module
    call_frame = inspect.stack()[1]
    call_module = inspect.getmodule(call_frame[0])
    module_name = call_module.__name__

    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(LOG_LEVEL)
    module_logger.addHandler(FILE_HANDLER)

    return module_logger