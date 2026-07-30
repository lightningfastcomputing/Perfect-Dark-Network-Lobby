from __future__ import annotations

import json
import ipaddress
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

APP_TITLE = "Thorfect Dark"
DEFAULT_MASTER = "http://127.0.0.1:8088"
DEFAULT_PORT = 27100
HEARTBEAT_SECONDS = 5
CHAT_POLL_MS = 2000
DEFAULT_MODE = "Co-Op"
ACTIVE_REFRESH_MS = 1000
INACTIVE_REFRESH_MS = 5000
PROCESS_POLL_MS = 1000


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = base_dir()
COOP_EXE = BASE_DIR / "coop-pd.x86_64.exe"
COMBAT_EXE = BASE_DIR / "combat-pd.x86_64.exe"
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
    defaults = {"master": DEFAULT_MASTER, "player": "Player", "server_name": "Perfect Dark Match", "port": DEFAULT_PORT, "advertised_ip": detect_lan_ip(), "mode": DEFAULT_MODE}
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


def is_coop_mode(mode: str) -> bool:
    mode_text = mode.strip().lower()
    return mode_text.startswith("co-op") or mode_text.startswith("coop")


def game_executable_for_mode(mode: str) -> Path:
    return COOP_EXE if is_coop_mode(mode) else COMBAT_EXE


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
        self.host_process: subprocess.Popen[str] | None = None
        self.host_process_name = ""
        self.host_public_name = ""
        self.host_public_mode = DEFAULT_MODE
        self.host_player_count = 1
        self.host_max_players = 2
        self.host_log_path = BASE_DIR / "pd-server.log"
        self.host_log_offset = 0
        self.server_rows: dict[str, dict] = {}
        self.server_count = 0
        self.requester_ip = ""
        self.last_chat_id = 0
        self.chat_polling = False
        self.refresh_inflight = False
        self.window_active = True
        self.last_refresh_started = 0.0
        self.join_process: subprocess.Popen[str] | None = None
        self.join_process_name = ""

        self._build()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.after(200, self.refresh)
        self.after(350, self.start_chat_polling)
        self.after(INACTIVE_REFRESH_MS, self._auto_refresh_tick)
        self.after(PROCESS_POLL_MS, self._process_tick)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(3, weight=1)
        outer.rowconfigure(5, weight=1)

        ttk.Label(outer, text="Thorfect Dark", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(outer, text="Public server browser, launcher, and lobby chat").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Master URL:").grid(row=2, column=0, sticky="w")
        ttk.Entry(outer, textvariable=self.master_url).grid(row=2, column=1, sticky="ew", padx=(6, 12))
        ttk.Label(outer, text="Player:").grid(row=2, column=2, sticky="w")
        ttk.Entry(outer, textvariable=self.player, width=20).grid(row=2, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(outer, text="Host game IP:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(outer, textvariable=self.advertised_ip).grid(row=3, column=1, sticky="ew", padx=(6, 12), pady=(6, 0))
        action_frame = ttk.Frame(outer)
        action_frame.grid(row=3, column=2, columnspan=2, sticky="ew", pady=(6, 0))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(2, weight=1)
        action_frame.columnconfigure(3, weight=1)
        ttk.Button(action_frame, text="USE MY LAN IP", command=lambda: self.advertised_ip.set(detect_lan_ip())).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(action_frame, text="HOST CO-OP", command=lambda: self.host_public("Co-Op")).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(action_frame, text="HOST COMBAT", command=lambda: self.host_public("Combat Simulator")).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(action_frame, text="JOIN SELECTED", command=self.join_selected).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(outer, text="Auto-refreshes every second while active, every 5 seconds in the background.").grid(row=4, column=0, columnspan=4, sticky="w", pady=(10, 0))

        columns = ("name", "host", "players", "map", "mode", "status", "address")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 180, "host": 95, "players": 65, "map": 100, "mode": 120, "status": 70, "address": 140}
        labels = {"name": "Server", "host": "Host", "players": "Players", "map": "Map", "mode": "Mode", "status": "Status", "address": "Address"}
        for col in columns:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=10)
        self.tree.bind("<Double-1>", lambda _e: self.join_selected())

        chat_frame = ttk.LabelFrame(outer, text="Master Lobby Chat", padding=8)
        chat_frame.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(0, 10))
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
        save_settings({"master": self.master_url.get().strip(), "player": self.player.get().strip(), "server_name": self.server_name.get().strip(), "port": port, "advertised_ip": self.advertised_ip.get().strip(), "mode": self.host_public_mode})

    def _on_focus_in(self, _event: tk.Event[tk.Misc]) -> None:
        self.window_active = True

    def _on_focus_out(self, _event: tk.Event[tk.Misc]) -> None:
        self.window_active = False

    def _auto_refresh_tick(self) -> None:
        if not self.winfo_exists():
            return
        self.refresh(silent=True)
        self.after(ACTIVE_REFRESH_MS if self.window_active else INACTIVE_REFRESH_MS, self._auto_refresh_tick)

    def refresh(self, silent: bool = False) -> None:
        if self.refresh_inflight:
            return
        self.refresh_inflight = True
        self.last_refresh_started = time.time()
        if not silent:
            self.status.set("Refreshing server list...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            result = api(self.master_url.get().strip(), "/servers")
            servers = result.get("servers", [])
            requester_ip = str(result.get("requester_ip", "")).strip()
            if not isinstance(servers, list):
                raise ValueError("Invalid server list")
            self.after(0, lambda: self._show_servers(servers, requester_ip))
        except (URLError, HTTPError, OSError, ValueError) as exc:
            self.after(0, lambda e=exc: self._show_refresh_error(e))

    def _show_refresh_error(self, exc: Exception) -> None:
        self.refresh_inflight = False
        self.status.set(f"Master unavailable: {exc}")

    def _show_servers(self, servers: list[dict], requester_ip: str = "") -> None:
        self.refresh_inflight = False
        self.requester_ip = requester_ip
        self.server_count = len(servers)
        self.tree.delete(*self.tree.get_children())
        self.server_rows.clear()
        for server in servers:
            sid = str(server.get("server_id", ""))
            address = f"{server.get('public_host', server.get('public_ip', ''))}:{server.get('port', DEFAULT_PORT)}"
            values = (
                server.get("name", "Unnamed"), server.get("host_name", "Host"),
                f"{server.get('players', 0)}/{server.get('max_players', 8)}",
                server.get("map_name", "Unknown"), server.get("mode", "Combat Simulator"),
                server.get("status", "Lobby"), address,
            )
            self.tree.insert("", "end", iid=sid, values=values)
            self.server_rows[sid] = server
        if self.host_session and self.host_process and self.host_process.poll() is None:
            self.status.set(
                f"Hosting {self.host_public_mode}: {self.host_player_count}/{self.host_max_players} in lobby | {self.server_count} public server(s)"
            )
        else:
            self.status.set(f"{self.server_count} public server(s)")

    def host_public(self, selected_mode: str) -> None:
        server_name = simpledialog.askstring(APP_TITLE, "Public server name:", initialvalue=self.server_name.get(), parent=self)
        if not server_name:
            return
        port = simpledialog.askinteger(APP_TITLE, "UDP game port:", initialvalue=int(self.port.get() or DEFAULT_PORT), minvalue=1, maxvalue=65535, parent=self)
        if port is None:
            return
        self.server_name.set(server_name)
        self.port.set(str(port))
        self.host_public_mode = selected_mode
        self._remember()
        player_name = self.player.get().strip() or "Player"
        game_exe = game_executable_for_mode(selected_mode)
        if not game_exe.is_file():
            messagebox.showerror(APP_TITLE, f"Missing game executable for {selected_mode}:\n{game_exe}")
            return
        is_coop = is_coop_mode(selected_mode)
        self.stop_advertising(silent=True)
        payload = {
            "name": server_name,
            "host_name": player_name,
            "port": port,
            "advertised_ip": self.advertised_ip.get().strip() or detect_lan_ip(),
            "lan_ip": detect_lan_ip(),
            "players": 1,
            "max_players": 2 if is_coop else 8,
            "map_name": "Select in lobby",
            "mode": "Co-Op" if is_coop else "Combat Simulator",
            "status": "Lobby",
            "version": "thorfect-1.0.3",
        }
        try:
            session = api(self.master_url.get().strip(), "/servers/register", payload)
        except (URLError, HTTPError, OSError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, f"Could not register with the master:\n{exc}")
            return
        self.host_session = session
        self.host_stop.clear()
        self.host_public_name = server_name
        self.host_player_count = 1
        self.host_max_players = 2 if is_coop else 8
        self.host_process_name = game_exe.name
        self.host_log_offset = self.host_log_path.stat().st_size if self.host_log_path.exists() else 0
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        try:
            self.host_process = subprocess.Popen([
                str(game_exe),
                "--portable",
                "--skip-intro",
                "--host",
                "--port",
                str(port),
                "--maxclients",
                "2" if is_coop else "8",
                "--player-name",
                player_name,
                "--net-mode",
                "coop" if is_coop else "combat",
            ], cwd=str(BASE_DIR))
        except OSError as exc:
            self.stop_advertising(silent=True)
            messagebox.showerror(APP_TITLE, f"Could not launch Perfect Dark:\n{exc}")
            return
        self.status.set(f"Hosting {selected_mode}: {self.host_player_count}/{self.host_max_players} in lobby")
        self.after(500, lambda: self.refresh(silent=True))

    def _heartbeat_loop(self) -> None:
        while not self.host_stop.wait(HEARTBEAT_SECONDS):
            session = self.host_session
            if not session:
                return
            try:
                api(self.master_url.get().strip(), "/servers/heartbeat", {
                    "server_id": session["server_id"], "token": session["token"],
                    "players": self.host_player_count,
                    "status": "Lobby",
                    "mode": self.host_public_mode,
                })
            except Exception as exc:
                self.after(0, lambda e=exc: self.status.set(f"Heartbeat failed: {e}"))

    def stop_advertising(self, silent: bool = False) -> None:
        self.host_stop.set()
        session = self.host_session
        self.host_session = None
        self.host_process = None
        self.host_process_name = ""
        self.host_public_name = ""
        self.host_player_count = 1
        self.host_max_players = 2
        self.host_log_offset = 0
        if session:
            try:
                api(self.master_url.get().strip(), "/servers/unregister", {"server_id": session["server_id"], "token": session["token"]}, timeout=2)
            except Exception:
                pass
        if not silent:
            self.status.set("Host closed. Stopped advertising.")
            self.after(200, lambda: self.refresh(silent=True))

    def _update_host_player_count_from_log(self) -> None:
        if not self.host_log_path.exists():
            return
        try:
            current_size = self.host_log_path.stat().st_size
            if current_size < self.host_log_offset:
                self.host_log_offset = 0
            with self.host_log_path.open("r", encoding="utf-8", errors="ignore") as handle:
                handle.seek(self.host_log_offset)
                chunk = handle.read()
                self.host_log_offset = handle.tell()
        except OSError:
            return

        for line in chunk.splitlines():
            if "NET:" in line and " joined" in line:
                self.host_player_count = min(self.host_max_players, self.host_player_count + 1)
            elif "NET:" in line and " disconnected" in line:
                self.host_player_count = max(1, self.host_player_count - 1)

    def _process_tick(self) -> None:
        if not self.winfo_exists():
            return

        if self.host_process:
            if self.host_process.poll() is None:
                self._update_host_player_count_from_log()
                if self.host_session:
                    self.status.set(
                        f"Hosting {self.host_public_mode}: {self.host_player_count}/{self.host_max_players} in lobby"
                    )
            else:
                self.stop_advertising(silent=False)

        if self.join_process:
            if self.join_process.poll() is None:
                if not self.host_session:
                    self.status.set(f"{self.join_process_name} is open")
            else:
                self.join_process = None
                self.join_process_name = ""
                if not self.host_session:
                    self.status.set(f"{self.server_count} public server(s)")

        self.after(PROCESS_POLL_MS, self._process_tick)

    @staticmethod
    def _same_private_subnet(left: str, right: str) -> bool:
        try:
            left_ip = ipaddress.ip_address(left)
            right_ip = ipaddress.ip_address(right)
        except ValueError:
            return False
        if left_ip.version != 4 or right_ip.version != 4:
            return False
        if not left_ip.is_private or not right_ip.is_private:
            return False
        return left.split(".")[:3] == right.split(".")[:3]

    def join_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(APP_TITLE, "Select a public server first.")
            return

        server = self.server_rows[selected[0]]
        public_host = str(
            server.get("public_host", server.get("public_ip", ""))
        ).strip()
        lan_ip = str(server.get("lan_ip", "")).strip()
        host_observed_ip = str(server.get("observed_ip", "")).strip()
        requester_ip = self.requester_ip.strip()

        connect_host = public_host
        route = "public"

        # Use the LAN endpoint only when the master can establish that host
        # and client are behind the same public connection. This preserves
        # local play without replacing or rewriting the advertised hostname.
        if lan_ip and requester_ip and host_observed_ip and requester_ip == host_observed_ip:
            connect_host = lan_ip
            route = "LAN"
        elif lan_ip and self._same_private_subnet(requester_ip, host_observed_ip):
            connect_host = lan_ip
            route = "LAN"

        if not connect_host:
            messagebox.showerror(APP_TITLE, "The selected server has no usable address.")
            return

        address = f"{connect_host}:{server['port']}"
        player_name = self.player.get().strip() or "Player"
        mode_text = str(server.get("mode", DEFAULT_MODE)).strip().lower()
        mode_arg = "coop" if "coop" in mode_text else "combat"
        game_exe = game_executable_for_mode(str(server.get("mode", DEFAULT_MODE)))
        if not game_exe.is_file():
            messagebox.showerror(APP_TITLE, f"Missing game executable for {server.get('mode', DEFAULT_MODE)}:\n{game_exe}")
            return
        try:
            self.join_process = subprocess.Popen(
                [
                    str(game_exe),
                    "--portable",
                    "--skip-intro",
                    "--connect",
                    address,
                    "--player-name",
                    player_name,
                    "--net-mode",
                    mode_arg,
                ],
                cwd=str(BASE_DIR),
            )
            self.join_process_name = game_exe.name
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch Perfect Dark:\n{exc}")
            return

        self.status.set(
            f"Joining {server.get('name', 'server')} via {route} at {address}"
        )

    def close(self) -> None:
        self.chat_polling = False
        self._remember()
        self.stop_advertising(silent=True)
        self.destroy()


if __name__ == "__main__":
    PerfectThork().mainloop()
