# 📖 КРАТКАЯ ИНСТРУКЦИЯ: Запуск удалённого подключения к BG3 Lua Debugger

## 🎯 Самый простой способ (РЕКОМЕНДУЕТСЯ)

### На Windows:

**1. Открой порт 9998 в Firewall (PowerShell с правами администратора):**
```powershell
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow
```

**2. Проверь, что игра запущена с отладчиком:**
```powershell
netstat -an | findstr 9998
# Должно быть: TCP    0.0.0.0:9998    0.0.0.0:0    LISTENING
```

### На Linux:

**3. Подключайся напрямую:**
```bash
cd /home/kolya/Projects/REMCON
python3 remote_lua_console.py -H 192.168.0.107 -p 9998
```

**4. Тестовая команда:**
```bash
python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Работает!')"
```

---

## 🔍 Если не работает

### Проблема: "Connection refused"
```bash
# Проверь доступность порта
nc -zv 192.168.0.107 9998

# Если недоступен - вернись к шагу 1-2 на Windows
```

### Проблема: "Unable to decode protobuf message" в логах
```bash
# Убей ncat туннель (он искажает бинарные данные!)
pkill -f ncat

# Используй прямое подключение (см. выше)
```

---

## 📁 Документация

- **RUN.md** - Полная инструкция со всеми деталями
- **TROUBLESHOOTING.md** - Решение проблемы с ncat
- **SSH_TUNNEL_GUIDE.md** - Настройка SSH туннеля (сложнее)
- **QUICK_START.md** - Примеры Lua команд

---

## ✅ Готово!

После успешного подключения:
```
🔌 Подключено к 192.168.0.107:9998
📝 Введите Lua-команды (Ctrl+C для выхода)

BG3 Lua > print("Hello BG3!")
✅ Отправлено

BG3 Lua > Osi.AddGold(Osi.GetHostCharacter(), 1000)
✅ Отправлено
```
