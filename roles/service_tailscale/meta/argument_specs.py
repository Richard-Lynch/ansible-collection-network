# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

DEFAULT_AUTHOR = "Collection maintainers"
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Install Tailscale and join a node, optionally as subnet router/exit node",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "tailscale_login_server": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "Control server URL (a Headscale instance), e.g. https://hs.example.com:8443.",
                    ],
                ),
                "tailscale_auth_key": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    no_log=True,
                    description=[
                        "Pre-auth key, consumed ONLY when the node is not already logged in to",
                        "tailscale_login_server. A node that is already joined ignores it, so a",
                        "re-run needs no new key. Tags come from the key, not from this role.",
                    ],
                ),
                "tailscale_hostname": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=["Name the node registers under (its MagicDNS label)."],
                ),
                "tailscale_advertise_routes": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=["Subnets this node routes for the tailnet (subnet router)."],
                ),
                "tailscale_advertise_exit_node": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=["Offer this node as an exit node for all internet traffic."],
                ),
                "tailscale_accept_dns": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Let the control server rewrite this node's resolver. Off by default: on a",
                        "server — and above all on a DNS server — the tailnet must not take over",
                        "the host's own name resolution.",
                    ],
                ),
                "tailscale_accept_routes": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Install other nodes' subnet routes. Off for a subnet router, which is",
                        "already ON the networks it advertises.",
                    ],
                ),
                "tailscale_tun_path": OptionSpec(
                    type="str",
                    required=False,
                    default="/dev/net/tun",
                    description=[
                        "TUN device the role requires before installing anything. Overridable",
                        "only so a test can prove the gate fires.",
                    ],
                ),
                "tailscale_version": OptionSpec(
                    type="str",
                    required=False,
                    default="1.104.1",
                    description=["Pinned package version from pkgs.tailscale.com/stable."],
                ),
            },
        )
    }
)
