# homelab

Infrastructure for self-hosting my projects. Every project ships as a Docker stack:
push to its repo, CI builds the image and calls a deploy webhook, the host pulls and
restarts it. Secrets live in an encrypted vault.

## Hosts

| Host | Role |
|------|------|
| GL-MT6000 | Router, DNS, VPN, Tailscale |
| nil | Docker stacks, deploy webhooks |

## Stack auto-deploy

Pushing to main runs the `Stacks` workflow: it validates every
`roles/raspberry-pi/files/*/docker-compose.yml` with `docker compose config -q`,
then calls `$HOOKS_BASE/deploy-<stack>` for each stack whose files changed in that
push. A non-2xx webhook response fails the job.

- skip a deploy: put `[skip deploy]` in the commit message
- jarvis is never auto-deployed: redeploying it would restart the bot mid-run,
  so it is skipped with a notice and must be deployed manually

## Usage

Copy .taskconfig.example to .taskconfig and fill in your values first.

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
