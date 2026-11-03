# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

DEFAULT_AUTHOR = "Collection maintainers"
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Deploy Traefik as a reverse proxy with Cloudflare DNS-01 certificates",
            description=[
                "Deploys Traefik v3 with Docker Compose: the static configuration, the compose project",
                "and its environment file, and a directory of file-provider route files supplied by the",
                "caller. Certificates come from Let's Encrypt through the Cloudflare DNS-01 challenge,",
                "so a wildcard certificate is possible and no inbound port 80 is needed for issuance.",
                "Route files are DATA: the role ships one generic file (the HTTPS-redirect and",
                "forwarded-proto middlewares its own dashboard router uses) and copies every file in",
                "traefik_dynamic_dir next to it. A route file the role used to deploy is not removed",
                "by deleting it from the source; list it in traefik_retired_dynamic_files.",
            ],
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                "traefik_container_name": OptionSpec(
                    type="str",
                    required=False,
                    default="traefik",
                    description=["Container (and compose service) name."],
                ),
                "traefik_config_dir": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    description=[
                        "Directory on the host holding the compose project, app.env, the static",
                        "config (config/traefik.yml), the route files (config/dynamic/) and the ACME",
                        "store (letsencrypt/). Empty means /opt/<traefik_container_name>.",
                    ],
                ),
                "traefik_network": OptionSpec(
                    type="str",
                    required=False,
                    default="traefik",
                    description=[
                        "Attachable docker network Traefik joins; containers routed by docker labels",
                        "join it too. Created if absent.",
                    ],
                ),
                "traefik_image": OptionSpec(
                    type="str",
                    required=False,
                    default="traefik:v3.3",
                    description=["Image, pinned to a release tag; bump it deliberately."],
                ),
                "traefik_bind_address": OptionSpec(
                    type="str",
                    required=False,
                    default="127.0.0.1",
                    description=[
                        "Host address the HTTP and HTTPS entrypoints are published on. The default",
                        "publishes on loopback only, so nothing is reachable until the caller decides",
                        "it should be. The dashboard router has no authentication of its own, so",
                        "publishing on every interface (an empty string) also publishes the dashboard",
                        "to everyone who can reach the host; restrict it with a firewall or by giving",
                        "a specific address.",
                    ],
                ),
                "traefik_http_port": OptionSpec(
                    type="int",
                    required=False,
                    default=80,
                    description=[
                        "Host port for the web (HTTP) entrypoint, which redirects to HTTPS."
                    ],
                ),
                "traefik_https_port": OptionSpec(
                    type="int",
                    required=False,
                    default=443,
                    description=["Host port for the websecure (HTTPS) entrypoint."],
                ),
                "traefik_timezone": OptionSpec(
                    type="str",
                    required=False,
                    default="UTC",
                    description=["TZ for the container."],
                ),
                "traefik_acme_resolver": OptionSpec(
                    type="str",
                    required=False,
                    default="letsencryptresolver",
                    description=[
                        "Name of the certificate resolver in the static config; route files refer to",
                        "it as tls.certResolver.",
                    ],
                ),
                "traefik_acme_email": OptionSpec(
                    type="str",
                    required=True,
                    description=["Contact address registered with Let's Encrypt."],
                ),
                "traefik_cf_api_email": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Cloudflare account e-mail for the DNS-01 challenge (CF_API_EMAIL).",
                    ],
                ),
                "traefik_cf_dns_api_token": OptionSpec(
                    type="str",
                    required=True,
                    no_log=True,
                    description=[
                        "Cloudflare API token with DNS edit rights on the certificate's zone",
                        "(CF_DNS_API_TOKEN). Written to app.env; supply it from a secret store.",
                    ],
                ),
                "traefik_servers_insecure_skip_verify": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Disable TLS verification for EVERY https upstream (serversTransport). Only",
                        "for backends with self-signed certificates and no better option; prefer a",
                        "per-service serversTransport with the backend's CA.",
                    ],
                ),
                "traefik_dashboard_host": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Hostname of the dashboard and API routers (for example",
                        "traefik.example.com).",
                    ],
                ),
                "traefik_cert_domain": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Main domain of the certificate requested on the dashboard router (for",
                        "example example.com).",
                    ],
                ),
                "traefik_cert_sans": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Subject alternative names for that certificate, comma-separated (for",
                        "example *.example.com for a wildcard).",
                    ],
                ),
                "traefik_dynamic_dir": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Controller directory of file-provider route files (*.yml), copied verbatim",
                        "into config/dynamic/ at mode 0644. Must exist; it may be empty. A file named",
                        "like one the role ships (ssl.yml) is refused.",
                    ],
                ),
                "traefik_dynamic_templates_dir": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    description=[
                        "Optional controller directory of route TEMPLATES (*.j2), rendered into",
                        "config/dynamic/ without the .j2 suffix at mode 0640 — the place for a route",
                        "that carries a secret (a forwardAuth header, an upstream credential). Empty",
                        "means none; a non-empty path must exist.",
                    ],
                ),
                "traefik_retired_dynamic_files": OptionSpec(
                    type="list",
                    elements="str",
                    required=False,
                    default=[],
                    description=[
                        "Basenames of route files to remove from config/dynamic/. The file provider",
                        "serves whatever is in that directory, so a route deleted from the source",
                        "stays live until it is listed here.",
                    ],
                ),
                "traefik_forward_auth_network": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    description=[
                        "Optional existing docker network to a forward-auth service, joined at the",
                        "fixed address traefik_forward_auth_traefik_ip so the auth service can tell",
                        "Traefik's requests from anything else's. Empty means none. The network is",
                        "not created here: it must already exist, be internal, and use",
                        "traefik_forward_auth_subnet (checked before the stack is deployed).",
                    ],
                ),
                "traefik_forward_auth_subnet": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    description=["IPv4 subnet of traefik_forward_auth_network (CIDR)."],
                ),
                "traefik_forward_auth_traefik_ip": OptionSpec(
                    type="str",
                    required=False,
                    default="",
                    description=[
                        "Traefik's fixed address on traefik_forward_auth_network, inside",
                        "traefik_forward_auth_subnet.",
                    ],
                ),
                "traefik_deploy": OptionSpec(
                    type="bool",
                    required=False,
                    default=True,
                    description=[
                        "Bring the stack up (and restart it on a route change). False renders and",
                        "copies the configuration only, for tests.",
                    ],
                ),
            },
        )
    }
)
