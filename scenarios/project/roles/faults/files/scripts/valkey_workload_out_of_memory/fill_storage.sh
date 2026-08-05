#!/bin/sh

set -eou pipefail

RANGE_MAX=10000
RANGE_MIN=1

fill_storage() {
    sleep 20 # Delay for a few seconds to allow server to start

    while true; do # Fill the storage with 1M key value pairings
        key_id=$((RANDOM % (RANGE_MAX - RANGE_MIN + 1) + RANGE_MIN))

        head -c 1m /dev/urandom | valkey-cli -x SET largekey$key_id
        sleep 1
    done
}

(
    fill_storage
)& # Run the storage fill task in the background

valkey-server # Start the valkey server
