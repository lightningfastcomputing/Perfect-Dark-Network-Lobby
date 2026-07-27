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
* Git
* Microsoft Visual C++ x64 runtime
* A legally obtained Perfect Dark NTSC-final ROM

The ROM is **not included**.

After downloading the branch, place your ROM here:

```text
data\pd.ntsc-final.z64
```

All players should use the same build and compatible ROM.

## Install and Run — PowerShell One-Liner

Open PowerShell and run:

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C $dir fetch origin $branch; git -C $dir checkout -B $branch "origin/$branch"; git -C $dir reset --hard "origin/$branch"}else{git clone --branch $branch --single-branch $repo $dir}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; Start-Process -FilePath "$dir\pd.x86_64.exe" -WorkingDirectory $dir
```

This command:

1. Downloads the `cooperative-lobby-latest` branch.
2. Updates an existing installation to the latest commit.
3. Creates the required `data` directory.
4. Launches the server browser when the ROM is present.
5. Opens the ROM directory when the ROM is missing.

The installation directory is:

```text
%USERPROFILE%\Thorfect-Dark-Coop
```

Place your ROM at:

```text
%USERPROFILE%\Thorfect-Dark-Coop\data\pd.ntsc-final.z64
```

Then run the same one-liner again.

## Run the Browser Directly

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; git -C "$dir" reset --hard "origin/$branch"}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"}; if($LASTEXITCODE -ne 0){throw "Unable to clone or update the repository."}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; $exe="$dir\perfect_thork_browser.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"
```

Launching through the browser is recommended because it supplies the appropriate hosting and joining arguments to the game.

## Run the Game Directly

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; git -C "$dir" reset --hard "origin/$branch"}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"}; if($LASTEXITCODE -ne 0){throw "Unable to clone or update the repository."}; New-Item -ItemType Directory -Force "$dir\data" | Out-Null; $exe="$dir\pd.x86_64.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"```

## Run the Master Server

```powershell
$dir="$HOME\Thorfect-Dark-Coop"; $repo="https://github.com/lightningfastcomputing/Perfect-Dark-Network-Lobby.git"; $branch="cooperative-lobby-latest"; if(Test-Path "$dir\.git"){git -C "$dir" fetch origin "$branch"; if($LASTEXITCODE -ne 0){throw "Unable to fetch the repository."}; git -C "$dir" checkout -f -B "$branch" "origin/$branch"; git -C "$dir" reset --hard "origin/$branch"}elseif(Test-Path "$dir"){throw "The destination already exists but is not a Git repository: $dir"}else{git clone --branch "$branch" --single-branch "$repo" "$dir"}; if($LASTEXITCODE -ne 0){throw "Unable to clone or update the repository."}; $exe="$dir\perfect_thork_master.exe"; if(!(Test-Path "$exe")){throw "Executable not found: $exe"}; Start-Process -FilePath "$exe" -WorkingDirectory "$dir"```

Most players do not need to operate their own master server.

## Default Ports

| Service                  | Protocol | Default Port |
| ------------------------ | -------: | -----------: |
| Master registry and chat |      TCP |         8088 |
| Perfect Dark game        |      UDP |        27100 |

A public game host will normally need to forward UDP port `27100` to the hosting computer.

A master-server operator will need TCP port `8088` reachable.

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
* Whether the problem happened on the host, client, or both
* The last objective or event completed
* Exact steps needed to reproduce the problem

Relevant logs may include:

```text
pd-client.log
pd-server.log
```

## Updating Later

Run the installation one-liner again.

It fetches the newest version of `cooperative-lobby-latest` and resets the installation directory to the published branch state.

Local modifications inside the installation directory will be discarded during an update.

## Disclaimer

This is an experimental fan-made networking modification. It is not affiliated with or endorsed by Rare, Nintendo, Microsoft, or the original Perfect Dark developers.

A legally obtained ROM is required and is not distributed by this repository.
