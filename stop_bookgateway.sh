#!/bin/bash
# Stop the bookgateway container

cd "$(dirname "$0")"
docker compose stop bookgateway
