from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_TITLE = "Perfect Thork"
DEFAULT_MASTER = "http://127.0.0.1:8088"
DEFAULT_PORT = 27100
HEARTBEAT_SECONDS = 15
CHAT_POLL_MS = 2000


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = base_dir()
GAME_EXE = BASE_DIR / "pd.x86_64.exe"
CONFIG_FILE = BASE_DIR / "perfect_thork_settings.json"


def detect_lan_ip() -> str:
    """Best-effort LAN IPv4 detection for server advertisements."""
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


def api(master: str, path: str, payload: dict | None = None, timeout: float = 5.0) -> dict:
    url = master.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("Master returned invalid JSON")
        return body


def load_settings() -> dict:
    defaults = {"master": DEFAULT_MASTER, "player": "Player", "server_name": "Perfect Dark Match", "port": DEFAULT_PORT, "advertised_ip": detect_lan_ip()}
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            defaults.update({k: loaded[k] for k in defaults if k in loaded})
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def save_settings(values: dict) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps(values, indent=2), encoding="utf-8")
    except OSError:
        pass


class PerfectThork(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        settings = load_settings()
        self.title(APP_TITLE)
        self.geometry("920x700")
        self.minsize(800, 600)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.master_url = tk.StringVar(value=str(settings["master"]))
        self.player = tk.StringVar(value=str(settings["player"]))
        self.server_name = tk.StringVar(value=str(settings["server_name"]))
        self.port = tk.StringVar(value=str(settings["port"]))
        self.advertised_ip = tk.StringVar(value=str(settings.get("advertised_ip", detect_lan_ip())))
        self.status = tk.StringVar(value="Ready")
        self.host_session: dict | None = None
        self.host_stop = threading.Event()
        self.server_rows: dict[str, dict] = {}
        self.last_chat_id = 0
        self.chat_polling = False

        self._build()
        self.after(200, self.refresh)
        self.after(350, self.start_chat_polling)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(3, weight=1)
        outer.rowconfigure(4, weight=1)

        ttk.Label(outer, text="Perfect Thork", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(outer, text="Perfect Dark public server browser prototype").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Master URL:").grid(row=2, column=0, sticky="w")
        ttk.Entry(outer, textvariable=self.master_url).grid(row=2, column=1, sticky="ew", padx=(6, 12))
        ttk.Label(outer, text="Player:").grid(row=2, column=2, sticky="w")
        ttk.Entry(outer, textvariable=self.player, width=20).grid(row=2, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(outer, text="Host game IP:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(outer, textvariable=self.advertised_ip).grid(row=3, column=1, sticky="ew", padx=(6, 12), pady=(6, 0))
        ttk.Button(outer, text="USE MY LAN IP", command=lambda: self.advertised_ip.set(detect_lan_ip())).grid(row=3, column=2, columnspan=2, sticky="w", pady=(6, 0))

        columns = ("name", "host", "players", "map", "mode", "status", "address")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 180, "host": 95, "players": 65, "map": 100, "mode": 120, "status": 70, "address": 140}
        labels = {"name": "Server", "host": "Host", "players": "Players", "map": "Map", "mode": "Mode", "status": "Status", "address": "Address"}
        for col in columns:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=10)
        self.tree.bind("<Double-1>", lambda _e: self.join_selected())

        chat_frame = ttk.LabelFrame(outer, text="Master Lobby Chat", padding=8)
        chat_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_text = tk.Text(chat_frame, height=8, wrap="word", state="disabled")
        self.chat_text.grid(row=0, column=0, columnspan=2, sticky="nsew")
        chat_scroll = ttk.Scrollbar(chat_frame, orient="vertical", command=self.chat_text.yview)
        chat_scroll.grid(row=0, column=2, sticky="ns")
        self.chat_text.configure(yscrollcommand=chat_scroll.set)

        self.chat_entry = ttk.Entry(chat_frame)
        self.chat_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda _event: self.send_chat())
        ttk.Button(chat_frame, text="SEND", command=self.send_chat).grid(row=1, column=1, columnspan=2, sticky="e", pady=(8, 0))

        controls = ttk.Frame(outer)
        controls.grid(row=6, column=0, columnspan=4, sticky="ew")
        ttk.Button(controls, text="REFRESH", command=self.refresh).pack(side="left", padx=(0, 6), ipady=5)
        ttk.Button(controls, text="HOST PUBLIC GAME", command=self.host_public).pack(side="left", padx=6, ipady=5)
        ttk.Button(controls, text="JOIN SELECTED", command=self.join_selected).pack(side="left", padx=6, ipady=5)
        ttk.Button(controls, text="STOP ADVERTISING", command=self.stop_advertising).pack(side="left", padx=6, ipady=5)

        ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w").grid(row=7, column=0, columnspan=4, sticky="ew", pady=(10, 0))


    def start_chat_polling(self) -> None:
        if self.chat_polling:
            return
        self.chat_polling = True
        self._poll_chat()

    def _poll_chat(self) -> None:
        if not self.chat_polling:
            return
        threading.Thread(target=self._chat_worker, daemon=True).start()
        self.after(CHAT_POLL_MS, self._poll_chat)

    def _chat_worker(self) -> None:
        try:
            result = api(self.master_url.get().strip(), f"/chat?after={self.last_chat_id}", timeout=4)
            messages = result.get("messages", [])
            if isinstance(messages, list) and messages:
                self.after(0, lambda items=messages: self._append_chat_messages(items))
        except (URLError, HTTPError, OSError, ValueError):
            pass

    def _append_chat_messages(self, messages: list[dict]) -> None:
        self.chat_text.configure(state="normal")
        for message in messages:
            try:
                message_id = int(message.get("message_id", 0))
            except (TypeError, ValueError):
                message_id = 0
            if message_id <= self.last_chat_id:
                continue
            self.last_chat_id = message_id
            player = str(message.get("player", "Player"))
            text = str(message.get("text", ""))
            created_at = message.get("created_at")
            try:
                stamp = time.strftime("%H:%M", time.localtime(float(created_at)))
            except (TypeError, ValueError, OSError):
                stamp = "--:--"
            self.chat_text.insert("end", f"[{stamp}] {player}: {text}\n")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def send_chat(self) -> None:
        text = self.chat_entry.get().strip()
        if not text:
            return
        player = self.player.get().strip() or "Player"
        self.chat_entry.delete(0, "end")
        self._remember()
        threading.Thread(target=self._send_chat_worker, args=(player, text), daemon=True).start()

    def _send_chat_worker(self, player: str, text: str) -> None:
        try:
            result = api(self.master_url.get().strip(), "/chat/send", {"player": player, "text": text}, timeout=5)
            message = result.get("message")
            if isinstance(message, dict):
                self.after(0, lambda: self._append_chat_messages([message]))
        except HTTPError as exc:
            detail = str(exc)
            try:
                body = json.loads(exc.read().decode("utf-8"))
                detail = str(body.get("detail", detail))
            except Exception:
                pass
            self.after(0, lambda d=detail: self.status.set(f"Chat send failed: {d}"))
        except (URLError, OSError, ValueError) as exc:
            self.after(0, lambda e=exc: self.status.set(f"Chat send failed: {e}"))

    def _remember(self) -> None:
        try:
            port = int(self.port.get())
        except ValueError:
            port = DEFAULT_PORT
        save_settings({"master": self.master_url.get().strip(), "player": self.player.get().strip(), "server_name": self.server_name.get().strip(), "port": port, "advertised_ip": self.advertised_ip.get().strip()})

    def refresh(self) -> None:
        self.status.set("Refreshing server list…")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            result = api(self.master_url.get().strip(), "/servers")
            servers = result.get("servers", [])
            if not isinstance(servers, list):
                raise ValueError("Invalid server list")
            self.after(0, lambda: self._show_servers(servers))
        except (URLError, HTTPError, OSError, ValueError) as exc:
            self.after(0, lambda: self.status.set(f"Master unavailable: {exc}"))

    def _show_servers(self, servers: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.server_rows.clear()
        for server in servers:
            sid = str(server.get("server_id", ""))
            address = f"{server.get('public_ip', '')}:{server.get('port', DEFAULT_PORT)}"
            values = (
                server.get("name", "Unnamed"), server.get("host_name", "Host"),
                f"{server.get('players', 0)}/{server.get('max_players', 8)}",
                server.get("map_name", "Unknown"), server.get("mode", "Combat Simulator"),
                server.get("status", "Lobby"), address,
            )
            self.tree.insert("", "end", iid=sid, values=values)
            self.server_rows[sid] = server
        self.status.set(f"{len(servers)} public server(s)")

    def host_public(self) -> None:
        if not GAME_EXE.is_file():
            messagebox.showerror(APP_TITLE, f"Place this browser beside the game executable:\n{GAME_EXE}")
            return
        server_name = simpledialog.askstring(APP_TITLE, "Public server name:", initialvalue=self.server_name.get(), parent=self)
        if not server_name:
            return
        port = simpledialog.askinteger(APP_TITLE, "UDP game port:", initialvalue=int(self.port.get() or DEFAULT_PORT), minvalue=1, maxvalue=65535, parent=self)
        if port is None:
            return
        self.server_name.set(server_name)
        self.port.set(str(port))
        self._remember()
        payload = {
            "name": server_name,
            "host_name": self.player.get().strip() or "Host",
            "port": port,
            "advertised_ip": self.advertised_ip.get().strip() or detect_lan_ip(),
            "lan_ip": detect_lan_ip(),
            "players": 1,
            "max_players": 8,
            "map_name": "Select in lobby",
            "mode": "Combat Simulator",
            "status": "Lobby",
            "version": "prototype-1",
        }
        try:
            session = api(self.master_url.get().strip(), "/servers/register", payload)
        except (URLError, HTTPError, OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, f"Could not register with the master:\n{exc}")
            return
        self.stop_advertising(silent=True)
        self.host_session = session
        self.host_stop.clear()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        try:
            subprocess.Popen([str(GAME_EXE), "--portable", "--skip-intro", "--host", "--port", str(port), "--maxclients", "8"], cwd=str(BASE_DIR))
        except OSError as exc:
            self.stop_advertising(silent=True)
            messagebox.showerror(APP_TITLE, f"Could not launch Perfect Dark:\n{exc}")
            return
        self.status.set(f"Advertising '{server_name}' on UDP {port}")
        self.after(500, self.refresh)

    def _heartbeat_loop(self) -> None:
        while not self.host_stop.wait(HEARTBEAT_SECONDS):
            session = self.host_session
            if not session:
                return
            try:
                api(self.master_url.get().strip(), "/servers/heartbeat", {
                    "server_id": session["server_id"], "token": session["token"],
                    "players": 1, "status": "Lobby",
                })
            except Exception as exc:
                self.after(0, lambda e=exc: self.status.set(f"Heartbeat failed: {e}"))

    def stop_advertising(self, silent: bool = False) -> None:
        self.host_stop.set()
        session = self.host_session
        self.host_session = None
        if session:
            try:
                api(self.master_url.get().strip(), "/servers/unregister", {"server_id": session["server_id"], "token": session["token"]}, timeout=2)
            except Exception:
                pass
        if not silent:
            self.status.set("Stopped advertising")
            self.after(200, self.refresh)

    def join_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(APP_TITLE, "Select a public server first.")
            return
        if not GAME_EXE.is_file():
            messagebox.showerror(APP_TITLE, f"Place this browser beside the game executable:\n{GAME_EXE}")
            return
        server = self.server_rows[selected[0]]
        public_host = str(server.get("public_ip", "")).strip()
        lan_host = str(server.get("lan_ip", "")).strip()
        local_ip = detect_lan_ip()

        # Prefer the host's LAN address when both machines appear to share
        # the same IPv4 /24 subnet. Otherwise use the public/DDNS address.
        connect_host = public_host
        try:
            local_parts = local_ip.split(".")
            lan_parts = lan_host.split(".")
            if len(local_parts) == 4 and len(lan_parts) == 4 and local_parts[:3] == lan_parts[:3]:
                connect_host = lan_host
        except Exception:
            pass

        if not connect_host:
            messagebox.showerror(APP_TITLE, "The selected server has no usable address.")
            return

        address = f"{connect_host}:{server['port']}"
        try:
            subprocess.Popen([str(GAME_EXE), "--portable", "--skip-intro", "--connect", address], cwd=str(BASE_DIR))
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch Perfect Dark:\n{exc}")
            return
        self.status.set(f"Joining {server.get('name', 'server')} at {address}")

    def close(self) -> None:
        self.chat_polling = False
        self._remember()
        self.stop_advertising(silent=True)
        self.destroy()


if __name__ == "__main__":
    PerfectThork().mainloop()
