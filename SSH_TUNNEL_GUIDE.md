# 🔧 Пошаговая настройка SSH туннеля для BG3 Debugger

## Проблема
После команды `ssh -L 9998:localhost:9998 username@192.168.0.107` не получается подключиться через `python3 remote_lua_console.py -H 127.0.0.1 -p 9998`

---

## ✅ Правильная процедура настройки SSH туннеля

### Шаг 1: Проверка SSH сервера на Windows

**На Windows PowerShell:**
```powershell
# Проверить, установлен ли SSH сервер
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

# Если State = NotPresent, установи:
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Запустить службу
Start-Service sshd

# Автозапуск
Set-Service -Name sshd -StartupType 'Automatic'

# Проверить статус
Get-Service sshd
# Должно быть: Status = Running

# Узнать имя пользователя
whoami
# Например: DESKTOP-ABC123\kolya
```

### Шаг 2: Проверка SSH подключения с Linux

**На Linux:**
```bash
# Проверить, можешь ли подключиться к Windows по SSH
ssh username@192.168.0.107

# Где username - имя пользователя Windows (из команды whoami)
# Например: ssh kolya@192.168.0.107
```

**Возможные проблемы:**

#### Ошибка: "Connection refused"
```bash
# Решение: SSH сервер не запущен на Windows
# Вернись к Шагу 1 и запусти службу sshd
```

#### Ошибка: "Permission denied (publickey)"
```bash
# Решение: используй пароль вместо ключей
ssh -o PreferredAuthentications=password username@192.168.0.107

# Введи пароль Windows пользователя
```

### Шаг 3: Создание SSH туннеля

**ВАЖНО:** Нужно открыть **ДВА терминала** на Linux!

#### Терминал 1 (оставь запущенным):
```bash
# Создать туннель в интерактивном режиме
ssh -L 9998:localhost:9998 username@192.168.0.107

# ИЛИ в фоновом режиме:
ssh -f -N -L 9998:localhost:9998 username@192.168.0.107
```

**После успешного подключения:**
- В интерактивном режиме: увидишь приглашение Windows `C:\Users\username>`
- В фоновом режиме: команда завершится, туннель останется

#### Терминал 2 (проверка туннеля):
```bash
# Проверить, что туннель создан
ps aux | grep 'ssh.*9998'

# Проверить, что порт слушается
ss -tuln | grep 9998
# Должна быть строка: tcp   LISTEN   0   128   127.0.0.1:9998   0.0.0.0:*
```

### Шаг 4: Проверка, что игра запущена с отладчиком

**На Windows:**
1. Запусти BG3 через Script Extender
2. Загрузи сохранение
3. Проверь логи в `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\`
4. Должна быть строка: `Debugger listening on port 9998`

**На Windows PowerShell:**
```powershell
netstat -an | findstr 9998
# Должно быть: TCP    0.0.0.0:9998    0.0.0.0:0    LISTENING
```


---

## 🔍 Диагностика проблем

### Проблема 1: "Connection refused" при подключении через туннель

**Причина:** Туннель не создан или игра не запущена

**Проверка на Linux:**
```bash
# 1. Проверить туннель
ss -tuln | grep 9998
# Если пусто - туннель не создан, вернись к Шагу 3

# 2. Проверить подключение к локальному порту
nc -zv 127.0.0.1 9998
# Успех: Connection to 127.0.0.1 9998 port [tcp/*] succeeded!
# Ошибка: Connection refused = игра не запущена на Windows
```

**Проверка на Windows:**
```powershell
netstat -an | findstr 9998
# Если нет строки с LISTENING - игра не запущена с отладчиком
```

### Проблема 2: SSH туннель не создаётся

**Причина:** SSH сервер не запущен на Windows или Firewall блокирует

**Решение:**
```powershell
# На Windows PowerShell (администратор)
# 1. Запустить SSH сервер
Start-Service sshd

# 2. Разрешить SSH в Firewall
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' `
                    -Enabled True -Direction Inbound -Protocol TCP `
                    -Action Allow -LocalPort 22
```

### Проблема 3: Туннель постоянно разрывается

**Решение: используй keep-alive**
```bash
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 \
    -L 9998:localhost:9998 username@192.168.0.107
```

### Проблема 4: Не знаю имя пользователя Windows

**На Windows PowerShell:**
```powershell
whoami
# Вывод: DESKTOP-ABC123\kolya
# Используй только часть после \: kolya
```

---

## 📊 Схема работы SSH туннеля

```
Linux PC                    SSH Tunnel                Windows PC
┌─────────────┐            ┌──────────┐             ┌────────────┐
│             │            │          │             │            │
│ Python      │  connect   │  SSH     │  forward    │ BG3        │
│ 127.0.0.1:  │ ────────>  │  tunnel  │  ────────>  │ 127.0.0.1: │
│ 9998        │            │          │             │ 9998       │
│             │            │          │             │            │
└─────────────┘            └──────────┘             └────────────┘
     ^                          ^                         ^
     │                          │                         │
  Терминал 2               Терминал 1                  Игра
  (команды)                (туннель)                 (запущена)
```

---

## ✅ Checklist успешной настройки

### На Windows:
- [ ] SSH Server установлен и запущен (`Get-Service sshd`)
- [ ] Firewall разрешает SSH (порт 22)
- [ ] Script Extender настроен (`EnableDebugger: true`)
- [ ] Игра запущена и загружено сохранение
- [ ] Порт 9998 слушается (`netstat -an | findstr 9998`)

### На Linux:
- [ ] SSH клиент установлен (`ssh -V`)
- [ ] Можешь подключиться к Windows (`ssh user@192.168.0.107`)
- [ ] Туннель создан в отдельном терминале
- [ ] Порт 9998 слушается локально (`ss -tuln | grep 9998`)
- [ ] Python скрипт подключается к `127.0.0.1:9998`

---

## 🎯 Быстрый тест туннеля

```bash
#!/bin/bash
echo "=== SSH Tunnel Diagnostic ==="

echo -n "1. SSH server reachable: "
nc -zv -w2 192.168.0.107 22 2>&1 | grep -q succeeded && echo "✅" || echo "❌"

echo -n "2. SSH tunnel running: "
pgrep -f 'ssh.*9998' > /dev/null && echo "✅" || echo "❌"

echo -n "3. Local port listening: "
ss -tuln | grep -q ':9998' && echo "✅" || echo "❌"

echo ""
echo "If all ✅ - tunnel is ready!"
```

Сохрани в `test_tunnel.sh` и выполни: `bash test_tunnel.sh`

---

## 💡 Альтернатива: Прямое подключение (проще!)

Если SSH туннель не работает, используй **Решение 1** из TROUBLESHOOTING.md:

```powershell
# На Windows (администратор)
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound -Protocol TCP `
                    -LocalPort 9998 -Action Allow
```

```bash
# На Linux подключайся напрямую
python3 remote_lua_console.py -H 192.168.0.107 -p 9998
```

**Это намного проще, чем настройка SSH!** 🚀

