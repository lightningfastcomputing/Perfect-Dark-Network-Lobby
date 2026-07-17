from __future__ import annotations

import argparse
import json
import secrets
import socket
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

STALE_AFTER_SECONDS = 45
DEFAULT_PORT = 8088
CHAT_HISTORY_LIMIT = 200
CHAT_MESSAGE_LIMIT = 300
CHAT_RATE_LIMIT_SECONDS = 0.75


def detect_lan_ip() -> str:
    """Best-effort LAN IPv4 detection without sending application data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


@dataclass
class ServerEntry:
    server_id: str
    token: str
    name: str
    host_name: str
    public_host: str
    lan_ip: str
    observed_ip: str
    port: int
    players: int
    max_players: int
    map_name: str
    mode: str
    version: str
    passworded: bool
    status: str
    updated_at: float

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("token", None)
        data["age_seconds"] = max(0, int(time.time() - self.updated_at))
        return data


@dataclass
class ChatMessage:
    message_id: int
    player: str
    text: str
    created_at: float

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChatStore:
    def __init__(self) -> None:
        self._messages: list[ChatMessage] = []
        self._next_id = 1
        self._last_post_by_ip: dict[str, float] = {}
        self._lock = threading.RLock()

    def list_after(self, after_id: int) -> list[dict[str, Any]]:
        with self._lock:
            return [message.public_dict() for message in self._messages if message.message_id > after_id]

    def post(self, player: str, text: str, source_ip: str) -> ChatMessage:
        now = time.time()
        clean_player = " ".join(player.replace("\r", " ").replace("\n", " ").split())[:32] or "Player"
        clean_text = " ".join(text.replace("\r", " ").replace("\n", " ").split())[:CHAT_MESSAGE_LIMIT]
        if not clean_text:
            raise ValueError("Message is empty")
        with self._lock:
            last = self._last_post_by_ip.get(source_ip, 0.0)
            if now - last < CHAT_RATE_LIMIT_SECONDS:
                raise RuntimeError("Please wait before sending another message")
            self._last_post_by_ip[source_ip] = now
            message = ChatMessage(self._next_id, clean_player, clean_text, now)
            self._next_id += 1
            self._messages.append(message)
            if len(self._messages) > CHAT_HISTORY_LIMIT:
                self._messages = self._messages[-CHAT_HISTORY_LIMIT:]
            return message


class Registry:
    def __init__(self) -> None:
        self._servers: dict[str, ServerEntry] = {}
        self._lock = threading.RLock()

    def cleanup(self) -> None:
        cutoff = time.time() - STALE_AFTER_SECONDS
        with self._lock:
            dead = [sid for sid, entry in self._servers.items() if entry.updated_at < cutoff]
            for sid in dead:
                self._servers.pop(sid, None)

    def list_public(self) -> list[dict[str, Any]]:
        self.cleanup()
        with self._lock:
            return [entry.public_dict() for entry in sorted(self._servers.values(), key=lambda e: e.updated_at, reverse=True)]

    def register(self, payload: dict[str, Any], source_ip: str) -> ServerEntry:
        server_id = secrets.token_urlsafe(10)
        token = secrets.token_urlsafe(24)
        requested_host = _normalize_host(str(payload.get("advertised_ip", "")).strip())
        public_host = requested_host if _valid_host(requested_host) else source_ip

        requested_lan = _normalize_host(str(payload.get("lan_ip", "")).strip())
        lan_ip = requested_lan if _valid_ipv4(requested_lan) else ""

        entry = ServerEntry(
            server_id=server_id,
            token=token,
            name=str(payload.get("name", "Perfect Dark Server"))[:64],
            host_name=str(payload.get("host_name", "Host"))[:32],
            public_host=public_host,
            lan_ip=lan_ip,
            observed_ip=source_ip,
            port=_bounded_int(payload.get("port"), 1, 65535, 27100),
            players=_bounded_int(payload.get("players"), 0, 32, 1),
            max_players=_bounded_int(payload.get("max_players"), 1, 32, 8),
            map_name=str(payload.get("map_name", "Unknown"))[:48],
            mode=str(payload.get("mode", "Combat Simulator"))[:48],
            version=str(payload.get("version", "prototype-1"))[:32],
            passworded=bool(payload.get("passworded", False)),
            status=str(payload.get("status", "Lobby"))[:24],
            updated_at=time.time(),
        )
        with self._lock:
            self._servers[server_id] = entry
        return entry

    def heartbeat(self, server_id: str, token: str, payload: dict[str, Any]) -> ServerEntry | None:
        with self._lock:
            entry = self._servers.get(server_id)
            if not entry or not secrets.compare_digest(entry.token, token):
                return None
            entry.players = _bounded_int(payload.get("players"), 0, entry.max_players, entry.players)
            entry.status = str(payload.get("status", entry.status))[:24]
            entry.map_name = str(payload.get("map_name", entry.map_name))[:48]
            entry.mode = str(payload.get("mode", entry.mode))[:48]
            entry.updated_at = time.time()
            return entry

    def unregister(self, server_id: str, token: str) -> bool:
        with self._lock:
            entry = self._servers.get(server_id)
            if not entry or not secrets.compare_digest(entry.token, token):
                return False
            self._servers.pop(server_id, None)
            return True


def _normalize_host(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    try:
        parsed = urlparse(value if "://" in value else f"//{value}")
        host = parsed.hostname
        if host:
            return host.strip().rstrip(".")
    except ValueError:
        pass

    return value.rstrip(".")


def _valid_host(value: str) -> bool:
    if _valid_ipv4(value):
        return True
    if not value or len(value) > 253:
        return False

    labels = value.rstrip(".").split(".")
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(char.isalnum() or char == "-" for char in label):
            return False
    return True


def _valid_ipv4(value: str) -> bool:
    try:
        socket.inet_aton(value)
        return value.count(".") == 3 and value != "0.0.0.0"
    except OSError:
        return False


def _bounded_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


REGISTRY = Registry()
CHAT = ChatStore()


class Handler(BaseHTTPRequestHandler):
    server_version = "ThorfectDarkMaster/1.0.3"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 64 * 1024:
            raise ValueError("Request too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
        return data

    def _send(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send(HTTPStatus.OK, {"ok": True, "service": "Thorfect Dark Master"})
        elif path == "/servers":
            self._send(HTTPStatus.OK, {
                "servers": REGISTRY.list_public(),
                "stale_after": STALE_AFTER_SECONDS,
                "requester_ip": self._client_ip(),
            })
        elif path == "/chat":
            query = parse_qs(urlparse(self.path).query)
            try:
                after_id = max(0, int(query.get("after", ["0"])[0]))
            except ValueError:
                after_id = 0
            self._send(HTTPStatus.OK, {"messages": CHAT.list_after(after_id)})
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._json_body()
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "detail": str(exc)})
            return

        if path == "/chat/send":
            try:
                message = CHAT.post(str(payload.get("player", "Player")), str(payload.get("text", "")), self._client_ip())
            except ValueError as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_message", "detail": str(exc)})
            except RuntimeError as exc:
                self._send(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited", "detail": str(exc)})
            else:
                self._send(HTTPStatus.CREATED, {"ok": True, "message": message.public_dict()})
            return

        if path == "/servers/register":
            entry = REGISTRY.register(payload, self._client_ip())
            self._send(HTTPStatus.CREATED, {
                "server": entry.public_dict(),
                "server_id": entry.server_id,
                "token": entry.token,
                "heartbeat_seconds": 15,
            })
            return

        if path == "/servers/heartbeat":
            entry = REGISTRY.heartbeat(str(payload.get("server_id", "")), str(payload.get("token", "")), payload)
            if not entry:
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "invalid_session"})
            else:
                self._send(HTTPStatus.OK, {"ok": True, "server": entry.public_dict()})
            return

        if path == "/servers/unregister":
            ok = REGISTRY.unregister(str(payload.get("server_id", "")), str(payload.get("token", "")))
            self._send(HTTPStatus.OK if ok else HTTPStatus.UNAUTHORIZED, {"ok": ok})
            return

        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def run_cli(host: str, port: int) -> int:
    server = ReusableThreadingHTTPServer((host, port), Handler)
    lan_ip = detect_lan_ip()
    print(f"Perfect Thork master listening on all interfaces: {host}:{port}")
    print(f"Use this on the master PC: http://127.0.0.1:{port}")
    print(f"Use this on other LAN PCs: http://{lan_ip}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def run_gui() -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    class MasterGUI(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Thorfect Dark Master")
            self.geometry("590x310")
            self.resizable(False, False)
            self.server: ReusableThreadingHTTPServer | None = None
            self.server_thread: threading.Thread | None = None
            self.lan_ip = tk.StringVar(value=detect_lan_ip())
            self.bind_ip = tk.StringVar(value="0.0.0.0")
            self.port = tk.StringVar(value=str(DEFAULT_PORT))
            self.status = tk.StringVar(value="Stopped")
            self.protocol("WM_DELETE_WINDOW", self.close)
            self._build()

        def _build(self) -> None:
            frame = ttk.Frame(self, padding=16)
            frame.pack(fill="both", expand=True)
            frame.columnconfigure(1, weight=1)

            ttk.Label(frame, text="Thorfect Dark Master", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
            ttk.Label(frame, text="Public server-list registry").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 16))

            ttk.Label(frame, text="Detected LAN IP:").grid(row=2, column=0, sticky="w", pady=5)
            ttk.Entry(frame, textvariable=self.lan_ip, state="readonly").grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 0))

            ttk.Label(frame, text="Bind address:").grid(row=3, column=0, sticky="w", pady=5)
            ttk.Entry(frame, textvariable=self.bind_ip).grid(row=3, column=1, sticky="ew", padx=(8, 8))
            ttk.Label(frame, text="Use 0.0.0.0").grid(row=3, column=2, sticky="w")

            ttk.Label(frame, text="TCP port:").grid(row=4, column=0, sticky="w", pady=5)
            ttk.Entry(frame, textvariable=self.port, width=10).grid(row=4, column=1, sticky="w", padx=(8, 0))

            buttons = ttk.Frame(frame)
            buttons.grid(row=5, column=0, columnspan=3, sticky="w", pady=(16, 10))
            self.start_button = ttk.Button(buttons, text="START MASTER", command=self.start)
            self.start_button.pack(side="left", padx=(0, 8), ipady=5)
            self.stop_button = ttk.Button(buttons, text="STOP MASTER", command=self.stop, state="disabled")
            self.stop_button.pack(side="left", ipady=5)

            ttk.Label(frame, text="Local browser URL:").grid(row=6, column=0, sticky="w")
            self.local_url = ttk.Label(frame, text=f"http://127.0.0.1:{DEFAULT_PORT}")
            self.local_url.grid(row=6, column=1, columnspan=2, sticky="w", padx=(8, 0))
            ttk.Label(frame, text="Other LAN PCs:").grid(row=7, column=0, sticky="w")
            self.lan_url = ttk.Label(frame, text=f"http://{self.lan_ip.get()}:{DEFAULT_PORT}")
            self.lan_url.grid(row=7, column=1, columnspan=2, sticky="w", padx=(8, 0))

            ttk.Label(frame, textvariable=self.status, relief="sunken", anchor="w").grid(row=8, column=0, columnspan=3, sticky="ew", pady=(16, 0))

        def start(self) -> None:
            try:
                port = int(self.port.get())
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Thorfect Dark Master", "Enter a valid TCP port from 1 to 65535.")
                return
            bind_ip = self.bind_ip.get().strip() or "0.0.0.0"
            try:
                self.server = ReusableThreadingHTTPServer((bind_ip, port), Handler)
            except OSError as exc:
                messagebox.showerror("Thorfect Dark Master", f"Could not start the master:\n{exc}")
                self.server = None
                return
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.local_url.configure(text=f"http://127.0.0.1:{port}")
            self.lan_url.configure(text=f"http://{self.lan_ip.get()}:{port}")
            self.status.set(f"Running on {bind_ip}:{port} — give LAN clients http://{self.lan_ip.get()}:{port}")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")

        def stop(self) -> None:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            self.status.set("Stopped")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

        def close(self) -> None:
            self.stop()
            self.destroy()

    MasterGUI().mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Thorfect Dark master-server")
    parser.add_argument("--host", default=None, help="Run without GUI and bind to this address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--gui", action="store_true", help="Force the GUI")
    args = parser.parse_args()
    if args.gui or args.host is None:
        return run_gui()
    return run_cli(args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
