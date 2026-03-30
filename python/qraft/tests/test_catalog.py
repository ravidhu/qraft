import json
from pathlib import Path

import pytest

from qraft.catalog.generator import generate_catalog


class TestGenerateCatalog:
    def _setup_target(self, tmp_path: Path) -> Path:
        """Create a minimal target directory with manifest and static files."""
        target = tmp_path / "target"
        target.mkdir()

        # Create a minimal manifest.json
        manifest = {
            "metadata": {"project_name": "test", "env": "local"},
            "nodes": {},
            "sources": {},
        }
        (target / "manifest.json").write_text(json.dumps(manifest))

        # Create mock static/index.html (simulating the pre-built catalog app)
        static_dir = Path(__file__).parent.parent / "catalog" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        index_path = static_dir / "index.html"
        if not index_path.exists():
            index_path.write_text("<html><body>catalog</body></html>")
            self._created_mock = True
        else:
            self._created_mock = False

        return target

    def test_generates_catalog_dir(self, tmp_path):
        target = self._setup_target(tmp_path)
        catalog_dir = generate_catalog(target)

        assert catalog_dir == target / "catalog"
        assert (catalog_dir / "index.html").exists()
        assert (catalog_dir / "manifest.json").exists()

    def test_copies_test_results_if_present(self, tmp_path):
        target = self._setup_target(tmp_path)
        (target / "test_results.json").write_text('{"results": []}')

        catalog_dir = generate_catalog(target)
        assert (catalog_dir / "test_results.json").exists()

    def test_missing_manifest_raises(self, tmp_path):
        target = tmp_path / "target"
        target.mkdir()

        # Create static index.html but no manifest
        static_dir = Path(__file__).parent.parent / "catalog" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        if not (static_dir / "index.html").exists():
            (static_dir / "index.html").write_text("<html></html>")

        with pytest.raises(FileNotFoundError, match="manifest.json"):
            generate_catalog(target)
