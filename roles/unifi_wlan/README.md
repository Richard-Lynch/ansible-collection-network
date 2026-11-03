# unifi_wlan

Creates or updates one WLAN (SSID) on a UniFi controller through its Network API, and reads it
back before reporting success.

## Merge, never construct

The UniFi REST API **replaces the whole object** on PUT, and a WLAN carries ~55 fields (DTIM
timers, minimum-rate tables, PMF mode, band steering...). This role always starts from a real
object: the live WLAN when the SSID exists, otherwise an existing WLAN on the same controller
(`unifi_wlan_model_ssid`) with its identity fields stripped. Only identity, security and the
requested settings are overridden, so a new SSID inherits the radio and roaming settings the
controller actually uses.

## POST drops fields that PUT accepts

Creating a WLAN with `hide_ssid`, `pmf_mode` or `wpa3_support` in the POST body can return
`rc: ok` and store the MODEL's values for all three. So creation is two steps: POST to allocate the
object, then always PUT the requested settings — and the read-back gate asserts what the controller
now holds, which is what catches it.

## What it does

1. Asserts an API key was supplied (the placeholder is rejected).
2. Resolves the target network by name and refuses to guess: an SSID on the wrong network puts
   every client on the wrong VLAN.
3. Builds the desired WLAN and reports the plan (the passphrase never appears in it). **Changes
   nothing** unless `unifi_wlan_apply=true`.
4. When applying: creates or updates, re-reads, and asserts the stored settings.

## Variables

| variable | required | default | meaning |
| --- | :---: | --- | --- |
| `unifi_wlan_host` | **yes** | — | Address of the UniFi controller. |
| `unifi_wlan_api_key` | **yes** | — | API key for the `X-API-KEY` header. |
| `unifi_wlan_ssid` | **yes** | — | The SSID to create or update. |
| `unifi_wlan_network_name` | **yes** | — | The UniFi network the SSID attaches to (decides the VLAN). |
| `unifi_wlan_passphrase` | **yes** | — | WPA passphrase. Never logged. |
| `unifi_wlan_model_ssid` | **yes** | — | An EXISTING SSID a new WLAN is cloned from. |
| `unifi_wlan_hidden` | no | `false` | Hide the SSID. |
| `unifi_wlan_enabled` | no | `true` | Enable the WLAN. |
| `unifi_wlan_security` / `_wpa_mode` | no | `wpapsk` / `wpa2` | Security mode. |
| `unifi_wlan_wpa3_support` / `_wpa3_transition` | no | `false` | WPA3 settings. |
| `unifi_wlan_pmf_mode` | no | `optional` | 802.11w: `disabled`, `optional` or `required`. |
| `unifi_wlan_site` | no | `default` | Controller site id. |
| `unifi_wlan_validate_certs` | no | `false` | Verify the controller's TLS certificate. |
| `unifi_wlan_apply` | no | `false` | Generate-don't-apply gate. |

The full validated interface is `meta/argument_specs.yml`.

## Example

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: richard_lynch.network.unifi_wlan
      vars:
        unifi_wlan_host: 192.0.2.1
        unifi_wlan_api_key: "{{ unifi_api_key }}"          # from your secrets manager
        unifi_wlan_passphrase: "{{ guest_wifi_passphrase }}"
        unifi_wlan_ssid: guest
        unifi_wlan_network_name: guest
        unifi_wlan_model_ssid: home
```
