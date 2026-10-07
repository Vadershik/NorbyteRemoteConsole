# BG3 Remote Lua Console

Удалённое выполнение Lua-кода в Baldur's Gate 3 с Script Extender (bg3se) из терминала на Linux/macOS.

Работает по бинарному protobuf-протоколу Lua-отладчика — без VS Code и без `ncat`-туннелей.

---

## Требования

| На стороне | Что нужно |
|---|---|
| Windows (машина с игрой) | [Script Extender](https://github.com/Norbyte/bg3se) + загруженное сохранение |
| Linux (машина для подключения) | Python 3.8+ |

## 1. Настройка на Windows

Включите отладчик. Файл `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json`:

```json
{
  "EnableLuaDebugger": true,
  "LuaDebuggerPort": 9998
}
```
### 1.1. Временное открытие порта
Скачиваем nmap -> запускаем powershell:
```powershell
.\ncat.exe -lk -p 9999 -c ".\ncat.exe 127.0.0.1 9998"
```
Это откроет временно нам переадресацию с 9999 порта на 9998, пока запущено окно powershell.

### 1.2. Постоянное открытие порта
Откройте порт в брандмауэре (PowerShell от администратора):

```powershell
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
  -Direction Inbound -Protocol TCP -LocalPort 9998 -Action Allow
```
### Продолжение настройки
Проверьте, что игра слушает порт:

```powershell
netstat -an | findstr 9998
```

Должно быть `LISTENING`. Если порта нет — отладчик не запустился: проверьте конфиг и то, что игра запущена напрямую через `bg3_dx11.exe`, а не через Steam.

> Отладчик поднимается **только после загрузки сохранения**. В главном меню порта не будет.

## 2. Подключение

```bash
# напрямую по локальной сети
python3 bg3_console.py -H 192.168.0.107 -p 9998

# через SSH-туннель (предпочтительно: зашифровано, не нужен файрвол)
ssh -L 9998:localhost:9998 user@192.168.0.107
python3 bg3_console.py -H 127.0.0.1 -p 9998
```

При успешном подключении:

```
✓ подключено к 192.168.0.107:9998 (контекст: Server)
· протокол игры: 4
· отладчик готов
введите Lua-команду, :help — справка, :quit — выход
```

## 3. Выполнение команд

```bash
# одна команда и выход
python3 bg3_console.py -H 192.168.0.107 -e "print('Привет')"

# в контексте клиента
python3 bg3_console.py -H 192.168.0.107 --client -e "print(1)"
```

Примеры Lua:

```lua
print("Тест связи")

Osi.AddGold(Osi.GetHostCharacter(), 500)

local c = Osi.GetHostCharacter()
Osi.Print(c:GetName())

DumpedStats(Selected())
```

Вывод `print()` из игры приходит в консоль — раньше это не работало, потому что скрипт не читал ответы.

## Команды в консоли

| Команда | Действие |
|---|---|
| `:server` / `:client` | переключить контекст выполнения (server-side / client-side) |
| `:context` | показать текущий контекст |
| `:reset` | сбросить контекст |
| `:break` / `:nobreak` | остановка на ошибках |
| `:reconnect` | переподключиться |
| `:help`, `:quit` | справка, выход |

## Диагностика

Проверить, что собирается отправить, ничего не подключая:

```bash
python3 bg3_console.py -H 192.168.0.107 -e "print(1)" --hex
```

Подробный лог TCP-обмена в hex:

```bash
python3 bg3_console.py -H 192.168.0.107 -v
```

Проверить доступность порта:

```bash
nc -zv 192.168.0.107 9998
```

| Симптом | Причина |
|---|---|
| `Connection refused` | отладчик не слушает — не загружено сохранение или не запущен `bg3_dx11.exe` |
| таймаут | закрыт брандмауэр Windows |
| `✖ отправка не удалась` | соединение разорвано, попробуйте `:reconnect` |

## Как это работает

Фрейминг — 4 байта длины little-endian, затем protobuf. Длина **включает сама себя**:

```
[uint32 LE = len(body) + 4][protobuf body]
```

Схема сообщений (направление клиент → игра):

```
DebuggerToBackend {
    uint32 seqNo      = 1;
    oneof msg {
        DbgConnectRequest connect  = 3  { uint32 protocolVersion = 1; }
        DbgEvaluate     evaluate  = 7  { context = 1; expression = 2; frame = 3; }
        DbgReset        reset     = 11 { context = 1; }
        ...
    }
}
enum DbgContext { Server = 0; Client = 1; }
```

Ключевые моменты, на которых обычно ломается реализация:

- длина в заголовке = `len(body) + 4`, а не `len(body)`;
- `evaluate` — это поле **7**, а не 3 (поле 3 — это `connect`, и в нём `protocolVersion` ждёт varint, из-за чего protobuf и падает с `Unable to decode protobuf message from coded stream`);
- `expression` — поле **2**, не 1;
- контексты — `0 = Server`, `1 = Client`, а не `1` и `2`;
- соединение должно быть **одним и постоянным**, а не новое на каждую команду.

Схема восстановлена из метаданных и IL `LuaDebugger.exe` (namespace `NSE.DebuggerFrontend`).

## Отладка через VS Code

Если нужен полноценный дебаггер с точками останова, а не просто REPL, — штатный `LuaDebugger.exe` из состава bg3se. Он читает тот же протокол, но общается по DAP. Конфиги запуска лежат в `.vscode/`.

## Структура проекта

```
bg3_console.py      # основной клиент (протокол + REPL)
test_connection.sh  # диагностика доступности порта
.vscode/            # конфиги отладки
```

Остальные `.md`-файлы и `msg*.py` — ранние черновики, можно удалять.
