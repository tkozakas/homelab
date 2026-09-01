#!/usr/bin/env python3

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COMPOSE_TEMPLATE = """services:
  {name}:
    profiles: ["prod"]
    image: {registry}/{owner}/{name}:main
    environment:
      - EXAMPLE_VAR=${{EXAMPLE_VAR}}
    volumes:
      - state:/state
    restart: unless-stopped

volumes:
  state:
"""

ENV_TEMPLATE = "EXAMPLE_VAR={{{{ vault_{snake}_example_var }}}}\n"

STACK_ENTRY = "  - name: {name}\n    profile: prod\n    deploy: true\n"


def load_config():
    config = {}
    for line in (ROOT / ".taskconfig").read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip():
            config[key.strip()] = value.strip()
    return config


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z0-9-]+", sys.argv[1]):
        sys.exit("usage: new-stack.py <name>  (lowercase, digits, dashes)")
    name = sys.argv[1]
    config = load_config()
    vars_file = ROOT / f"inventory/host_vars/{config['HOST_VARS']}/vars.yml"
    compose = ROOT / f"roles/raspberry-pi/files/{name}/docker-compose.yml"
    env = ROOT / f"roles/raspberry-pi/templates/{name}.env.j2"
    if compose.exists() or env.exists():
        sys.exit(f"stack {name} already exists")

    compose.parent.mkdir(parents=True)
    compose.write_text(COMPOSE_TEMPLATE.format(name=name, registry=config["REGISTRY"], owner=config["GH_OWNER"]))
    env.write_text(ENV_TEMPLATE.format(snake=name.replace("-", "_")))

    vars_text = vars_file.read_text()
    if f"- name: {name}\n" not in vars_text:
        vars_file.write_text(vars_text.rstrip("\n") + "\n" + STACK_ENTRY.format(name=name))

    print(f"created {compose.relative_to(ROOT)}")
    print(f"created {env.relative_to(ROOT)}")
    print("registered the stack (deploy: true)")
    print(f"next: edit both files for real env vars, then: task secrets, task deploy, task verify NAME={name}")


if __name__ == "__main__":
    main()
