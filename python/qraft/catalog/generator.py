import shutil
from pathlib import Path


def generate_catalog(target_dir: Path) -> Path:
    """Generate catalog site from manifest.json.

    Copies the pre-built catalog app and manifest/test_results JSON
    into target_dir/catalog/.
    """
    catalog_dir = target_dir / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)

    # Copy pre-built index.html from package static/
    static_dir = Path(__file__).parent / "static"
    index_src = static_dir / "index.html"
    if not index_src.exists():
        raise FileNotFoundError(
            f"Catalog app not found at {index_src}. "
            "Rebuild with: cd catalog_app && npm run build"
        )
    shutil.copy2(index_src, catalog_dir / "index.html")

    # Copy manifest.json
    manifest_src = target_dir / "manifest.json"
    if not manifest_src.exists():
        raise FileNotFoundError(
            f"manifest.json not found at {manifest_src}. "
            "Run 'qraft compile --env <env>' first."
        )
    shutil.copy2(manifest_src, catalog_dir / "manifest.json")

    # Copy test_results.json if it exists (optional)
    test_results_src = target_dir / "test_results.json"
    if test_results_src.exists():
        shutil.copy2(test_results_src, catalog_dir / "test_results.json")

    return catalog_dir
