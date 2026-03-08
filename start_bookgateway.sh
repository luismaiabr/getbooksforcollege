#!/bin/bash
# Start the bookgateway container

cd "$(dirname "$0")"
docker compose up -d bookgateway
