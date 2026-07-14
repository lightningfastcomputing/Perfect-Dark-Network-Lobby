# Perfect Thork v0.3.2 dual-route fix

Changes:

- Master accepts IPv4 addresses and DNS hostnames in `Host game IP`.
- Values such as `http://plentyfasthosting.ddns.net:27100` are normalized to `plentyfasthosting.ddns.net`.
- Host registration also publishes the host machine's LAN IPv4 address.
- Clients on the same `/24` LAN automatically join through the LAN address.
- Clients on other networks use the public IPv4/DDNS address.
- The server-list Address column continues to show the public/DDNS endpoint.

Replace both Python files, rebuild both EXEs, restart the master and browser, then stop and re-advertise the server.
