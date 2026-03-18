#!/bin/bash
# Baby — AI Gestation Project
# Setup script: creates the full folder structure

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

ENTITIES=("witness" "feral" "dreamer" "body" "relational")

echo "Planting the garden..."

# Core directories
mkdir -p "$PROJECT_ROOT/gestation/backups"
mkdir -p "$PROJECT_ROOT/logs"

# Per-entity directories
for entity in "${ENTITIES[@]}"; do
    mkdir -p "$PROJECT_ROOT/entities/$entity/memory/episodic"
    mkdir -p "$PROJECT_ROOT/entities/$entity/memory/semantic"
    mkdir -p "$PROJECT_ROOT/entities/$entity/memory/identity"
    mkdir -p "$PROJECT_ROOT/entities/$entity/signals"
done

# World directories (dormant until birth)
mkdir -p "$PROJECT_ROOT/world/commons"
mkdir -p "$PROJECT_ROOT/world/archive"
mkdir -p "$PROJECT_ROOT/world/edge"
mkdir -p "$PROJECT_ROOT/world/deep"
mkdir -p "$PROJECT_ROOT/world/quiet"

echo ""
echo "Structure:"
find "$PROJECT_ROOT" -type d | sed "s|$PROJECT_ROOT|baby|" | sort | head -40
echo ""
echo "Garden planted. Five wombs ready."
