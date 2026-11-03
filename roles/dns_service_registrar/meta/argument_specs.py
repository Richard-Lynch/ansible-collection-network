# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Reconcile a svc.* zone against the services a host runs",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "svc_dns_zone": OptionSpec(
                    type="str",
                    required=True,
                    description="The service zone to reconcile, e.g. svc.lab.vlans.example.com.",
                ),
                "svc_dns_target": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "The owning host's DDNS-registered FQDN, e.g. app1.lab.vlans.example.com. "
                        "Every record written points here, and it doubles as the ownership marker "
                        "that scopes garbage collection in a shared zone."
                    ),
                ),
                "svc_dns_names": OptionSpec(
                    type="list",
                    elements="str",
                    required=True,
                    description="Service labels this host should have, derived from its traefik routers.",
                ),
                "svc_dns_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description="Generate-don't-apply: report the diff unless explicitly true.",
                ),
                "svc_dns_ttl": OptionSpec(type="int", required=False, default=60),
                "svc_tsig_key_name": OptionSpec(type="str", required=False, default="svc-key"),
                "svc_tsig_key_algorithm": OptionSpec(
                    type="str", required=False, default="hmac-sha256"
                ),
                "svc_tsig_key_secret": OptionSpec(
                    type="str",
                    required=True,
                    description="TSIG key for svc.* zones. From vault; never defaulted.",
                ),
                "bind9_addr": OptionSpec(
                    type="str",
                    required=True,
                    description="Address of the bind9 server the zone is read from and updated on.",
                ),
            },
        ),
    }
)
