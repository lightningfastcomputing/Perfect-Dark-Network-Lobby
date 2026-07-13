from __future__ import annotations

import json
import queue
import socket
import subprocess
import sys
import threading
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

APP_TITLE = "Perfect Dark Pre-Lobby"
DEFAULT_PORT = "27100"
DEFAULT_MAX_CLIENTS = "8"
DEFAULT_NAME = "Player"


def get_launcher_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_launcher_dir()
GAME_EXE = BASE_DIR / "pd.x86_64.exe"
CONFIG_FILE = BASE_DIR / "pd_lobby_settings.json"


def detect_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def load_settings() -> dict[str, str]:
    defaults = {
        # Always begin with a blank server field. A client must enter the
        # host address explicitly; a host can use the LAN-IP button.
        "server_ip": "",
        "port": DEFAULT_PORT,
        "max_clients": DEFAULT_MAX_CLIENTS,
        "player_name": DEFAULT_NAME,
    }
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            # Deliberately do not restore server_ip. Restoring a prior or
            # locally detected address can make a client connect to itself.
            for key in ("port", "max_clients", "player_name"):
                value = loaded.get(key)
                if isinstance(value, (str, int)):
                    defaults[key] = str(value)
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def save_settings(server_ip: str, port: str, max_clients: str, player_name: str) -> None:
    payload = {
        # Never persist the host/server address. It starts blank each run.
        "port": port,
        "max_clients": max_clients,
        "player_name": player_name,
    }
    try:
        CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


class ChatServer:
    def __init__(self, host: str, port: int, events: queue.Queue) -> None:
        self.host = host
        self.port = port
        self.events = events
        self.server_socket: socket.socket | None = None
        self.clients: dict[socket.socket, str] = {}
        self.lock = threading.Lock()
        self.running = threading.Event()

    def start(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(16)
        self.server_socket.settimeout(0.5)
        self.running.set()
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self) -> None:
        assert self.server_socket is not None
        while self.running.is_set():
            try:
                client, _address = self.server_socket.accept()
                client.settimeout(0.5)
                threading.Thread(target=self._client_loop, args=(client,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _client_loop(self, client: socket.socket) -> None:
        buffer = b""
        name = "Player"
        try:
            while self.running.is_set():
                try:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not line:
                            continue
                        message = json.loads(line.decode("utf-8"))
                        kind = message.get("type")
                        if kind == "hello":
                            requested = str(message.get("name", "Player")).strip()[:24] or "Player"
                            name = self._unique_name(requested)
                            with self.lock:
                                self.clients[client] = name
                            self._broadcast({"type": "system", "text": f"{name} joined the pre-lobby."})
                            self._broadcast_players()
                        elif kind == "chat" and client in self.clients:
                            text = str(message.get("text", "")).strip()[:500]
                            if text:
                                self._broadcast({"type": "chat", "name": name, "text": text})
                except socket.timeout:
                    continue
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        finally:
            with self.lock:
                departed = self.clients.pop(client, None)
            try:
                client.close()
            except OSError:
                pass
            if departed:
                self._broadcast({"type": "system", "text": f"{departed} left the pre-lobby."})
                self._broadcast_players()

    def _unique_name(self, requested: str) -> str:
        with self.lock:
            existing = set(self.clients.values())
        if requested not in existing:
            return requested
        number = 2
        while f"{requested} {number}" in existing:
            number += 1
        return f"{requested} {number}"

    def _broadcast_players(self) -> None:
        with self.lock:
            players = list(self.clients.values())
        self._broadcast({"type": "players", "players": players})

    def _broadcast(self, message: dict) -> None:
        encoded = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        dead: list[socket.socket] = []
        with self.lock:
            clients = list(self.clients)
        for client in clients:
            try:
                client.sendall(encoded)
            except OSError:
                dead.append(client)
        for client in dead:
            try:
                client.close()
            except OSError:
                pass

    def stop(self) -> None:
        self.running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        with self.lock:
            clients = list(self.clients)
            self.clients.clear()
        for client in clients:
            try:
                client.close()
            except OSError:
                pass


class ChatClient:
    def __init__(self, host: str, port: int, name: str, events: queue.Queue) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.events = events
        self.sock: socket.socket | None = None
        self.running = threading.Event()
        self.send_lock = threading.Lock()

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=5)
        sock.settimeout(0.5)
        self.sock = sock
        self.running.set()
        self._send({"type": "hello", "name": self.name})
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self) -> None:
        assert self.sock is not None
        buffer = b""
        try:
            while self.running.is_set():
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("Server closed the connection")
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if line:
                            self.events.put(("message", json.loads(line.decode("utf-8"))))
                except socket.timeout:
                    continue
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError, ConnectionError) as exc:
            if self.running.is_set():
                self.events.put(("disconnected", str(exc)))
        finally:
            self.running.clear()
            try:
                self.sock.close()
            except (OSError, AttributeError):
                pass

    def _send(self, message: dict) -> None:
        if not self.sock:
            raise ConnectionError("Not connected")
        encoded = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        with self.send_lock:
            self.sock.sendall(encoded)

    def send_chat(self, text: str) -> None:
        self._send({"type": "chat", "text": text})

    def close(self) -> None:
        self.running.clear()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass


class LobbyLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x590")
        self.minsize(680, 540)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        settings = load_settings()
        self.server_ip = tk.StringVar(value=settings["server_ip"])
        self.port = tk.StringVar(value=settings["port"])
        self.max_clients = tk.StringVar(value=settings["max_clients"])
        self.player_name = tk.StringVar(value=settings["player_name"])
        self.status = tk.StringVar(value="Not connected to a pre-lobby")
        self.events: queue.Queue = queue.Queue()
        self.chat_server: ChatServer | None = None
        self.chat_client: ChatClient | None = None
        self.mode: str | None = None

        self._build_ui()
        self.after(100, self._poll_events)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Perfect Dark", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(outer, text="Pre-Lobby Chat + Native Direct Game Lobby").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))

        ttk.Label(outer, text="Player name:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.player_name, width=20).grid(row=2, column=1, sticky="ew", padx=(8, 10), pady=4)
        ttk.Label(outer, text="Host / Server IP:").grid(row=2, column=2, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.server_ip, width=20).grid(row=2, column=3, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(outer, text="Game port:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.port, width=10).grid(row=3, column=1, sticky="w", padx=(8, 10), pady=4)
        ttk.Label(outer, text="Maximum clients:").grid(row=3, column=2, sticky="w", pady=4)
        ttk.Spinbox(outer, from_=1, to=32, textvariable=self.max_clients, width=8).grid(row=3, column=3, sticky="w", padx=(8, 0), pady=4)

        ttk.Button(outer, text="Use My LAN IP", command=self.use_local_ip).grid(row=4, column=0, sticky="ew", pady=(6, 10), padx=(0, 5))
        ttk.Button(outer, text="Allow Chat Port Through Firewall", command=self.allow_chat_firewall).grid(row=4, column=1, columnspan=2, sticky="ew", pady=(6, 10), padx=5)
        ttk.Button(outer, text="Disconnect Pre-Lobby", command=self.disconnect_chat).grid(row=4, column=3, sticky="ew", pady=(6, 10), padx=(5, 0))

        connect_frame = ttk.LabelFrame(outer, text="1. Enter Pre-Lobby", padding=8)
        connect_frame.grid(row=5, column=0, columnspan=4, sticky="ew")
        self.host_chat_button = ttk.Button(connect_frame, text="HOST PRE-LOBBY", command=self.host_pre_lobby)
        self.host_chat_button.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=5)
        self.join_chat_button = ttk.Button(connect_frame, text="JOIN PRE-LOBBY", command=self.join_pre_lobby)
        self.join_chat_button.pack(side="left", fill="x", expand=True, padx=(4, 0), ipady=5)

        chat_frame = ttk.LabelFrame(outer, text="Players and Chat", padding=8)
        chat_frame.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=10)
        self.chat_text = ScrolledText(chat_frame, height=14, wrap="word", state="disabled", font=("Segoe UI", 10))
        self.chat_text.grid(row=0, column=0, sticky="nsew")
        self.player_list = tk.Listbox(chat_frame, width=22, height=14)
        self.player_list.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.message_entry = ttk.Entry(chat_frame)
        self.message_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        ttk.Button(chat_frame, text="Send", command=self.send_message).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        launch_frame = ttk.LabelFrame(outer, text="2. Launch the Proven In-Game Lobby", padding=8)
        launch_frame.grid(row=7, column=0, columnspan=4, sticky="ew")
        ttk.Button(launch_frame, text="LAUNCH AS HOST", command=self.launch_as_host).pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=6)
        ttk.Button(launch_frame, text="LAUNCH AS CLIENT", command=self.launch_as_client).pack(side="left", fill="x", expand=True, padx=(4, 0), ipady=6)

        ttk.Label(outer, text="Pre-lobby chat uses TCP on the selected game port and closes before Perfect Dark launches.", anchor="w").grid(row=8, column=0, columnspan=4, sticky="ew", pady=(8, 4))
        ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w").grid(row=9, column=0, columnspan=4, sticky="ew")

        outer.rowconfigure(6, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(3, weight=1)

    def use_local_ip(self) -> None:
        address = detect_local_ip()
        self.server_ip.set(address)
        self.status.set(f"Detected LAN IP: {address}")

    def allow_chat_firewall(self) -> None:
        values = self.validate_values(require_ip=False)
        if values is None:
            return
        _address, game_port, _max_clients, _name = values
        chat_port = game_port
        rule_name = f"Perfect Dark Pre-Lobby TCP {chat_port}"
        args = (
            'advfirewall firewall add rule '
            f'name="{rule_name}" dir=in action=allow protocol=TCP '
            f'localport={chat_port} profile=any enable=yes'
        )
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "netsh.exe", args, str(BASE_DIR), 1
            )
        except (AttributeError, OSError) as exc:
            messagebox.showerror(APP_TITLE, f"Could not request the firewall rule:\n{exc}")
            return
        if result <= 32:
            messagebox.showerror(
                APP_TITLE,
                f"Windows did not add the firewall rule (ShellExecute result {result}).",
            )
            return
        self.status.set(f"Requested Windows Firewall access for TCP {chat_port}")
        messagebox.showinfo(
            APP_TITLE,
            f"Approve the Windows administrator prompt.\n\n"
            f"This opens inbound TCP {chat_port} for the pre-lobby chat.\n"
            "After approval, host the pre-lobby again.",
        )

    def validate_values(self, require_ip: bool = True) -> tuple[str, int, int, str] | None:
        address = self.server_ip.get().strip()
        name = self.player_name.get().strip()[:24]
        if require_ip and not address:
            messagebox.showerror(APP_TITLE, "Enter the host/server IP address.")
            return None
        if not name:
            messagebox.showerror(APP_TITLE, "Enter a player name.")
            return None
        try:
            port = int(self.port.get().strip())
            if not 1 <= port <= 65534:
                raise ValueError
            max_clients = int(self.max_clients.get().strip())
            if not 1 <= max_clients <= 32:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_TITLE, "Use a game port from 1-65534 and maximum clients from 1-32.")
            return None
        return address, port, max_clients, name

    def host_pre_lobby(self) -> None:
        values = self.validate_values(require_ip=True)
        if values is None:
            return
        address, game_port, max_clients, name = values
        self.disconnect_chat(silent=True)
        chat_port = game_port
        try:
            self.chat_server = ChatServer(address, chat_port, self.events)
            self.chat_server.start()
            self.chat_client = ChatClient(address, chat_port, name, self.events)
            self.chat_client.connect()
        except OSError as exc:
            self.disconnect_chat(silent=True)
            messagebox.showerror(APP_TITLE, f"Could not host pre-lobby on TCP port {chat_port}:\n{exc}")
            return
        self.mode = "host"
        save_settings(address, str(game_port), str(max_clients), name)
        self.status.set(f"Hosting pre-lobby at {address}:{chat_port}")
        self._append_chat(f"[System] Pre-lobby server started on TCP {chat_port}.\n")
        self.message_entry.focus_set()

    def join_pre_lobby(self) -> None:
        values = self.validate_values(require_ip=True)
        if values is None:
            return
        address, game_port, max_clients, name = values
        self.disconnect_chat(silent=True)
        chat_port = game_port
        try:
            self.chat_client = ChatClient(address, chat_port, name, self.events)
            self.chat_client.connect()
        except OSError as exc:
            self.disconnect_chat(silent=True)
            messagebox.showerror(
                APP_TITLE,
                f"Could not join pre-lobby at {address}:{chat_port}:\n{exc}\n\n"
                "Verify the host used Use My LAN IP, both PCs are on the same LAN, and the host is still showing Hosting pre-lobby.",
            )
            return
        self.mode = "client"
        save_settings(address, str(game_port), str(max_clients), name)
        self.status.set(f"Connected to pre-lobby at {address}:{chat_port}")
        self.message_entry.focus_set()

    def disconnect_chat(self, silent: bool = False) -> None:
        if self.chat_client:
            self.chat_client.close()
            self.chat_client = None
        if self.chat_server:
            self.chat_server.stop()
            self.chat_server = None
        self.mode = None
        self.player_list.delete(0, tk.END)
        if not silent:
            self.status.set("Disconnected from pre-lobby")
            self._append_chat("[System] Disconnected from pre-lobby.\n")

    def send_message(self) -> None:
        text = self.message_entry.get().strip()
        if not text:
            return
        if not self.chat_client or not self.chat_client.running.is_set():
            messagebox.showinfo(APP_TITLE, "Host or join the pre-lobby before sending chat messages.")
            return
        try:
            self.chat_client.send_chat(text)
            self.message_entry.delete(0, tk.END)
        except OSError as exc:
            self.status.set(f"Chat send failed: {exc}")

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "message":
                    kind = payload.get("type")
                    if kind == "chat":
                        self._append_chat(f"{payload.get('name', 'Player')}: {payload.get('text', '')}\n")
                    elif kind == "system":
                        self._append_chat(f"[System] {payload.get('text', '')}\n")
                    elif kind == "players":
                        self.player_list.delete(0, tk.END)
                        for player in payload.get("players", []):
                            self.player_list.insert(tk.END, player)
                elif event == "disconnected":
                    self.status.set("Pre-lobby connection lost")
                    self._append_chat(f"[System] Connection lost: {payload}\n")
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _append_chat(self, text: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, text)
        self.chat_text.see(tk.END)
        self.chat_text.configure(state="disabled")

    def launch_game(self, arguments: list[str], status_text: str) -> None:
        # The chat listener uses TCP on the selected game port. Close it first
        # so the game receives a completely clean launch environment.
        self.disconnect_chat(silent=True)
        if not GAME_EXE.is_file():
            messagebox.showerror(APP_TITLE, f"Game executable not found in the launcher folder:\n{GAME_EXE}")
            return
        try:
            subprocess.Popen(
                [str(GAME_EXE), *arguments],
                cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch Perfect Dark:\n{exc}")
            self.status.set("Game launch failed")
            return
        self.status.set(status_text)

    def launch_as_host(self) -> None:
        values = self.validate_values(require_ip=False)
        if values is None:
            return
        address, port, max_clients, name = values
        save_settings(address, str(port), str(max_clients), name)
        self.launch_game(
            ["--portable", "--skip-intro", "--host", "--port", str(port), "--maxclients", str(max_clients)],
            f"Perfect Dark host lobby launched on port {port}",
        )

    def launch_as_client(self) -> None:
        values = self.validate_values(require_ip=True)
        if values is None:
            return
        address, port, max_clients, name = values
        connect_address = address if ":" in address else f"{address}:{port}"
        save_settings(address, str(port), str(max_clients), name)
        self.launch_game(
            ["--portable", "--skip-intro", "--connect", connect_address],
            f"Perfect Dark client lobby launched for {connect_address}",
        )

    def on_close(self) -> None:
        save_settings(
            self.server_ip.get().strip(),
            self.port.get().strip() or DEFAULT_PORT,
            self.max_clients.get().strip() or DEFAULT_MAX_CLIENTS,
            self.player_name.get().strip() or DEFAULT_NAME,
        )
        self.disconnect_chat(silent=True)
        self.destroy()


def main() -> int:
    if sys.version_info < (3, 8):
        print("Python 3.8 or newer is required.")
        return 1
    app = LobbyLauncher()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
