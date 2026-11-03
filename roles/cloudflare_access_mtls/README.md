# cloudflare_access_mtls

Codified lifecycle for a **Cloudflare Access mTLS client CA** and the client certificates issued
from it: generate-or-adopt the CA, store its private key in 1Password, upload it to Cloudflare,
associate it with hostnames, and issue per-device client certificates (with optional PKCS#12
`.p12` bundles for mobile devices) from a **declared list**.

## What it does and does not own

| | |
|---|---|
| **Owns** | the client CA (key in 1Password, cert in Cloudflare), its `associated_hostnames`, and every client certificate + `.p12` declared to it |
| **Does NOT own** | the Access **application** and its **policies**. The calling play owns those |

That split matters: **a client certificate only works when BOTH halves are in place.** The CA
must be associated with the hostname, *and* the hostname's Access app must carry a `non_identity`
policy whose include is a `common_name` matching the certificate's CN. With either half missing,
the request falls through to the ordinary SSO redirect — which reads as "mTLS is broken" and
points at neither half.

A policy that admits a client certificate must use decision `non_identity` (the dashboard's
"Service Auth"), never `bypass`: `bypass` skips identity evaluation, a `common_name` include is
identity-dependent, and Cloudflare resolves the contradiction by denying everyone.

## Plan entitlement

Access mTLS with an uploaded CA is available on Enterprise and pay-as-you-go Zero Trust plans, not
on the Free plan. On an account without the entitlement, `POST /access/certificates` returns HTTP
400 with

```
code 12130  "access.api.error.invalid_request: maximum number of certificates has been reached"
```

while `GET /access/certificates` reports zero CAs — a quota of zero. Error 12130 is the
**Access** certificate quota, not the API Shield BYOCA quota (error `1489`). The role's upload gate
names this case explicitly. **Scope is not entitlement**: a 400 rather than a 403 proves the token
is authorised, not that the account may hold a CA. Where the plan is the blocker, an Access
**service token** works on every plan, for a client that can send two HTTP headers.

## Actions

| `cloudflare_access_mtls_action` | Does |
|---|---|
| `report` (default) | read-only: live CA, association drift, declared-vs-issued clients |
| `ca` | create-or-**adopt** the CA; store the key in 1Password; upload the cert |
| `client` | issue every declared client certificate not already issued (+ `.p12`) |
| `associate` | reconcile the CA's `associated_hostnames` against the declared list |

All writes are behind `cloudflare_access_mtls_apply=true`. The default run reports the real diff
and writes nothing — no key generated, no 1Password item, no Cloudflare call that mutates. The
read-only calls also run under `--check`, so a check-mode run reports from the real state.

## Adding a client — this is the seam

A new device is **a vars entry, not a code change**:

```yaml
cloudflare_access_mtls_hostnames:
  - chat.example.com
  - home.example.com                 # <- 1. the hostname the CA may authenticate for

cloudflare_access_mtls_clients:
  - name: phone-app
    common_name: phone-app.chat.example.com
    hostnames: [chat.example.com]
    p12: true
  - name: tablet-app                 # <- 2. the device
    common_name: tablet-app.home.example.com
    hostnames: [home.example.com]
    p12: true
```

Then re-run `associate` (associates the new hostname), `client` (issues only the new certificate —
the existing one is left untouched), and add the CN to the Access policy for that hostname.

If the hostname is currently protected by something other than Access (a `bypass` app plus a WAF
rule, say), a new, more specific Access app for it **starts enforcing Access** there. Decide
deliberately whether mTLS replaces the existing control or sits beside it.

## Idempotence, and the one thing that is never retried

**A CA that exists is adopted, never regenerated.** Generating a new key pair under the same name
does not update the CA — it produces a *different* CA, and every certificate already issued stops
validating, silently, until a device next connects.

The role therefore treats three locations as one state, and refuses to proceed when they
disagree in the direction that cannot be auto-repaired:

| Cloudflare | 1Password key | Role does |
|---|---|---|
| absent | absent | **generate** — key to 1Password first, then upload |
| absent | present | **re-upload** from the stored key (this is also how a fresh controller recovers) |
| present | present | **adopt** — nothing, reports `ok` not `changed` |
| present | **absent** | **HARD FAIL** — that CA can never sign again; recovering or retiring it is a human decision |

`cloudflare_access_mtls_ca_name` is the idempotency key. Renaming it creates a SECOND CA rather
than renaming the first, and Cloudflare permits duplicate names.

A client certificate is likewise identified by its **1Password item**, not by the workdir (which
is scratch and may be empty). An existing item means "already issued" and the cert is not
reissued — reissuing would invalidate the copy already on the device while reporting success.

## Revocation and rotation — mostly NOT automated

**There is no revocation mechanism at the Cloudflare edge for an uploaded (BYO) CA.** From
Cloudflare's documentation:

> "This check only applies to client certificates issued by the Cloudflare-managed CA. Cloudflare
> currently does **not** check certificate revocation lists (CRL) for CAs that have been
> uploaded."
> — [API Shield: check for revoked certificates](https://developers.cloudflare.com/api-shield/security/mtls/configure/#check-for-revoked-certificates)

So the `cf.tls_client_auth.cert_revoked` field and the dashboard's **Revoke** button apply to the
*Cloudflare-managed* CA, **not to this one**. Enforcing a CRL needs a Worker (Cloudflare ships a
[template](https://github.com/cloudflare/access-crl-worker-template)).

**Therefore: revoke one device by removing its CN from the Access policy.** That is the control
that actually exists, and it is per-device because each certificate has its own CN.

| Goal | How | Automated? |
|---|---|---|
| **Revoke ONE device** | remove its `common_name` from the `non_identity` policy's include list, and its entry from `cloudflare_access_mtls_clients`; archive its 1Password items | the policy edit is, by the play that owns the Access app |
| Reissue ONE device (expiry/lost phone) | archive its 1Password key item, re-run `client` | yes — only that device is reissued |
| Rotate the CA | invalidates **every** issued certificate | **no** — delete the CA + key deliberately, re-run `ca`, reissue every client, redistribute every `.p12` |
| Get a `.p12` onto a device | transfer it, install it, trust the profile on the device | **no** — no Cloudflare or vendor API does this |

Removing a CN from the policy takes effect at the edge immediately, which is why it is the
revocation path worth having rather than a CRL nobody enforces. The certificate itself remains
cryptographically valid until it expires — so treat "removed from the policy" as the boundary, and
keep client validity short (default 365 days) so a forgotten device eventually ages out.

## The credential cache stores a MISS, so an existence test goes stale

This role asks 1Password "does this key already exist?" to decide whether to generate or adopt.
That question **must not** go through `richard_lynch.common.onepassword_cached`.

The cache stores a miss as an **empty string**. That is right for reading a secret that exists
(fetch once, then free and silent) and wrong for an existence *test*: the first run asks before the
item exists, caches `''`, and every later run reads that stale `''` instead of re-asking. **The
negative answer becomes permanent** — and a CA key that is in 1Password then reads as absent, so
the role would choose GENERATE over RE-UPLOAD and create a second CA.

So every existence check here reads 1Password directly with `op item get --vault ... --fields`, and
interprets `rc` rather than only emptiness. It is **`op item get`, not `op read op://...`**: an
item title containing slashes is treated by `op read` as path separators, silently returning `''`.

`op item get --fields` wraps a MULTI-LINE value in literal double quotes; the role strips them,
and then proves the recovered key parses with `openssl pkey` before signing anything.

## `pass:env:VAR` is not `env:VAR`

OpenSSL's `pass:` and `env:` are **different pass-phrase sources**, and `pass:` takes everything
after its colon as the **literal** passphrase. So `-passout pass:env:MTLS_P12_PW` sets the `.p12`
password to the 15-character string `env:MTLS_P12_PW` and never reads the environment — i.e. a
private key protected by a constant. The correct form is a bare `-passout env:MTLS_P12_PW`.

A positive-only check cannot see that class of bug: export and verify sharing the same wrong
syntax agree with each other, on the wrong value. The role therefore also asserts that a
**deliberately wrong password FAILS** to open the bundle.

## Inputs

See `meta/argument_specs.py` (the source of truth; `meta/argument_specs.yml` and `defaults/` are
generated from it).

Required, with no role default: `cloudflare_access_mtls_account_id`,
`cloudflare_access_mtls_api_token`, `cloudflare_access_mtls_vault`,
`cloudflare_access_mtls_ca_1p_title` (the CA key's 1Password item) and
`cloudflare_access_mtls_p12_password_1p_prefix` (the per-client item prefix). The `ca` entrypoint
also refuses an empty `cloudflare_access_mtls_ca_subject`. `cloudflare_access_mtls_hostnames` and
`cloudflare_access_mtls_clients` default to empty lists.

The API token is passed directly (`cloudflare_access_mtls_api_token`, no_log), from any secret
store. **1Password is this role's key store, not just a token source**: the CA private key, every
client key and every `.p12` import password live there, and every entrypoint — `report` included —
reads it with the `op` CLI to decide what exists. A controller without a 1Password service account
cannot use this role.

```yaml
- name: Report the client CA's state
  ansible.builtin.include_role:
    name: richard_lynch.network.cloudflare_access_mtls
  vars:
    cloudflare_access_mtls_action: report
    cloudflare_access_mtls_account_id: "{{ cf_account_id }}"
    cloudflare_access_mtls_api_token: "{{ cf_api_token }}"
    cloudflare_access_mtls_vault: Infrastructure
    cloudflare_access_mtls_ca_name: client-ca
    cloudflare_access_mtls_ca_subject: "/C=GB/O=Example Org/CN=Example Org Client CA"
    cloudflare_access_mtls_ca_1p_title: cloudflare-access-mtls-ca-key
    cloudflare_access_mtls_p12_password_1p_prefix: cloudflare-access-mtls-client
    cloudflare_access_mtls_hostnames: [chat.example.com]
    cloudflare_access_mtls_clients:
      - {name: phone-app, common_name: phone-app.chat.example.com, hostnames: [chat.example.com], p12: true}
```

## The token

Needs **Access: Mutual TLS Certificates Read + Write**
(`4f3196a5c95747b6ad82e34e1d0a694f`, `29d3afbfd4054af9accdd1118815ed05`). Prefer a narrow token
carrying exactly these groups over a broad account token. A 403 on the certificates endpoint is a
**scope** answer, not a verdict on the account's plan — a deliberately-invalid POST returning
**400** proves write scope is present (content rejected) versus **403** (refused).

## Working directory

`.mtls-workdir/` (configurable), mode 0700. **Ignore it in version control as a directory.** It
holds the CA key, client keys and `.p12` bundles. It is a *working area*: the authoritative copy
of every private key is 1Password, and the role recovers the CA from there on a controller with an
empty workdir.

## Deliberately not done

- **No Access app or policy management** — the caller owns that (see the table at the top).
- **No CRL** — see the revocation section; it would need a Worker.
- **No device enrolment** — the `.p12` hop is manual and stated as such in the output.
- **No certificate expiry monitoring.** Nothing warns before a client certificate lapses; the
  symptom would be one device failing to authenticate.

## Testing

`molecule/default/` exercises the client split (`_split_clients.yml`) without a live Cloudflare
account or a real CA: already-issued / to-issue / cannot-tell, and the duplicate-name guard both
ways (it must FAIL on a duplicate). A full converge would mint a real CA on a real account, so
coverage is honestly partial rather than claimed complete.
