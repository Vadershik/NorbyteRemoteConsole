# 🔥 РЕШЕНИЕ: Windows полностью недоступен из сети

## Проблема
- Отладчик работает (порт 9998 в netstat)
- НО: `ping 192.168.0.107` — 100% packet loss
- НО: `nc -zv 192.168.0.107 9998` — connection timed out
- **Вывод:** Windows Firewall блокирует ВСЕ входящие подключения

---

## ✅ БЫСТРОЕ РЕШЕНИЕ (копируй на Windows)

**PowerShell (администратор):**

```powershell
# 1. Измени сетевой профиль на Private (если Public)
$interface = (Get-NetConnectionProfile).InterfaceAlias
Set-NetConnectionProfile -InterfaceAlias $interface -NetworkCategory Private

# 2. Удали старое правило и создай новое с Profile=Any
Remove-NetFirewallRule -DisplayName "BG3 Lua Debugger" -ErrorAction SilentlyContinue

New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
                    -Direction Inbound `
                    -Protocol TCP `
                    -LocalPort 9998 `
                    -Action Allow `
                    -Profile Any `
                    -Enabled True

# 3. Разреши ping (для диагностики)
New-NetFirewallRule -DisplayName "Allow ICMPv4-In" `
                    -Direction Inbound `
                    -Protocol ICMPv4 `
                    -IcmpType 8 `
                    -Action Allow `
                    -Profile Any

# 4. Проверка
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger" | Format-List Name,Enabled,Profile
```

---

## 🔍 Диагностика: что не так с текущим правилом

**Проверь профиль:**
```powershell
Get-NetConnectionProfile
# Если NetworkCategory = Public — это проблема!
```

**Проверь правило:**
```powershell
Get-NetFirewallRule -DisplayName "BG3 Lua Debugger" | Format-List Profile
# Если Profile НЕ содержит "Any" или "Public" — правило не работает!
```

---

## ⚡ АЛЬТЕРНАТИВА: Временно отключи Firewall (для теста)

**⚠️ ТОЛЬКО ДЛЯ ДИАГНОСТИКИ!**

```powershell
# Отключить
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Тест с Linux: ping 192.168.0.107

# ОБЯЗАТЕЛЬНО включи обратно:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

**Если после отключения ping работает** — проблема в Firewall!

---

## 🎯 Проверка на Linux (после исправления)

```bash
# 1. Тест ping
ping -c 2 192.168.0.107

# 2. Тест порта
nc -zv 192.168.0.107 9998

# 3. Подключение
python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Works!')"
```

---

## 💡 Причина проблемы

Windows Firewall имеет **профили**:
- **Public** (гостевые сети) — блокирует почти всё
- **Private** (домашние сети) — более мягкие правила  
- **Domain** (корпоративные сети)

**Твоя проблема:** правило создано без `-Profile Any`, поэтому применяется только к одному профилю.

**Решение:** Используй `-Profile Any` — правило будет работать для всех профилей!

---

**После исправления ping и подключение должны работать!** 🚀
