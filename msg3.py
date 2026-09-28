import socket
import json
import time

# === НАСТРОЙКИ СВЯЗИ ===
HOST = '192.168.31.95'  # IP вашего Windows-ПК (ПК №1)
PORT = 9999             # Порт LuaDebugger.exe

def send_dap_raw(sock, request_dict):
    """Упаковывает словарь в легальный JSON-DAP фрейм и отправляет в открытый сокет"""
    body = json.dumps(request_dict, ensure_ascii=False)
    body_bytes = body.encode('utf-8')
    header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode('utf-8')
    sock.sendall(header + body_bytes)

def main():
    print(f"Установление DAP-сессии с {HOST}:{PORT}...")
    
    try:
        # Открываем ОДНО постоянное соединение на всю сессию (DAP не работает через кучу коротких сокетов!)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((HOST, PORT))
        
        # ШАГ 1: Обязательное рукопожатие "initialize"
        print(" -> Отправка handshake: initialize")
        send_dap_raw(s, {
            "seq": 1,
            "type": "request",
            "command": "initialize",
            "arguments": {
                "adapterID": "bg3-lua",
                "linesStartAt1": True,
                "columnsStartAt1": True,
                "pathFormat": "path"
            }
        })
        # Читаем ответ, чтобы очистить буфер
        s.recv(4096)
        
        # ШАГ 2: Симуляция старта "launch" (чтобы вывести Script Extender из ступора)
        print(" -> Отправка handshake: launch")
        send_dap_raw(s, {
            "seq": 2,
            "type": "request",
            "command": "launch",
            "arguments": {
                "noDebug": False
            }
        })
        s.recv(4096)
        
        # ШАГ 3: Запрос конфигурации завершен
        send_dap_raw(s, {
            "seq": 3,
            "type": "request",
            "command": "configurationDone"
        })
        s.recv(4096)
        
        print("\n[УСПЕХ] Сессия инициализирована без ошибок Empty Headers!")
        print("Пишите команды Lua (Например: Ext.Utils.Print('Привет!') ). Для выхода: Ctrl+C\n")
        
        seq_counter = 4
        while True:
            cmd = input("BG3 Lua > ")
            if not cmd.strip():
                continue
                
            # ШАГ 4: Отправка самой команды Lua (теперь легально)
            evaluate_request = {
                "seq": seq_counter,
                "type": "request",
                "command": "evaluate",
                "arguments": {
                    "expression": cmd,
                    "context": "repl"
                }
            }
            send_dap_raw(s, evaluate_request)
            seq_counter += 1
            
            # Читаем ответ от игры
            response = s.recv(4096).decode('utf-8', errors='ignore')
            if "success\":true" in response:
                print(" -> Выполнено!")
            else:
                print(" -> Ответ от игры:", response)
                
    except KeyboardInterrupt:
        print("\nЗакрытие сессии.")
    except Exception as e:
        print(f"\nКритическая ошибка сессии: {e}")
    finally:
        s.close()

if __name__ == '__main__':
    main()
