# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

DEFAULT_AUTHOR = "Collection maintainers"
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Headscale control server + embedded DERP behind a TLS-terminating traefik",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "headscale_server_hostname": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "Public DNS name clients use to reach the control server. Must already",
                        "resolve to this host — the certificate is issued for it.",
                    ],
                ),
                "headscale_server_port": OptionSpec(
                    type="int",
                    required=False,
                    default=443,
                    description=[
                        "Public HTTPS port traefik listens on. Also the embedded DERP's port:",
                        "Headscale derives the DERP port from server_url, so the two cannot differ.",
                    ],
                ),
                "headscale_public_ipv4": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "Public IPv4 advertised for the embedded DERP/STUN node, so clients can",
                        "reach the relay without a DNS lookup.",
                    ],
                ),
                "headscale_stun_port": OptionSpec(
                    type="int",
                    required=False,
                    default=3478,
                    description=["UDP port for the embedded DERP's STUN listener."],
                ),
                "headscale_derp_region_code": OptionSpec(
                    type="str",
                    required=False,
                    default="headscale",
                    description=["Short code of the embedded DERP region in the DERP map."],
                ),
                "headscale_derp_region_name": OptionSpec(
                    type="str",
                    required=False,
                    default="Headscale embedded DERP",
                    description=[
                        "Display name of the embedded DERP region, shown by `tailscale netcheck`."
                    ],
                ),
                "headscale_ipv4_prefix": OptionSpec(
                    type="str",
                    required=False,
                    default="100.64.0.0/10",
                    description=[
                        "Tailnet IPv4 range. Narrow it when anything else on the hosts involved",
                        "already uses part of 100.64.0.0/10.",
                    ],
                ),
                "headscale_base_domain": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "MagicDNS domain (<node>.<base_domain>). Headscale refuses one equal to, or",
                        "a parent of, the server hostname's domain.",
                    ],
                ),
                "headscale_split_dns": OptionSpec(
                    type="dict",
                    required=False,
                    default={},
                    description=[
                        "Split DNS: {domain: [resolver, ...]}. Queries for these domains go to the",
                        "listed resolvers; everything else uses the client's own DNS.",
                    ],
                ),
                "headscale_users": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=[
                        "Headscale users to ensure exist. Never deletes one that is not listed —",
                        "deleting a user deletes every node it owns.",
                    ],
                ),
                "headscale_policy": OptionSpec(
                    type="dict",
                    required=True,
                    description=[
                        "The tailnet policy (tagOwners, autoApprovers, grants) as data, rendered",
                        "to JSON. An empty dict would mean ALLOW ALL, so the role refuses one.",
                    ],
                ),
                "headscale_acme_email": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=["Let's Encrypt account email for traefik's DNS-01 resolver."],
                ),
                "headscale_cf_dns_api_token": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    min_length=1,
                    description=[
                        "Cloudflare token with DNS edit on the zone, for the DNS-01 challenge.",
                        "DNS-01 because the usual HTTP-01/TLS-ALPN-01 need ports 80/443, which",
                        "may belong to something else on the host.",
                    ],
                ),
                "headscale_deploy_dir": OptionSpec(
                    type="str",
                    required=False,
                    default="/opt/headscale",
                    description=["Directory holding the compose project, config and state."],
                ),
                "headscale_image": OptionSpec(
                    type="str",
                    required=False,
                    default="docker.io/headscale/headscale:0.29.5",
                    description=["Headscale image. Pinned; bump deliberately."],
                ),
                "headscale_traefik_image": OptionSpec(
                    type="str",
                    required=False,
                    default="docker.io/library/traefik:v3.7.15",
                    description=["Traefik image for TLS termination. Pinned; bump deliberately."],
                ),
                "headscale_listen_port": OptionSpec(
                    type="int",
                    required=False,
                    default=8080,
                    description=["Loopback port Headscale serves plain HTTP on, behind traefik."],
                ),
                "headscale_metrics_port": OptionSpec(
                    type="int",
                    required=False,
                    default=9095,
                    description=[
                        "Loopback metrics port. Not Headscale's 9090 default, which collides with",
                        "anything Prometheus-shaped on the same host.",
                    ],
                ),
            },
        )
    }
)
