import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

API_BASE = "https://api.cloudflare.com/client/v4"
API_TIMEOUT = 30
TUNNEL_SUFFIX = "cfargotunnel.com"
DEFAULT_VARS = "inventory/host_vars/nil/vars.yml"
TOKEN_ENV = "CF_API_TOKEN"


class CloudflareError(Exception):
    pass


class Cloudflare:
    def __init__(self, token):
        self.token = token

    def request(self, method, path, payload=None):
        request = urllib.request.Request(
            f"{API_BASE}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            raise CloudflareError(
                f"{method} {path}: {exc.code} {exc.read().decode(errors='replace')[:300]}"
            ) from exc
        if not body.get("success"):
            raise CloudflareError(f"{method} {path}: {body.get('errors')}")
        return body.get("result")


def declared(inventory):
    default_tunnel = inventory.get("subdomain_tunnel")
    hosts = {}
    for stack in inventory.get("stacks") or []:
        for entry in stack.get("subdomains") or []:
            host = entry["host"]
            if host in hosts:
                raise SystemExit(f"{host} is declared twice")
            hosts[host] = {
                "service": entry["service"],
                "tunnel": entry.get("tunnel") or default_tunnel,
            }
    return hosts


def zone_for(host, zones):
    matches = [
        zone
        for zone in zones
        if host == zone["name"] or host.endswith("." + zone["name"])
    ]
    if not matches:
        print(
            f"::warning::DNS for {host} is not managed here, the API token cannot see its zone"
        )
        return None
    return max(matches, key=lambda zone: len(zone["name"]))


class Reconciler:
    def __init__(self, cf, apply):
        self.cf = cf
        self.apply = apply
        self.zones = cf.request("GET", "/zones?per_page=50")
        accounts = {zone["account"]["id"] for zone in self.zones}
        self.tunnels = {}
        for account in accounts:
            for tunnel in (
                cf.request("GET", f"/accounts/{account}/cfd_tunnel?is_deleted=false")
                or []
            ):
                self.tunnels[tunnel["name"]] = {"id": tunnel["id"], "account": account}
        self.configs = {}

    def say(self, action, detail):
        mode = "" if self.apply else "would "
        print(f"{mode}{action}: {detail}")

    def config(self, name):
        if name not in self.configs:
            tunnel = self.tunnels[name]
            path = f"/accounts/{tunnel['account']}/cfd_tunnel/{tunnel['id']}/configurations"
            result = self.cf.request("GET", path) or {}
            config = result.get("config") or {}
            self.configs[name] = {
                "path": path,
                "config": config,
                "ingress": list(config.get("ingress") or []),
            }
        return self.configs[name]

    def save(self, name):
        entry = self.configs[name]
        if self.apply:
            self.cf.request(
                "PUT",
                entry["path"],
                {"config": {**entry["config"], "ingress": entry["ingress"]}},
            )

    def ensure(self, host, service, tunnel_name):
        if tunnel_name not in self.tunnels:
            raise CloudflareError(f"{host}: tunnel {tunnel_name} not found")
        entry = self.config(tunnel_name)
        ingress = entry["ingress"]
        index = next(
            (i for i, rule in enumerate(ingress) if rule.get("hostname") == host), None
        )
        if index is None:
            catch_all = next(
                (i for i, rule in enumerate(ingress) if not rule.get("hostname")),
                len(ingress),
            )
            ingress.insert(catch_all, {"hostname": host, "service": service})
            self.say("add route", f"{host} -> {service} on {tunnel_name}")
            self.save(tunnel_name)
        elif ingress[index].get("service") != service:
            ingress[index] = {**ingress[index], "service": service}
            self.say("fix route", f"{host} -> {service} on {tunnel_name}")
            self.save(tunnel_name)
        self.ensure_dns(host, self.tunnels[tunnel_name]["id"])

    def ensure_dns(self, host, tunnel_id):
        zone = zone_for(host, self.zones)
        if zone is None:
            return
        target = f"{tunnel_id}.{TUNNEL_SUFFIX}"
        records = self.records(zone, host)
        payload = {"type": "CNAME", "name": host, "content": target, "proxied": True}
        if not records:
            self.say("add dns", f"{host} -> {target}")
            if self.apply:
                self.cf.request("POST", f"/zones/{zone['id']}/dns_records", payload)
        elif records[0].get("content") != target or not records[0].get("proxied"):
            self.say("fix dns", f"{host} -> {target}")
            if self.apply:
                self.cf.request(
                    "PUT",
                    f"/zones/{zone['id']}/dns_records/{records[0]['id']}",
                    payload,
                )

    def records(self, zone, host):
        query = urllib.parse.quote(host)
        return (
            self.cf.request(
                "GET", f"/zones/{zone['id']}/dns_records?type=CNAME&name={query}"
            )
            or []
        )

    def retire(self, host):
        for name in self.tunnels:
            entry = self.config(name)
            kept = [rule for rule in entry["ingress"] if rule.get("hostname") != host]
            if len(kept) != len(entry["ingress"]):
                entry["ingress"] = kept
                self.say("remove route", f"{host} from {name}")
                self.save(name)
        zone = zone_for(host, self.zones)
        if zone is None:
            return
        for record in self.records(zone, host):
            self.say("remove dns", host)
            if self.apply:
                self.cf.request(
                    "DELETE", f"/zones/{zone['id']}/dns_records/{record['id']}"
                )

    def drift(self, known):
        undeclared = []
        for name in self.tunnels:
            for rule in self.config(name)["ingress"]:
                host = rule.get("hostname")
                if host and host not in known:
                    undeclared.append(f"{host} on {name}")
        return undeclared


def main(argv):
    apply = "--apply" in argv
    paths = [arg for arg in argv if not arg.startswith("--")]
    with open(paths[0] if paths else DEFAULT_VARS) as handle:
        inventory = yaml.safe_load(handle)
    hosts = declared(inventory)
    retired = list(inventory.get("retired_subdomains") or [])
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise SystemExit(f"{TOKEN_ENV} is not set")
    reconciler = Reconciler(Cloudflare(token), apply)
    failures = []
    for host, spec in sorted(hosts.items()):
        try:
            reconciler.ensure(host, spec["service"], spec["tunnel"])
        except CloudflareError as exc:
            failures.append(str(exc))
    for host in retired:
        try:
            reconciler.retire(host)
        except CloudflareError as exc:
            failures.append(str(exc))
    for line in reconciler.drift(set(hosts) | set(retired)):
        print(f"::warning::undeclared subdomain {line}")
    print(
        f"{len(hosts)} declared, {len(retired)} retired, {'applied' if apply else 'dry run'}"
    )
    for failure in failures:
        print(f"::error::{failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
