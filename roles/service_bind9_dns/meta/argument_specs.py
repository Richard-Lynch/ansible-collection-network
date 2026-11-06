# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Authoritative bind9 DNS (optionally forwarding) + record task interface",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "ddns_tsig_key_secret": OptionSpec(
                    no_log=True,
                    type="str",
                    required=True,
                    description="TSIG key for Kea DDNS (openssl rand -base64 32). From vault.",
                ),
                "bind9_image": OptionSpec(type="str", required=False),
                "bind9_forward_ip": OptionSpec(
                    type="str",
                    required=False,
                    description="Upstream resolver this bind9 forwards to when recursion is on (forward-only).",
                ),
                "bind9_forward_port": OptionSpec(type="int", required=False, default=5053),
                "bind9_forwarders": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=(
                        "Explicit forwarders, each '<ip>' or '<ip> port <n>'. Non-empty replaces "
                        "bind9_forward_ip/bind9_forward_port. Used when recursion stays on but "
                        "Pi-hole is in front of bind9 (forwarding to it would loop)."
                    ),
                ),
                "bind9_primary_domain": OptionSpec(
                    type="str",
                    required=True,
                    description="The zone this server is authoritative for, e.g. example.com.",
                ),
                "bind9_ns_fqdn": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "NS/SOA nameserver name, with the trailing dot. Defaults to "
                        "`dns.<bind9_primary_domain>.`, the `dns` record every new zone is seeded with."
                    ),
                ),
                "bind9_soa_contact": OptionSpec(
                    type="str",
                    required=False,
                    description="SOA RNAME, with the trailing dot. Defaults to `hostmaster.<bind9_primary_domain>.`.",
                ),
                "bind9_ns_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Address of the `dns` A record a NEW zone file is seeded with, when the caller "
                        "does not pass bind9_dns_ip. Required the first time a zone is created."
                    ),
                ),
                "bind9_allow_transfer": OptionSpec(
                    type="str",
                    required=False,
                    default="none;",
                    description="BIND address-match list allowed to AXFR, `;`-terminated. Default: nobody.",
                ),
                "bind9_recursion": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=(
                        "Whether named recurses (forward-only to bind9_forward_ip) or is "
                        "authoritative-only (recursion no). Leave false when another resolver "
                        "(e.g. Pi-hole) sits in front: clients query it directly and bind9 only "
                        "answers for the zones it is authoritative for."
                    ),
                ),
                "bind9_dns_service_port": OptionSpec(
                    type="int",
                    required=False,
                    default=53,
                    description="Port bind9 publishes on the host (both tcp+udp).",
                ),
                "bind9_dns_service_bind_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Host IP bind9's port publish binds to. Empty/undefined publishes on all "
                        "addresses. Set it to one host address (e.g. a management address) when "
                        "another DNS server on the same host owns the service address's :53."
                    ),
                ),
                "bind9_zones_owner_uid": OptionSpec(
                    type="int",
                    required=False,
                    default=100,
                    description=(
                        "UID that must own the host-side zones directory so DDNS updates can be "
                        "written. The ubuntu/bind9 image runs `named -u bind`, and `bind` is UID "
                        "100 in that image's /etc/passwd (the standard Debian/Ubuntu allocation). "
                        "Without this, the host directory (root:root, mode 0755 by default) has "
                        "no write bit for uid 100, named cannot create the .jnl journal a "
                        "dynamic update requires, and every DDNS UPDATE fails SERVFAIL even "
                        "though TSIG and the zone's allow-update are both correct."
                    ),
                ),
                "bind9_zones_owner_gid": OptionSpec(
                    type="int",
                    required=False,
                    default=101,
                    description="GID paired with bind9_zones_owner_uid (bind's primary group, gid 101).",
                ),
            },
        ),
        "add_domain": ArgumentSpec(
            short_description="Ensure a primary domain zone exists (static)",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "bind9_domain": OptionSpec(type="str", required=True),
            },
        ),
        "add_vlan": ArgumentSpec(
            short_description="Ensure a VLAN forward + reverse zone exists (<vlan>.vlans.<domain>)",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "bind9_vlan_item": OptionSpec(
                    type="dict",
                    required=False,
                    description="VLAN dict {name, domain_name, base, cidr}. Or bind9_vlan.",
                ),
                "bind9_vlan": OptionSpec(type="dict", required=False),
            },
        ),
        "add_host_to_domain": ArgumentSpec(
            short_description="A host registers an A record in a zone (present/absent)",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "bind9_ip": OptionSpec(type="str", required=True),
                "bind9_sub_domain": OptionSpec(type="str", required=True),
                "bind9_parent_domain": OptionSpec(type="str", required=True),
                "bind9_dns_service_bind_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Address dig reaches bind9 on (the dynamic-zone checks). Empty: "
                        "bind9_server_address."
                    ),
                ),
                "bind9_server_address": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Address dig and nsupdate reach bind9 on when bind9_dns_service_bind_ip is "
                        "empty (bind9 publishing on every address). Needed only for records in a "
                        "dynamic zone."
                    ),
                ),
                "bind9_dns_service_port": OptionSpec(type="int", required=False, default=53),
                "bind9_record_infra_exception": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=(
                        "The record's zone is DYNAMIC (Kea-served) and this name can never lease "
                        "(a static-IP host, the DNS/DHCP host itself): reconcile it over RFC 2136 "
                        "against what bind9 serves. Without it a record in a dynamic zone is not "
                        "written; a present one is checked read-only."
                    ),
                ),
                "bind9_record_ttl": OptionSpec(
                    type="int",
                    required=False,
                    default=3600,
                    description="TTL for a record added over RFC 2136 (the infrastructure exception only).",
                ),
                "ddns_tsig_key_secret": OptionSpec(
                    type="str",
                    required=False,
                    no_log=True,
                    description="The TSIG update key (the infrastructure exception only); supplied by the caller.",
                ),
                "ddns_tsig_key_name": OptionSpec(type="str", required=False, default="dhcp-key"),
                "ddns_tsig_key_algorithm": OptionSpec(
                    type="str", required=False, default="hmac-sha256"
                ),
                "bind9_state": OptionSpec(
                    type="str",
                    choices=["absent", "present"],
                    required=False,
                    default="present",
                ),
            },
        ),
        "add_cname_to_domain": ArgumentSpec(
            short_description="A service registers a CNAME in a zone (present/absent)",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "bind9_domain": OptionSpec(
                    type="str",
                    required=True,
                    description="Target FQDN (no trailing dot).",
                ),
                "bind9_sub_domain": OptionSpec(type="str", required=True),
                "bind9_parent_domain": OptionSpec(type="str", required=True),
                "bind9_dns_service_bind_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Address dig reaches bind9 on (the dynamic-zone checks). Empty: "
                        "bind9_server_address."
                    ),
                ),
                "bind9_server_address": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Address dig and nsupdate reach bind9 on when bind9_dns_service_bind_ip is "
                        "empty (bind9 publishing on every address). Needed only for records in a "
                        "dynamic zone."
                    ),
                ),
                "bind9_dns_service_port": OptionSpec(type="int", required=False, default=53),
                "bind9_record_infra_exception": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=(
                        "The record's zone is DYNAMIC (Kea-served) and this name can never lease "
                        "(a static-IP host, the DNS/DHCP host itself): reconcile it over RFC 2136 "
                        "against what bind9 serves. Without it a record in a dynamic zone is not "
                        "written; a present one is checked read-only."
                    ),
                ),
                "bind9_record_ttl": OptionSpec(
                    type="int",
                    required=False,
                    default=3600,
                    description="TTL for a record added over RFC 2136 (the infrastructure exception only).",
                ),
                "ddns_tsig_key_secret": OptionSpec(
                    type="str",
                    required=False,
                    no_log=True,
                    description="The TSIG update key (the infrastructure exception only); supplied by the caller.",
                ),
                "ddns_tsig_key_name": OptionSpec(type="str", required=False, default="dhcp-key"),
                "ddns_tsig_key_algorithm": OptionSpec(
                    type="str", required=False, default="hmac-sha256"
                ),
                "bind9_state": OptionSpec(
                    type="str",
                    choices=["absent", "present"],
                    required=False,
                    default="present",
                ),
            },
        ),
    }
)
