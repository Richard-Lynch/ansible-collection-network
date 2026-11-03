#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wake-on-LAN over HTTP, from a host with a leg on every VLAN.

MANAGED BY ANSIBLE — roles/config_vlan_probe/files/wake_endpoint.py. Edits here are overwritten.

WHY THIS EXISTS. A magic packet is a layer-2 broadcast and cannot cross a VLAN boundary, so it
must originate on the target's own segment. A guest with a leg on each segment is the one place a
packet for ANY of them can be sent from. Exposing that over HTTP means a caller needs no SSH key,
no credential and no leg of its own: a phone, a handheld, a dashboard tile.

It is preferred over an SSH-based relay for exactly that reason: a key on a client device is an
access decision that has to be created, authorised, rotated and stored, and a key that can run
arbitrary commands on a multi-homed guest is a much larger grant than "send this one packet".
Here the grant IS the packet.

WHAT IT DELIBERATELY DOES NOT DO:

  * No arbitrary MAC. A caller names a TARGET from the allowlist this is started with, and the
    MAC/broadcast come from that entry. Accepting a MAC and a broadcast address from the request
    would turn a wake button into a general-purpose packet injector on every segment.
  * No authentication: anyone who can reach the port can list and wake the declared targets, so
    bind or firewall it to trusted segments. That is a deliberate trade and the reason for the
    point above: the blast radius is "something
    on your LAN can power on a machine you already declared wakeable", not "something on your LAN
    can broadcast anything anywhere". If that ever stops being acceptable, add a shared secret
    here — do not widen the allowlist model.
  * No shelling out. The packet is 102 bytes of stdlib socket work; `wakeonlan` is not installed
    and adding a package to a guest whose whole job is network position is not worth it.

GET /wake/<target>   send the packet, then report
GET /healthz         liveness, and the allowlist this process actually loaded
"""

from __future__ import annotations

import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# {target: {"mac": ..., "broadcast": ..., "port": int}} — passed in as JSON by the unit, so the
# allowlist is inventory-declared rather than baked into this file.
TARGETS: dict[str, dict] = {}


def magic_packet(mac: str) -> bytes:
    """Build the 102-byte magic packet: six 0xFF bytes, then the MAC sixteen times."""
    cleaned = mac.replace(":", "").replace("-", "")
    if len(cleaned) != 12:
        raise ValueError(f"malformed MAC {mac!r}")
    packet = b"\xff" * 6 + bytes.fromhex(cleaned) * 16
    # Asserted rather than trusted: a wrong-length packet sends successfully and wakes nothing,
    # which is the silent failure this whole endpoint exists to avoid.
    if len(packet) != 102:
        raise ValueError(f"built a {len(packet)}-byte packet, expected 102")
    return packet


def send_wake(entry: dict) -> None:
    """Broadcast the packet onto the target's own segment.

    SO_BROADCAST is required for a directed broadcast. The OS picks the source interface by
    route, and because this guest holds a leg in the target's subnet that route is the correct
    leg — which is the entire reason the endpoint lives on this host and not on the controller.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(magic_packet(entry["mac"]), (entry["broadcast"], int(entry["port"])))
    finally:
        sock.close()


class Handler(BaseHTTPRequestHandler):
    # Keep the access log on one line and on stderr, so journalctl owns it.
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _reply(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802  (stdlib's casing, not ours)
        path = urlparse(self.path).path.rstrip("/")

        if path == "/healthz":
            # Reports the allowlist it ACTUALLY loaded, not what the file says — the cheap way to
            # tell "the unit restarted with my new target" from "I edited inventory and forgot
            # to re-run the play".
            self._reply(200, {"ok": True, "targets": sorted(TARGETS)})
            return

        if path.startswith("/wake/"):
            name = path[len("/wake/") :]
            entry = TARGETS.get(name)
            if entry is None:
                # Names the allowlist, because the usual cause is a typo or a target that was
                # never declared, and a bare 404 sends the reader to the wrong place.
                self._reply(
                    404,
                    {
                        "ok": False,
                        "error": f"unknown target {name!r}",
                        "known": sorted(TARGETS),
                    },
                )
                return
            try:
                send_wake(entry)
            except Exception as exc:  # noqa: BLE001 — report any failure to the caller verbatim
                self._reply(500, {"ok": False, "target": name, "error": str(exc)})
                return
            # HONEST ABOUT WHAT WAS PROVEN. The packet is unacknowledged UDP, so a 200 here means
            # "sent", never "awake". The caller does the probing — e.g. polling the target
            # afterwards — because only the caller knows what reachability it needs.
            self._reply(
                200,
                {
                    "ok": True,
                    "target": name,
                    "sent_to": f"{entry['broadcast']}:{entry['port']}",
                    "note": "unacknowledged UDP broadcast — sending proves nothing about arrival",
                },
            )
            return

        self._reply(404, {"ok": False, "error": "try /wake/<target> or /healthz"})


def main() -> int:
    global TARGETS
    if len(sys.argv) != 3:
        return print("usage: wake_endpoint.py <listen_port> <targets_json>", file=sys.stderr) or 2

    port = int(sys.argv[1])
    TARGETS = json.loads(sys.argv[2])
    if not TARGETS:
        # Refuse to start rather than serve an endpoint that can only ever 404. A service that is
        # up and useless is harder to diagnose than one that failed loudly at boot.
        print("no targets configured — refusing to start", file=sys.stderr)
        return 1

    for name, entry in TARGETS.items():
        # Validate every entry AT STARTUP, so a malformed MAC is a failed unit at deploy time
        # rather than a 500 on the first press of a tile weeks later.
        magic_packet(entry["mac"])
        if not entry.get("broadcast"):
            print(f"target {name!r} has no broadcast address", file=sys.stderr)
            return 1

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"wake endpoint listening on :{port} for {sorted(TARGETS)}", file=sys.stderr)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
