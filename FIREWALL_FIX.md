# 🔥 Решение проблемы: Firewall правило создано, но порт закрыт

## Проблема
- Firewall правило добавлено: `New-NetFirewallRule -DisplayName "BG3 Lua Debugger" ...`
- Порт LISTENING виден в netstat: `TCP 0.0.0.0:9998 LISTENING`
- НО подключение с Linux не работает

---

## 🔍 Причина

Windows Firewall имеет **профили** (Domain, Private, Public), и правило может быть не применено ко всем профилям.

---

## ✅ Решение 1: Правильное создание правила (применить ко всем профилям)

**На Windows PowerShell (администратор):**

```powershell
# Удали старое правило
Remove-NetFirewallRule -DisplayName "BG3 Lua Debugger" -ErrorAction SilentlyContinue

# Создай новое правило для ВСЕХ профилей
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow `
                    -Profile Any `
                    -Enabled True

# Проверь правило
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger" | Format-List Name,Enabled,Direction,Action,Profile
```

**Должно быть:**
```
Name      : BG3 Lua Debugger
Enabled   : True
Direction : Inbound
Action    : Allow
Profile   : Domain, Private, Public  ← ВАЖНО: все три профиля!
```

---

## ✅ Решение 2: Проверка текущего сетевого профиля

**На Windows PowerShell:**

```powershell
# Узнай активный сетевой профиль
Get-NetConnectionProfile

# Вывод покажет:
# NetworkCategory: Public / Private / Domain
```

Если профиль **Public**, а правило создано только для **Private** — подключение не работает!

**Исправление:**
```powershell
# Измени существующее правило
Set-NetFirewallRule -DisplayName "BG3 Lua Debugger" -Profile Any
```

---

## ✅ Решение 3: Проверка, что правило действительно активно

**На Windows PowerShell:**

```powershell
# Полная информация о правиле
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger" | Get-NetFirewallPortFilter

# Должно показать:
# Protocol  : TCP
# LocalPort : 9998
```

**Проверка применения правила:**
```powershell
# Тест локального подключения
Test-NetConnection -ComputerName localhost -Port 9998

# Ожидаемый результат:
# TcpTestSucceeded : True
```

---

## ✅ Решение 4: Временно отключить Firewall (для теста)

**ТОЛЬКО ДЛЯ ДИАГНОСТИКИ!**

```powershell
# Отключить Firewall (временно)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Теперь попробуй подключиться с Linux
# Если работает - проблема в правиле Firewall

# ОБЯЗАТЕЛЬНО включи обратно:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

---

## ✅ Решение 5: Создать правило через GUI (альтернатива)

1. **Windows Defender Firewall with Advanced Security**
2. **Inbound Rules** → **New Rule**
3. **Rule Type:** Port
4. **Protocol:** TCP, Port: 9998
5. **Action:** Allow the connection
6. **Profile:** ✅ Domain, ✅ Private, ✅ Public (все три!)
7. **Name:** BG3 Lua Debugger

---

## 🔍 Диагностика с Linux

**На Linux запусти тест:**

```bash
cd /home/kolya/Projects/REMCON
bash test_connection.sh
```

**ИЛИ вручную:**

```bash
# 1. Ping хоста
ping -c 1 192.168.0.107

# 2. Проверка порта
nc -zv 192.168.0.107 9998

# 3. Проверка с таймаутом
timeout 3 bash -c 'cat < /dev/null > /dev/tcp/192.168.0.107/9998' && echo "✅ Open" || echo "❌ Closed"

# 4. Nmap (если установлен)
nmap -p 9998 192.168.0.107
```

---

## 🎯 Рекомендуемый порядок действий

### На Windows:

```powershell
# 1. Удали старое правило
Remove-NetFirewallRule -DisplayName "BG3 Lua Debugger" -ErrorAction SilentlyContinue

# 2. Создай правильное правило
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow `
                    -Profile Any `
                    -Enabled True

# 3. Проверь правило
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger" | Format-List Name,Enabled,Profile

# 4. Проверь, что порт слушается
netstat -an | findstr 9998

# 5. Тест локального подключения
Test-NetConnection -ComputerName localhost -Port 9998
```

### На Linux:

```bash
# 6. Тест подключения
nc -zv 192.168.0.107 9998

# 7. Попробуй подключиться
python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Test')"
```

---

## 📊 Таблица диагностики

| Симптом | Причина | Решение |
|---------|---------|---------|
| `netstat` показывает LISTENING, но `nc` с Linux не работает | Firewall блокирует | Добавь `-Profile Any` |
| Правило создано, но не работает | Неправильный профиль | `Set-NetFirewallRule ... -Profile Any` |
| Работает локально, но не снаружи | Профиль Public не включён | Пересоздай правило с `-Profile Any` |
| `Test-NetConnection` не работает | Игра не запущена | Запусти BG3 с Script Extender |

---

## 💡 Дополнительная проверка (Windows)

```powershell
# Показать все правила для порта 9998
Get-NetFirewallPortFilter | Where-Object LocalPort -eq 9998 | Get-NetFirewallRule

# Показать активный профиль Firewall
Get-NetFirewallProfile | Format-Table Name,Enabled

# Логи Firewall (если включены)
Get-WinEvent -LogName "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall" -MaxEvents 50 | Where-Object {$_.Message -like "*9998*"}
```

---

## ✅ Финальная проверка

После применения **Решения 1**, выполни полный тест:

```bash
# На Linux
cd /home/kolya/Projects/REMCON
python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Firewall fixed!')"

# Ожидаемый результат:
# 📤 Отправка: print('Firewall fixed!')
# ✅ Отправлено
```

---

**Скорее всего проблема в `-Profile` — добавь `-Profile Any` при создании правила!** 🔥
