# unifi_network

Creates or updates one network (VLAN) on a UniFi controller through its Network API, and reads it
back before reporting success.

## Why it models on an existing network

The UniFi REST API **replaces the whole object** on PUT and POST, and a network object carries
~40 fields (IGMP snooping, mDNS, UPnP, IPv6 RA, gateway type...). A network built from scratch
would drop every field not thought of, and the API's defaults are not necessarily the controller's.
So a NEW network is cloned from an existing one (`unifi_network_model`) with only its identity and
addressing overridden; an existing network (matched by VLAN id) is updated in place.

## The relay trap

`dhcp_relay_enabled: true` is only honoured when nothing else in the object changes. Sent with
anything else, the controller answers `rc: ok`, applies the rest and silently drops the flag,
leaving a network with no DHCP at all. This role therefore creates every network with DHCP **off**
(relay off, relay servers stripped) and leaves relay to a separate, flag-alone PUT — see
`unifi_network_dhcp`'s `relay_on` entrypoint.

## What it does

1. Asserts an API key was supplied.
2. GETs the live `networkconf`, finds the target by VLAN id and the model by name. Fails if a new
   network has no model to clone.
3. Builds the desired object and reports the plan. **Changes nothing** unless
   `unifi_network_apply=true`.
4. When applying: POSTs (create) or PUTs (update), re-reads the controller, and asserts every field
   it wrote is what the controller now holds.

## Variables

| variable | required | default | meaning |
| --- | :---: | --- | --- |
| `unifi_network_host` | **yes** | — | Address of the UniFi controller. |
| `unifi_network_api_key` | **yes** | — | API key for the `X-API-KEY` header. |
| `unifi_network_name` | **yes** | — | Network name. |
| `unifi_network_vlan` | **yes** | — | VLAN id; also how an existing network is matched. |
| `unifi_network_subnet` | **yes** | — | Gateway address with prefix, e.g. `192.0.2.1/24`. |
| `unifi_network_domain` | **yes** | — | Short domain name handed to clients. |
| `unifi_network_dhcp_start` / `_stop` | **yes** | — | The DHCP range the controller stores (DHCP stays off on create). |
| `unifi_network_model` | **yes** | — | Name of an EXISTING network a new one is cloned from. |
| `unifi_network_site` | no | `default` | Controller site id. |
| `unifi_network_validate_certs` | no | `false` | Verify the controller's TLS certificate. |
| `unifi_network_apply` | no | `false` | Generate-don't-apply gate. |

The full validated interface is `meta/argument_specs.yml`.

## Example

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: richard_lynch.network.unifi_network
      vars:
        unifi_network_host: 192.0.2.1
        unifi_network_api_key: "{{ unifi_api_key }}"   # from your secrets manager
        unifi_network_name: lab
        unifi_network_vlan: 99
        unifi_network_subnet: 198.51.100.1/24
        unifi_network_domain: lab
        unifi_network_dhcp_start: 198.51.100.11
        unifi_network_dhcp_stop: 198.51.100.250
        unifi_network_model: Default
```

Run it once without `unifi_network_apply` and read the plan; then apply.
