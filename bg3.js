const net = require('net');
const readline = require('readline');

const HOST = '192.168.31.95'; // IP вашего Windows-ПК
const PORT = 9999;

const client = new net.Socket();
let seq = 1;

function sendDAP(payload) {
    payload.seq = seq++;
    const body = JSON.stringify(payload);
    const header = `Content-Length: ${Buffer.byteLength(body, 'utf8')}\r\n\r\n`;
    client.write(header + body);
}

client.connect(PORT, HOST, () => {
    console.log(`[+] Подключено к Windows-адаптеру! Инициализация DAP...`);
    // Шаг 1: Инициализация
    sendDAP({ type: "request", command: "initialize", arguments: { clientID: "vscode", adapterID: "bg3-lua" } });
});

client.on('data', (data) => {
    const str = data.toString();
    // Если адаптер ответил на initialize, шлем launch
    if (str.includes('"command":"initialize"')) {
        sendDAP({ type: "request", command: "launch", arguments: { noDebug: false } });
    }
    // Если сессия готова, открываем ввод
    if (str.includes('"command":"launch"') || str.includes('"event":"initialized"')) {
        console.log(`\n[УСПЕХ] Консоль готова! Вводите Lua-команды (например: print("Привет") )`);
        rl.prompt();
    }
    if (str.includes('"command":"evaluate"')) {
        try {
            const res = JSON.parse(str.split('\r\n\r\n')[1]);
            console.log(`-> Ответ игры: ${res.body.result}`);
        } catch(e) {}
        rl.prompt();
    }
});

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
rl.setPrompt('BG3 Lua > ');

rl.on('line', (line) => {
    if (!line.trim()) { rl.prompt(); return; }
    // Шаг 2: Отправка Lua-команды в формате DAP Evaluate
    sendDAP({
        type: "request",
        command: "evaluate",
        arguments: { expression: line, context: "repl" }
    });
});

client.on('error', (err) => console.log(`[-] Ошибка: ${err.message}`));
client.on('close', () => console.log('[-] Соединение закрыто.'));
