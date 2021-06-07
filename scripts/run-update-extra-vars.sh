#!/usr/bin/env bash

for filename in $(echo extra_vars_*.json); do
    python3 src/update-extra-vars.py $filename;
done
