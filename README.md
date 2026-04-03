# homelab

Absurdly over-engineered and completely unnecessary Ansible automation for two devices. One command to rebuild everything from zero. If you're reading this, you're lost.

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
