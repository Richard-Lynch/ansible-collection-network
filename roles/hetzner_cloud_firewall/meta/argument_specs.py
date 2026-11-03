# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Reconcile a Hetzner Cloud firewall to a declared rule set",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                "hetzner_firewall_name": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "Name of the existing Hetzner Cloud firewall to reconcile. The role",
                        "REFUSES to create one: attaching a new firewall to a live server is how a",
                        "public host loses SSH, and it must be a deliberate console action.",
                    ],
                ),
                "hetzner_api_token": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    min_length=1,
                    description=[
                        "Hetzner Cloud API token with firewall write scope. Supply it from a",
                        "secret store or Ansible Vault; never hardcode it.",
                    ],
                ),
                "hetzner_firewall_rules": OptionSpec(
                    type="list",
                    required=True,
                    elements="dict",
                    description=[
                        "The COMPLETE desired rule set. This is a REPLACE, not a merge — the",
                        "Hetzner API's set_rules endpoint overwrites everything, so a rule omitted",
                        "here is a rule deleted. That is deliberate: the repo is the source of",
                        "truth, and a merge would let console-added rules accumulate invisibly.",
                        "",
                        "Each entry:",
                        "  direction   'in' or 'out'",
                        "  protocol    tcp | udp | icmp | esp | gre",
                        "  port        '22', '80-90', or 'any' (omit for icmp/esp/gre)",
                        "  source_ips       list of CIDRs (direction: in)",
                        "  destination_ips  list of CIDRs (direction: out)",
                        "  description a human reason — REQUIRED by this role's guards, because a",
                        "              rule nobody can justify is a rule nobody dares remove.",
                    ],
                ),
                "hetzner_firewall_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Generate-don't-apply. When false, reports the diff and changes nothing.",
                    ],
                ),
                "hetzner_firewall_required_ports": OptionSpec(
                    type="list",
                    required=False,
                    elements="int",
                    default=[22],
                    description=[
                        "Inbound TCP ports that MUST remain open. Guarded before any write: this",
                        "role runs against a host reachable by exactly one path, and a rule set",
                        "that omits SSH locks everyone out with no way back but the console.",
                    ],
                ),
            },
        ),
    }
)
