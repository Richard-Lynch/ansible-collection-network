# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Create or update a WLAN (SSID) on the UniFi controller",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "unifi_wlan_ssid": OptionSpec(
                    type="str",
                    required=True,
                    description="The SSID to create or update.",
                ),
                "unifi_wlan_network_name": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "Name of the UniFi network the SSID attaches to. This decides the VLAN "
                        "clients land on, and therefore which DHCP server they reach."
                    ),
                ),
                "unifi_wlan_passphrase": OptionSpec(
                    type="str",
                    required=True,
                    description="WPA passphrase. Never defaulted, never logged.",
                ),
                "unifi_wlan_model_ssid": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "An EXISTING SSID whose radio/roaming settings a new WLAN is modelled on. "
                        "The UniFi API replaces whole objects, so a WLAN built from scratch would "
                        "drop ~55 fields the controller actually sets."
                    ),
                ),
                "unifi_wlan_hidden": OptionSpec(type="bool", required=False, default=False),
                "unifi_wlan_enabled": OptionSpec(type="bool", required=False, default=True),
                "unifi_wlan_security": OptionSpec(type="str", required=False, default="wpapsk"),
                "unifi_wlan_wpa_mode": OptionSpec(type="str", required=False, default="wpa2"),
                "unifi_wlan_wpa3_support": OptionSpec(type="bool", required=False, default=False),
                "unifi_wlan_wpa3_transition": OptionSpec(
                    type="bool", required=False, default=False
                ),
                "unifi_wlan_pmf_mode": OptionSpec(
                    type="str",
                    required=False,
                    default="optional",
                    description="802.11w protected management frames: disabled|optional|required.",
                ),
                "unifi_wlan_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description="Generate-don't-apply: report the plan unless explicitly true.",
                ),
                "unifi_wlan_host": OptionSpec(
                    type="str", required=True, description="Address of the UniFi controller."
                ),
                "unifi_wlan_site": OptionSpec(type="str", required=False, default="default"),
                "unifi_wlan_validate_certs": OptionSpec(type="bool", required=False, default=False),
                "unifi_wlan_api_key": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "UniFi API key for the X-API-KEY header. Never defaulted, never logged."
                    ),
                ),
            },
        ),
    }
)
