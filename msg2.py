import socket
import struct
import sys

# === НАСТРОЙКИ СВЯЗИ ===
HOST = '192.168.0.107'  # IP-адрес вашего Windows-ПК (ПК №1)
PORT = 9999           # Ваш проброшенный порт (или 9998, если туннель прямой)

def encode_protobuf_evaluate(command_text):
    """
    Ручная сборка бинарного пакета Protobuf для Norbyte Lua Debugger.
    Формат сообщения:
    Поле 1 (Varint): Идентификатор запроса / Тип (Evaluate)
    Поле 2 (String): Текст Lua-команды
    """
    cmd_bytes = command_text.encode('utf-8')
    
    # Конструируем тело Protobuf сообщения (Внутренний формат Norbyte Debugger)
    # Поле expression имеет tag = 1, type = 2 (Length-delimited) -> байт 0x0a
    payload = b'\x0a' + struct.pack(f'B', len(cmd_bytes)) + cmd_bytes
    
    # Оборачиваем во внешнее сообщение отладчика (InboundMessage)
    # Поле evaluateRequest имеет tag = 3, type = 2 -> байт 0x1a
    wrapped_payload = b'\x1a' + struct.pack(f'B', len(payload)) + payload
    
    # Перед сообщением Script Extender строго требует 4 байта длины (Little-Endian)
    header = struct.pack('<I', len(wrapped_payload))
    
    return header + wrapped_payload

def main():
    print(f"Подключение к BG3 Script Extender на {HOST}:{PORT}...")
    print("Вводите команды Lua (Пример: print('Тест из Linux!') или Osi.AddGold(Osi.GetHostCharacter(), 500))")
    print("Для выхода нажмите Ctrl+C\n")
    
    while True:
        try:
            cmd = input("BG3 Lua > ")
            if not cmd.strip():
                continue
                
            packet = encode_protobuf_evaluate(cmd)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((HOST, PORT))
                s.sendall(packet)
                print(" -> Отправлено успешно")
        except KeyboardInterrupt:
            print("\nВыход из консоли.")
            break
        except Exception as e:
            print(f"Ошибка передачи: {e}")

if __name__ == '__main__':
    main()
