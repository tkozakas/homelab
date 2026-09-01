# homelab

Infrastructure for self-hosting my projects. Every project ships as a Docker stack:
push to its repo, CI builds the image and calls a deploy webhook, the host pulls and
restarts it. Secrets live in an encrypted vault, and a Taskfile automates adding
new stacks end to end.

## Hosts

| Host | Role |
|------|------|
| GL-MT6000 | Router, DNS, VPN, Tailscale |
| nil | Docker stacks, deploy webhooks |

## Usage

```sh
# list automation tasks
task

# everything
ansible-playbook playbooks/site.yml

# router only
ansible-playbook playbooks/router.yml

# stacks host only
ansible-playbook playbooks/raspberry-pi.yml

# verify router config
ansible-playbook playbooks/verify.yml
```

New project? Follow [AGENTS.md](AGENTS.md).
