# homelab

Ansible automation for my home setup.

## Hosts

| Host | Role |
|------|------|
| GL-MT6000 | Router, DNS, VPN, Tailscale |
| nil | Raspberry Pi, Docker stacks |

## Usage

```sh
# everything
ansible-playbook playbooks/site.yml

# router only
ansible-playbook playbooks/router.yml

# raspberry pi only
ansible-playbook playbooks/raspberry-pi.yml

# verify router config
ansible-playbook playbooks/verify.yml
```
