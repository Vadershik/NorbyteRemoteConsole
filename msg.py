import socket
import struct

# === НАСТРОЙКИ СВЯЗИ ===
HOST = '192.168.0.107'  # IP-адрес вашего Windows-ПК (ПК №1)
PORT = 9999           # Внешний порт ncat на Windows

def encode_varint(value):
    """Кодирует число в формат Protobuf Varint"""
    bits = value & 0x7f
    value >>= 7
    ret = bytearray()
    while value:
        ret.append(bits | 0x80)
        bits = value & 0x7f
        value >>= 7
    ret.append(bits)
    return bytes(ret)

def make_packet(outer_tag, inner_tag, payload_bytes):
    """Собирает Protobuf структуру сообщения для SE v32"""
    inner_len = encode_varint(len(payload_bytes))
    expression_field = inner_tag + inner_len + payload_bytes
    
    outer_len = encode_varint(len(expression_field))
    protobuf_body = outer_tag + outer_len + expression_field
    
    se_header = struct.pack('<I', len(protobuf_body))
    return se_header + protobuf_body

def send_packet(packet_bytes):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((HOST, PORT))
        s.sendall(packet_bytes)

def main():
    print(f"Сетевой мост для SE v32 запущен. Цель: {HOST}:{PORT}")
    
    # 1. Инициализируем сессию подключения
    print("Инициализация Protobuf-сессии...")
    try:
        send_packet(make_packet(b'\x0a', b'\x0a', b'Linux_Console_Session'))
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        return

    # 2. ПРИНУДИТЕЛЬНО ПЕРЕКЛЮЧАЕМ КОНТЕКСТ НА СЕРВЕР (Критично для SE v32)
    # Тег 0x22 (Байт 34) отвечает за установку контекста выполнения (1 = Server, 2 = Client)
    print("Переключение контекста на SERVER...")
    context_packet = struct.pack('<I', 2) + b'\x22\x01\x01' 
    try:
        send_packet(context_packet)
    except Exception:
        pass

    print("Готово! Теперь вводите команды Lua. Для выхода: Ctrl+C\n")
    
    while True:
        try:
            cmd = input("BG3 Server Lua > ")
            if not cmd.strip():
                continue
            
            # Отправка самой команды Lua (outer_tag = 0x1a, inner_tag = 0x0a)
            packet = make_packet(b'\x1a', b'\x0a', cmd.encode('utf-8'))
            send_packet(packet)
            print(" -> Отправлено")
                
        except KeyboardInterrupt:
            print("\nВыход.")
            break
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == '__main__':
    main()
