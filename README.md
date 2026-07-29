# Thorfect Dark

Thorfect Dark is a Windows launcher and master-server bundle for the Perfect Dark PC port with experimental online play support.

This project currently ships:

* A public server browser
* A master-server registry
* Master lobby chat
* Browser-based hosting and joining
* Experimental cooperative campaign support
* Experimental Combat Simulator support
* A temporary dual-launcher setup that routes coop and combat to different game executables

This is still experimental software. Expect crashes, desyncs, mission bugs, and mode-specific issues.

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

Place your ROM at:

```text
data\pd.ntsc-final.z64
```

All players should use the same build and the same compatible ROM.

## Install

Open PowerShell and run:

```powershell
$dir="$HOME\Thorfect-Dark"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="main"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; $data="$dir\data"; New-Item -ItemType Directory -Force "$data" | Out-Null; $rom="$data\pd.ntsc-final.z64"; if(Test-Path "$rom"){$exe="$dir\perfect_thork_browser.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"}else{Write-Host "Place your legally obtained ROM at: $rom"; Start-Process -FilePath "explorer.exe" -ArgumentList "$data"}
```

This command:

1. Clones or updates the `main` branch.
2. Creates the `data` directory if needed.
3. Launches the browser when the ROM is present.
4. Opens the ROM folder when the ROM is missing.

Install location:

```text
%USERPROFILE%\Thorfect-Dark
```

## Using the Browser

Launch:

```text
perfect_thork_browser.exe
```

The browser lets you:

* View public servers
* Host a public coop game
* Host a public Combat Simulator game
* Join public servers
* Chat in the master lobby
* Prefer LAN routing automatically when the browser can confirm both players are on the same local network

When hosting:

* Select `Co-Op` to launch `coop-pd.x86_64.exe`
* Select `Combat Simulator` to launch `combat-pd.x86_64.exe`

When joining:

* Joining a coop listing launches `coop-pd.x86_64.exe`
* Joining a Combat Simulator listing launches `combat-pd.x86_64.exe`

The browser also passes the correct host, join, player-name, port, and net-mode arguments automatically.

## Run the Game Directly

Direct launching is supported, but it bypasses the browser's automatic routing and host or join setup.

Coop executable:

```text
coop-pd.x86_64.exe
```

Combat executable:

```text
combat-pd.x86_64.exe
```

If you launch these directly, you may need to supply command-line arguments yourself depending on what you are testing.

## Run the Master Server

Launch:

```text
perfect_thork_master.exe
```

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
| Carrington Villa | Working                  |
| Chicago          | Broken                   |
| Other missions   | Untested or experimental |

### Combat Simulator

Combat Simulator netplay is also experimental. It may work for testing, but it still has known sync and gameplay issues inherited from the underlying network implementation.

### General

Expect:

* Desyncs
* Crashes
* Incomplete mission scripting
* Visual inconsistencies
* Mode-specific bugs
* Cases where one executable works better than the other

## Config and Logs

Common runtime files may include:

* `pd.ini`
* `perfect_thork_settings.json`
* `pd.log`
* `pd-client.log`

These files can help when diagnosing launch, connection, or gameplay issues.

## Updating Later

Run the install command again to update to the latest `main` branch commit.

That command resets tracked files to the published branch state before launching the browser. Keep backups of any local experiments you do not want overwritten.

## Version Notes

### July 29, 2026

* Browser launcher updated to route by mode
* Coop host and join now use `coop-pd.x86_64.exe`
* Combat Simulator host and join now use `combat-pd.x86_64.exe`
* README updated to reflect the full launcher and master-server workflow

## Disclaimer

This is an experimental fan-made networking modification. It is not affiliated with or endorsed by Rare, Nintendo, Microsoft, or the original Perfect Dark developers.

A legally obtained Perfect Dark ROM is required and is not distributed by this repository.
