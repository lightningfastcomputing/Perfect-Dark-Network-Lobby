# Perfect Dark Pre-Lobby + Direct Network Lobby

A Windows Tkinter launcher that adds a lightweight TCP pre-lobby with player presence and chat, then launches the existing Perfect Dark PC port directly into its native network lobby as host or client.

## Features

- Host or join a pre-lobby before launching the game
- Player list and text chat
- Direct native host/client launch into the in-game lobby
- Host/server IP field starts blank each launch
- **Use My LAN IP** helper for hosts
- Launcher only looks for `pd.x86_64.exe` in its own folder
- No scripted keyboard input or menu automation

## Quick start

1. Supply your own legally obtained Perfect Dark NTSC-final ROM.
2. Place it at:

   ```text
   data/pd.ntsc-final.z64
   ```

3. Run:

   ```text
   Perfect_Dark_Lobby.exe
   ```

### Host

1. Enter a player name.
2. Click **Use My LAN IP**.
3. Click **HOST PRE-LOBBY**.
4. Share the shown IP and port with the other players.
5. When ready, click **LAUNCH AS HOST**.

### Client

1. Enter a player name.
2. Enter the host's LAN IP or reachable address.
3. Click **JOIN PRE-LOBBY**.
4. When ready, click **LAUNCH AS CLIENT**.

The default port is `27100`.

## Cross-network / Internet play

The native Perfect Dark game lobby also works across different networks when the host configures router port forwarding.

Forward the selected game port to the host PC using **UDP only**. With the default configuration, forward:

```text
External port: 27100
Internal port: 27100
Protocol: UDP only
Destination: the host PC's local IPv4 address
```

> [!IMPORTANT]
> Do **not** select TCP, TCP/UDP, `Both`, or `All protocols` for the game-port forwarding rule. In tested configurations, allowing additional protocol types prevents the native game connection from working correctly. Delete conflicting rules and leave one UDP-only forward for the game port.

The host should give remote players the host network's **public IP address**, not the host PC's `192.168.x.x`, `10.x.x.x`, or `172.16-31.x.x` LAN address. Keep the host PC on a reserved/static local address so the router rule continues pointing to the correct machine.

The Tkinter pre-lobby chat uses TCP while it is open, then closes before Perfect Dark launches. The UDP-only router-forwarding instruction above is specifically for the native game's cross-network traffic. The pre-lobby chat is best treated as a LAN feature unless a separate TCP path is deliberately configured; do not add TCP to the game's UDP forwarding rule.

### Internet host

1. Reserve the host PC's local IPv4 address in the router.
2. Forward the selected port to that PC as **UDP only**.
3. Start the launcher and host normally.
4. Give remote clients the public IP address and game port.

### Internet client

1. Enter the host's public IP address.
2. Use the same port forwarded by the host.
3. Launch as client. The client normally does not need router port forwarding.

## Current network note

The pre-lobby has been confirmed working with one tested PC hosting and another joining. On some Windows systems, inbound connections may be blocked by the local network profile, firewall, endpoint-security software, or adapter configuration. If one PC can join but cannot host, test the port from the other machine and inspect the host's inbound rules.

Example PowerShell test from the joining PC:

```powershell
Test-NetConnection HOST_IP -Port 27100
```

## Build the launcher

Python 3 with Tkinter is required.

```powershell
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Perfect_Dark_Lobby" pd_lobby_tk.py
copy /Y .\dist\Perfect_Dark_Lobby.exe .\Perfect_Dark_Lobby.exe
```

Or run:

```text
BUILD_LAUNCHER_EXE.bat
```

## Native launch commands

Host:

```text
pd.x86_64.exe --portable --skip-intro --host --port 27100 --maxclients 8
```

Client:

```text
pd.x86_64.exe --portable --skip-intro --connect HOST_IP:27100
```

## Repository contents

- `pd_lobby_tk.py` — Tkinter pre-lobby/chat launcher source
- `Perfect_Dark_Lobby.exe` — compiled launcher
- `pd.x86_64.exe` — game-port executable used by the launcher
- `PD_DIRECT_LOBBY.bat` — command-line host/join helper
- `HOST_LOBBY.bat` / `JOIN_LOBBY.bat` — simple batch wrappers
- `BUILD_LAUNCHER_EXE.bat` — PyInstaller build helper
- `START_PD_LOBBY_GUI.bat` — runs the Python source directly
- `pd.ini` — neutralized default configuration

## ROM and licensing

The Perfect Dark ROM is **not included**. Users must provide their own legally obtained ROM.

The game executable and bundled runtime libraries may be subject to their respective upstream licenses. Review the upstream Perfect Dark PC-port project and third-party library licenses before redistributing binaries publicly.
