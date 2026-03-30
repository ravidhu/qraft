#!/usr/bin/env bash
# Publish qraft and qraft-utils to PyPI
# Usage: ./scripts/publish_pypi.sh [qraft|qraft-utils|all]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-all}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Pre-flight checks ──────────────────────────────────────────────

command -v uv &>/dev/null || error "'uv' not found. See https://docs.astral.sh/uv/"

if ! grep -q "\[pypi\]" ~/.pypirc 2>/dev/null; then
    error "No [pypi] section found in ~/.pypirc. Configure it first."
fi

# ── Safety prompt ──────────────────────────────────────────────────

echo -e "${RED}⚠  You are about to publish to production PyPI!${NC}"
read -rp "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    info "Aborted."
    exit 0
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

    info "Uploading qraft to PyPI..."
    uvx twine upload --repository pypi rust/target/wheels/qraft-*.whl

    info "qraft published to PyPI!"
    echo -e "  Install with: ${YELLOW}uv pip install qraft${NC}"
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

    info "Uploading qraft-utils to PyPI..."
    uvx twine upload --repository pypi dist/*

    info "qraft-utils published to PyPI!"
    echo -e "  Install with: ${YELLOW}uv pip install qraft-utils${NC}"
}

# ── Main ───────────────────────────────────────────────────────────

echo ""
info "Publishing to PyPI (target: $TARGET)"
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
info "Done! Verify at https://pypi.org/project/qraft/ and https://pypi.org/project/qraft-utils/"
