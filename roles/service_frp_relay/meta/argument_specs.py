# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Deploy an frps TCP relay on a public host (dashboard off or loopback-only)",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                "frp_version": OptionSpec(
                    type="str",
                    required=False,
                    default="v0.65.0",
                    description=["fatedier/frps image tag to deploy."],
                ),
                "frp_deploy_dir": OptionSpec(
                    type="str",
                    required=False,
                    default="/opt/frps",
                    description=[
                        "Directory holding the frps compose file and frps.ini on the relay host."
                    ],
                ),
                "frp_bind_port": OptionSpec(
                    type="int",
                    required=False,
                    default=7000,
                    description=["Control port the frpc client dials out to."],
                ),
                "frp_allow_ports": OptionSpec(
                    type="str",
                    required=False,
                    default="80,443",
                    description=["Ports the relay is permitted to publish (raw TCP passthrough)."],
                ),
                "frp_token": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    description=[
                        "Shared control-channel secret. Source from a secret store; must match frpc.ini.",
                        "No default: a placeholder or a value shorter than 16 characters is rejected",
                        "before anything is rendered.",
                    ],
                ),
                "frp_dashboard_enabled": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Dashboard OFF by default (an admin panel with basic auth only). If true,",
                        "the template hard-binds it to 127.0.0.1 (reach it via SSH tunnel only).",
                    ],
                ),
                "frp_dashboard_port": OptionSpec(
                    type="int",
                    required=False,
                    default=7500,
                    description=["Dashboard port (loopback-only when enabled)."],
                ),
                "frp_dashboard_user": OptionSpec(
                    type="str",
                    required=False,
                    default="admin",
                    description=["Dashboard basic-auth user (only used when enabled)."],
                ),
                "frp_dashboard_pwd": OptionSpec(
                    type="str",
                    required=False,
                    no_log=True,
                    description=[
                        "Dashboard basic-auth password; source from a secret store. No default:",
                        "required (at least 12 characters, not a placeholder) when the dashboard is enabled.",
                    ],
                ),
            },
        )
    }
)
