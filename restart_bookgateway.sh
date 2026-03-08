#!/bin/bash
# Restart the bookgateway container

cd "$(dirname "$0")"
docker compose restart bookgateway
