# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

DEFAULT_AUTHOR = "Collection maintainers"
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            description=[
                "Configure a multi-homed VLAN probe guest: the tooling it needs to send",
                "link-local traffic (Wake-on-LAN magic packets, ARP checks) on each segment",
                "it has a leg on, and a position assertion that proves each leg really landed",
                "on the VLAN it was tagged for.",
                "",
                "WHY A POSITION ASSERTION IS PART OF THE ROLE, not an afterthought: a magic",
                "packet is unacknowledged UDP, so a probe sitting on the WRONG broadcast domain",
                "sends successfully and reports success while waking nothing. Liveness is not",
                "coverage.",
            ],
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                # Which segments this guest is expected to be on is INSTALLATION CONFIGURATION,
                # so it is required with NO default. A probe that defaulted to some plausible
                # VLAN list would assert a position it was never asked to hold, and would be
                # silently wrong on any other network.
                "config_vlan_probe_expected": OptionSpec(
                    type="list",
                    elements="dict",
                    required=True,
                    description=[
                        "The segments this guest must be on, one entry per leg.",
                        "Each: {name, id, address, cidr, gateway}. Derive it in the CALLER from",
                        "the same VLAN data that builds the legs — never copy it by hand.",
                    ],
                    options={
                        "name": OptionSpec(type="str", required=True),
                        "id": OptionSpec(type="int", required=True),
                        "address": OptionSpec(type="str", required=True),
                        "cidr": OptionSpec(type="int", required=True),
                        "gateway": OptionSpec(type="str", required=True),
                    },
                ),
                # Packages the probe needs to do link-local work. A default is legitimate here:
                # these are properties of the JOB, not of any one network — any caller wanting a
                # WoL/ARP presence needs exactly these.
                "config_vlan_probe_packages": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=["iputils-arping", "iputils-ping", "iproute2", "dnsutils"],
                    description=[
                        "Tooling installed on the probe.",
                        "NOTE community.general.wakeonlan needs NOTHING here: it builds and",
                        "sends the magic packet from the module's own Python over a UDP socket,",
                        "so no etherwake/wakeonlan binary is required.",
                        "avahi/gssdp and tcpdump are deliberately NOT included — an unused",
                        "daemon on every VLAN is attack surface for a capability nobody asked",
                        "for, and avahi-daemon would make the probe an mDNS PARTICIPANT rather",
                        "than an observer.",
                    ],
                ),
                # -------------------------------------------------------------------------
                # wake_endpoint: Wake-on-LAN over HTTP, from a guest with a leg everywhere.
                # -------------------------------------------------------------------------
                "config_vlan_probe_wake_targets": OptionSpec(
                    type="dict",
                    required=False,
                    default={},
                    description=[
                        "Wakeable targets, as {name: {mac, broadcast, port}}. THE ALLOWLIST IS",
                        "THE SECURITY MODEL: a caller names an entry and cannot supply a MAC or",
                        "a broadcast address, so the endpoint is a wake button rather than a",
                        "packet injector on every segment. Declare them in inventory — they are",
                        "installation facts, and the entrypoint asserts each broadcast lands in a",
                        "subnet this guest actually holds a leg in, because a send into a",
                        "segment it is not on succeeds and wakes nothing.",
                        "Empty (default) means the entrypoint refuses to deploy.",
                    ],
                ),
                "config_vlan_probe_wake_port": OptionSpec(
                    type="int",
                    required=False,
                    default=8080,
                    description=[
                        "TCP port for the HTTP endpoint. Pick one nothing else on the guest uses.",
                        "The endpoint has no authentication; restrict who can reach this port.",
                    ],
                ),
                "config_vlan_probe_wake_unit": OptionSpec(
                    type="str",
                    required=False,
                    default="iaac-wake-endpoint.service",
                    description=[
                        "systemd unit name for the endpoint. The prefix marks it as",
                        "Ansible-managed on the guest; override it to match your own convention.",
                    ],
                ),
                "config_vlan_probe_wake_script": OptionSpec(
                    type="str",
                    required=False,
                    default="/usr/local/bin/iaac_wake_endpoint.py",
                    description=[
                        "Where the endpoint script is installed. Stdlib-only, so there is no",
                        "virtualenv and nothing to install beyond python3.",
                    ],
                ),
                "config_vlan_probe_relays": OptionSpec(
                    type="list",
                    elements="dict",
                    required=False,
                    default=[],
                    options={
                        "name": OptionSpec(
                            type="str",
                            required=True,
                            description="Label, for logs and the status file.",
                        ),
                        "port": OptionSpec(
                            type="int",
                            required=True,
                            description="UDP destination port of the broadcast to relay.",
                        ),
                        "from_broadcast": OptionSpec(
                            type="str",
                            required=True,
                            description="Broadcast address of the leg it is HEARD on, e.g. 192.0.2.255.",
                        ),
                        "to_broadcast": OptionSpec(
                            type="str",
                            required=True,
                            description="Broadcast address of the leg it is RE-EMITTED on.",
                        ),
                    },
                    description=[
                        "UDP broadcasts to carry from one VLAN leg to another, ONE WAY, with the",
                        "sender's address preserved so the answer (a unicast) goes straight back",
                        "to it. For LAN game discovery, which cannot cross a VLAN. THE LIST IS",
                        "THE ALLOWLIST: only these ports, legs and directions. Installation config —",
                        "declare in inventory; the entrypoint asserts both legs are held.",
                    ],
                ),
                "config_vlan_probe_relay_rate": OptionSpec(
                    type="int",
                    required=False,
                    default=20,
                    min_value=1,
                    max_value=1000,
                    description=[
                        "Packets per second the relay re-emits, across all relays — the cap that",
                        "stops a flood on one leg being amplified onto another. Discovery is a",
                        "handful of packets per refresh.",
                    ],
                ),
                "config_vlan_probe_relay_unit": OptionSpec(
                    type="str",
                    required=False,
                    default="iaac-broadcast-relay.service",
                    description="systemd unit name for the relay.",
                ),
                "config_vlan_probe_relay_script": OptionSpec(
                    type="str",
                    required=False,
                    default="/usr/local/bin/iaac_broadcast_relay.py",
                    description="Where the relay script is installed (stdlib-only).",
                ),
                # The gate. Generate-don't-apply: report the position diff by default.
                "config_vlan_probe_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "false (default) reports what would change and asserts position only.",
                        "true installs tooling. Never set from a role default — this is the",
                        "explicit act-vs-report gate.",
                    ],
                ),
            },
        ),
    }
)
