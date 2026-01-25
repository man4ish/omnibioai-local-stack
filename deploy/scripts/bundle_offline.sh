
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/deploy/bundle"
IMAGES_DIR="$OUT/images"
DATA_DIR="$OUT/data"

mkdir -p "$IMAGES_DIR" "$DATA_DIR"

# 1) Choose the images you need to ship
# Replace these with your actual image tags
IMAGES=(
  "mysql:8"
  "redis:7"
  "ollama/ollama:latest"
  "man4ish/omnibioai-web:latest"
  "man4ish/omnibioai-workflow-service:latest"
  "man4ish/omnibioai-tool-exec:latest"
  "man4ish/omnibioai-toolserver:latest"
  # add others: lims, rag, jupyter, etc
)

echo "[bundle] Pulling images..."
for img in "${IMAGES[@]}"; do
  docker pull "$img"
done

echo "[bundle] Saving images..."
for img in "${IMAGES[@]}"; do
  safe="$(echo "$img" | tr '/:' '__')"
  docker save -o "$IMAGES_DIR/$safe.tar" "$img"
done

# 2) Export optional volumes (ollama models, db, object store)
# Only export what exists. You can add more volumes here.
VOLS=(
  "ollama"
  "mysql_data"
  "object_store"
)

echo "[bundle] Exporting volumes (if present)..."
for v in "${VOLS[@]}"; do
  if docker volume inspect "$v" >/dev/null 2>&1; then
    docker run --rm -v "$v:/data" -v "$DATA_DIR:/backup" alpine \
      sh -c "cd /data && tar -czf /backup/${v}.tgz ."
    echo "  exported $v -> $DATA_DIR/${v}.tgz"
  else
    echo "  skip (volume not found): $v"
  fi
done

# 3) Copy compose + env
cp -f "$ROOT/deploy/compose/docker-compose.yml" "$OUT/docker-compose.yml"
cp -f "$ROOT/deploy/compose/.env.example" "$OUT/.env.example"

# 4) Create installer
cat > "$OUT/install.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$HERE/images"
DATA_DIR="$HERE/data"

echo "[install] Loading images..."
for f in "$IMAGES_DIR"/*.tar; do
  echo "  docker load -i $f"
  docker load -i "$f" >/dev/null
done

echo "[install] Creating volumes + importing data (if available)..."
for tgz in "$DATA_DIR"/*.tgz; do
  v="$(basename "$tgz" .tgz)"
  docker volume create "$v" >/dev/null
  docker run --rm -v "$v:/data" -v "$DATA_DIR:/backup" alpine \
    sh -c "cd /data && tar -xzf /backup/${v}.tgz"
  echo "  imported volume: $v"
done

if [[ ! -f "$HERE/.env" ]]; then
  cp "$HERE/.env.example" "$HERE/.env"
  echo "[install] Created .env from .env.example (edit if needed)."
fi

echo "[install] Done. Start with:"
echo "  cd $HERE && docker compose --env-file .env up -d"
EOF
chmod +x "$OUT/install.sh"

echo "[bundle] Done. Bundle at: $OUT"
echo "Ship this folder (or tar it) to any machine with Docker."
