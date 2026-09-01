#!/bin/sh
set -e
cd "$(dirname "$0")/.."
. ./.taskconfig
ansible-vault view "inventory/host_vars/${HOST_VARS}/vault.yml" | grep "${DEPLOY_TOKEN_VAULT_KEY}" | sed 's/.*: *"\(.*\)"/\1/'
