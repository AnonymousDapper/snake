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

# Get elapsed time in 'Xy, Xm, Xw, Xd, Xh, Xm, Xs' format
def get_elapsed_time(date1, date2):
    delta = abs(date2 - date1)
    time = int(delta.total_seconds())

    names = ["y", "m", "w", "d", "h", "m", "s"]

    years, remainder = divmod(time, 31536000)
    months, remainder = divmod(remainder, 2592000)
    weeks, remainder = divmod(remainder, 606461.538462)
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    times = [years, months, weeks, days, hours, minutes, seconds]

    return ", ".join(f"{int(times[i])}{names[i]}" for i in range(len(names)) if times[i] > 0)

# Get elapsed time in ms/s format
def get_ping_time(time1, time2):
    millis = abs(time1 - time2).microseconds / 1000

    if millis > 1000:
        format_sep = "{:d}ms"
        millis = int(millis)

    else:
        format_sep = "{:.2f}s"

        return format_sep.format(millis)