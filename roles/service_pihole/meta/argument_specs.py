# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Pi-hole ad-block/forwarding DNS",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "pihole_web_password": OptionSpec(
                    no_log=True,
                    type="str",
                    required=True,
                    description="Web/API password (from your secrets manager). Placeholder is rejected.",
                ),
                "pihole_image": OptionSpec(type="str", required=False),
                "pihole_dns_port": OptionSpec(type="int", required=False, default=5053),
                "pihole_web_http_port": OptionSpec(type="int", required=False, default=5080),
                "pihole_web_https_port": OptionSpec(type="int", required=False, default=5443),
                "pihole_timezone": OptionSpec(type="str", required=False, default="UTC"),
                "pihole_upstreams": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    description="Public DNS upstreams pihole forwards to.",
                ),
                "pihole_listening_mode": OptionSpec(type="str", required=False, default="all"),
                "pihole_adlists": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    description="Ad-block list URLs (gravity rebuilt from these).",
                ),
                "pihole_dns_bind_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Host IP the DNS port publish binds to. Empty/undefined binds all addresses "
                        "(port pihole_dns_port). Set to the service address with pihole_dns_port=53 "
                        "in the Pi-hole-in-front topology so Pi-hole becomes the client-facing "
                        "resolver without also grabbing every other address on the host."
                    ),
                ),
                "pihole_reply_host_ip": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Fixed IPv4 address FTL uses when it auto-answers queries for its OWN "
                        "hostname/pi.hole (FTL's 'local interface' reply logic, pihole.toml "
                        "dns.reply.host). Empty/undefined leaves FTL's default behaviour: it "
                        "detects the interface a query arrived on and answers with THAT address. "
                        "Docker sets the container's kernel hostname to the FULL pihole_hostname "
                        "string (dots included, e.g. 'pihole.example.com'), so FTL's own-hostname "
                        "match fires for that name too, and once Pi-hole is the client-facing front "
                        "door FTL answers from the docker-bridge interface (a 172.x address) instead "
                        "of the service address every other local name uses. Set this to the "
                        "service address in the front-door topology so pi.hole AND the full "
                        "hostname both answer the address bind9 is authoritative for, instead of "
                        "the shadowing address. Rendered as "
                        "FTLCONF_dns_reply_host_force4=true + FTLCONF_dns_reply_host_IPv4=<value>."
                    ),
                ),
                "pihole_rev_servers": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    description=(
                        "Conditional-forwarding ('reverse server') entries, one per CIDR, format "
                        "'<enabled>,<ip-cidr>,<server>[#port][,<domain>]'. Rendered as "
                        "FTLCONF_dns_revServers (pihole.toml dns.revServers). Used for each local "
                        "subnet's reverse zone so Pi-hole delegates them to bind9 instead of sending "
                        "them upstream, and to get real device names instead of bare IPs. Default []."
                    ),
                ),
                "pihole_dnsmasq_lines": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    description=(
                        "Raw dnsmasq config lines for forwarding that pihole_rev_servers cannot "
                        "express (a plain domain not tied to one CIDR, e.g. the primary "
                        "example.com zone). Rendered as FTLCONF_misc_dnsmasq_lines. Default []. Advanced — "
                        "malformed lines can break DNS resolution entirely."
                    ),
                ),
                "pihole_allow_domains": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=(
                        "Domains ALWAYS allowed, reconciled via the Pi-hole v6 REST API "
                        "(/api/domains). Repo list is the source of truth; entries not in this list "
                        "are removed from Pi-hole on apply. Add single-domain overrides here — see "
                        "the README for exactly where."
                    ),
                ),
                "pihole_deny_domains": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Domains ALWAYS blocked, reconciled the same way as pihole_allow_domains.",
                ),
                "pihole_allow_regex": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=(
                        "Regex allow rules (kind=regex, not exact), reconciled the same way as "
                        "pihole_allow_domains via the v6 REST API. Separate from pihole_allow_domains "
                        "so an exact domain is never silently reinterpreted as a pattern."
                    ),
                ),
                "pihole_deny_regex": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Regex deny rules, reconciled the same way as pihole_allow_regex.",
                ),
                "pihole_groups": OptionSpec(
                    type="list",
                    elements="dict",
                    required=False,
                    default=[],
                    description="Reserved for future group management (cheap to add; see README).",
                ),
                "pihole_clients": OptionSpec(
                    type="list",
                    elements="dict",
                    required=False,
                    default=[],
                    description="Reserved for future client management (cheap to add; see README).",
                ),
                "pihole_domains_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=(
                        "Generate-don't-apply for domain rule reconciliation: false (default) "
                        "reports the drift between the repo list and Pi-hole's live domains and "
                        "changes nothing; true reconciles via the REST API (add missing, remove "
                        "extra)."
                    ),
                ),
                "pihole_api_host": OptionSpec(
                    type="str",
                    required=False,
                    default="127.0.0.1",
                    description="Address manage_domains calls the Pi-hole REST API on.",
                ),
                "pihole_domains_managed_comment": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Comment stamped on every domain rule this role creates, and the only "
                        "marker manage_domains uses to decide a live rule is safe to remove. "
                        "Rules with any other comment (added by hand in the web UI) are never "
                        "touched."
                    ),
                ),
            },
        ),
        "manage_domains": ArgumentSpec(
            short_description="Reconcile Pi-hole allow/deny domain rules via the v6 REST API (present/absent)",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "pihole_allow_domains": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Domains ALWAYS allowed. Source of truth — see defaults/main.yml.",
                ),
                "pihole_deny_domains": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Domains ALWAYS blocked. Source of truth — see defaults/main.yml.",
                ),
                "pihole_allow_regex": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Regex allow rules (kind=regex). Source of truth — see defaults/main.yml.",
                ),
                "pihole_deny_regex": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description="Regex deny rules (kind=regex). Source of truth — see defaults/main.yml.",
                ),
                "pihole_domains_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description="false = report the diff only (default); true = reconcile via the API.",
                ),
                "pihole_web_password": OptionSpec(
                    no_log=True,
                    type="str",
                    required=True,
                    description="Web/API password (from your secrets manager). Placeholder is rejected.",
                ),
            },
        ),
    }
)
