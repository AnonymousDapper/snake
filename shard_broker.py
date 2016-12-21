import asyncio, websockets, json, sys, traceback, psutil, logging
from datetime import datetime

try:
    shard_limit = int(sys.argv[1])
except:
    shard_limit = 4

class ShardBroker:
    EXIT = 0
    RESTART = 1
    EVENT = 2
    PING = 3
    PONG = 4
    DATA = 5
    IDENTIFY = 6
    SHARD_COUNT = 7

    def __init__(self, shard_limit):
        self.loop = asyncio.get_event_loop()
        self.shards = {}
        self.shard_processes = {}
        self.shard_limit = shard_limit
        self._DEBUG = any("debug" in arg for arg in sys.argv)
        self.server = None

        # self.log = logging.getLogger()
        # self.log.setLevel(logging.INFO)
        # self.log.addHandler(
        #     logging.FileHandler(filename="broker.log", encoding="utf-8", mode='w')
        # )

        for shard_id in range(0, self.shard_limit):
            args = ["python", "new_snake.py", str(shard_id)]

            if self._DEBUG:
                args.append("debug")

            shard_process = psutil.Popen(args, stdout=sys.stdout)
            print("Started shard {}/{} pid {} [{}]".format(shard_id, self.shard_limit - 1, shard_process.pid, shard_process.cmdline()))

        print("Broker created!")

    def _get_ping(self, t_1, t_2):
        return abs(t_2 - t_1).microseconds / 1000

    def _color(self, text, color_code):
        return "\033[3{}m{}\033[0m".format(color_code, text)

    def _log_shard(self, event_name, ws, op, unknown=False):
        if unknown:
            print("Unknown op {} from shard #{}".format(op, ws.shard_id))
        else:
            print("{} from shard #{}".format(self._color(event_name, op), ws.shard_id))

    async def _run_event(self, event, ws, *args, **kwargs):
        try:
            await getattr(self, event)(ws, *args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(event, ws, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def dispatch(self, event, ws, *args, **kwargs):
        method = "on_" + event
        handler = "handle_" + event

        if hasattr(self, handler):
            getattr(self, handler)(ws, *args, **kwargs)

        if hasattr(self, method):
            asyncio.ensure_future(self._run_event(method, ws, *args, **kwargs), loop=self.loop)

    async def on_error(self, event_method, ws, *args, **kwargs):
        print("Ignoring exception in {} [shard #{}]".format(event_method, ws.shard_id), file=sys.stderr)
        traceback.print_exc()

    def close_shard(self, ws):
        try:
            asyncio.ensure_future(ws.close(code=1004, reason="closing"))
            if self.shard_processes[ws.shard_id].is_running():
                self.shard_processes[ws.shard_id].kill() # Kill the shard process

            del self.shards[ws.shard_id]
            del self.shard_processes[ws.shard_id]
        except:
            pass

    def close(self):
        for ws in self.shards.items():
            self.close_shard(ws)

        self.server.close()
        #pending = asyncio.Task.all_tasks()
        #gathered = asyncio.gather(*pending)
        #try:
        #    gathered.cancel()
        #    self.loop.run_until_complete(gathered)
        #    gathered.exception()
        #except:
        #    pass
        self.loop.stop()
        #    self.loop.close()
        sys.exit()

    async def send(self, payload, ws): # Assumes payload is dict and converts to JSON then encodes to utf-8 bytes
        data = bytes(json.dumps(payload), "utf-8")
        try:
            await ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Shard #{} closed, removing.".format(ws.shard_id))
            self.close_shard(ws)

    def _decode(self, raw_data):
        data = None
        if isinstance(raw_data, bytes):
            # Assuming UTF-8 encoding ¯\_(ツ)_/¯
            data = raw_data.decode(encoding="utf-8")
        elif isinstance(raw_data, str):
            data = raw_data
        else:
            raise ValueError("Data must be bytes or str. Got {}".format(type(raw_data).__name__))
        try:
            data = json.loads(data)
        except:
            pass
        return data

    async def _ping_task(self): # Task to constantly ping each shard
        while True:
            for shard_id, ws in self.shards.items():
                payload = {"op": self.PING}
                try:
                    await self.send(payload, ws)
                    ws.temp_ping = datetime.now()
                except websockets.exceptions.ConnectionClosed:
                    print("Shard #{} closed, removing.".format(ws.shard_id))
                    self.close_shard(ws)
            await asyncio.sleep(10)

    async def poll_event(self, ws):
        try:
            data = await ws.recv()
            await self.process_message(ws, data)
        except websockets.exceptions.ConnectionClosed:
            print("Shard #{} closed, removing.".format(ws.shard_id))
            self.close_shard(ws)

    async def process_message(self, ws, message):
        self.dispatch("raw_data", ws, message)
        message = self._decode(message)
        self.dispatch("pre_data", ws, message)

        op = message.get("op")
        data = message.get("data")
        event = message.get("event")

        if op == self.EXIT:
            self._log_shard("EXIT", ws, op)
            payload = {"op": self.EXIT}
            for shard_id, ws in self.shards.items():
                await self.send(payload, ws)

            self.close()

        elif op == self.RESTART:
            self._log_shard("RESTART", ws, op)
            # lolrip

        elif op == self.EVENT:
            self._log_shard("EVENT", ws, op)
            self.shard_dispatch(event, **data)

        elif op == self.PING:
            self._log_shard("PING", ws, op)
            payload = {
                "op": self.PONG,
                "data": {
                    "reply": datetime.now().strftime("%H-%M-%S:%f")
                }
            }
            await self.send(payload, ws)

        elif op == self.PONG:
            self._log_shard("PONG", ws, op)
            if hasattr(ws, "temp_ping"):
                ws.temp_pong = datetime.strptime(data.get("reply"), "%H-%M-%S:%f")
                ws.ping = self._get_ping(ws.temp_pong, datetime.now())
                print("Shard #{} responded from ping with response time of {}ms".format(ws.shard_id, ws.ping))
                del ws.temp_pong
                del ws.temp_ping

        elif op == self.DATA:
            self._log_shard("DATA", ws, op)
            try:
                self.dispatch("data", ws, *data, **data)
            except:
                pass

        elif op == self.IDENTIFY:
            self._log_shard("IDENTIFY", ws, op)

        elif op == self.SHARD_COUNT:
            self._log_shard("SHARD_COUNT", ws, op)
            payload = {
                "op": self.DATA,
                "data": {
                    "shard_count": len(self.shards)
                }
            }
            await self.send(payload, ws)

        else:
            self._log_shard("", ws, op, unknown=True)

    async def __call__(self, ws, url):
        print("Incoming connection on {}:{} from {}:{}".format(*ws.local_address, *ws.remote_address))
        try:
            handshake_data = await asyncio.wait_for(ws.recv(), 20, loop=self.loop) # Wait for 20 seconds
        except asyncio.TimeoutError:
            print("Connection from {}:{} timed out".format(*ws.remote_address))
            asyncio.ensure_future(ws.close(code=1000, reason="timed out"))
            return
        except websockets.exceptions.ConnectionClosed:
            print("Connection from {}:{} closed".format(*ws.remote_address))
            return

        self.dispatch("raw_data", ws, handshake_data)

        try:
            data = self._decode(handshake_data)
        except:
            print("Connection from {}:{} failed to send proper handshake".format(*ws.remote_address))
            asyncio.ensure_future(ws.close(code=1001, reason="illegal handshake"))
            return

        self.dispatch("pre_data", ws, data)
        op = data.get("op")
        shard_id = data.get("shard_id")

        ws.shard_id = shard_id

        if op == self.IDENTIFY:
            if ws.shard_id <= (self.shard_limit - 1):
                if ws.shard_id not in self.shards:
                    self.shards[ws.shard_id] = ws
                else:
                    print("Connection from {}:{} (shard #{}) already in use".format(*ws.remote_address, ws.shard_id))
                    asyncio.ensure_future(ws.close(code=1002, reason="already in use"))
                    return
            else:
                print("Connection from {}:{} (shard #{}) exceeds shard limit".format(*ws.remote_address, ws.shard_id))
                asyncio.ensure_future(ws.close(code=1003, reason="exceeds shard limit"))
                return
        else:
            print("Connection from {}:{} (shard #{}) failed to identify".format(*ws.remote_address, ws.shard_id))
            asyncio.ensure_future(ws.close(code=1004, reason="failed to identify"))
            return

        return_handshake = {
            "op": self.IDENTIFY,
            "data": {
                "shard_count": self.shard_limit
            }
        }
        try:
            data = bytes(json.dumps(return_handshake), "utf-8")
            await ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection from {}:{} closed".format(*ws.remote_address))
            return

        self.loop.create_task(self._ping_task())

        while ws.open:
            try:
                await self.poll_event(ws)
            except websockets.exceptions.ConnectionClosed as e:
                print("Shard #{} closed [{}]".format(ws.shard_id, e.reason))
                self.close_shard(ws)

    async def on_data(self, ws, *args, **kwargs):
        print(args, kwargs)

loop = asyncio.get_event_loop()
broker = ShardBroker(shard_limit)

try:
    broker.server = loop.run_until_complete(websockets.server.serve(broker, "localhost", 5230))
    print("Broker running")
    loop.run_forever()

except KeyboardInterrupt:
    broker.close()