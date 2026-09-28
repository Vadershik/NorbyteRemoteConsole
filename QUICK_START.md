# Быстрый старт: Удалённая консоль BG3 Lua Debugger

## 🚀 Три способа подключения

### 1️⃣ Python-консоль (Рекомендуется для быстрых команд)

```bash
# Прямое подключение
python3 remote_lua_console.py -H 192.168.0.107 -p 9998

# Через SSH туннель (безопаснее)
ssh -L 9998:localhost:9998 user@192.168.0.107
python3 remote_lua_console.py -H 127.0.0.1 -p 9998

# Одноразовая команда
python3 remote_lua_console.py -e "print('Тест!')"
python3 remote_lua_console.py -c 1 -e "Osi.AddGold(Osi.GetHostCharacter(), 1000)"
```

### 2️⃣ VS Code Debug Console (Рекомендуется для отладки)

1. Открой **Run and Debug** (Ctrl+Shift+D)
2. Выбери конфигурацию:
   - **BG3 Remote Debug (Direct)** - прямое подключение
   - **BG3 Remote Debug (SSH Tunnel)** - через SSH
3. Нажми F5
4. Используй **Debug Console** (Ctrl+Shift+Y) для выполнения команд

### 3️⃣ SSH Port Forwarding (Универсальный метод)

```bash
# В отдельном терминале
ssh -N -L 9998:localhost:9998 user@192.168.0.107

# Теперь localhost:9998 = удалённый отладчик
```

## ⚙️ Настройка удалённого ПК (Windows)

### Вариант A: Через Windows Firewall (для прямого подключения)

```powershell
# PowerShell с правами администратора
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow
```

### Вариант B: SSH сервер (для туннелей)

1. Установи **OpenSSH Server** через Settings → Apps → Optional Features
2. Запусти службу:
   ```powershell
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```

## 📝 Примеры команд

```lua
-- Проверка связи
print("Привет из Linux!")

-- Добавить золото
Osi.AddGold(Osi.GetHostCharacter(), 500)

-- Телепорт
local player = Osi.GetHostCharacter()
Osi.TeleportToPosition(player, -100.0, 50.0, 200.0, 1, 1)

-- Дамп статистики
_D(Ext.Stats.Get('WPN_Greatsword'))

-- Получить информацию о персонаже
local char = Osi.GetHostCharacter()
print("Character GUID: " .. char)
```

## 🔍 Диагностика проблем

```bash
# Проверка доступности порта
nc -zv 192.168.0.107 9998

# На Windows проверь, слушает ли отладчик
netstat -an | findstr 9998

# Проверка SSH туннеля
ss -tuln | grep 9998

# Убить зависший туннель
pkill -f 'ssh.*9998'
```

## 💡 Советы

- **Контекст Server (1)**: основная игровая логика, Osiris функции
- **Контекст Client (2)**: UI, визуальные эффекты
- Используй SSH туннели для безопасности
- Для массовой отладки используй VS Code Debug Console
- Для быстрых команд используй Python-консоль

## 🛑 Устранение проблем

| Ошибка | Решение |
|--------|---------|
| Connection refused | Убедись, что игра запущена с отладчиком |
| Timeout | Проверь firewall или используй SSH туннель |
| SSH denied | Проверь SSH-ключи: `ssh user@192.168.0.107` |
| Команды не выполняются | Установи правильный контекст (`-c 1` или `-c 2`) |

---

**Полная документация:** `README_REMOTE_DEBUG.md`
