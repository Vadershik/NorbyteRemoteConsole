#!/usr/bin/env python3
"""
bg3_console.py — удалённая консоль Lua для Baldur's Gate 3 Script Extender (bg3se).

Схема протокола восстановлена из метаданных LuaDebugger.exe (netmodule,
namespace NSE.DebuggerFrontend) и из IL AsyncProtobufClient.Send/RunLoop.

ФРАМИНГ (AsyncProtobufClient.Send):
    [uint32 LE total_len][protobuf body]
    ГДЕ total_len = len(body) + 4  <-- длина ВКЛЮЧАЕТ САМИ 4 байта заголовка.

    В RunLoop длина собирается так:
        b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)          -> little-endian
    а тело парсится как CodedInputStream(buf, 4, length - 4).
    Максимальный размер сообщения: 1048576 байт (1 MiB).

СООБЩЕНИЯ (DebuggerToBackend, клиент -> игра):
    message DebuggerToBackend {
        uint32 seqNo      = 1;
        uint32 replySeqNo = 2;
        oneof msg {
            DbgConnectRequest connect       = 3  { uint32 protocolVersion = 1; }
            DbgUpdateSettings updateSettings = 4
            DbgSetBreakpoints setBreakpoints = 5
            DbgContinue      continuation   = 6  { DbgContext context = 1; Action action = 2; }
            DbgEvaluate      evaluate       = 7  { DbgContext context = 1;
                                                   string expression = 2;
                                                   uint32 frame = 3; }
            DbgFetchMods     fetchMods      = 8
            DbgRequestSource requestSource  = 9
            DbgGetVariables  getVariables   = 10 { ... }
            DbgReset         reset          = 11 { DbgContext context = 1; }
        }
    }

    enum DbgContext { Server = 0; Client = 1; }   // НЕ 1/2!
    DBGProtocolVersion = 4

ОТВЕТЫ (BackendToDebugger, игра -> клиент):
    seqNo = 1, replySeqNo = 2, connectResponse = 3 { protocolVersion = 1 },
    evaluateResponse = 5 { BkResult result = 1; string errorMessage = 2; },
    contextUpdated = 6 { context = 1; status = 2; },
    modInfoResponse = 7, debugOutput = 8 { message = 1; severity = 2; },
    results = 9, debuggerReady = 10, sourceResponse = 11, getVariablesResponse = 12

    BkResult { StatusCode statusCode = 1; }
    StatusCode: 0 Success, 1 NotInPause, 2 NoDebuggee, 3 InvalidContinueAction,
                4 InPause, 5 EvalEngineNotReady, 6 EvalFailed, 7 NoSuchFile
    Severity:   0 info, 1 warning, 2 error, 3 debug
"""

import argparse
import queue
import socket
import struct
import sys
import threading

DBG_PROTOCOL_VERSION = 4
MAX_MESSAGE_SIZE = 1 << 20  # 1048576, как в RunLoop

CTX_SERVER = 0
CTX_CLIENT = 1
CTX_NAMES = {CTX_SERVER: "Server", CTX_CLIENT: "Client"}

STATUS_CODES = {
    0: "Success", 1: "NotInPause", 2: "NoDebuggee", 3: "InvalidContinueAction",
    4: "InPause", 5: "EvalEngineNotReady", 6: "EvalFailed", 7: "NoSuchFile",
}
SEVERITIES = {0: "info", 1: "warning", 2: "error", 3: "debug"}


# --------------------------------------------------------------------------
# Низкоуровневый protobuf (wire format), без внешних зависимостей
# --------------------------------------------------------------------------

def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        bits = value & 0x7F
        value >>= 7
        if value:
            out.append(bits | 0x80)
        else:
            out.append(bits)
            return bytes(out)


def _tag(field: int, wire_type: int) -> bytes:
    return encode_varint((field << 3) | wire_type)


def f_varint(field: int, value: int) -> bytes:
    """Поле wire_type=0 (varint)."""
    return _tag(field, 0) + encode_varint(value)


def f_bytes(field: int, payload: bytes) -> bytes:
    """Поле wire_type=2 (length-delimited)."""
    return _tag(field, 2) + encode_varint(len(payload)) + payload


def f_string(field: int, text: str) -> bytes:
    return f_bytes(field, text.encode("utf-8"))


def f_enum(field: int, value: int) -> bytes:
    """Enum кодируется как varint (int32), в т.ч. при значении 0."""
    return f_varint(field, value)


def decode_varint(buf: bytes, pos: int):
    result = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise ValueError("varint обрезан")
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint слишком длинный")


def iter_fields(buf: bytes):
    """Разбирает protobuf-сообщение в список (номер_поля, wire_type, значение)."""
    pos = 0
    out = []
    while pos < len(buf):
        key, pos = decode_varint(buf, pos)
        field, wire_type = key >> 3, key & 0x07
        if wire_type == 0:
            value, pos = decode_varint(buf, pos)
        elif wire_type == 2:
            length, pos = decode_varint(buf, pos)
            value = buf[pos:pos + length]
            if len(value) != length:
                raise ValueError("length-delimited поле обрезано")
            pos += length
        elif wire_type == 5:
            value = struct.unpack_from("<f", buf, pos)[0]
            pos += 4
        elif wire_type == 1:
            value = struct.unpack_from("<d", buf, pos)[0]
            pos += 8
        else:
            raise ValueError(f"неподдерживаемый wire_type={wire_type}")
        out.append((field, wire_type, value))
    return out


# --------------------------------------------------------------------------
# Фрейминг: [uint32 LE total_len][body], total_len = len(body) + 4
# --------------------------------------------------------------------------

def frame(body: bytes) -> bytes:
    return struct.pack("<I", len(body) + 4) + body


class FrameReader:
    """Собирает TCP-поток в сообщения по 4-байтовому заголовку."""

    def __init__(self, max_size: int = MAX_MESSAGE_SIZE):
        self._buf = bytearray()
        self._max = max_size

    def feed(self, data: bytes):
        self._buf.extend(data)
        while len(self._buf) >= 4:
            total = struct.unpack_from("<I", self._buf, 0)[0]
            if total < 4:
                raise ValueError(f"некорректная длина сообщения: {total}")
            if total > self._max:
                raise ValueError(f"сообщение слишком велико: {total} > {self._max}")
            if len(self._buf) < total:
                break
            body = bytes(self._buf[4:total])
            del self._buf[:total]
            yield body


# --------------------------------------------------------------------------
# Построение сообщений DebuggerToBackend
# --------------------------------------------------------------------------

def build_connect(protocol_version: int = DBG_PROTOCOL_VERSION) -> bytes:
    """connect = 3 { protocolVersion = 1 }"""
    return f_bytes(3, f_varint(1, protocol_version))


def build_evaluate(expression: str, context: int = CTX_SERVER,
                   frame_id: int = 0) -> bytes:
    """evaluate = 7 { context = 1; expression = 2; frame = 3 }"""
    inner = f_enum(1, context) + f_string(2, expression) + f_varint(3, frame_id)
    return f_bytes(7, inner)


def build_continue(context: int, action: int) -> bytes:
    """continue = 6 { context = 1; action = 2 }"""
    return f_bytes(6, f_enum(1, context) + f_enum(2, action))


def build_reset(context: int) -> bytes:
    """reset = 11 { context = 1 }"""
    return f_bytes(11, f_enum(1, context))


def build_update_settings(break_on_error: bool = False,
                          break_on_generic_error: bool = False) -> bytes:
    """updateSettings = 4 { breakOnError = 1; breakOnGenericError = 2 }"""
    inner = f_varint(1, 1 if break_on_error else 0) + \
            f_varint(2, 1 if break_on_generic_error else 0)
    return f_bytes(4, inner)


def wrap(seq_no: int, payload: bytes) -> bytes:
    """Добавляет seqNo = 1 в конверт DebuggerToBackend."""
    return f_varint(1, seq_no) + payload


# --------------------------------------------------------------------------
# Разбор ответов BackendToDebugger
# --------------------------------------------------------------------------

def _submessage(raw: bytes) -> dict:
    result = {}
    for field, wire_type, value in iter_fields(raw):
        result[field] = value
    return result


def decode_backend_message(body: bytes) -> dict:
    """Разбирает BackendToDebugger в словарь для вывода."""
    msg = {"seq_no": None, "reply_seq_no": None, "kind": None, "detail": {}}

    for field, wire_type, value in iter_fields(body):
        if field == 1:
            msg["seq_no"] = value
        elif field == 2:
            msg["reply_seq_no"] = value
        elif field == 3 and wire_type == 2:          # connectResponse
            sub = _submessage(value)
            msg["kind"] = "connectResponse"
            msg["detail"] = {"protocolVersion": sub.get(1)}
        elif field == 5 and wire_type == 2:          # evaluateResponse
            sub = _submessage(value)
            result = sub.get(1)
            status = None
            if isinstance(result, (bytes, bytearray)):
                status = _submessage(result).get(1)
            err = sub.get(2)
            msg["kind"] = "evaluateResponse"
            msg["detail"] = {
                "status": status,
                "error": err.decode("utf-8", "replace") if isinstance(err, (bytes, bytearray)) else None,
            }
        elif field == 6 and wire_type == 2:          # contextUpdated
            sub = _submessage(value)
            msg["kind"] = "contextUpdated"
            msg["detail"] = {
                "context": sub.get(1),
                "status": sub.get(2),
            }
        elif field == 7 and wire_type == 2:          # modInfoResponse
            msg["kind"] = "modInfoResponse"
        elif field == 8 and wire_type == 2:          # debugOutput
            sub = _submessage(value)
            text = sub.get(1, b"")
            msg["kind"] = "debugOutput"
            msg["detail"] = {
                "message": text.decode("utf-8", "replace") if isinstance(text, (bytes, bytearray)) else str(text),
                "severity": sub.get(2, 0),
            }
        elif field == 9 and wire_type == 2:          # results / requestSource
            msg["kind"] = "results"
        elif field == 10 and wire_type == 2:         # debuggerReady
            msg["kind"] = "debuggerReady"
        elif field == 11 and wire_type == 2:         # sourceResponse
            msg["kind"] = "sourceResponse"
        elif field == 12 and wire_type == 2:         # getVariablesResponse
            sub = _submessage(value)
            msg["kind"] = "getVariablesResponse"
            msg["detail"] = {"status": _submessage(sub[1]).get(1) if 1 in sub else None}
        else:
            msg["kind"] = msg["kind"] or f"field{field}"

    return msg


# --------------------------------------------------------------------------
# Клиент
# --------------------------------------------------------------------------

class BG3Client:
    def __init__(self, host: str, port: int, timeout: float = 5.0,
                 verbose: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self.context = CTX_SERVER

        self._sock = None
        self._seq = 0
        self._events = queue.Queue()
        self._reader = None
        self._running = False

    # -- соединение ---------------------------------------------------------

    def connect(self):
        self.close()
        sock = socket.create_connection((self.host, self.port), self.timeout)
        sock.settimeout(None)
        self._sock = sock
        self._seq = 0
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def close(self):
        self._running = False
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # -- отправка -----------------------------------------------------------

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _send_payload(self, payload: bytes) -> int:
        if self._sock is None:
            raise ConnectionError("нет соединения с отладчиком")
        seq = self._next_seq()
        body = wrap(seq, payload)
        packet = frame(body)
        if self.verbose:
            print(f"  → seq={seq}  {packet.hex(' ')}", file=sys.stderr)
        self._sock.sendall(packet)
        return seq

    def send_connect(self, version: int = DBG_PROTOCOL_VERSION) -> int:
        return self._send_payload(build_connect(version))

    def send_evaluate(self, expression: str) -> int:
        return self._send_payload(
            build_evaluate(expression, self.context, 0))

    def send_continue(self, action: int) -> int:
        return self._send_payload(build_continue(self.context, action))

    def send_reset(self) -> int:
        return self._send_payload(build_reset(self.context))

    def send_update_settings(self, break_on_error=False, break_on_generic_error=False):
        return self._send_payload(
            build_update_settings(break_on_error, break_on_generic_error))

    # -- приём --------------------------------------------------------------

    def _read_loop(self):
        reader = FrameReader()
        try:
            while self._running:
                try:
                    chunk = self._sock.recv(32768)
                except OSError:
                    break
                if not chunk:
                    break
                if self.verbose:
                    print(f"  ← raw {chunk.hex(' ')}", file=sys.stderr)
                for body in reader.feed(chunk):
                    try:
                        self._events.put(decode_backend_message(body))
                    except (ValueError, IndexError, KeyError, struct.error) as exc:
                        self._events.put({"kind": "parseError", "detail": str(exc),
                                          "seq_no": None, "reply_seq_no": None})
        finally:
            self._events.put({"kind": "disconnected", "detail": {},
                              "seq_no": None, "reply_seq_no": None})

    def events(self, timeout=None):
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None


# --------------------------------------------------------------------------
# Печать ответов
# --------------------------------------------------------------------------

def print_event(event: dict):
    kind = event.get("kind")
    detail = event.get("detail", {})

    if kind == "debugOutput":
        text = detail.get("message", "")
        severity = detail.get("severity", 0)
        prefix = {"error": "✖", "warning": "⚠", "debug": "·"}.get(
            SEVERITIES.get(severity, "info"), "•")
        for line in str(text).splitlines() or [""]:
            print(f"{prefix} {line}")
    elif kind == "evaluateResponse":
        status = detail.get("status")
        error = detail.get("error")
        if error:
            print(f"✖ ошибка: {error}")
        else:
            print(f"· статус: {STATUS_CODES.get(status, status)}")
    elif kind == "connectResponse":
        print(f"· протокол игры: {detail.get('protocolVersion')}")
    elif kind == "contextUpdated":
        ctx = CTX_NAMES.get(detail.get("context"), detail.get("context"))
        print(f"· контекст: {ctx} (status={detail.get('status')})")
    elif kind == "debuggerReady":
        print("· отладчик готов")
    elif kind == "parseError":
        print(f"✖ не удалось разобрать ответ: {detail}")
    elif kind == "disconnected":
        print("✖ соединение закрыто отладчиком")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

HELP = """
Команды REPL:
  :server / :client   — переключить контекст выполнения
  :context            — показать текущий контекст
  :reset              — сбросить контекст (отправить reset)
  :break / :nobreak   — включить/выключить остановку на ошибках
  :reconnect          — переподключиться
  :help               — эта справка
  :quit               — выход

Примеры Lua:
  print("Привет из консоли")
  Osi.AddGold(Osi.GetHostCharacter(), 500)
  local c = Osi.GetHostCharacter(); Osi.Print(c:GetName())
""".strip()


def drain(client: BG3Client, seconds: float = 0.6):
    """Печатает накопившиеся ответы в течение seconds."""
    import time
    deadline = time.time() + seconds
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            return
        event = client.events(timeout=remaining)
        if event is None:
            return
        print_event(event)
        if event.get("kind") == "disconnected":
            return


def handle_meta(client: BG3Client, line: str) -> bool:
    """Обрабатывает команду :... Возвращает False для выхода."""
    cmd = line[1:].strip().lower()
    if cmd in ("quit", "q", "exit"):
        return False
    if cmd in ("help", "h", "?"):
        print(HELP)
    elif cmd == "server":
        client.context = CTX_SERVER
        print("· контекст: Server")
    elif cmd == "client":
        client.context = CTX_CLIENT
        print("· контекст: Client")
    elif cmd == "context":
        print(f"· контекст: {CTX_NAMES[client.context]}")
    elif cmd == "reset":
        client.send_reset()
        drain(client)
    elif cmd == "break":
        client.send_update_settings(break_on_error=True, break_on_generic_error=True)
        print("· остановка на ошибках включена")
    elif cmd == "nobreak":
        client.send_update_settings(break_on_error=False, break_on_generic_error=False)
        print("· остановка на ошибках выключена")
    elif cmd == "reconnect":
        client.connect()
        client.send_connect()
        drain(client)
    else:
        print(f"неизвестная команда: {line}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Удалённая консоль Lua для Baldur's Gate 3 Script Extender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры:
  python3 bg3_console.py -H 192.168.0.107 -p 9998
  python3 bg3_console.py -H 127.0.0.1 -p 9998 -e "print('hi')"
  python3 bg3_console.py -H 192.168.0.107 -e "print(1+1)" --client
  python3 bg3_console.py -H 192.168.0.107 -e "print(1)" --hex
""")
    parser.add_argument("-H", "--host", default="127.0.0.1",
                        help="адрес машины с игрой (по умолчанию 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=9998,
                        help="порт отладчика (по умолчанию 9998)")
    parser.add_argument("-e", "--execute", help="выполнить команду и выйти")
    parser.add_argument("--server", action="store_true", help="контекст Server")
    parser.add_argument("--client", action="store_true", help="контекст Client")
    parser.add_argument("-t", "--timeout", type=float, default=5.0,
                        help="таймаут подключения, сек")
    parser.add_argument("--wait", type=float, default=1.5,
                        help="сколько ждать ответов, сек (по умолчанию 1.5)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="показывать hex отправляемых и принимаемых кадров")
    parser.add_argument("--hex", action="store_true",
                        help="напечатать пакет в hex и выйти (ничего не отправляя)")
    args = parser.parse_args()

    client = BG3Client(args.host, args.port, args.timeout, args.verbose)
    if args.server:
        client.context = CTX_SERVER
    if args.client:
        client.context = CTX_CLIENT

    if args.execute:
        packet = frame(wrap(1, build_evaluate(args.execute, client.context, 0)))
        if args.hex:
            print(f"header  : {packet[:4].hex(' ')}  "
                  f"(= {int.from_bytes(packet[:4], 'little')} = len(body)+4)")
            print(f"body    : {packet[4:].hex(' ')}")
            print(f"total   : {len(packet)} байт")
            return 0
        try:
            client.connect()
        except OSError as exc:
            print(f"✖ не удалось подключиться к {args.host}:{args.port}: {exc}",
                  file=sys.stderr)
            return 1
        client.send_connect()
        drain(client, 0.5)
        client.send_evaluate(args.execute)
        drain(client, args.wait)
        client.close()
        return 0

    if args.hex:
        print("используйте --hex вместе с -e")
        return 1

    try:
        client.connect()
    except OSError as exc:
        print(f"✖ не удалось подключиться к {args.host}:{args.port}: {exc}",
              file=sys.stderr)
        print("  проверьте: netstat -an | findstr 9998 на стороне игры",
              file=sys.stderr)
        return 1

    print(f"✓ подключено к {args.host}:{args.port} "
          f"(контекст: {CTX_NAMES[client.context]})")
    client.send_connect()
    drain(client, 1.0)

    print("введите Lua-команду, :help — справка, :quit — выход\n")
    try:
        while True:
            try:
                line = input("bg3> ")
            except EOFError:
                break
            line = line.strip()
            if not line:
                continue
            if line.startswith(":"):
                if not handle_meta(client, line):
                    break
                continue
            try:
                client.send_evaluate(line)
            except (ConnectionError, OSError) as exc:
                print(f"✖ отправка не удалась: {exc}")
                break
            drain(client, args.wait)
    except KeyboardInterrupt:
        print()
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
