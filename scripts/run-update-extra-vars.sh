#!/usr/bin/env bash

for filename in overrides/*.json; do
    python3 scripts/update-extra-vars.py "$filename"
done
