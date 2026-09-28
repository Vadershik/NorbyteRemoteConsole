# Удалённая отладка BG3 Lua Debugger

## Обзор решений

### Метод 1: SSH Port Forwarding (Рекомендуется) 🏆

**Преимущества:**
- ✅ Безопасное шифрованное соединение
- ✅ Работает через NAT/firewall
- ✅ Не требует настройки Windows Firewall
- ✅ Можно использовать VS Code Debug Console

**Как использовать:**

```bash
# 1. Создай SSH туннель (в отдельном терминале)
ssh -L 9998:localhost:9998 user@192.168.0.107

# 2. Запусти игру с включённым отладчиком на удалённом ПК

# 3. В VS Code: Run > Start Debugging > "BG3 Remote Debug (SSH Tunnel)"
# ИЛИ используй Python-консоль:
python3 remote_lua_console.py -H 127.0.0.1 -p 9998
```

### Метод 2: Прямое TCP-подключение

**Требования:**
- Открыть порт 9998 в Windows Firewall на удалённом ПК
- Оба устройства в одной локальной сети

```bash
# На Windows (PowerShell с правами администратора):
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" -Direction Inbound -Protocol TCP -LocalPort 9998 -Action Allow

# На Linux:
python3 remote_lua_console.py -H 192.168.0.107 -p 9998
# ИЛИ в VS Code: "BG3 Remote Debug (Direct)"
```

### Метод 3: Netcat Relay (Твой текущий подход)

**Проблемы:**
- ❌ Нестабильное соединение
- ❌ Требует ручной настройки ncat на Windows
- ❌ Не работает с VS Code Debug Adapter

## Python-консоль (remote_lua_console.py)

### Основные команды

```bash
# Интерактивный режим
python3 remote_lua_console.py -H 192.168.0.107 -p 9998

# Одноразовая команда
python3 remote_lua_console.py -e "print('Hello BG3!')"

# Установка контекста Server + команда
python3 remote_lua_console.py -c 1 -e "Osi.AddGold(Osi.GetHostCharacter(), 1000)"

# Через SSH туннель
ssh -L 9998:localhost:9998 user@192.168.0.107 &
python3 remote_lua_console.py -H 127.0.0.1 -p 9998
```

### Примеры Lua-команд

```lua
-- Базовая диагностика
print("Тест связи из Linux!")

-- Добавить золото игроку
Osi.AddGold(Osi.GetHostCharacter(), 500)

-- Телепортация
local player = Osi.GetHostCharacter()
Osi.TeleportToPosition(player, -100.0, 50.0, 200.0, 1, 1)

-- Дамп статистики предмета
_D(Ext.Stats.Get('WPN_Greatsword'))

-- Выполнение на клиенте (установи контекст 2)
-- python3 remote_lua_console.py -c 2
-- _C():ShowNotification("Привет с клиента!")
```

## VS Code Debug Console

После подключения через VS Code (F5 → выбрать конфигурацию), можешь использовать Debug Console:

1. Открой панель Debug Console (Ctrl+Shift+Y)
2. Вводи команды напрямую:
   ```lua
   print("Test from VS Code!")
   Osi.AddGold(Osi.GetHostCharacter(), 1000)
   ```

## Устранение проблем

### Ошибка "Connection refused"
```bash
# Проверь, слушает ли отладчик на порту
# На Windows:
netstat -an | findstr 9998

# На Linux:
nc -zv 192.168.0.107 9998
```

### Ошибка "Timeout"
- Проверь firewall на Windows
- Убедись, что игра запущена с включённым отладчиком
- Проверь IP-адрес: `ip addr show` (Linux) / `ipconfig` (Windows)

### SSH туннель не работает
```bash
# Отладка SSH туннеля
ssh -vvv -L 9998:localhost:9998 user@192.168.0.107

# Убей зависшие туннели
pkill -f 'ssh.*9998'
```

## Архитектура протокола

```
[Linux Client] --TCP--> [Port 9998] --Protobuf--> [BG3 Script Extender]
                                                         |
                                                   [Lua Runtime]
                                                         |
                                                    [Game World]
```

### Формат Protobuf-сообщения

```
[4-byte Length Header (Little-Endian)]
[Protobuf Message]
  ├─ InboundMessage
  │   └─ evaluateRequest (tag=3)
  │       └─ EvaluateRequest
  │           └─ expression (tag=1): string
  │
  └─ SetContextMessage (tag=4): varint
      ├─ 1 = Server context
      └─ 2 = Client context
```

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не открывай порт 9998 в интернет (только локальная сеть)
- Используй SSH туннели для подключения через интернет
- Отладчик не имеет аутентификации - любой в сети может подключиться

## Дополнительные ресурсы

- [BG3 Script Extender Docs](https://github.com/Norbyte/bg3se)
- [Osiris Functions Reference](https://github.com/Norbyte/ositools/blob/master/APIDocs.md)
