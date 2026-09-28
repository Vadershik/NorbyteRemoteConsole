# 🔧 Решение: Порт 9998 не появляется в netstat

## Проблема
- Игра запущена
- Firewall правило создано
- НО: `netstat -an | findstr 9998` не показывает порт
- **Вывод:** Отладчик Script Extender не запущен

---

## ✅ Решение: Правильная настройка Script Extender

### Шаг 1: Проверь установку Script Extender

**На Windows:**

1. Открой папку игры:
   ```
   Steam\steamapps\common\Baldurs Gate 3\bin
   ```

2. Должны быть файлы:
   - `DXGIWrapper.dll` ✅
   - `DWrite.dll` ✅  
   - `ScriptExtender.dll` ✅

3. **ВАЖНО:** Запускай игру через `bg3_dx11.exe`, а **НЕ через Steam!**

### Шаг 2: Настрой ScriptExtenderSettings.json

**Путь к файлу:**
```
%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json
```

**Содержимое (минимальное):**
```json
{
  "EnableDebugger": true,
  "DebuggerPort": 9998,
  "EnableLogging": true
}
```

**ИЛИ полное:**
```json
{
  "CreateConsole": true,
  "EnableLogging": true,
  "EnableExtensions": true,
  "EnableLuaDebugger": true,
  "LuaDebuggerPort": 9998,
  "EnableDebugger": true,
  "DebuggerPort": 9998,
  "DeveloperMode": true
}
```

### Шаг 3: Перезапусти игру ПРАВИЛЬНО

1. **Закрой игру полностью** (проверь Task Manager)
2. **Запусти через `bg3_dx11.exe`** напрямую из папки `bin`
3. **Загрузи сохранение** (отладчик активируется только после загрузки!)

### Шаг 4: Проверь логи Script Extender

**Путь к логам:**
```
%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\
```

**Должна быть строка:**
```
Lua debugger listening on port 9998
```

**Если НЕТ:**
- Проблема в конфигурации
- ИЛИ игра запущена без Script Extender


---

## 🔍 Диагностика проблем

### Проблема 1: Script Extender не загружен

**Проверка в игре:**
- Нажми `~` (тильда) — должна открыться консоль
- Если консоли нет — Script Extender не работает

**Решение:**
1. Скачай [BG3 Script Extender](https://github.com/Norbyte/bg3se/releases/latest)
2. Распакуй в `Steam\steamapps\common\Baldurs Gate 3\bin`
3. Запусти через `bg3_dx11.exe`

### Проблема 2: Конфиг не создан

**Создай файл вручную (PowerShell):**
```powershell
$config = @"
{
  "EnableDebugger": true,
  "DebuggerPort": 9998,
  "EnableLogging": true
}
"@

$path = "$env:LOCALAPPDATA\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json"
New-Item -Path $path -ItemType File -Force -Value $config

Write-Host "Config created at: $path"
```

### Проблема 3: Антивирус блокирует

**Временно отключи** Windows Defender или добавь в исключения:
```
C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\bin\DXGIWrapper.dll
```

---

## 📊 Checklist

### На Windows:
- [ ] Script Extender файлы в папке `bin`
- [ ] `ScriptExtenderSettings.json` создан
- [ ] Игра запущена через `bg3_dx11.exe` (НЕ через Steam)
- [ ] Сохранение загружено
- [ ] Консоль Script Extender (клавиша `~`) работает
- [ ] Лог содержит "Lua debugger listening on port 9998"
- [ ] `netstat -an | findstr 9998` показывает LISTENING

---

## 🎯 Быстрая проверка (PowerShell)

```powershell
# 1. Проверка конфига
Test-Path "$env:LOCALAPPDATA\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json"

# 2. Проверка процесса
Get-Process | Where-Object {$_.ProcessName -like "*bg3*"}

# 3. Проверка порта
netstat -an | findstr 9998

# 4. Проверка логов (последние 20 строк)
Get-ChildItem "$env:LOCALAPPDATA\Larian Studios\Baldur's Gate 3\ScriptExtender\Logs\" | 
  Sort-Object LastWriteTime -Descending | 
  Select-Object -First 1 | 
  Get-Content -Tail 20
```

---

## ✅ После исправления

**На Windows:**
```powershell
netstat -an | findstr 9998
# Должно показать: TCP    0.0.0.0:9998    0.0.0.0:0    LISTENING
```

**На Linux:**
```bash
cd /home/kolya/Projects/REMCON

# Тест подключения
nc -zv 192.168.0.107 9998

# Если порт открыт:
python3 remote_lua_console.py -H 192.168.0.107 -p 9998 -e "print('Отладчик работает!')"
```

---

## 💡 Важные замечания

1. **Отладчик активируется только после загрузки сохранения!** Порт не появится в главном меню.

2. **Запускай через `bg3_dx11.exe`**, а не через Steam — иначе Script Extender не загрузится.

3. **После изменения конфига всегда перезапускай игру полностью.**

4. **Проверяй логи** — там будет написано, почему отладчик не запустился.

---

## 📝 Структура правильной установки

```
Baldurs Gate 3\
├── bin\
│   ├── bg3_dx11.exe             ← ЗАПУСКАЙ ЭТОТ
│   ├── DXGIWrapper.dll          ← Script Extender
│   ├── DWrite.dll               ← Script Extender
│   └── ScriptExtender.dll       ← Script Extender

%LOCALAPPDATA%\
└── Larian Studios\
    └── Baldur's Gate 3\
        ├── ScriptExtenderSettings.json  ← Конфиг с EnableDebugger: true
        └── ScriptExtender\
            └── Logs\                     ← Проверяй логи здесь
```

---

**После правильной настройки порт 9998 появится в netstat, и подключение заработает!** 🚀

