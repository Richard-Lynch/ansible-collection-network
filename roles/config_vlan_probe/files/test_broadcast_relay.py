#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for broadcast_relay.py's decisions and packet building. Stdlib only.

Both directions per rule: a case that must act and a near-miss that must not. The expensive failures are a
relay that forwards what it should not — a unicast, a packet from another segment (which is how
a loop or an amplifier starts), a flood — and one that emits a malformed packet, which the
receiver drops silently and which therefore reads exactly like "nothing is listening".
"""

from __future__ import annotations

import os
import socket
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broadcast_relay import (  # noqa: E402
    IP_PKTINFO,
    MAX_PAYLOAD,
    RateLimiter,
    build_packet,
    ip_checksum,
    out_destination,
    pktinfo_dst,
    validate,
    verdict,
)

RELAY = {
    "name": "game-lan",
    "port": 47777,
    "from_iface": "eth3",
    "to_iface": "eth4",
    "from_network": "198.51.100.0/24",
    "from_broadcast": "198.51.100.255",
    "to_broadcast": "203.0.113.255",
}


class Verdict(unittest.TestCase):
    def test_limited_broadcast_from_the_source_leg_is_relayed(self):
        self.assertEqual(verdict("198.51.100.4", "255.255.255.255", 40, RELAY), "relay")

    def test_directed_broadcast_of_the_source_leg_is_relayed(self):
        self.assertEqual(verdict("198.51.100.4", "198.51.100.255", 40, RELAY), "relay")

    def test_unicast_to_this_guest_is_not(self):
        # Near-miss: same port, same leg, but addressed to the guest itself.
        self.assertEqual(verdict("198.51.100.4", "198.51.100.10", 40, RELAY), "not_broadcast")

    def test_the_other_legs_broadcast_is_not(self):
        self.assertEqual(verdict("198.51.100.4", "203.0.113.255", 40, RELAY), "not_broadcast")

    def test_a_foreign_source_is_dropped_which_is_the_loop_guard(self):
        # What a reverse relay would see of THIS relay's output: a source from the first leg's
        # subnet arriving on the second leg.
        reverse = dict(RELAY, from_network="203.0.113.0/24", from_broadcast="203.0.113.255")
        self.assertEqual(verdict("198.51.100.4", "255.255.255.255", 40, reverse), "foreign_source")

    def test_size_cap(self):
        self.assertEqual(
            verdict("198.51.100.4", "255.255.255.255", MAX_PAYLOAD + 1, RELAY),
            "too_large",
        )
        self.assertEqual(verdict("198.51.100.4", "255.255.255.255", MAX_PAYLOAD, RELAY), "relay")

    def test_garbage_source(self):
        self.assertEqual(verdict("not-an-ip", "255.255.255.255", 1, RELAY), "bad_source")


class Destination(unittest.TestCase):
    def test_limited_stays_limited_directed_is_translated(self):
        self.assertEqual(out_destination("255.255.255.255", RELAY), "255.255.255.255")
        self.assertEqual(out_destination("198.51.100.255", RELAY), "203.0.113.255")


class Packet(unittest.TestCase):
    def test_fields_and_checksum(self):
        pkt = build_packet("198.51.100.4", 51234, "255.255.255.255", 47777, b"hello")
        ver_ihl, _tos, total, _id, _frag, ttl, proto, csum, src, dst = struct.unpack(
            "!BBHHHBBH4s4s", pkt[:20]
        )
        self.assertEqual(ver_ihl, 0x45)
        self.assertEqual(total, 20 + 8 + 5)
        self.assertEqual(proto, socket.IPPROTO_UDP)
        self.assertEqual(ttl, 64)
        # THE PRESERVED SOURCE: the whole point of the relay.
        self.assertEqual(socket.inet_ntoa(src), "198.51.100.4")
        self.assertEqual(socket.inet_ntoa(dst), "255.255.255.255")
        # A header whose checksum field is correct sums to zero.
        self.assertEqual(ip_checksum(pkt[:20]), 0)
        self.assertNotEqual(csum, 0)
        sport, dport, ulen, ucsum = struct.unpack("!HHHH", pkt[20:28])
        self.assertEqual((sport, dport, ulen, ucsum), (51234, 47777, 13, 0))
        self.assertEqual(pkt[28:], b"hello")


class Rate(unittest.TestCase):
    def test_burst_then_refill(self):
        r = RateLimiter(3, now=0.0)
        self.assertEqual([r.allow(0.0) for _ in range(4)], [True, True, True, False])
        self.assertFalse(r.allow(0.1))  # 0.3 tokens: not yet
        self.assertTrue(r.allow(0.5))  # refilled past 1


class PktInfo(unittest.TestCase):
    def test_reads_the_header_destination(self):
        data = struct.pack(
            "i4s4s",
            3,
            socket.inet_aton("198.51.100.10"),
            socket.inet_aton("255.255.255.255"),
        )
        # The module's own constant: IP_PKTINFO is 8 on Linux (the target) but 26 on macOS.
        self.assertEqual(pktinfo_dst([(socket.IPPROTO_IP, IP_PKTINFO, data)]), "255.255.255.255")

    def test_no_pktinfo_is_none_so_the_packet_is_dropped(self):
        self.assertIsNone(pktinfo_dst([]))
        self.assertEqual(verdict("198.51.100.4", "", 1, RELAY), "not_broadcast")


class Config(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate({"relays": [RELAY]}), [])

    def test_refuses_empty_same_leg_and_missing_keys(self):
        self.assertIn("no relays declared", validate({"relays": []}))
        self.assertTrue(validate({"relays": [dict(RELAY, to_iface="eth3")]}))
        broken = dict(RELAY)
        del broken["from_network"]
        self.assertTrue(validate({"relays": [broken]}))


if __name__ == "__main__":
    unittest.main(verbosity=1)
