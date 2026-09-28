# 🚀 Инструкция по настройке и запуску

## 📋 Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Настройка удалённого ПК (Windows)](#настройка-удалённого-пк-windows)
3. [Настройка локального ПК (Linux)](#настройка-локального-пк-linux)
4. [Запуск: Метод 1 - Python Console](#метод-1-python-console-рекомендуется)
5. [Запуск: Метод 2 - SSH Tunnel](#метод-2-ssh-tunnel-безопасный)
6. [Запуск: Метод 3 - VS Code Debug](#метод-3-vs-code-debug-профессиональный)
7. [Проверка работоспособности](#проверка-работоспособности)
8. [Устранение проблем](#устранение-проблем)

---

## Предварительные требования

### На локальном ПК (Linux)
- ✅ Python 3.7+ (`python3 --version`)
- ✅ VS Code с расширением BG3 Script Extender (опционально)
- ✅ SSH клиент (`ssh -V`)
- ✅ Утилита netcat для диагностики (`nc -h`)

### На удалённом ПК (Windows)
- ✅ Baldur's Gate 3 с установленным **Norbyte's Script Extender**
- ✅ Игра должна быть запущена с включённым отладчиком
- ✅ Windows Firewall (или SSH сервер)

### Сетевые требования
- ✅ Оба устройства в одной локальной сети
- ✅ Известен IP-адрес удалённого ПК (например: `192.168.0.107`)

---

## Настройка удалённого ПК (Windows)

### Шаг 1: Установка Script Extender

1. Скачай [BG3 Script Extender](https://github.com/Norbyte/bg3se/releases/latest)
2. Распакуй в корень игры: `Steam/steamapps/common/Baldurs Gate 3/bin/`
3. Запускай игру через `DXGIWrapper.exe` (или измени ярлык Steam)

### Шаг 2: Включение Lua Debugger

Отредактируй файл:
```
%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json
```

Добавь/измени:
```json
{
  "EnableDebugger": true,
  "DebuggerPort": 9998,
  "EnableLogging": true
}
```

### Шаг 3A: Открытие порта в Firewall (для прямого подключения)

**PowerShell с правами администратора:**
```powershell
# Создать правило для входящих соединений
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow

# Проверить правило
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger"
```

**ИЛИ через GUI:**
1. Открой **Windows Defender Firewall** → Advanced Settings
2. Inbound Rules → New Rule → Port
3. TCP, порт `9998`, Allow connection
4. Применить ко всем профилям

### Шаг 3B: Установка SSH сервера (для туннелей) — АЛЬТЕРНАТИВА

**Если не хочешь открывать порты:**

1. **Settings** → **Apps** → **Optional Features** → **Add a feature**
2. Найди и установи **"OpenSSH Server"**
3. Запусти службу:
```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Проверка
Get-Service sshd
```

4. Узнай имя пользователя:
```powershell
whoami
```

### Шаг 4: Узнать IP-адрес Windows ПК

```powershell
ipconfig

# Ищи строку "IPv4 Address" для активного адаптера
# Пример: 192.168.0.107
```

### Шаг 5: Запустить игру

1. Запусти **Baldur's Gate 3** через Script Extender
2. Загрузи любое сохранение
3. Проверь логи в `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\`
4. Должна быть строка: `Debugger listening on port 9998`

---

## Настройка локального ПК (Linux)

### Шаг 1: Клонировать/распаковать проект

```bash
cd /home/kolya/Projects/REMCON
ls -lh remote_lua_console.py  # Проверь наличие файла
```

### Шаг 2: Установить зависимости

```bash
# Проверь Python
python3 --version  # Должно быть 3.7+

# Проверь SSH (обычно уже установлен)
ssh -V
```

**Зависимостей не требуется!** Скрипт использует только стандартные библиотеки Python.

### Шаг 3: Сделать скрипт исполняемым

```bash
chmod +x /home/kolya/Projects/REMCON/remote_lua_console.py
```

### Шаг 4: Узнать IP удалённого ПК

```bash
# Сканировать сеть (если неизвестен IP)
nmap -sn 192.168.0.0/24

# ИЛИ просто ping
ping 192.168.0.107
```

---

## Метод 1: Python Console (Рекомендуется)

### Запуск в интерактивном режиме

```bash
cd /home/kolya/Projects/REMCON

# Подключиться к удалённому отладчику
python3 remote_lua_console.py -H 192.168.0.107 -p 9998
```

**Ожидаемый вывод:**
```
🔌 Подключено к 192.168.0.107:9998
📝 Введите Lua-команды (Ctrl+C для выхода)

BG3 Lua > 
```

### Примеры команд

```lua
# Проверка связи
BG3 Lua > print("Привет из Linux!")
✅ Отправлено

# Добавить золото
BG3 Lua > Osi.AddGold(Osi.GetHostCharacter(), 1000)
✅ Отправлено

# Дамп статистики
BG3 Lua > _D(Ext.Stats.Get('WPN_Greatsword'))
✅ Отправлено
```

### Одноразовые команды

```bash
# Выполнить команду и выйти
python3 remote_lua_console.py -e "print('Тест!')"

# С установкой контекста Server (основной контекст игры)
python3 remote_lua_console.py -c 1 -e "Osi.AddGold(Osi.GetHostCharacter(), 500)"

# С установкой контекста Client (UI, визуальные эффекты)
python3 remote_lua_console.py -c 2 -e "_C():ShowNotification('Привет!')"
```

### Параметры командной строки

```
-H, --host HOST        IP-адрес (default: 192.168.0.107)
-p, --port PORT        Порт (default: 9998)
-c, --context {1,2}    Контекст: 1=Server, 2=Client
-e, --execute CMD      Выполнить команду и выйти
-t, --timeout SEC      Таймаут подключения (default: 5)
-h, --help             Показать справку
```

---

## Метод 2: SSH Tunnel (Безопасный)

### Когда использовать
- ✅ Не хочешь открывать порты в Firewall
- ✅ Нужно шифрованное соединение
- ✅ Работа через NAT/сложные сети

### Шаг 1: Создать SSH туннель

```bash
# В отдельном терминале (оставь запущенным)
ssh -L 9998:localhost:9998 username@192.168.0.107

# Где username — имя пользователя Windows
# Пример: ssh -L 9998:localhost:9998 kolya@192.168.0.107
```

**При первом подключении:**
```
The authenticity of host '192.168.0.107' can't be established.
Are you sure you want to continue connecting (yes/no)? yes
```

**Введи пароль Windows пользователя.**

### Шаг 2: Подключиться через туннель

```bash
# В другом терминале
cd /home/kolya/Projects/REMCON
python3 remote_lua_console.py -H 127.0.0.1 -p 9998
```

Теперь `127.0.0.1:9998` (локальный) → `192.168.0.107:9998` (удалённый)

### Автоматизация с SSH ключами (опционально)

```bash
# Сгенерировать ключ (если ещё не создан)
ssh-keygen -t ed25519

# Скопировать на Windows
ssh-copy-id username@192.168.0.107

# Теперь можно подключаться без пароля
ssh -L 9998:localhost:9998 username@192.168.0.107
```

### Фоновый туннель

```bash
# Запустить в фоне
ssh -f -N -L 9998:localhost:9998 username@192.168.0.107

# Убить туннель
pkill -f 'ssh.*9998:localhost:9998'

# Проверить активные туннели
ps aux | grep 'ssh.*9998'
```

---

## Метод 3: VS Code Debug (Профессиональный)

### Предварительные требования

1. **VS Code** установлен
2. Расширение **Norbyte's BG3 Script Extender** установлено
3. Открыта папка `/home/kolya/Projects/REMCON` в VS Code

### Запуск (прямое подключение)

1. Открой **Run and Debug** (`Ctrl+Shift+D`)
2. Выбери конфигурацию: **"BG3 Remote Debug (Direct)"**
3. Нажми `F5` (или кнопку Start Debugging)
4. Открой **Debug Console** (`Ctrl+Shift+Y`)

### Запуск (через SSH туннель)

1. В терминале создай туннель:
   ```bash
   ssh -L 9998:localhost:9998 username@192.168.0.107
   ```
2. В VS Code выбери: **"BG3 Remote Debug (SSH Tunnel)"**
3. Нажми `F5`

### Использование Debug Console

```lua
# Вводи команды напрямую в консоли
print("Тест из VS Code!")
Osi.AddGold(Osi.GetHostCharacter(), 1000)

# Используй автодополнение и подсветку синтаксиса
_D(Ext.Stats.Get('WPN_Greatsword'))
```

### Преимущества VS Code метода

- ✅ Breakpoints в Lua-коде (если есть исходники)
- ✅ Просмотр переменных в реальном времени
- ✅ Автодополнение Lua API
- ✅ История команд
- ✅ Цветовая подсветка синтаксиса

---

## Проверка работоспособности

### 1. Проверка доступности порта

```bash
# На Linux
nc -zv 192.168.0.107 9998

# Ожидаемый результат (успех):
# Connection to 192.168.0.107 9998 port [tcp/*] succeeded!

# Результат (ошибка):
# nc: connect to 192.168.0.107 port 9998 (tcp) failed: Connection refused
```

### 2. Проверка отладчика на Windows

```powershell
# На Windows
netstat -an | findstr 9998

# Должна быть строка:
# TCP    0.0.0.0:9998           0.0.0.0:0              LISTENING
```

### 3. Тестовая команда

```bash
# Отправить простую команду
python3 remote_lua_console.py -e "print('Test connection')" -t 3

# Успех:
# 📤 Отправка: print('Test connection')
# ✅ Отправлено

# Ошибка:
# ⚠️  Таймаут подключения к 192.168.0.107:9998
```

### 4. Проверка SSH туннеля

```bash
# Создать туннель
ssh -L 9998:localhost:9998 username@192.168.0.107 &

# Проверить локальный порт
ss -tuln | grep 9998

# Должна быть строка:
# tcp   LISTEN 0   128   127.0.0.1:9998   0.0.0.0:*

# Тест через туннель
python3 remote_lua_console.py -H 127.0.0.1 -p 9998 -e "print('SSH Test')"
```

---

## Устранение проблем

### Ошибка: "Connection refused"

**Причина:** Отладчик не запущен или порт закрыт

**Решение:**
```bash
# 1. Проверь, что игра запущена
# 2. Проверь ScriptExtenderSettings.json (EnableDebugger: true)
# 3. Проверь логи Script Extender на Windows:
#    %LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\

# 4. На Windows проверь порт:
netstat -an | findstr 9998

# 5. Попробуй переоткрыть игру
```

### Ошибка: "Timeout"

**Причина:** Firewall блокирует или неверный IP

**Решение:**
```bash
# 1. Проверь IP-адрес Windows ПК
ping 192.168.0.107

# 2. Проверь Firewall на Windows (см. Шаг 3A выше)

# 3. Используй SSH туннель вместо прямого подключения:
ssh -L 9998:localhost:9998 username@192.168.0.107
python3 remote_lua_console.py -H 127.0.0.1 -p 9998
```

### Ошибка: "SSH connection failed"

**Причина:** SSH сервер не запущен на Windows

**Решение:**
```powershell
# На Windows PowerShell
Get-Service sshd

# Если не установлен — см. Шаг 3B выше

# Если установлен но остановлен:
Start-Service sshd

# Проверь firewall для SSH (порт 22):
Get-NetFirewallRule -DisplayName "*SSH*"
```

### Ошибка: "Permission denied (publickey)"

**Причина:** SSH требует аутентификацию

**Решение:**
```bash
# Используй пароль вместо ключей
ssh -o PreferredAuthentications=password -L 9998:localhost:9998 username@192.168.0.107

# ИЛИ настрой SSH ключи (см. раздел "Автоматизация с SSH ключами")
```

### Команды отправляются но ничего не происходит

**Причина:** Неверный контекст выполнения

**Решение:**
```bash
# Для Osiris функций (Osi.*) используй контекст Server:
python3 remote_lua_console.py -c 1 -e "Osi.AddGold(Osi.GetHostCharacter(), 100)"

# Для клиентских функций (_C()) используй контекст Client:
python3 remote_lua_console.py -c 2 -e "_C():ShowNotification('Test')"
```

### VS Code не видит конфигурации отладки

**Причина:** Не установлено расширение или неправильная структура папок

**Решение:**
```bash
# 1. Установи расширение: Norbyte's BG3 Script Extender
# 2. Открой папку проекта в VS Code:
#    File → Open Folder → /home/kolya/Projects/REMCON

# 3. Проверь файлы:
ls -la /home/kolya/Projects/REMCON/.vscode/launch.json
ls -la /home/kolya/Projects/REMCON/.vscode/tasks.json

# 4. Перезагрузи VS Code
```

---

## 💡 Полезные Lua-команды

```lua
-- Информация о персонаже
local player = Osi.GetHostCharacter()
print("Player GUID: " .. player)

-- Добавить опыт
Osi.AddExplorationExperience(Osi.GetHostCharacter(), 1000)

-- Телепортация
Osi.TeleportToPosition(Osi.GetHostCharacter(), -100.0, 50.0, 200.0, 1, 1)

-- Получить статистику предмета
_D(Ext.Stats.Get('WPN_Greatsword'))

-- Вывод всех доступных функций Osiris
_D(Osi)

-- Вывод структуры объекта
_D(Ext.Entity.Get(Osi.GetHostCharacter()))
```

---

## ✅ Checklist перед запуском

### На Windows (удалённый ПК):
- [ ] Script Extender установлен
- [ ] `ScriptExtenderSettings.json` настроен (`EnableDebugger: true`)
- [ ] Игра запущена через Script Extender
- [ ] Порт 9998 открыт в Firewall **ИЛИ** SSH сервер запущен
- [ ] IP-адрес известен

### На Linux (локальный ПК):
- [ ] Python 3.7+ установлен
- [ ] `remote_lua_console.py` исполняемый (`chmod +x`)
- [ ] Проверено подключение к удалённому ПК (`ping`)
- [ ] Порт доступен (`nc -zv`) **ИЛИ** SSH туннель создан

### Финальная проверка:
```bash
# Тестовая команда
python3 remote_lua_console.py -e "print('🎮 BG3 Remote Console Ready!')"

# Ожидаемый результат:
# 📤 Отправка: print('🎮 BG3 Remote Console Ready!')
# ✅ Отправлено
```

---

## 📚 Дополнительные ресурсы

- **QUICK_START.md** — Быстрые примеры команд
- **README_REMOTE_DEBUG.md** — Полная документация протокола
- [BG3 Script Extender GitHub](https://github.com/Norbyte/bg3se)
- [Osiris API Reference](https://github.com/Norbyte/ositools/blob/master/APIDocs.md)

---

**Всё готово к работе! Выбери один из трёх методов и начинай управлять игрой удалённо.** 🚀
