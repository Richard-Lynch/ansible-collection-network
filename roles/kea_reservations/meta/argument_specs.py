# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

# Shared by every entrypoint: where the per-host declarations live.
_DIR = OptionSpec(
    type="str",
    required=True,
    description=[
        "Directory holding one YAML file per reserved host.",
        "",
        "No default: where the declarations live is the caller's decision. If it is given",
        "relative to `playbook_dir`, note that is the directory of the play being RUN, not of",
        "this role, so plays in different directories need an absolute or project-relative path.",
    ],
)


argument_specs = ArgumentSpecs(
    argument_specs={
        # ---- main: merge + validate ---------------------------------------------------------
        "main": ArgumentSpec(
            short_description="Merge and validate per-host Kea DHCP reservations",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "kea_reservations_dir": _DIR,
                "kea_reservations_require_why": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Require every declaration to explain why its address must not move.",
                        "",
                        "ON by default, and the reason is not bureaucratic: the rationale is the",
                        "most valuable part of a reservation and the part that cannot be",
                        "reconstructed later. That an address is hardcoded in a dozen agents'",
                        "configs, is the storage portal a stack mounts through, or sits behind",
                        "router port forwards is not visible in the address, so the next person",
                        "either keeps a reservation nobody can justify or moves one that silently",
                        "breaks things.",
                    ],
                ),
                "kea_reservations_extra": OptionSpec(
                    type="list",
                    required=False,
                    elements="dict",
                    default=[],
                    description=[
                        "Reservations merged IN ADDITION to the directory, validated identically.",
                        "",
                        "Useful when migrating from a single inventory list: the old list can be",
                        "merged alongside the per-host files so both can be proven equivalent",
                        "before the old one is deleted. Normally empty.",
                    ],
                ),
            },
        ),
        # ---- assert_reserved: the provisioning gate ------------------------------------------
        "assert_reserved": ArgumentSpec(
            short_description="Gate provisioning on a reservation being declared AND live",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "kea_reservations_dir": _DIR,
                "reservation_host": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "The hostname whose reservation must exist. Matches the declaration's",
                        "FILENAME (`<host>.yml`), which is also its `hostname` field.",
                    ],
                ),
                "reservation_expected": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Set false to DECLARE that this host deliberately has no reservation.",
                        "",
                        "Needed for genuine bootstrap cases — the host that runs Kea cannot gate on",
                        "the Kea it is about to run — and for consumer devices that lease normally.",
                        "A declared exception, not a silently-skipped check: pair it with a comment",
                        "saying why, the same shape as kea_inpool_reservations_allowed.",
                    ],
                ),
                "reservation_check_live": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Also verify the reservation is LIVE in the running Kea, not merely",
                        "declared on disk.",
                        "",
                        "This is the half that makes the gate mean anything. A file in the repo",
                        "proves someone wrote it; it says nothing about whether Kea would honour it",
                        "— and the two diverge routinely, because service_kea_dhcp restarts only",
                        "`when: deployment_config_changed`, so a re-render after a failed run",
                        "leaves the process serving stale config from memory while every file on",
                        "disk looks right.",
                        "",
                        "Set false only where the live check cannot work (no path to the Kea host).",
                    ],
                ),
                "reservation_kea_host": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Inventory host running Kea; the live check is delegated to it.",
                    ],
                ),
                "reservation_kea_container": OptionSpec(
                    type="str",
                    required=False,
                    default="kea_dhcp",
                    description=["Kea container name on that host."],
                ),
            },
        ),
        # ---- declare: scaffold one declaration -----------------------------------------------
        "declare": ArgumentSpec(
            short_description="Write one validated reservation declaration",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                "kea_reservations_dir": _DIR,
                "reservation_host": OptionSpec(
                    type="str",
                    required=True,
                    min_length=1,
                    description=[
                        "Short hostname. Becomes the filename AND the `hostname` field, which Kea",
                        "qualifies with the subnet's ddns suffix — so never pass an FQDN.",
                    ],
                ),
                "reservation_subnet": OptionSpec(
                    type="int",
                    required=True,
                    description=["VLAN id. Must exist in kea_vlans."],
                ),
                "reservation_mac": OptionSpec(
                    type="str",
                    required=True,
                    pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$",
                    description=["MAC address, colon-separated."],
                ),
                "reservation_ip": OptionSpec(
                    type="str",
                    required=True,
                    description=["Address to pin. Must be in the subnet's reserved band."],
                ),
                "reservation_why": OptionSpec(
                    type="str",
                    required=True,
                    min_length=10,
                    description=[
                        "What breaks if this address moves. Required, and min-length'd so it",
                        "cannot be satisfied with 'n/a'.",
                    ],
                ),
                "reservation_declare_apply": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Generate-don't-apply: report the file that WOULD be written and change",
                        "nothing unless true. Matches the house convention for anything that",
                        "writes.",
                    ],
                ),
            },
        ),
    }
)
