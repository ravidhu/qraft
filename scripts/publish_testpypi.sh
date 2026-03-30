#!/usr/bin/env bash
# Publish qraft and qraft-utils to TestPyPI
# Usage: ./scripts/publish_testpypi.sh [--dev] [qraft|qraft-utils|all]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="all"
DEV_MODE=false

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev) DEV_MODE=true; shift ;;
        *)     TARGET="$1"; shift ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Pre-flight checks ──────────────────────────────────────────────

command -v uv &>/dev/null || error "'uv' not found. See https://docs.astral.sh/uv/"

if ! grep -q "\[testpypi\]" ~/.pypirc 2>/dev/null; then
    error "No [testpypi] section found in ~/.pypirc. Configure it first."
fi

# ── Dev version patching ──────────────────────────────────────────

BASE_VERSION="0.1.0"
DEV_SUFFIX="dev$(date +%Y%m%d%H%M%S)"
DEV_VERSION="${BASE_VERSION}.${DEV_SUFFIX}"
FILES_TO_RESTORE=()

patch_version() {
    local file="$1"
    local pattern="$2"
    local replacement="$3"
    cp "$file" "$file.bak"
    FILES_TO_RESTORE+=("$file")
    sed -i '' "s|${pattern}|${replacement}|" "$file"
    info "Patched $(basename "$file") → $DEV_VERSION"
}

restore_versions() {
    for file in "${FILES_TO_RESTORE[@]}"; do
        if [[ -f "$file.bak" ]]; then
            mv "$file.bak" "$file"
        fi
    done
}

if $DEV_MODE; then
    info "Dev mode: version → $DEV_VERSION"
    trap restore_versions EXIT

    if [[ "$TARGET" == "all" || "$TARGET" == "qraft" ]]; then
        patch_version "$ROOT_DIR/pyproject.toml" \
            "version = \"${BASE_VERSION}\"" \
            "version = \"${DEV_VERSION}\""
    fi
    if [[ "$TARGET" == "all" || "$TARGET" == "qraft-utils" ]]; then
        patch_version "$ROOT_DIR/python/qraft-utils/pyproject.toml" \
            "version = \"${BASE_VERSION}\"" \
            "version = \"${DEV_VERSION}\""
    fi
fi

# ── Publish qraft (Rust + Python via maturin) ──────────────────────

publish_qraft() {
    info "Building qraft wheel (maturin)..."
    cd "$ROOT_DIR"

    # Clean previous wheels
    rm -f rust/target/wheels/qraft-*.whl

    uvx maturin build --release -m rust/Cargo.toml

    WHEEL=$(ls rust/target/wheels/qraft-*.whl 2>/dev/null | head -1)
    if [[ -z "$WHEEL" ]]; then
        error "No wheel found in rust/target/wheels/"
    fi

    info "Uploading qraft to TestPyPI..."
    uvx twine upload --skip-existing --repository testpypi rust/target/wheels/qraft-*.whl

    info "qraft published to TestPyPI!"
    echo -e "  Install with: ${YELLOW}uv pip install -i https://test.pypi.org/simple/ qraft${NC}"
}

# ── Publish qraft-utils (pure Python via hatchling) ────────────────

publish_qraft_utils() {
    info "Building qraft-utils wheel..."
    cd "$ROOT_DIR/python/qraft-utils"

    # Clean previous builds
    rm -rf dist/

    uvx --from build pyproject-build

    if ! ls dist/qraft_utils-*.whl &>/dev/null; then
        error "No wheel found in python/qraft-utils/dist/"
    fi

    info "Uploading qraft-utils to TestPyPI..."
    uvx twine upload --skip-existing --repository testpypi dist/*

    info "qraft-utils published to TestPyPI!"
    echo -e "  Install with: ${YELLOW}uv pip install -i https://test.pypi.org/simple/ qraft-utils${NC}"
}

# ── Main ───────────────────────────────────────────────────────────

echo ""
info "Publishing to TestPyPI (target: $TARGET)"
echo ""

case "$TARGET" in
    qraft)
        publish_qraft
        ;;
    qraft-utils)
        publish_qraft_utils
        ;;
    all)
        publish_qraft_utils
        echo "=================================="
        publish_qraft
        ;;
    *)
        error "Unknown target '$TARGET'. Use: qraft, qraft-utils, or all"
        ;;
esac

echo ""
info "Done! Verify at https://test.pypi.org/project/qraft/ and https://test.pypi.org/project/qraft-utils/"
