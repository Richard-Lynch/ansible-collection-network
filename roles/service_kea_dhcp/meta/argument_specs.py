# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

# The shape of one `kea_vlans` entry, declared here rather than imported from a shared
# argspec library so the role carries its whole interface with it.
VLAN_OPTIONS = {
    "id": OptionSpec(type="int", required=True, description=["VLAN id; also the Kea subnet id."]),
    "name": OptionSpec(type="str", required=True, description=["Short VLAN name."]),
    "domain_name": OptionSpec(
        type="str",
        required=True,
        description=["DNS suffix the VLAN's zone sits under; must equal `kea_dns_zone_suffix`."],
    ),
    "gateway": OptionSpec(
        type="str", required=True, description=["Router address, in the form `192.0.2.1`."]
    ),
    "dns": OptionSpec(type="str", required=False, description=["In the form `192.0.2.53`."]),
    "base": OptionSpec(
        type="str", required=True, description=["Subnet base address, in the form `192.0.2.0`."]
    ),
    "cidr": OptionSpec(type="int", required=True, description=["Prefix length."]),
}

# Every option this role actually READS is declared here. An undeclared option is not a small gap:
# Ansible validates ONLY what is declared, so an undeclared `kea_reservations` shape would let a
# `hw_addres` typo produce a reservation Kea renders without the MAC, and nothing until
# `kea-dhcp4 -t` (or nothing at all) would say so.
#
# DEFAULTS ARE GENERATED FROM HERE. The role reads plain names (`kea_pool_offset`) rather than the
# `<name>__default` indirection the generator emits; tasks/_resolve_defaults.yml binds
# `x: "{{ x | default(x__default) }}"` before anything reads x, so tasks and templates keep using
# the plain name. The prose below is emitted as comments into the generated defaults.
RESERVATION_OPTIONS = {
    "subnet_id": OptionSpec(
        type="int",
        required=True,
        description=[
            "The VLAN id this reservation belongs to. MUST match a `kea_vlans[].id`, or the",
            "reservation is silently dropped: the template filters reservations per subnet with",
            "selectattr('subnet_id','equalto', vlan.id), so an id matching no VLAN renders",
            "nowhere and the host quietly keeps leasing from the dynamic pool.",
        ],
    ),
    "hw_address": OptionSpec(
        type="str",
        required=True,
        # Colon-separated MAC, either case. Kea emits lowercase in config-get regardless of what
        # is written here, which is why every comparison against the live config normalises case.
        pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$",
        description=[
            "MAC address, colon-separated (either case).",
            "This is the ONLY thing a reservation matches on: the role sets",
            "`match-client-id: false`, so Kea ignores the client-identifier option entirely.",
            "That is deliberate — a client that sends two different client-ids across reboots",
            "under one MAC does not match its reservation the second time, and is handed a",
            "fresh address from the pool, breaking every consumer pinned to the old one.",
        ],
    ),
    "ip_address": OptionSpec(
        type="str",
        required=True,
        description=[
            "The address to pin. Must sit inside the subnet AND inside its reserved band",
            "(.2 .. .kea_pool_offset) — an in-pool reservation can be leased to another client",
            "before the reserving host next renews. Declare a deliberate exception in",
            "kea_inpool_reservations_allowed rather than deleting the guard.",
        ],
    ),
    "hostname": OptionSpec(
        type="str",
        required=False,
        description=[
            "SHORT hostname, never an FQDN. Kea appends the subnet's ddns-qualifying-suffix",
            "(`<vlan.name>.<vlan.domain_name>.`), so an FQDN here is double-qualified and the",
            "registered name is wrong in a way nothing errors on.",
        ],
    ),
    "why": OptionSpec(
        type="str",
        required=False,
        description=[
            "Why this address must not move — what breaks if it does.",
            "Optional in the ROLE (a caller may legitimately pass a bare reservation), but",
            "REQUIRED by kea_reservations for anything declared in reservations.d/. The",
            "rationale is the most valuable part of a reservation: that an address is hardcoded",
            "in a dozen configs, is a storage portal, or sits behind router port forwards is not",
            "recoverable from the address alone.",
        ],
    ),
}


argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Deploys kea for DHCP and DDNS",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "ddns_tsig_key_secret": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    description="Generate with: openssl rand -base64 32",
                ),
                "kea_vlans": OptionSpec(
                    type="list", required=True, elements="dict", options=VLAN_OPTIONS
                ),
                "kea_dns_servers": OptionSpec(
                    type="list",
                    required=True,
                    elements="dict",
                    options={
                        "ip": OptionSpec(type="str", required=True),
                        "port": OptionSpec(type="str", required=True),
                    },
                ),
                "kea_dhcp4_image_version": OptionSpec(type="str", required=False, default="2.5.8"),
                "kea_ctrl_agent_bind_address": OptionSpec(
                    type="str",
                    required=False,
                    default="127.0.0.1",
                    description=[
                        "Host address the Kea control API (port 8000, unauthenticated) is published"
                        " on. Loopback by default, so only the guest itself can reach it.",
                        "An empty string publishes it on EVERY interface; a published Docker port"
                        " bypasses the host firewall, so do that only on a network you trust.",
                    ],
                ),
                "kea_dhcp_ddns_image_version": OptionSpec(
                    type="str", required=False, default="2.5.8"
                ),
                # ---- reservations -------------------------------------------------------------
                "kea_reservations": OptionSpec(
                    type="list",
                    required=False,
                    elements="dict",
                    default=[],
                    options=RESERVATION_OPTIONS,
                    description=[
                        "DHCP host reservations (static leases), rendered into each subnet's",
                        "`reservations` array. Reserving an address takes it out of the dynamic",
                        "pool for everyone else — the supported way to pin a host.",
                        "",
                        "Normally supplied by kea_reservations, which merges one file per",
                        "host from a reservations directory and validates the set before this",
                        "role ever sees it. A caller may also pass a literal list.",
                        "",
                        "Defaults to [] rather than being required: a Kea with no reservations is",
                        "valid (every client leases dynamically).",
                    ],
                ),
                "kea_reservations_allow_empty": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Permit deploying with NO reservations at all.",
                        "",
                        "An empty reservation set is legitimate but is also exactly what a caller",
                        "gets by forgetting to merge reservations.d — and the two are",
                        "indistinguishable from inside this role. The failure is silent: the config",
                        "renders, `kea-dhcp4 -t` passes, the restart succeeds, and every reserved",
                        "host renumbers at its next renewal, hours later and far from the play that",
                        "caused it.",
                        "",
                        "So an empty set must be DECLARED rather than arrived at. Leave this false",
                        "and merge reservations first; set it true only where a Kea genuinely has",
                        "no reservations.",
                    ],
                ),
                "kea_inpool_reservations_allowed": OptionSpec(
                    type="list",
                    required=False,
                    elements="str",
                    default=[],
                    description=[
                        "Addresses permitted to hold a reservation INSIDE the dynamic pool, by",
                        "explicit exception.",
                        "",
                        "The band guard is right — an in-pool reservation can be leased to another",
                        "client before the reserving host renews — so exceptions are DECLARED here",
                        "rather than achieved by deleting the check. Kea does honour in-pool",
                        "reservations, so the risk is real but bounded, and sometimes an address is",
                        "load-bearing enough that moving it is the larger risk.",
                        "",
                        "Each entry needs a reason recorded next to the reservation itself.",
                    ],
                ),
                # ---- address plan -------------------------------------------------------------
                "kea_pool_offset": OptionSpec(
                    type="int",
                    required=False,
                    default=10,
                    min_value=1,
                    max_value=250,
                    description=[
                        "Offset from each subnet's base address where the DYNAMIC pool starts.",
                        "",
                        "Default address plan (shown for a /24 whose base is .1):",
                        "  .1         gateway (router)",
                        "  .2 - .10   RESERVED BAND — infrastructure statics + DHCP reservations",
                        "  .11 - .251 dynamic DHCP pool",
                        "",
                        "A DHCP reservation whose address falls INSIDE the pool is not safe: Kea",
                        "can hand that address to another client before the reserving host next",
                        "renews (it only honours the reservation for the matching MAC). Keeping",
                        "the band outside the pool makes statics and reservations structurally",
                        "safe instead of relying on luck. 10 => pool starts at base+10 (.11 when",
                        "base is .1).",
                    ],
                ),
                # ---- DNS / DDNS ---------------------------------------------------------------
                "kea_dns_zone_suffix": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "The zone suffix bind9 delegates per-VLAN zones under, e.g.",
                        "`vlans.example.com`. Kea's ddns-qualifying-suffix is built as",
                        "`<vlan.name>.<vlan.domain_name>`, and bind9 serves",
                        "`<vlan.name>.<kea_dns_zone_suffix>` — an assert in tasks/main.yml fails",
                        "the play if any VLAN's domain_name disagrees, so the two can never drift",
                        "apart silently (a domain_name missing the `vlans` label registers every",
                        "name into a zone bind9 does not serve).",
                    ],
                ),
                "kea_ddns_update_on_renew": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Re-assert DNS on every renewal (see kea-dhcp4.conf.template.j2 for the",
                        "full rationale). Kea's own default is false; true makes DDNS self-healing",
                        "after a dropped NCR.",
                    ],
                ),
                "kea_ddns_conflict_mode": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    choices=[
                        "",
                        "check-with-dhcid",
                        "no-check-with-dhcid",
                        "check-exists-with-dhcid",
                        "no-check-without-dhcid",
                    ],
                    description=[
                        "RFC 4703 conflict resolution. EMPTY = Kea's default (check-with-dhcid),",
                        "which is the normal setting. Set to 'no-check-with-dhcid' ONLY",
                        "for the duration of a migration cutover, so DDNS can take ownership of a",
                        "name currently held by a DHCID-less static without a resolution gap.",
                        "Leaving it set disables conflict checking for every subnet — always clear it",
                        "afterwards.",
                    ],
                ),
                # ---- lease timing -------------------------------------------------------------
                "kea_valid_lifetime": OptionSpec(
                    type="int",
                    required=False,
                    default=7200,
                    min_value=60,
                    description=[
                        "Lease lifetime in seconds, pinned rather than inherited from Kea's",
                        "implicit default.",
                    ],
                ),
                "kea_renew_timer": OptionSpec(
                    type="int",
                    required=False,
                    default=3600,
                    min_value=30,
                    description=[
                        "T1. Kea's implicit default is 50% of valid-lifetime; pinned so the",
                        "renewal cadence ddns-update-on-renew depends on is a stated property of",
                        "the config rather than an inherited accident.",
                    ],
                ),
                "kea_rebind_timer": OptionSpec(
                    type="int",
                    required=False,
                    default=6300,
                    min_value=30,
                    description=[
                        "T2. Kea's implicit default is 87.5% of valid-lifetime.",
                    ],
                ),
                # ---- client-facing identity ---------------------------------------------------
                "kea_option_dns_servers": OptionSpec(
                    type="list",
                    required=False,
                    elements="dict",
                    min_length=1,
                    options={
                        "ip": OptionSpec(type="str", required=True),
                        "port": OptionSpec(type="str", required=False),
                    },
                    description=[
                        "The resolver handed to DHCP CLIENTS via option 6 (domain-name-servers).",
                        "Unset: kea_dns_servers.",
                        "",
                        "This is NOT the same thing as the server Kea's own DDNS updates go to.",
                        "When Pi-hole is the client-facing resolver and bind9 is authoritative-only",
                        "(`recursion no`), option 6 must name Pi-hole: a client pointed at bind9",
                        "resolves the local zones and NOTHING else, so image pulls and every other",
                        "external lookup fail with `server misbehaving`.",
                        "",
                        "An explicitly EMPTY list does not fall back (it is defined), and renders",
                        "option 6 empty; the role's non-empty assert exists to catch exactly that.",
                    ],
                ),
                "kea_server_identifier": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "DHCP option 54 — the address clients unicast renewals to. MUST be the",
                        "host's real (service) address, not Kea's docker-internal one.",
                        "",
                        "Kea runs in a container on a bridge behind a 67/udp port map, so left to",
                        "derive it Kea advertises its bridge address and every unicast renewal",
                        "goes nowhere. A well-behaved client falls back to a broadcast rebind",
                        "(which the router's relay rescues) so this LOOKS fine — but any client",
                        "whose DHCP daemon dies instead never re-acquires: the lease expires, the",
                        "address vanishes, and the host sits running-but-unreachable.",
                    ],
                ),
                "kea_match_client_id": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Match reservations on MAC alone; ignore the client-identifier option.",
                        "Safe only where no two hosts share a MAC.",
                    ],
                ),
                "kea_authoritative": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Answer DHCPNAK rather than staying silent when a client REQUESTs an",
                        "address we will not grant. Kea's default is false = ignore, which turns a",
                        "renumber into a slow mystery: the client retries its old address, gets",
                        "nothing, limps to lease expiry and only THEN rediscovers.",
                    ],
                ),
                "kea_socket_type": OptionSpec(
                    type="str",
                    required=False,
                    default="udp",
                    choices=["udp", "raw"],
                    description=[
                        "RELAY-ONLY BY DESIGN. Kea runs in a container behind a port map, so it",
                        "can never legitimately see a client broadcast — every packet it should",
                        "serve arrives as relayed unicast from the router with giaddr set.",
                    ],
                ),
                "kea_service_ip": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "The address the DHCP port map binds to. NOT the wildcard: a UDP socket on",
                        "0.0.0.0 receives broadcasts, which bypass the kernel DNAT and reach",
                        "docker-proxy instead of Kea — the proxy re-sends from its own bridge",
                        "socket, so Kea sees no giaddr and NAKs with 'failed to select a subnet'.",
                        "Binding to a unicast address makes that path impossible.",
                    ],
                ),
                "kea_container_name": OptionSpec(
                    type="str",
                    required=False,
                    default="kea_dhcp",
                    description=[
                        "Container name used by the config-validation and liveness gates.",
                    ],
                ),
            },
        ),
    }
)
