# Thorfect Dark — Network Cooperative Campaign WIP

This branch contains the latest work-in-progress implementation of network cooperative campaign play for the Perfect Dark PC port.

## Current Status

* Native green Network Lobby
* Public master-server registry and lobby chat
* Public server browser
* Network cooperative campaign support
* Carrington Villa is currently working
* Chicago is currently broken
* Packaged Windows game, browser, and master-server executables
* Work in progress: expect crashes, synchronization issues, and mission-specific bugs

## Branch

```text
cooperative-lobby-latest
```

## Requirements

* Windows 10 or Windows 11, 64-bit
* Git for Windows
* Microsoft Visual C++ x64 runtime
* A legally obtained Perfect Dark NTSC-final ROM

The ROM is **not included**.

After downloading the branch, place your ROM at:

```text
data\pd.ntsc-final.z64
```

All players should use the same build and a compatible ROM.

## Recommended Install and Launch Command

Open PowerShell and run the following command:

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; $data="$dir\data"; New-Item -ItemType Directory -Force "$data" | Out-Null; $rom="$data\pd.ntsc-final.z64"; if(Test-Path "$rom"){$exe="$dir\perfect_thork_browser.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"}else{Write-Host "Place your legally obtained ROM at: $rom"; Start-Process -FilePath "explorer.exe" -ArgumentList "$data"}
```

This command:

1. Clones the `cooperative-lobby-latest` branch when it is not already installed.
2. Updates an existing installation to the latest published commit.
3. Creates the required `data` directory.
4. Launches the Thorfect Dark server browser when the ROM is present.
5. Opens the ROM directory when the ROM is missing.

The installation directory is:

```text
%USERPROFILE%\Thorfect-Dark-Coop
```

Place your legally obtained ROM at:

```text
%USERPROFILE%\Thorfect-Dark-Coop\data\pd.ntsc-final.z64
```

After adding the ROM, run the same PowerShell command again.

## Run the Browser

The browser is the recommended way to launch Thorfect Dark because it supplies the appropriate hosting and joining arguments to the game.

This command installs or updates the branch and then launches the browser:

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; $exe="$dir\perfect_thork_browser.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"
```

## Run the Game Directly

This command installs or updates the branch and then launches the game executable directly:

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; $exe="$dir\pd.x86_64.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"
```

Launching the game directly bypasses the server browser. Hosting and joining network games may require command-line arguments normally supplied by the browser.

## Run the Master Server

This command installs or updates the branch and then launches the master-server executable:

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to check out the requested branch."}; git -C "$dir" reset --hard "origin/$branch"; if($LASTEXITCODE -ne 0){throw "Unable to update the installation."}}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"; if($LASTEXITCODE -ne 0){throw "Unable to clone the repository."}}; $exe="$dir\perfect_thork_master.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"
```

Most players do not need to operate their own master server.

## Default Ports

| Service                        | Protocol | Default port |
| ------------------------------ | -------: | -----------: |
| Master registry and lobby chat |      TCP |       `8088` |
| Perfect Dark game traffic      |      UDP |      `27100` |

A player hosting a public game will normally need to forward UDP port `27100` to the hosting computer.

A master-server operator will need to make TCP port `8088` publicly reachable.

Windows Firewall may also ask for permission the first time each executable is launched.

## Cooperative Testing

Current known campaign status:

| Mission          | Status                   |
| ---------------- | ------------------------ |
| Carrington Villa | Working                  |
| Chicago          | Broken                   |
| Other missions   | Untested or experimental |

For the most useful bug reports, include:

* Host and client logs
* Mission and difficulty
* Number of connected players
* Whether the problem occurred on the host, client, or both
* The last objective or mission event completed
* Exact steps needed to reproduce the problem
* Any crash message or screenshot

Relevant logs may include:

```text
pd-client.log
pd-server.log
```

## Updating Later

Run any of the PowerShell launch commands again.

Each command fetches the newest version of `cooperative-lobby-latest` and resets the tracked installation files to the published branch state before launching the selected executable.

Tracked local modifications inside the installation directory will be discarded during an update.

The ROM is an untracked file and will not normally be removed by these commands. Nevertheless, keeping a backup of your ROM is recommended.

## Experimental Software Warning

Thorfect Dark cooperative campaign support is under active development.

Expect crashes, synchronization problems, incomplete mission scripting, visual inconsistencies, and mission-specific bugs. Progress in one mission does not guarantee that another mission will work.

## Disclaimer

This is an experimental, fan-made networking modification. It is not affiliated with or endorsed by Rare, Nintendo, Microsoft, or the original Perfect Dark developers.

A legally obtained Perfect Dark ROM is required and is not distributed by this repository.
