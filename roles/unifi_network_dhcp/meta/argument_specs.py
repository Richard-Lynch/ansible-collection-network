# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Reconcile per-network DHCP settings on a UniFi controller",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "unifi_network_dhcp_host": OptionSpec(
                    type="str",
                    required=True,
                    description=["Address of the UniFi controller (e.g. a UniFi gateway)."],
                ),
                "unifi_network_dhcp_site": OptionSpec(
                    type="str",
                    required=False,
                    default="default",
                    description=[
                        "UniFi site name — the controller's internal reference, not the display name.",
                    ],
                ),
                "unifi_network_dhcp_api_key": OptionSpec(
                    type="str",
                    required=False,
                    default="CHANGE_ME_VIA_1PASSWORD",
                    description=[
                        "API key sent as the X-API-KEY header. Supply it from a secrets manager; the placeholder "
                        "is rejected. A lookup that silently returns an empty string makes every request 401 "
                        "in a way that looks like a scope error, so check the lookup before the key.",
                    ],
                ),
                "unifi_network_dhcp_validate_certs": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Whether to validate the controller's TLS certificate. The UDM presents a self-signed cert.",
                    ],
                ),
                "unifi_network_dhcp_networks": OptionSpec(
                    type="list",
                    elements="dict",
                    required=False,
                    default=[],
                    description=[
                        "Desired per-network state. Any setting omitted from an entry is left exactly as the "
                        "controller has it — this role is a reconciler, not a template.",
                    ],
                    options={
                        "vlan": OptionSpec(
                            type="int",
                            required=True,
                            description=[
                                "VLAN id, matched against the controller's live network objects. The role fails "
                                "if the VLAN does not exist rather than guessing.",
                            ],
                        ),
                        "dhcpd_enabled": OptionSpec(
                            type="bool",
                            required=False,
                            description=(
                                "Whether the UDM serves DHCP on this network. Set false to hand "
                                "DHCP authority to Kea — the network keeps its subnet and "
                                "gateway, it simply stops answering DHCP."
                            ),
                        ),
                        "dhcpd_start": OptionSpec(
                            type="str",
                            required=False,
                            description=["First address of the dynamic DHCP pool."],
                        ),
                        "dhcpd_stop": OptionSpec(
                            type="str",
                            required=False,
                            description=["Last address of the dynamic DHCP pool."],
                        ),
                        "dhcpd_leasetime": OptionSpec(
                            type="int",
                            required=False,
                            description=[
                                "DHCP lease lifetime in seconds. Clients renew at T1 (50%), so this "
                                "sets how quickly a change to handed-out settings — resolvers above "
                                "all — reaches the fleet.",
                            ],
                        ),
                        "dhcpd_dns": OptionSpec(
                            type="list",
                            elements="str",
                            required=False,
                            description=[
                                "Resolvers handed to clients, in order. Maps to dhcpd_dns_1 through dhcpd_dns_4.",
                            ],
                        ),
                        "dhcp_relay_enabled": OptionSpec(
                            type="bool",
                            required=False,
                            description=[
                                "Whether this network RELAYS DHCP to an external server instead of "
                                "serving it locally. Mutually exclusive with dhcpd_enabled: the UDM "
                                "is either the DHCP server for a network or a relay for it, never "
                                "both. Always set alongside dhcp_relay_servers — enabling relay "
                                "with no target silently relays to nothing, which is an outage.",
                            ],
                        ),
                        "dhcp_relay_servers": OptionSpec(
                            type="list",
                            elements="str",
                            required=False,
                            description=[
                                "DHCP relay targets. Only meaningful on networks where relay is enabled.",
                            ],
                        ),
                    },
                ),
                "unifi_network_dhcp_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "When false (the default) the role reports the computed diff and changes nothing.",
                        "Set true to PUT the changes. This edits the router every VLAN depends on — always run "
                        "once with false and read the diff first.",
                    ],
                ),
            },
        )
    }
)
