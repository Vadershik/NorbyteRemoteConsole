#!/usr/bin/env python3
"""
Улучшенная удалённая консоль для Norbyte BG3 Lua Debugger
Поддерживает SSH туннели и прямое подключение
"""
import socket
import struct
import sys
import argparse
from typing import Optional

class LuaDebuggerClient:
    def __init__(self, host: str, port: int, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.session_id = 0
    
    def encode_evaluate_request(self, lua_code: str) -> bytes:
        """
        Создаёт Protobuf-пакет для EvaluateRequest
        Формат: [4-byte length header][protobuf body]
        
        Protobuf структура:
        message InboundMessage {
            EvaluateRequest evaluateRequest = 3; // tag=3, wire_type=2 -> 0x1a
        }
        message EvaluateRequest {
            string expression = 1; // tag=1, wire_type=2 -> 0x0a
        }
        """
        cmd_bytes = lua_code.encode('utf-8')
        
        # Внутреннее сообщение: expression (tag=1, wire_type=2)
        inner_payload = b'\x0a' + self._encode_length(len(cmd_bytes)) + cmd_bytes
        
        # Внешнее сообщение: evaluateRequest (tag=3, wire_type=2)
        outer_payload = b'\x1a' + self._encode_length(len(inner_payload)) + inner_payload
        
        # 4-байтовый заголовок длины (Little-Endian)
        header = struct.pack('<I', len(outer_payload))
        
        return header + outer_payload
    
    def encode_set_context(self, context: int) -> bytes:
        """
        Переключает контекст выполнения:
        1 = Server, 2 = Client
        tag=4, wire_type=0 -> 0x20
        """
        varint_context = self._encode_varint(context)
        protobuf_body = b'\x20' + varint_context
        header = struct.pack('<I', len(protobuf_body))
        return header + protobuf_body
    
    @staticmethod
    def _encode_varint(value: int) -> bytes:
        """Кодирует число в Protobuf Varint"""
        result = bytearray()
        while value > 0x7f:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value & 0x7f)
        return bytes(result)
    
    @staticmethod
    def _encode_length(length: int) -> bytes:
        """Кодирует длину строки (Varint для коротких строк)"""
        if length < 128:
            return bytes([length])
        return LuaDebuggerClient._encode_varint(length)
    
    def send_command(self, lua_code: str) -> bool:
        """Отправляет Lua-команду на сервер"""
        try:
            packet = self.encode_evaluate_request(lua_code)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(packet)
            return True
        except socket.timeout:
            print(f"⚠️  Таймаут подключения к {self.host}:{self.port}", file=sys.stderr)
            return False
        except ConnectionRefusedError:
            print(f"❌ Соединение отклонено. Проверьте, запущен ли отладчик на {self.host}:{self.port}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}", file=sys.stderr)
            return False
    
    def set_context(self, context: int) -> bool:
        """Устанавливает контекст (1=Server, 2=Client)"""
        try:
            packet = self.encode_set_context(context)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(packet)
            return True
        except Exception as e:
            print(f"⚠️  Ошибка установки контекста: {e}", file=sys.stderr)
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Удалённая консоль для BG3 Lua Debugger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python3 remote_lua_console.py -H 192.168.0.107 -p 9998
  python3 remote_lua_console.py -H 127.0.0.1 -p 9998  # через SSH туннель
  python3 remote_lua_console.py -c 1 -e "print('Hello')"
        """
    )
    parser.add_argument('-H', '--host', default='192.168.0.107',
                        help='IP-адрес отладчика (default: 192.168.0.107)')
    parser.add_argument('-p', '--port', type=int, default=9998,
                        help='Порт отладчика (default: 9998)')
    parser.add_argument('-c', '--context', type=int, choices=[1, 2],
                        help='Контекст: 1=Server, 2=Client')
    parser.add_argument('-e', '--execute', type=str,
                        help='Выполнить команду и выйти')
    parser.add_argument('-t', '--timeout', type=int, default=5,
                        help='Таймаут в секундах (default: 5)')
    
    args = parser.parse_args()
    
    client = LuaDebuggerClient(args.host, args.port, args.timeout)
    
    if args.context:
        context_name = "Server" if args.context == 1 else "Client"
        print(f"🔧 Установка контекста: {context_name}")
        if not client.set_context(args.context):
            sys.exit(1)
    
    if args.execute:
        print(f"📤 Отправка: {args.execute}")
        success = client.send_command(args.execute)
        sys.exit(0 if success else 1)
    
    print(f"🔌 Подключено к {args.host}:{args.port}")
    print("📝 Введите Lua-команды (Ctrl+C для выхода)\n")
    
    try:
        while True:
            try:
                cmd = input("BG3 Lua > ")
                if not cmd.strip():
                    continue
                if client.send_command(cmd):
                    print("✅ Отправлено")
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n👋 Выход")
    
if __name__ == '__main__':
    main()
