# Thorfect Dark — Native Lobby + Authoritative Sims + Slayer Fly-by-Wire

This branch contains the current Thorfect Dark network-lobby build with:

- public master-server registry and lobby chat;
- public server browser;
- native green in-game Network Lobby;
- Protocol 21 networking;
- host-authoritative Sim movement, combat, death, respawn, weapons, firing, and corrected client-side falling;
- host-authoritative Slayer rockets with working remote-client fly-by-wire camera, repeat firing, and responsive loss-tolerant client steering;
- packaged Windows executables for the master, browser, and game.

Repository branch:

```text
net-sim/simulant-lobby-latest
```

## Requirements

- Windows 10 or Windows 11, 64-bit.
- Git for acquiring and updating the branch.
- Microsoft Visual C++ x64 runtime.
- A legally obtained Perfect Dark NTSC-final ROM.

The ROM is **not included**. Place your own ROM here after downloading the branch:

```text
data\pd.ntsc-final.z64
```

Users in the same network game must use compatible ROMs and the same Protocol 21 build.

## Install required dependencies — PowerShell one-liner

Run PowerShell as Administrator:

```powershell
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements; winget install --id Microsoft.VCRedist.2015+.x64 -e --accept-package-agreements --accept-source-agreements
```

The packaged `.exe` files do not require Python.

## Acquire/update and run the master server — PowerShell one-liner

```powershell
$dir="$HOME\Thorfect-Dark-Master"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="net-sim/simulant-lobby-latest"; if(Test-Path "$dir\.git"){git -C $dir fetch origin $branch; git -C $dir reset --hard "origin/$branch"}else{git clone --branch $branch --single-branch $repo $dir}; Start-Process -FilePath "$dir\perfect_thork_master.exe" -WorkingDirectory $dir
```

Start the master, leave it open, and ensure its TCP port is reachable by players who need to use it. The default master port is `8088`.

## Acquire/update and run the browser — PowerShell one-liner

```powershell
$dir="$HOME\Thorfect-Dark"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="net-sim/simulant-lobby-latest"; if(Test-Path "$dir\.git"){git -C $dir fetch origin $branch; git -C $dir reset --hard "origin/$branch"}else{git clone --branch $branch --single-branch $repo $dir}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; Start-Process -FilePath "$dir\perfect_thork_browser.exe" -WorkingDirectory $dir
```

Before hosting or joining, put your own ROM at:

```text
%USERPROFILE%\Thorfect-Dark\data\pd.ntsc-final.z64
```

The browser expects `pd.x86_64.exe` beside `perfect_thork_browser.exe`.

## Run the game directly

```powershell
Start-Process -FilePath "$HOME\Thorfect-Dark\pd.x86_64.exe" -WorkingDirectory "$HOME\Thorfect-Dark"
```

For public play, normally launch through `perfect_thork_browser.exe` so the correct host or join arguments are supplied.

## Default ports

| Service | Protocol | Default port |
|---|---:|---:|
| Master registry/chat | TCP | 8088 |
| Perfect Dark game | UDP | 27100 |

A public host normally needs UDP `27100` forwarded to the hosting PC. The master-server operator needs TCP `8088` reachable.

## Source

The branch includes the C source corresponding to the packaged Protocol 21 game executable. The primary networking changes are under:

```text
port/include/net/
port/src/net/
src/game/
```

## Updating later

Re-running either acquire/run one-liner fetches the branch and hard-resets that local install to the newest published version.

Local changes inside those acquisition directories will be discarded during an update.
