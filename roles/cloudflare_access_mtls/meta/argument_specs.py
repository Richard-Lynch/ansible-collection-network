# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

# Options shared by every entrypoint. Declared once and spread into each ArgumentSpec, because an
# argspec validates EVERY entrypoint against the spec named for it — a `required: true` option that
# only one entrypoint needs breaks all the others before a single task runs.
_COMMON = {
    "cloudflare_access_mtls_action": OptionSpec(
        type="str",
        required=False,
        default="report",
        choices=["report", "ca", "client", "associate"],
        description=[
            "Which entrypoint is running. Informational for `main`, which dispatches on it.",
            "report: read-only — what exists in Cloudflare and 1Password today.",
            "ca: create-or-adopt the CA, store the key in 1Password, upload to Cloudflare.",
            "client: issue client certificates from the declared list (+ iOS .p12 bundles).",
            "associate: reconcile the CA's associated_hostnames only.",
        ],
    ),
    "cloudflare_access_mtls_account_id": OptionSpec(
        type="str",
        required=True,
        description=[
            "Cloudflare account id. Installation-specific, so it has no default.",
        ],
    ),
    "cloudflare_access_mtls_api_token": OptionSpec(
        type="str",
        required=True,
        no_log=True,
        description=[
            "Cloudflare API token with Access: Mutual TLS Certificates Read+Write.",
            "Resolved by the caller from its secret store; never read from a file by the role.",
        ],
    ),
    "cloudflare_access_mtls_vault": OptionSpec(
        type="str",
        required=True,
        description=["1Password vault holding the CA key and client material."],
    ),
    "cloudflare_access_mtls_workdir": OptionSpec(
        type="str",
        required=False,
        default=".mtls-workdir",
        description=[
            "Controller-local scratch directory for key/CSR/cert material.",
            "Keep it out of version control (ignore it as a directory). The authoritative",
            "copy of every private key is 1Password; this is a working area, not storage.",
        ],
    ),
}

# The CA's identity. Separate from _COMMON because only the `ca` and `report` paths read it.
_CA_OPTIONS = {
    "cloudflare_access_mtls_ca_name": OptionSpec(
        type="str",
        required=False,
        default="client-ca",
        description=[
            "Name the CA is registered under in Cloudflare, and the idempotency key.",
            "A CA of this name is ADOPTED, never regenerated — regenerating invalidates every",
            "client certificate already issued from it.",
        ],
    ),
    "cloudflare_access_mtls_ca_subject": OptionSpec(
        type="str",
        required=False,
        default="",
        description=[
            "OpenSSL subject for the CA certificate, e.g.",
            "/C=GB/O=Example Org/CN=Example Org Client CA.",
            "Empty by default so the role carries no organisation identity; the `ca`",
            "entrypoint refuses to run until the caller supplies it.",
        ],
    ),
    "cloudflare_access_mtls_ca_days": OptionSpec(
        type="int",
        required=False,
        default=3650,
        description=[
            "CA validity in days. Long by design: rotating the CA means reissuing every client",
            "certificate and re-associating every hostname.",
        ],
    ),
    "cloudflare_access_mtls_ca_key_bits": OptionSpec(
        type="int",
        required=False,
        default=4096,
        description=["RSA key size for the CA."],
    ),
    "cloudflare_access_mtls_ca_1p_title": OptionSpec(
        type="str",
        required=True,
        description=[
            "1Password item title for the CA PRIVATE KEY. The repository never holds this value."
        ],
    ),
    "cloudflare_access_mtls_hostnames": OptionSpec(
        type="list",
        elements="str",
        required=False,
        default=[],
        description=[
            "Hostnames the CA is associated with in Cloudflare (its associated_hostnames).",
            "A client certificate is only accepted for a hostname in this list, so ADDING A",
            "HOSTNAME HERE IS PART OF ONBOARDING A NEW SERVICE: add its hostname here and an",
            "entry to cloudflare_access_mtls_clients.",
        ],
    ),
}

# THE SEAM. Adding a client is an entry in this list in the calling play's vars — no role change,
# no new tasks, no new code path.
_CLIENT_OPTIONS = {
    "cloudflare_access_mtls_clients": OptionSpec(
        type="list",
        elements="dict",
        required=False,
        default=[],
        description=[
            "DECLARED client certificates. Each entry is data, not code:",
            "  name:      short identifier, used for filenames and the 1Password item title",
            "  common_name: the cert's CN — this is what the Access policy matches on",
            "  hostnames: which hostnames this client is FOR (documentation + the report;",
            "             enforcement is the CA's associated_hostnames plus the Access policy)",
            "  days:      optional validity, defaults to cloudflare_access_mtls_client_days",
            "  p12:       optional bool, bundle a PKCS#12 for iOS import (default false)",
            "Adding a device is one more entry here. The role iterates this list.",
        ],
    ),
    "cloudflare_access_mtls_client_days": OptionSpec(
        type="int",
        required=False,
        default=365,
        description=[
            "Default client-certificate validity. Deliberately shorter than the CA: a device",
            "cert expiring is recoverable, a CA expiring breaks every client at once.",
        ],
    ),
    "cloudflare_access_mtls_client_key_bits": OptionSpec(
        type="int",
        required=False,
        default=2048,
        description=["RSA key size for client certificates."],
    ),
    "cloudflare_access_mtls_p12_password_1p_prefix": OptionSpec(
        type="str",
        required=True,
        description=[
            "1Password title PREFIX for per-client material. Each client gets",
            "<prefix>-<name>-key and, when p12 is requested, <prefix>-<name>-p12-password.",
        ],
    ),
}

_APPLY = {
    "cloudflare_access_mtls_apply": OptionSpec(
        type="bool",
        required=False,
        default=False,
        description=[
            "GENERATE-DON'T-APPLY gate. False (default) reports the real diff and writes",
            "nothing — no key generated, no 1Password item, no Cloudflare upload.",
        ],
    ),
}

_ALL = {**_COMMON, **_CA_OPTIONS, **_CLIENT_OPTIONS, **_APPLY}

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Cloudflare Access mTLS CA and client-certificate lifecycle",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options=_ALL,
        ),
        "report": ArgumentSpec(
            short_description="Read-only: the live CA, its hostnames, and declared vs issued clients",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options=_ALL,
        ),
        "ca": ArgumentSpec(
            short_description="Create-or-adopt the client CA, store its key in 1Password, upload it",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options=_ALL,
        ),
        "client": ArgumentSpec(
            short_description="Issue declared client certificates from the CA (+ optional iOS .p12)",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options=_ALL,
        ),
        "associate": ArgumentSpec(
            short_description="Reconcile the CA's associated_hostnames against the declared list",
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options=_ALL,
        ),
    }
)
