import json
import os
import socket
import threading
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000
HISTORY_LIMIT = 100
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.jsonl")
UPDATE_DIR = os.path.join(BASE_DIR, "update")  # сюда кладём version.txt и новый client_qt.py

clients = {}                # соединение -> имя участника
lock = threading.RLock()    # защита clients и файла истории


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pack(data):
    return (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")


def send_to(conn, data):
    try:
        conn.sendall(pack(data))
    except OSError:
        pass


def broadcast(data):
    line = pack(data)
    for conn in list(clients):
        try:
            conn.sendall(line)
        except OSError:
            pass


def users_record():
    return {"type": "users", "list": sorted(n for n in clients.values() if n)}


def save(record):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        lines = f.readlines()[-HISTORY_LIMIT:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except ValueError:
            pass
    return records


def read_update():
    """Возвращает (версия, текст файла) или (None, None), если обновления нет."""
    version_path = os.path.join(UPDATE_DIR, "version.txt")
    code_path = os.path.join(UPDATE_DIR, "client_qt.py")
    if not (os.path.exists(version_path) and os.path.exists(code_path)):
        return None, None
    with open(version_path, encoding="utf-8") as f:
        version = f.read().strip()
    with open(code_path, encoding="utf-8") as f:
        code = f.read()
    return version, code


def join_chat(conn, name):
    with lock:
        clients[conn] = name
        for record in load_history():
            send_to(conn, dict(record, history=True))
        event = {"type": "system", "text": f"{name} вошёл в чат", "time": now_str()}
        save(event)
        broadcast(event)
        broadcast(users_record())


def post_message(name, text):
    text = text.strip()
    if not text:
        return
    record = {"type": "msg", "author": name, "text": text, "time": now_str()}
    with lock:
        save(record)
        broadcast(record)


def leave_chat(conn, name):
    with lock:
        clients.pop(conn, None)
        if name:
            event = {"type": "system", "text": f"{name} вышел из чата", "time": now_str()}
            save(event)
            broadcast(event)
            broadcast(users_record())


def handle(conn, addr):
    print(f"Подключился {addr}")
    buffer = b""
    name = None
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                try:
                    data = json.loads(raw.decode("utf-8"))
                except ValueError:
                    continue
                kind = data.get("type")
                if kind == "join" and name is None:
                    name = data.get("name", "").strip() or "Гость"
                    join_chat(conn, name)
                    version, _ = read_update()
                    if version:
                        send_to(conn, {"type": "update_info", "version": version})
                elif kind == "msg" and name:
                    post_message(name, data.get("text", ""))
                elif kind == "get_update":
                    version, code = read_update()
                    if code is not None:
                        send_to(conn, {"type": "update_file", "version": version, "code": code})
    except OSError:
        pass
    finally:
        leave_chat(conn, name)
        conn.close()
        print(f"Отключился {addr}")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
print(f"Сервер запущен на порту {PORT}")

while True:
    conn, addr = server.accept()
    with lock:
        clients[conn] = None
    threading.Thread(target=handle, args=(conn, addr), daemon=True).start()