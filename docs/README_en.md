# BG3 Remote Lua Console

**English** | [Русский](README_ru.md)

Remote Lua code execution in Baldur's Gate 3 with Script Extender (bg3se) from a terminal on Linux/macOS.

Works over the binary protobuf protocol of the Lua debugger — no VS Code and no `ncat` tunnels.

Full documentation: [English](README_en.md) · [Русский](README_ru.md)

---

## Requirements

| Side | What you need |
|---|---|
| Windows (machine with the game) | [Script Extender](https://github.com/Norbyte/bg3se) + a loaded save |
| Linux (this machine) | Python 3.8+, nothing else |

## 1. Setup on Windows

Enable the debugger. Edit `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\ScriptExtenderSettings.json`:

```json
{
  "EnableLuaDebugger": true,
  "LuaDebuggerPort": 9998
}
```

Open the port in the firewall (PowerShell as administrator):

```powershell
New-NetFirewallRule -DisplayName "BG3 Lua Debugger" `
  -Direction Inbound -Protocol TCP -LocalPort 9998 -Action Allow
```

Check that the game is listening on the port:

```powershell
netstat -an | findstr 9998
```

You should see `LISTENING`. If the port is absent, the debugger did not start: check the config and make sure the game is launched directly via `bg3_dx11.exe`, not through Steam.

> The debugger comes up **only after a save is loaded**. There will be no port in the main menu.

## 2. Connecting

```bash
# directly over the local network
python3 bg3_console.py -H 192.168.0.107 -p 9998

# via SSH tunnel (preferred: encrypted, no firewall needed)
ssh -L 9998:localhost:9998 user@192.168.0.107
python3 bg3_console.py -H 127.0.0.1 -p 9998
```

On a successful connection:

```
✓ connected to 192.168.0.107:9998 (context: Server)
· game protocol: 4
· debugger ready
enter a Lua command, :help for help, :quit to exit
```

## 3. Running commands

```bash
# single command and exit
python3 bg3_console.py -H 192.168.0.107 -e "print('Hello')"

# in the client context
python3 bg3_console.py -H 192.168.0.107 --client -e "print(1)"
```

Lua examples:

```lua
print("connectivity test")

Osi.AddGold(Osi.GetHostCharacter(), 500)

local c = Osi.GetHostCharacter()
Osi.Print(c:GetName())

DumpedStats(Selected())
```

`print()` output from the game arrives in the console — this did not work before because the script did not read responses.

## Console commands

| Command | Action |
|---|---|
| `:server` / `:client` | switch the execution context (server-side / client-side) |
| `:context` | show the current context |
| `:reset` | reset the context |
| `:break` / `:nobreak` | break on errors |
| `:reconnect` | reconnect |
| `:help`, `:quit` | help, exit |

## Diagnostics

Check what will be sent without connecting to anything:

```bash
python3 bg3_console.py -H 192.168.0.107 -e "print(1)" --hex
```

Verbose hex log of the TCP exchange:

```bash
python3 bg3_console.py -H 192.168.0.107 -v
```

Check that the port is reachable:

```bash
nc -zv 192.168.0.107 9998
```

| Symptom | Cause |
|---|---|
| `Connection refused` | debugger is not listening — no save loaded or `bg3_dx11.exe` not running |
| timeout | Windows firewall is blocking |
| `✖ send failed` | connection dropped, try `:reconnect` |

## How it works

Framing is a 4-byte little-endian length followed by protobuf. The length **includes itself**:

```
[uint32 LE = len(body) + 4][protobuf body]
```

Message schema (client → game direction):

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

Key points where implementations usually break:

- the length in the header is `len(body) + 4`, not `len(body)`;
- `evaluate` is field **7**, not 3 (field 3 is `connect`, and there `protocolVersion` expects a varint, which is why protobuf fails with `Unable to decode protobuf message from coded stream`);
- `expression` is field **2**, not 1;
- contexts are `0 = Server`, `1 = Client`, not `1` and `2`;
- the connection must be **single and persistent**, not a new one per command.

The schema was recovered from the metadata and IL of `LuaDebugger.exe` (namespace `NSE.DebuggerFrontend`).

## Debugging via VS Code

If you need a full-fledged debugger with breakpoints rather than a plain REPL, use the stock `LuaDebugger.exe` shipped with bg3se. It speaks the same protocol but communicates over DAP. Launch configs live in `.vscode/`.

## Project structure

```
bg3_console.py      # main client (protocol + REPL)
test_connection.sh  # port reachability diagnostics
.vscode/            # debug configs
```

The remaining `.md` files and `msg*.py` are early drafts and can be deleted.
