# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Create or update a network (VLAN) on the UniFi controller",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "unifi_network_name": OptionSpec(type="str", required=True),
                "unifi_network_vlan": OptionSpec(type="int", required=True),
                "unifi_network_subnet": OptionSpec(
                    type="str",
                    required=True,
                    description="Gateway address with prefix, e.g. 192.0.2.1/24.",
                ),
                "unifi_network_domain": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "Short domain name handed to clients. If your DHCP server registers "
                        "clients in DNS by appending a qualifying suffix to this name, it must "
                        "match a zone your DNS server actually serves."
                    ),
                ),
                "unifi_network_dhcp_start": OptionSpec(type="str", required=True),
                "unifi_network_dhcp_stop": OptionSpec(type="str", required=True),
                "unifi_network_model": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "An EXISTING network whose settings a new one is modelled on. The UniFi "
                        "API replaces whole objects, so building one from scratch drops ~40 fields "
                        "the controller sets."
                    ),
                ),
                "unifi_network_apply": OptionSpec(type="bool", required=False, default=False),
                "unifi_network_host": OptionSpec(
                    type="str", required=True, description="Address of the UniFi controller."
                ),
                "unifi_network_site": OptionSpec(type="str", required=False, default="default"),
                "unifi_network_validate_certs": OptionSpec(
                    type="bool", required=False, default=False
                ),
                "unifi_network_api_key": OptionSpec(
                    type="str",
                    required=True,
                    description="UniFi API key for the X-API-KEY header. Never defaulted, never logged.",
                ),
            },
        ),
    }
)
