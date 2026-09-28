#!/bin/bash
# Диагностика подключения к BG3 Debugger

echo "=== BG3 Remote Debugger Connection Test ==="
echo ""

TARGET_IP="192.168.0.107"
TARGET_PORT="9998"

echo "Target: $TARGET_IP:$TARGET_PORT"
echo ""

# 1. Проверка сетевой доступности хоста
echo -n "1. Ping host: "
if ping -c 1 -W 2 $TARGET_IP > /dev/null 2>&1; then
    echo "✅ Host reachable"
else
    echo "❌ Host unreachable"
fi

# 2. Проверка порта TCP 9998
echo -n "2. Port 9998 open: "
if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$TARGET_IP/$TARGET_PORT" 2>/dev/null; then
    echo "✅ Port is open"
else
    echo "❌ Port is closed or filtered"
fi

# 3. Проверка с помощью nc
echo -n "3. Netcat test: "
if nc -zv -w 3 $TARGET_IP $TARGET_PORT 2>&1 | grep -q succeeded; then
    echo "✅ Connection succeeded"
else
    echo "❌ Connection failed"
fi

# 4. Проверка nmap (если установлен)
if command -v nmap > /dev/null 2>&1; then
    echo -n "4. Nmap scan: "
    NMAP_RESULT=$(nmap -p $TARGET_PORT $TARGET_IP 2>/dev/null | grep "^$TARGET_PORT")
    if echo "$NMAP_RESULT" | grep -q "open"; then
        echo "✅ Port detected as open"
    else
        echo "❌ Port detected as: $NMAP_RESULT"
    fi
fi

# 5. Тестовое подключение Python скриптом
echo -n "5. Python connect test: "
if python3 /home/kolya/Projects/REMCON/remote_lua_console.py -H $TARGET_IP -p $TARGET_PORT -e "print('test')" -t 2 2>&1 | grep -q "Отправлено"; then
    echo "✅ Python script connected"
else
    echo "❌ Python script failed"
fi

echo ""
echo "=== Summary ==="
echo "If all tests pass ✅ - connection is working!"
echo "If any test fails ❌ - check Windows Firewall settings"
echo ""
echo "Next steps if connection fails:"
echo "1. On Windows: Get-NetFirewallRule -DisplayName 'BG3 Lua Debugger' | Select-Object Enabled,Direction,Action"
echo "2. On Windows: Test-NetConnection -ComputerName localhost -Port 9998"
echo "3. Temporarily disable Windows Firewall to test"
