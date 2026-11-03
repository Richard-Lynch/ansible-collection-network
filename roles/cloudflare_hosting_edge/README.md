# cloudflare_hosting_edge

A Cloudflare wildcard edge for hosting tiers, published **once**: per tier, one wildcard tunnel
route, one proxied wildcard CNAME and one wildcard Access application. After it exists a new app
on a tier needs **no DNS, tunnel or Access step** -- a reverse-proxy route on the origin (for
example Traefik labels on the app's compose project) is the whole publication.

| entrypoint | does |
|---|---|
| `main` | tunnel route + DNS + service token + Access app per tier, behind the capture proof below |
| `acm` | orders an Advanced Certificate Manager pack for the wildcards and reads it back **active** |

Options are in [`meta/argument_specs.py`](meta/argument_specs.py). Every Cloudflare id (account,
zone, tunnel, the zone-wide wildcard Access app, the SSO group) is **required with no default**:
each is a fact about one installation.

The wildcard-safety logic is a set of filters in this collection (`hosting_edge_captured`,
`hosting_edge_winner`, `hosting_edge_winner_diff`, `hosting_edge_existing_hosts`,
`hosting_edge_merge_ingress`, `hosting_edge_cert_missing`, ...), each documented with `ansible-doc
-t filter`.

## Example

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Publish the hosting wildcard edge (preview unless cloudflare_hosting_edge_apply)
      ansible.builtin.include_role:
        name: richard_lynch.network.cloudflare_hosting_edge
      vars:
        cloudflare_hosting_edge_tiers:
          dev:
            suffix: dev.example.com
            entrypoint_port: 8080
            cf_id_item: hosting/dev/cf-access-client-id
            cf_secret_item: hosting/dev/cf-access-client-secret
          prod:
            suffix: apps.example.com
            entrypoint_port: 8081
            cf_id_item: hosting/prod/cf-access-client-id
            cf_secret_item: hosting/prod/cf-access-client-secret
        cloudflare_hosting_edge_origin: hosting.internal.example.com
        cloudflare_hosting_edge_account_id: "<account id>"
        cloudflare_hosting_edge_zone_id: "<zone id>"
        cloudflare_hosting_edge_tunnel_id: "<tunnel id>"
        cloudflare_hosting_edge_zone_app_id: "<id of the *.example.com Access app>"
        cloudflare_hosting_edge_sso_group_id: "<Access group id>"
        cloudflare_hosting_edge_api_token: "{{ vault_cloudflare_api_token }}"  # or token_item (1Password)
        cloudflare_hosting_edge_op_vault: "<vault>"   # where apply stores the tier service tokens
```

**The API token** is passed as `cloudflare_hosting_edge_api_token` (no_log) from any secret store,
or read from 1Password with `cloudflare_hosting_edge_token_item` + `cloudflare_hosting_edge_op_vault`.
A preview (`apply: false`) and the `acm` entrypoint need nothing else from 1Password. **An apply of
`main` does**: Cloudflare returns each tier's Access service-token secret exactly once, and the role
stores it in `cloudflare_hosting_edge_op_vault` (items `cf_id_item`/`cf_secret_item`) through
`richard_lynch.common.secrets_manager`, so that apply needs the `op` CLI.

## Why a wildcard needs a proof, not a hope

A wildcard covers names that do not exist yet **and names that do**. Published carelessly it could
re-authenticate `foo.dev.example.com` if that already exists, or stop protecting a name an
existing app deliberately treats differently. Before any write the role:

1. reads **every** DNS record (and asserts the listing is complete, not truncated), every tunnel's
   ingress hostnames and every Access app's domains;
2. **fails if any existing hostname falls under a new wildcard** (`hosting_edge_captured`), at any
   depth, while correctly treating the wildcard's own apex and suffix lookalikes
   (`xdev.example.com`) as *not* captured;
3. **fails if adding the new apps would change which Access app wins for any existing hostname**
   (`hosting_edge_winner_diff`, most-specific-wins), computed on the real app list with the new
   apps added -- defence in depth behind (2);
4. refuses a tier whose wildcard is not strictly below the zone, which would overwrite the
   zone-wide `*.example.com` application.

After the write it re-reads and asserts the same, plus that the zone-wide wildcard app is
unchanged. It **never** edits that app and never uses `bypass`.

## Tunnel safety

`PUT .../configurations` replaces the whole ingress list. The merge (`hosting_edge_merge_ingress`)
keeps every pre-existing rule byte-identical, places the wildcard rules before the catch-all, and
raises if the catch-all is missing, duplicated or not last, or if a route it is asked to own is not
a wildcard. The read-back asserts nothing pre-existing changed.

## ACM

The Universal certificate covers the zone and **one** label below it. `hello.dev.example.com` is
two labels down, so without an advanced pack Cloudflare proxies the request and serves a
certificate that does not name it -- which looks like the tunnel or Access being broken and is
neither. The `acm` entrypoint orders the pack only if one is not already active or in flight (a
second order would be a second pack), waits, then **asserts every wildcard is named by an `active`
pack**. The order's own 200 means "accepted", not "serving". It needs a token with *SSL and
Certificates* (Read to list, Edit to order); a 403 is reported as a token-scope problem rather than
read as "no packs".

## What it does NOT do

* Split-horizon DNS: if on-network resolvers answer from an internal copy of the zone, these
  wildcard names resolve there only once that copy carries them too.
* A per-app Access override for a public app. Add a more specific Access app for that hostname;
  the wildcard does not need to change.

## Testing

`molecule/default` runs the safety filters against fixtures in the API's own shapes: fixtures that
must be refused, near-misses that must pass, and a verify that every filter the tasks call is
defined by the plugin. The filters also have unit tests (`tests/unit/test_hosting_edge.py`). The
API tasks need a live account and are proven by their own read-backs when applied.
