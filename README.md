# Thorfect Dark

Thorfect Dark is a Windows launcher and master-server bundle for the Perfect Dark PC port with experimental online play support.

This project ships:

* Public server browser
* Master-server registry
* Lobby chat
* Browser-based hosting and joining
* Cooperative campaign support
* Combat Simulator support
* Temporary dual-launcher routing for coop and combat

## Current Build Behavior

As of July 29, 2026, the browser uses two separate game executables:

* `coop-pd.x86_64.exe` for all coop host and join actions
* `combat-pd.x86_64.exe` for all Combat Simulator host and join actions

This is an intentional temporary workaround. The browser selects the correct executable based on the hosted or joined mode so players can use one launcher even though a single game executable does not yet handle both modes reliably.

## Included Files

Top-level Windows launch files:

* `perfect_thork_browser.exe` - public browser and launcher
* `perfect_thork_master.exe` - master server registry and lobby chat server
* `coop-pd.x86_64.exe` - coop-focused game executable
* `combat-pd.x86_64.exe` - Combat Simulator-focused game executable

The browser is the recommended way to launch and join games.

## Requirements

* Windows 10 or Windows 11, 64-bit
* Git for Windows
* A legally obtained Perfect Dark NTSC-final ROM

The ROM is not included.

```text
data\pd.ntsc-final.z64
```

All players should use the same build and the same compatible ROM.

## One-Line Browser Install And Run

```powershell
$dir="$HOME\Thorfect-Dark"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="main"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; $data="$dir\data"; New-Item -ItemType Directory -Force "$data" | Out-Null; $rom="$data\pd.ntsc-final.z64"; if(Test-Path "$rom"){$exe="$dir\perfect_thork_browser.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"}else{Write-Host "Place your legally obtained ROM at: $rom"; Start-Process -FilePath "explorer.exe" -ArgumentList "$data"}
```

Installs or updates to:

```text
%USERPROFILE%\Thorfect-Dark
```

## One-Line Master Install And Run

```powershell
$dir="$HOME\Thorfect-Dark"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="main"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; $exe="$dir\perfect_thork_master.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"
```

## Browser

The browser:

* Lists public servers
* Hosts public coop or Combat Simulator sessions
* Joins public servers
* Provides lobby chat
* Uses LAN routing automatically when possible
* Passes the correct launch arguments automatically

Hosting and joining route by mode:

* `Co-Op` -> `coop-pd.x86_64.exe`
* `Combat Simulator` -> `combat-pd.x86_64.exe`

## Run the Game Directly

Direct launch files:

```text
coop-pd.x86_64.exe
combat-pd.x86_64.exe
```

Direct launching bypasses the browser's automatic routing and launch arguments.

## Master Server

The master server provides:

* Public server registration
* Public server listing
* Lobby chat
* Basic server heartbeat tracking

Default URLs:

* Local machine: `http://127.0.0.1:8088`
* Other LAN PCs: `http://<your-lan-ip>:8088`

Most players do not need to run their own master server unless they are hosting a separate registry.

## Default Ports

| Service                        | Protocol | Default port |
| ------------------------------ | -------: | -----------: |
| Master registry and lobby chat |      TCP |       `8088` |
| Perfect Dark game traffic      |      UDP |      `27100` |

Windows Firewall may prompt the first time an executable is launched.

If you host public games from outside your LAN, you will usually need to forward UDP port `27100` to the host machine.

If you run a public master server, you will need to make TCP port `8088` reachable.

## Current Status

### Coop

Current known campaign status:

| Mission          | Status                   |
| ---------------- | ------------------------ |
| DataDyne         | Working                  |
| Carrington Villa | Working                  |
| Chicago          | Working                  |
| Other missions   | Untested                 |

### Combat Simulator

Combat Simulator netplay is also experimental. It may work for testing, but it still has known sync and gameplay issues inherited from the underlying network implementation.

## Config and Logs

Common runtime files may include:

* `pd.ini`
* `perfect_thork_settings.json`
* `pd.log`
* `pd-client.log`

These files can help when diagnosing launch, connection, or gameplay issues.

## Version Notes

### July 29, 2026

* Browser launcher updated to route by mode
* Coop host and join now use `coop-pd.x86_64.exe`
* Combat Simulator host and join now use `combat-pd.x86_64.exe`
* README updated to reflect the full launcher and master-server workflow

## Disclaimer

This is an experimental fan-made networking modification. It is not affiliated with or endorsed by Rare, Nintendo, Microsoft, or the original Perfect Dark developers.

A legally obtained Perfect Dark ROM is required and is not distributed by this repository.
