# service_traefik

Deploys **Traefik v3** as a reverse proxy with Docker Compose:

- a static configuration (`config/traefik.yml`) with `web` (:80, redirects to HTTPS) and
  `websecure` (:443) entrypoints, the docker provider (`exposedByDefault: false`) and the file
  provider watching `config/dynamic/`;
- certificates from **Let's Encrypt over the Cloudflare DNS-01 challenge**, so a wildcard
  certificate works and issuance needs no inbound port 80;
- the dashboard and API on `traefik_dashboard_host`, with the certificate for
  `traefik_cert_domain` / `traefik_cert_sans` requested on that router;
- **your route files**: every file in `traefik_dynamic_dir` is copied into `config/dynamic/`, and
  every `*.j2` in `traefik_dynamic_templates_dir` is rendered there (mode 0640) for routes that
  carry a secret.

The ACME store (`letsencrypt/acme.json`) holds the issued private keys. Traefik creates it on the
host; the role never renders, reads or backs it up.

## Routes are data

The role ships exactly one route file, `files/dynamic/ssl.yml`: the `traefik-https-redirect` and
`sslheader` middlewares its own dashboard router uses. Everything else is the caller's, in a
directory on the controller:

```yaml
traefik_dynamic_dir: "{{ inventory_dir }}/files/traefik/dynamic"            # plain *.yml
traefik_dynamic_templates_dir: "{{ inventory_dir }}/files/traefik/templates" # *.j2, optional
```

Both directories are checked before anything is deployed: a missing directory fails the run
instead of deploying a proxy with no routes. A route file name supplied twice (by the role and by
you, or by both of your directories) is refused.

**Deleting a route file from the source does not delete it from the host**, and the file provider
serves whatever is in the directory. List the basename in `traefik_retired_dynamic_files` to
remove it.

A changed route file restarts the container.

## Exposure

`traefik_bind_address` defaults to `127.0.0.1`: the entrypoints are published on loopback until
you choose otherwise. Set a specific address, or `""` for every interface. The dashboard router
has **no authentication of its own**, so publishing on every interface publishes the dashboard
too; restrict it with a firewall, or add a middleware to the router in your own route files.

`traefik_servers_insecure_skip_verify` (default `false`) turns off TLS verification for every
HTTPS upstream. Prefer a per-service `serversTransport` with the upstream's CA.

## Forward authentication (optional)

An auth service that accepts callers by source address needs Traefik at a fixed address on a
network nothing else can join. Set `traefik_forward_auth_network`, `_subnet` and `_traefik_ip`
and the container joins that network at that address. The network belongs to the auth service:
the role checks it exists, is **internal** and has the declared subnet, and refuses to deploy
otherwise. The middleware itself (a `forwardAuth` pointing at the service) goes in your route
files.

## Example

```yaml
- hosts: proxy
  roles:
    - role: richard_lynch.network.service_traefik
      vars:
        traefik_bind_address: "192.0.2.10"
        traefik_acme_email: "admin@example.com"
        traefik_cf_api_email: "admin@example.com"
        traefik_cf_dns_api_token: "{{ vault_cloudflare_dns_token }}"
        traefik_dashboard_host: "traefik.example.com"
        traefik_cert_domain: "example.com"
        traefik_cert_sans: "*.example.com"
        traefik_dynamic_dir: "{{ inventory_dir }}/files/traefik/dynamic"
```

## Logging

The compose project sets json-file rotation (`max-size: 50m`, `max-file: 3`) on the container
itself rather than relying on the daemon default, which only applies to containers created after
it was set. The static configuration logs at INFO and drops request headers from the access log
(headers are where credentials travel).

## Testing

`molecule test` runs the real role on localhost with `traefik_deploy: false` twice: once with
the defaults (loopback bind, no forward-auth network) and once with every option set. It asserts
on the rendered compose project, static configuration and route files, that a retired route file
is removed, and that a missing route directory and a duplicated route file name both stop the run.
