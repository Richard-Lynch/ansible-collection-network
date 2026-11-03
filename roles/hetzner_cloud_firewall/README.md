# hetzner_cloud_firewall

Reconciles a **Hetzner Cloud firewall** to a rule set declared in the repo.

## Why this needs its own role

A cloud firewall sits **in front of** the VM and is **invisible from inside it**. `ufw status`,
`nft list ruleset` and `iptables -L` all report nothing about it, so a play that inspects the host's
own rules will confidently conclude there is no firewall.

The typical symptom: a UDP service (a WireGuard handshake, say) never arrives, `tcpdump` **on the
destination host** captures nothing, neither end logs an error, and the host's own `ufw`/nftables
rules allow the traffic. An outside-in TCP probe cannot settle the question either: against a
firewall that permits exactly the ports being probed, it reports "nothing is filtering". The
answer is a cloud firewall that allows some TCP ports and no UDP at all, which only the provider's
API can show.

## Replace, not merge

The API's `set_rules` endpoint **overwrites the entire rule set**. A rule omitted from the
declaration is a rule deleted. That is deliberate — the repo is the source of truth, and a merge
would let console-added rules accumulate invisibly, until nobody can say why a port is open or
whether the service behind it still exists.

It also means every apply is atomic: there is no window where the firewall is half-configured with
SSH removed and not yet re-added.

## Safety properties

- **It will not create a firewall.** Attaching a new one to a live public server is how a host
  loses SSH; that stays a deliberate console action. The role asserts the named firewall exists.
- **The lockout guard.** `hetzner_firewall_required_ports` (default `[22]`) must all appear in the
  declaration, checked **before** the API is called. Verified by a negative test: a rule set
  omitting SSH is refused.
- **Every rule needs a `description`.** A rule nobody can justify is a rule nobody dares remove.
- **Read-back.** The live rules are re-fetched and compared against the declaration, rather than
  trusting the POST's 201.
- Generate-don't-apply: the default run prints the added/removed diff and changes nothing.

## Usage

```yaml
- role: richard_lynch.network.hetzner_cloud_firewall
  vars:
    hetzner_firewall_name: "edge-firewall"
    hetzner_api_token: "{{ vault_hcloud_api_token }}"
    hetzner_firewall_required_ports: [22, 80, 443]
    hetzner_firewall_rules:
      - direction: in
        protocol: tcp
        port: "22"
        source_ips: ["0.0.0.0/0", "::/0"]
        description: "SSH — the only way into this host"
```

Apply by passing `hetzner_firewall_apply: true` (for example `-e hetzner_firewall_apply=true`).

## What it does NOT do

No host-level firewalling (`ufw`, `nftables`) — a different layer with different failure modes, and
one that Docker's own iptables rules bypass entirely.

## Testing

Molecule covers rule-set validation and the guards. It **cannot** test the API interaction: that
needs a real token and a real firewall, and mocking it would assert the mock. The API path is
covered by the read-back gate against the live firewall instead.
