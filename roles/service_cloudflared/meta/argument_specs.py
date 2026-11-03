# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Deploy a Cloudflare Tunnel client (cloudflared)",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                "cloudflared_container_name": OptionSpec(
                    type="str",
                    required=False,
                    default="cloudflared-tunnel",
                    description=[
                        "Container name. Give every host running its own cloudflared instance a",
                        "DISTINCT name (and cloudflared_config_dir) when the role is deployed more",
                        "than once, each instance with its own tunnel token pointing at a different",
                        "Cloudflare Tunnel.",
                    ],
                ),
                "cloudflared_image": OptionSpec(
                    type="str",
                    required=False,
                    default="cloudflare/cloudflared:2025.7.0",
                    description=[
                        "Image, PINNED to a specific tag — never 'latest', so an upgrade is a reviewed change."
                    ],
                ),
                "cloudflared_config_dir": OptionSpec(
                    type="str",
                    required=False,
                    default="/opt/cloudflared",
                    description=[
                        "Directory holding the compose file on the target host. Must be unique per",
                        "cloudflared instance if a host runs more than one.",
                    ],
                ),
                "cloudflared_network_mode": OptionSpec(
                    type="str",
                    required=False,
                    default="bridge",
                    choices=["bridge", "host"],
                    description=[
                        "Docker network mode. `host` is REQUIRED when the tunnel's ingress points",
                        "at a service on the HOST's loopback (e.g. http://127.0.0.1:3001) — on a",
                        "bridge network `localhost` means the cloudflared container itself and",
                        "every request 502s. Tunnels that reach their origin by DNS name",
                        "(https://proxy.example.com) do not need it, so bridge is the default.",
                    ],
                ),
                "cloudflared_protocol": OptionSpec(
                    type="str",
                    required=False,
                    default="quic",
                    choices=["quic", "http2", "auto"],
                    description=[
                        "Edge transport. `quic` is cloudflared's default and works on most networks,",
                        'but on some paths EVERY dial fails with "timeout: no recent network activity"',
                        "while TCP and UDP 7844 to the same edge IPs are reachable — the symptom of a",
                        "path MTU too small for QUIC's datagrams. Set this to `http2` per host where",
                        "that happens; it uses the TCP/7844 path that already works.",
                    ],
                ),
                "cloudflared_tunnel_token": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    description=[
                        "Cloudflare Tunnel token for THIS instance, from a secret store. No default:",
                        "an empty or placeholder-looking value is rejected by an assert before",
                        "anything is rendered. Every cloudflared instance should use its own distinct",
                        "tunnel/token; never reuse the token from another instance.",
                    ],
                ),
                "cloudflared_deploy": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Whether to actually converge the compose stack. Set false to STAGE config",
                        "only (render the compose file, do not start the container) — used during",
                        "parallel-build cutovers where a second running replica would make Cloudflare",
                        "load-balance live traffic to a not-yet-cut-over host.",
                    ],
                ),
            },
        )
    }
)
