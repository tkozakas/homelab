# New project stack

1. Ask user: name, purpose, secrets.
2. Write code in ~/Documents/<name>. Copy pipeline.yml from existing repo.
3. Lint and test until green.
4. Run there: task -t ~/Documents/homelab/Taskfile.yml repo NAME=<name>
5. In homelab: task new-stack NAME=<name>
6. Edit created files, set real env vars.
7. task secrets: add vault_<name>_* values. Unknown? Ask user.
8. task check. Red? Fix step 6.
9. task deploy. Unreachable? Tell user, stop. Failed? Fix, rerun.
10. task verify NAME=<name>. Bad logs? Fix, push.
11. Push commit, task ci NAME=<name> must be green.
12. Commit homelab. Ask user before push.
