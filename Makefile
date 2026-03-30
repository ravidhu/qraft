.PHONY: dev test test-rust test-python lint build build-catalog clean

# ══════════════════════════════════
# Dev
# ══════════════════════════════════

dev:                              ## Compile Rust + installe en mode dev
	maturin develop

# ══════════════════════════════════
# Tests
# ══════════════════════════════════

test: test-rust test-python       ## Run all tests

test-rust:                        ## Run Rust tests
	cd rust && cargo test

test-python: dev                  ## Run Python tests (builds Rust first)
	pytest python/tests -v

# ══════════════════════════════════
# Lint
# ══════════════════════════════════

lint:                             ## Lint Rust + Python
	cd rust && cargo clippy -- -D warnings
	cd rust && cargo fmt -- --check
	ruff check python/
	mypy python/qraft/

# ══════════════════════════════════
# Build
# ══════════════════════════════════

build:                            ## Build release wheel
	maturin build --release

build-catalog:                    ## Build catalog app and copy to package
	cd catalog_app && npm run build
	mkdir -p python/qraft/catalog/static
	cp catalog_app/dist/index.html python/qraft/catalog/static/index.html

# ══════════════════════════════════
# Publish
# ══════════════════════════════════

publish-testpypi:                 ## Publish both packages to TestPyPI
	./scripts/publish_testpypi.sh all

publish-testpypi-qraft:           ## Publish qraft to TestPyPI
	./scripts/publish_testpypi.sh qraft

publish-testpypi-utils:           ## Publish qraft-utils to TestPyPI
	./scripts/publish_testpypi.sh qraft-utils

publish:                          ## Publish both packages to PyPI
	./scripts/publish_pypi.sh all

publish-qraft:                    ## Publish qraft to PyPI
	./scripts/publish_pypi.sh qraft

publish-utils:                    ## Publish qraft-utils to PyPI
	./scripts/publish_pypi.sh qraft-utils

# ══════════════════════════════════
# Clean
# ══════════════════════════════════

clean:                            ## Clean build artifacts
	cd rust && cargo clean
	rm -rf dist/ target/ *.egg-info .pytest_cache
