# homelab

Infrastructure for self-hosting my projects. Every project ships as a Docker stack:
push to its repo, CI builds the image and calls a deploy webhook, the host pulls and
restarts it. Secrets live in an encrypted vault.

## Hosts

| Host | Role |
|------|------|
| GL-MT6000 | Router, DNS, VPN, Tailscale |
| nil | Docker stacks, deploy webhooks |

## Subdomains

Every public hostname is declared on its stack in `inventory/host_vars/nil/vars.yml`:

```yaml
  - name: lebedev-cut
    subdomains:
      - host: lebedev-cut.tkozakas.online
        service: http://lebedev-cut-lebedev-cut-1:8080
```

`tunnel` defaults to `subdomain_tunnel`. On every push to main the Subdomains job runs
`scripts/subdomains.py --apply`: it creates or fixes the Cloudflare tunnel route and DNS
record for each declared host and removes the hosts listed under `retired_subdomains`.
Routes that exist in Cloudflare but are declared nowhere are only reported as warnings.
Pull requests get a dry run.

## Usage

Copy .taskconfig.example to .taskconfig and fill in your values first.

```sh
# list automation tasks
task

# install required ansible collections (run once, and after requirements.yml changes)
task deps

# everything
ansible-playbook playbooks/site.yml

# router only
ansible-playbook playbooks/router.yml

# stacks host only
ansible-playbook playbooks/raspberry-pi.yml

# verify router config
ansible-playbook playbooks/verify.yml
```
