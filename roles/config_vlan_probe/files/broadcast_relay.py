#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Relay declared UDP BROADCASTS from one VLAN leg to another, keeping the sender's address.

MANAGED BY ANSIBLE — roles/config_vlan_probe/files/broadcast_relay.py. Edits here are overwritten.

    broadcast_relay.py '<config JSON>'

WHY. LAN game discovery is often a broadcast: a client finds LAN servers by sending ONE UDP
packet to 255.255.255.255:<port>, and a broadcast never leaves its VLAN. A client on one VLAN
therefore cannot see a server on another, although it can reach it perfectly well by unicast.
This guest has a leg on both, so it re-emits that one packet on the other leg.

THE SOURCE ADDRESS IS PRESERVED, and that is the whole design. The server answers discovery with
a UNICAST to whoever asked, and unicast already routes between the VLANs. Re-sent from this
guest's own address, the reply would come back HERE and go nowhere useful; re-sent with the
client's address, it goes straight to the client. Hence a raw IPv4 socket (CAP_NET_RAW, granted
to this unit and nothing else) — the kernel fills in the IP checksum and length, and the UDP
checksum is left 0, which IPv4 permits.

WHAT KEEPS THIS FROM BEING A PACKET INJECTOR on two segments:
  * only DECLARED ports, legs and directions (the config is the allowlist);
  * only packets that ARRIVED as a broadcast (IP_PKTINFO tells destination from sender);
  * only senders whose address is IN the source leg's subnet — which is also the loop guard: a
    packet this relay emitted onto the other leg carries a foreign source there, so a reverse
    relay on that leg drops it instead of bouncing it back;
  * a size cap and a global rate limit, so a flood on one leg cannot be amplified onto another.

STATUS. Writes <status_file> on start and every 30s: the relays as resolved, and per-relay
relayed/dropped counters — the read-back the play asserts on, and the counter a live test checks.
"""

from __future__ import annotations

import ipaddress
import json
import os
import select
import socket
import struct
import sys
import time

IP_PKTINFO = getattr(socket, "IP_PKTINFO", 8)
SO_BINDTODEVICE = getattr(socket, "SO_BINDTODEVICE", 25)
MAX_PAYLOAD = 1400
LIMITED_BROADCAST = "255.255.255.255"


# --------------------------------------------------------------------------------------------
# PURE LOGIC (tested in test_broadcast_relay.py)
# --------------------------------------------------------------------------------------------


def build_packet(src: str, sport: int, dst: str, dport: int, payload: bytes) -> bytes:
    """An IPv4+UDP datagram for a raw IPPROTO_RAW socket.

    Linux fills in the IP header checksum and total length for IP_HDRINCL sockets, but the
    values are set correctly here anyway so the bytes are a valid packet on their own (and the
    tests can check them). UDP checksum 0 = "not computed", valid for IPv4.
    """
    udp_len = 8 + len(payload)
    udp = struct.pack("!HHHH", sport, dport, udp_len, 0) + payload
    total = 20 + udp_len
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,  # version 4, IHL 5
        0,  # DSCP/ECN
        total,
        0,  # identification — kernel fills when 0
        0,  # flags/fragment offset
        64,  # TTL
        socket.IPPROTO_UDP,
        0,  # checksum, filled below
        socket.inet_aton(src),
        socket.inet_aton(dst),
    )
    csum = ip_checksum(header)
    header = header[:10] + struct.pack("!H", csum) + header[12:]
    return header + udp


def ip_checksum(header: bytes) -> int:
    total = 0
    for i in range(0, len(header), 2):
        total += (header[i] << 8) + header[i + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


class RateLimiter:
    """Token bucket: `rate` packets per second, bursting to `rate`."""

    def __init__(self, rate: float, now: float = 0.0) -> None:
        self.rate = float(rate)
        self.tokens = float(rate)
        self.last = now

    def allow(self, now: float) -> bool:
        self.tokens = min(self.rate, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


def verdict(src: str, dst: str, size: int, relay: dict) -> str:
    """'relay', or the reason not to. Pure: no rate limiting here (that needs a clock)."""
    if dst not in (LIMITED_BROADCAST, relay["from_broadcast"]):
        return "not_broadcast"
    try:
        if ipaddress.ip_address(src) not in ipaddress.ip_network(relay["from_network"]):
            return "foreign_source"
    except ValueError:
        return "bad_source"
    if size > MAX_PAYLOAD:
        return "too_large"
    return "relay"


def out_destination(dst: str, relay: dict) -> str:
    """Limited broadcast stays limited; a directed broadcast becomes the OTHER leg's."""
    return LIMITED_BROADCAST if dst == LIMITED_BROADCAST else relay["to_broadcast"]


def pktinfo_dst(ancdata) -> str | None:
    """The packet's destination address from an IP_PKTINFO control message."""
    for level, ctype, data in ancdata:
        if level == socket.IPPROTO_IP and ctype == IP_PKTINFO and len(data) >= 12:
            # struct in_pktinfo { int ifindex; in_addr spec_dst; in_addr addr; }
            return socket.inet_ntoa(data[8:12])
    return None


def validate(cfg: dict) -> list[str]:
    errors = []
    relays = cfg.get("relays") or []
    if not relays:
        errors.append("no relays declared")
    for r in relays:
        for k in (
            "name",
            "port",
            "from_iface",
            "to_iface",
            "from_network",
            "from_broadcast",
            "to_broadcast",
        ):
            if k not in r:
                errors.append("%s: missing %s" % (r.get("name", "?"), k))
        if r.get("from_iface") and r.get("from_iface") == r.get("to_iface"):
            errors.append("%s: from_iface == to_iface" % r.get("name"))
        if not (0 < int(r.get("port", 0)) < 65536):
            errors.append("%s: bad port" % r.get("name"))
    return errors


# --------------------------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------------------------


def log(msg: str) -> None:
    print(time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg, flush=True)


def open_sockets(relay: dict):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    rx.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, relay["from_iface"].encode())
    rx.setsockopt(socket.IPPROTO_IP, IP_PKTINFO, 1)
    rx.bind(("", int(relay["port"])))
    tx = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    tx.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, relay["to_iface"].encode())
    return rx, tx


def write_status(path: str, relays: list[dict], counters: dict, started: float) -> None:
    if not path:
        return
    body = {
        "ok": True,
        "started": started,
        "updated": time.time(),
        "relays": [
            {
                k: r[k]
                for k in (
                    "name",
                    "port",
                    "from_iface",
                    "to_iface",
                    "from_network",
                    "to_broadcast",
                )
            }
            | counters[r["name"]]
            for r in relays
        ],
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, sort_keys=True)
    os.replace(tmp, path)


def main() -> int:
    cfg = json.loads(sys.argv[1])
    errors = validate(cfg)
    if errors:
        log("refusing to start: " + "; ".join(errors))
        return 2
    relays = cfg["relays"]
    limiter = RateLimiter(cfg.get("rate", 20), time.monotonic())
    status_file = cfg.get("status_file", "")
    counters = {r["name"]: {"relayed": 0, "dropped": {}} for r in relays}
    socks = {}
    for r in relays:
        rx, tx = open_sockets(r)
        socks[rx.fileno()] = (rx, tx, r)
        log(
            "relaying UDP %s broadcasts %s -> %s (%s)"
            % (r["port"], r["from_iface"], r["to_iface"], r["name"])
        )
    started = time.time()
    write_status(status_file, relays, counters, started)
    next_status = time.monotonic() + 30
    while True:
        ready, _, _ = select.select([s[0] for s in socks.values()], [], [], 30)
        for rx in ready:
            _, tx, r = socks[rx.fileno()]
            data, anc, _flags, (src, sport) = rx.recvmsg(65535, socket.CMSG_SPACE(12))
            dst = pktinfo_dst(anc) or ""
            why = verdict(src, dst, len(data), r)
            if why == "relay" and not limiter.allow(time.monotonic()):
                why = "rate_limited"
            if why != "relay":
                d = counters[r["name"]]["dropped"]
                d[why] = d.get(why, 0) + 1
                continue
            out = out_destination(dst, r)
            tx.sendto(build_packet(src, sport, out, int(r["port"]), data), (out, 0))
            counters[r["name"]]["relayed"] += 1
            log(
                "%s: %s:%d -> %s:%s (%d bytes)" % (r["name"], src, sport, out, r["port"], len(data))
            )
        if time.monotonic() >= next_status:
            write_status(status_file, relays, counters, started)
            next_status = time.monotonic() + 30


if __name__ == "__main__":
    sys.exit(main())
