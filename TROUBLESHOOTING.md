# 🔧 Устранение ошибки "Unable to decode protobuf message"

## Проблема

Ошибка в логах Script Extender:
```
Unable to decode protobuf message from coded stream
```

## Причина

Ты используешь **ncat туннель** на порту 9999 → 127.0.0.1:9998, который искажает бинарные данные Protobuf.

### Почему ncat не работает:

1. **Text mode** — ncat может интерпретировать бинарные данные как текст
2. **Buffering** — буферизация может разбивать пакеты
3. **Line endings** — конвертация `\r\n` портит Protobuf
4. **Keep-alive проблемы** — соединение закрывается после каждого пакета

---

## ✅ Решение 1: SSH туннель (Рекомендуется)

SSH туннель корректно работает с бинарными протоколами.

### На Linux:

```bash
# Создать SSH туннель (оставь запущенным в отдельном терминале)
ssh -L 9998:localhost:9998 username@192.168.0.107

# В другом терминале подключайся локально
python3 remote_lua_console.py -H 127.0.0.1 -p 9998
```

### На Windows нужен SSH сервер:

```powershell
# PowerShell с правами администратора
# Установить OpenSSH Server (если ещё не установлен)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Запустить службу
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Проверить
Get-Service sshd
```

---

## ✅ Решение 2: Прямое подключение (Самое простое)

Открой порт 9998 напрямую, без ncat туннеля.

### На Windows:

```powershell
# PowerShell с правами администратора
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow

# Проверить правило
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger"
```

### На Linux:

```bash
# Подключайся напрямую к Windows IP
python3 remote_lua_console.py -H 192.168.0.107 -p 9998
```

---

## ✅ Решение 3: Правильный ncat туннель (Если SSH недоступен)

Если обязательно нужен ncat, используй правильные флаги:

### Неправильно (твой текущий вариант):
```bash
# ❌ Режим по умолчанию - может искажать данные
ncat -l 9999 -c "ncat 127.0.0.1 9998"
```

### Правильно:
```bash
# ✅ Бинарный режим + keep-alive
ncat -l 9999 --keep-open --broker --exec "ncat 127.0.0.1 9998"

# ИЛИ используй socat (лучше для бинарных протоколов)
socat TCP-LISTEN:9999,fork,reuseaddr TCP:127.0.0.1:9998
```

---

## 🔍 Диагностика

### 1. Проверь, что отладчик слушает порт

**На Windows:**
```powershell
netstat -an | findstr 9998
# Должно быть: TCP    0.0.0.0:9998    0.0.0.0:0    LISTENING
```

### 2. Проверь доступность напрямую

**На Linux:**
```bash
# Тест прямого подключения
nc -zv 192.168.0.107 9998

# Успех:
# Connection to 192.168.0.107 9998 port [tcp/*] succeeded!
```

### 3. Проверь пакет перед отправкой

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/kolya/Projects/REMCON')
from remote_lua_console import LuaDebuggerClient

client = LuaDebuggerClient('127.0.0.1', 9998)
packet = client.encode_evaluate_request('print("test")')

print(f'Packet length: {len(packet)} bytes')
print(f'Header (4 bytes): {packet[:4].hex()}')
print(f'Body: {packet[4:].hex()}')
print(f'Expected header value: {int.from_bytes(packet[:4], "little")} bytes')
print(f'Actual body length: {len(packet[4:])} bytes')
print(f'Match: {int.from_bytes(packet[:4], "little") == len(packet[4:])}')
EOF
```

Ожидаемый вывод:
```
Packet length: 21 bytes
Header (4 bytes): 11000000
Body: 1a0f0a0d7072696e742822746573742229
Expected header value: 17 bytes
Actual body length: 17 bytes
Match: True
```

### 4. Проверь логи Script Extender

**На Windows:**
```
%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\
```

Ищи строки:
- `Debugger listening on port 9998` ✅ (отладчик запущен)
- `Client connected from X.X.X.X` ✅ (подключение установлено)
- `Unable to decode protobuf message` ❌ (некорректный пакет)

---

## 🎯 Рекомендуемый порядок действий

1. **Убей текущий ncat туннель:**
   ```bash
   pkill -f ncat
   # ИЛИ на Windows: taskkill /F /IM ncat.exe
   ```

2. **Создай SSH туннель:**
   ```bash
   ssh -L 9998:localhost:9998 username@192.168.0.107
   ```

3. **Тестовая команда:**
   ```bash
   python3 remote_lua_console.py -H 127.0.0.1 -p 9998 -e "print('SSH Test')"
   ```

4. **Если SSH недоступен, открой порт напрямую:**
   ```powershell
   # На Windows
   New-NetFirewallRule -DisplayName "BG3 Lua Debugger" -Direction Inbound -Protocol TCP -LocalPort 9998 -Action Allow
   ```
   
   ```bash
   # На Linux
   python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Direct Test')"
   ```

---

## 💡 Почему SSH туннель лучше ncat

| Критерий | ncat | SSH туннель |
|----------|------|-------------|
| **Бинарные данные** | ❌ Может искажать | ✅ Безопасно |
| **Безопасность** | ❌ Нет шифрования | ✅ Шифрованное |
| **Надёжность** | ❌ Нестабильное | ✅ Стабильное |
| **Keep-alive** | ❌ Требует флагов | ✅ Автоматически |
| **Настройка** | ⚠️ Сложная | ✅ Простая |
| **Firewall** | ❌ Нужны проброс портов | ✅ Не нужен |

---

## 📚 Дополнительные ресурсы

- **RUN.md** — Детальная инструкция по настройке SSH
- **QUICK_START.md** — Быстрые примеры команд
- [BG3 Script Extender Docs](https://github.com/Norbyte/bg3se)

---

**Используй SSH туннель вместо ncat — это решит проблему!** 🚀
