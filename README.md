EADME_Thorfect_Dark.md


# Thorfect Dark

A Windows launcher, public server browser, master server, shared lobby chat, and direct native-network-lobby frontend for the Perfect Dark PC port.

Thorfect Dark supersedes the earlier direct pre-lobby workflow by adding a Halo CE-style server list while preserving direct LAN and Internet hosting.

## Features

- Public server browser with refreshable listings
- Shared master-lobby chat
- One-click public hosting
- One-click joining
- Native Perfect Dark host/client launch
- Automatic LAN-address fallback for players on the same network
- Public IPv4 and DNS/DDNS hostname support
- Master-server GUI with automatic LAN-IP detection
- Host heartbeats and stale-listing cleanup
- Player name, server name, map, mode, player count, status, and address display
- ROM-selection dialog during one-command setup
- No scripted keyboard input or menu automation

## One-command setup

Git is required. Install it from PowerShell with:

```powershell
winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
```

Close and reopen PowerShell after installation.

### Acquire or update and run the master server

```powershell
$ErrorActionPreference="Stop"; $dir="$HOME\Perfect-Dark-Network-Lobby"; if(Test-Path "$dir\.git"){git -C $dir fetch origin; git -C $dir reset --hard origin/main}else{git clone https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git $dir}; $exe="$dir\Perfect_Thork_Master.exe"; if(!(Test-Path $exe)){throw "Thorfect Dark Master executable was not found after updating: $exe"}; Start-Process -FilePath $exe -WorkingDirectory $dir
```

This command:

- clones the repository into `%USERPROFILE%\Perfect-Dark-Network-Lobby` when missing
- pulls the latest changes when the repository already exists
- launches the Thorfect Dark master-server GUI

### Acquire or update and run Thorfect Dark

```powershell
$ErrorActionPreference="Stop"; $dir="$HOME\Perfect-Dark-Network-Lobby"; if(Test-Path "$dir\.git"){git -C $dir fetch origin; git -C $dir reset --hard origin/main}else{git clone https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git $dir}; $rom="$dir\data\pd.ntsc-final.z64"; if(!(Test-Path $rom)){Add-Type -AssemblyName System.Windows.Forms; $dialog=New-Object System.Windows.Forms.OpenFileDialog; $dialog.Title="Select your legally obtained Perfect Dark NTSC-final ROM"; $dialog.Filter="Nintendo 64 ROM files (*.z64;*.n64;*.v64)|*.z64;*.n64;*.v64|All files (*.*)|*.*"; if($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){New-Item -ItemType Directory -Force "$dir\data"|Out-Null; Copy-Item $dialog.FileName $rom -Force}else{Write-Host "ROM selection cancelled."; exit}}; $exe="$dir\Perfect_Thork_Browser.exe"; if(!(Test-Path $exe)){throw "Thorfect Dark executable was not found after updating: $exe"}; Start-Process -FilePath $exe -WorkingDirectory $dir
```

This command:

- clones or updates the repository
- checks for `data\pd.ntsc-final.z64`
- opens a Windows file-selection dialog when the ROM is missing
- accepts `.z64`, `.n64`, and `.v64` files
- copies the selected file into the `data` folder
- renames the copied file to the exact filename expected by the game
- leaves the original ROM untouched
- launches Thorfect Dark automatically

The command does not download or include a ROM. You must provide your own legally obtained Perfect Dark NTSC-final ROM.

## Manual setup

1. Clone or download this repository.
2. Place your legally obtained ROM at:

   ```text
   data/pd.ntsc-final.z64
   ```

3. Run the master server:

   ```text
   Perfect_Thork_Master.exe
   ```

4. Run the server browser:

   ```text
   Perfect_Thork_Browser.exe
   ```

The master server and browser can run on the same PC or on separate PCs.

## Master-server setup

In the Thorfect Dark Master window:

```text
Bind address: 0.0.0.0
TCP port:     8088
```

Leave the bind address at `0.0.0.0` so the master listens on all local network adapters.

The GUI displays:

```text
Local browser URL: http://127.0.0.1:8088
Other LAN PCs:     http://YOUR_LAN_IP:8088
```

Use `127.0.0.1` only when the browser and master run on the same PC.

Other LAN computers must use the master PC's LAN address, for example:

```text
http://192.168.1.158:8088
```

For Internet access, forward TCP port `8088` to the master PC and use a public IP or DNS/DDNS hostname:

```text
http://example.ddns.net:8088
```

### Windows Firewall rule for the master

Run PowerShell as Administrator:

```powershell
New-NetFirewallRule -DisplayName "Thorfect Dark Master TCP 8088" -Direction Inbound -Protocol TCP -LocalPort 8088 -Action Allow
```

## Hosting a game

1. Start the master server.
2. Open Thorfect Dark.
3. Enter the master URL.
4. Enter a player name.
5. Enter the address players should use in **Host game IP**.
6. Click **HOST PUBLIC GAME**.
7. Enter a public server name and UDP game port.
8. Perfect Dark launches directly into the native host lobby.

The default game port is:

```text
27100
```

The host launch command is equivalent to:

```text
pd.x86_64.exe --portable --skip-intro --host --port 27100 --maxclients 8
```

## Joining a game

1. Open Thorfect Dark.
2. Enter the same master URL used by the host.
3. Click **REFRESH**.
4. Select a listed game.
5. Click **JOIN SELECTED**, or double-click the listing.

The client launch command is equivalent to:

```text
pd.x86_64.exe --portable --skip-intro --connect HOST:27100
```

## Address handling

The **Host game IP** field accepts IPv4 addresses, DNS hostnames, DDNS hostnames, and URL-style input.

Valid examples:

```text
192.168.1.154
108.15.34.92
example.com
game.example.net
plentyfasthosting.ddns.net
http://example.com
http://example.com:27100
https://game.example.net/path
```

URL schemes, paths, and supplied ports are normalized before the server is advertised.

For example:

```text
http://plentyfasthosting.ddns.net:27100
```

is advertised as:

```text
plentyfasthosting.ddns.net:27100
```

IPv6 literals are not currently supported.

## Dual-route networking

Thorfect Dark advertises both:

- the public IPv4 or DNS/DDNS address entered by the host
- the host machine's detected LAN IPv4 address

When a client appears to be on the same `/24` local subnet, Thorfect Dark automatically joins through the LAN address.

When the client is on another network, Thorfect Dark uses the public IPv4 or DNS/DDNS address.

Example:

```text
Same LAN:       192.168.1.154:27100
Other network:  plentyfasthosting.ddns.net:27100
```

The Address column continues to display the public endpoint even when a same-network client automatically uses the LAN route.

## Internet hosting

The master server and game server use different protocols and should use separate router rules.

### Master-server rule

```text
External port: 8088
Internal port: 8088
Protocol: TCP
Destination: master-server PC
```

### Perfect Dark game rule

```text
External port: 27100
Internal port: 27100
Protocol: UDP only
Destination: game-host PC
```

Do not use TCP, `Both`, `TCP/UDP`, or `All protocols` for the game-port rule. The native game connection has been tested with a UDP-only forwarding rule.

### Windows Firewall rule for gameplay

Run PowerShell as Administrator on the game host:

```powershell
New-NetFirewallRule -DisplayName "Perfect Dark UDP 27100" -Direction Inbound -Protocol UDP -LocalPort 27100 -Action Allow
```

Clients normally do not need router port forwarding.

## Master-lobby chat

Everyone connected to the same master server shares one lobby chat.

Chat:

- uses the master server's existing TCP port
- requires no additional forwarding rule
- polls automatically
- supports Enter-to-send
- keeps recent messages in master-server memory
- applies basic message-length and rate limits

Restarting the master clears the in-memory chat history and active server list.

## Building the executables

Python 3 with Tkinter is required.

```powershell
py -m pip install --upgrade pyinstaller

py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Perfect_Thork_Browser" .\perfect_thork_browser.py

py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Perfect_Thork_Master" .\perfect_thork_master.py

Copy-Item .\dist\Perfect_Thork_Browser.exe .\Perfect_Thork_Browser.exe -Force
Copy-Item .\dist\Perfect_Thork_Master.exe .\Perfect_Thork_Master.exe -Force
```

Or use the included build script when present:

```text
BUILD_EXES.bat
```

Generated files such as `build/`, `dist/`, `.spec` files, settings JSON, EEPROM data, logs, and ROM files should not be committed.

## Repository contents

Core Thorfect Dark files:

- `perfect_thork_browser.py` — public server browser, chat, hosting, joining, and launch logic
- `perfect_thork_master.py` — master-server registry, heartbeat, chat, and GUI
- `Perfect_Thork_Browser.exe` — compiled Thorfect Dark browser
- `Perfect_Thork_Master.exe` — compiled Thorfect Dark master server
- `pd.x86_64.exe` — Perfect Dark PC-port executable
- `pd_lobby_tk.py` — earlier direct pre-lobby launcher source
- `pd.ini` — game configuration
- `data/PUT ROM HERE.txt` — placeholder for the user-supplied ROM

The visible product name is **Thorfect Dark**. Some filenames retain the earlier `Perfect_Thork` naming for compatibility with existing scripts and installations.

## Current limitations

- The host still needs UDP port forwarding for direct Internet gameplay.
- The master server uses plain HTTP and is intended for community or controlled deployment.
- Server and chat state are stored in memory and reset when the master closes.
- Player counts and map/status fields are currently basic advertised values rather than live game telemetry.
- IPv6 is not currently supported.
- A UDP relay or NAT-traversal layer is not yet included.

## ROM and licensing

Users must provide their own Perfect Dark NTSC-final ROM.

