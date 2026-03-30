from qraft.dag.bridge import (
    build_dag,
    build_pipeline,
    scan_models,
    select_models,
    topo_sort,
    validate_dag,
)


class TestScanModels:
    def test_scan_finds_all_models(self, models_dir):
        models = scan_models(models_dir)
        names = [m.name for m in models]
        assert "stg_orders" in names
        assert "stg_customers" in names
        assert "fct_revenue" in names

    def test_scan_reads_sql(self, models_dir):
        models = scan_models(models_dir)
        stg = next(m for m in models if m.name == "stg_orders")
        assert "source('raw', 'orders')" in stg.raw_sql


class TestBuildDag:
    def test_build_dag(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        # Should not raise
        assert dag is not None


class TestTopoSort:
    def test_topo_sort_ordering(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        batches = topo_sort(dag)

        # Flatten to get order
        flat = [name for batch in batches for name in batch]
        # stg models should come before fct_revenue
        assert flat.index("stg_orders") < flat.index("fct_revenue")
        assert flat.index("stg_customers") < flat.index("fct_revenue")

    def test_topo_sort_batches(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        batches = topo_sort(dag)

        # stg_orders and stg_customers should be in the same batch
        # (they have no dependencies on each other)
        first_batch = batches[0]
        assert "stg_orders" in first_batch
        assert "stg_customers" in first_batch


class TestSelectModels:
    def test_select_exact(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        result = select_models(dag, "stg_orders")
        assert result == ["stg_orders"]

    def test_select_descendants(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        result = select_models(dag, "stg_orders+")
        assert "stg_orders" in result
        assert "fct_revenue" in result

    def test_select_ancestors(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        result = select_models(dag, "+fct_revenue")
        assert "fct_revenue" in result
        assert "stg_orders" in result
        assert "stg_customers" in result


class TestBuildPipeline:
    def test_pipeline_returns_dag_and_batches(self, models_dir):
        models = scan_models(models_dir)
        dag, batches, parsed_models, errors = build_pipeline(models, ["raw"])

        assert dag is not None
        assert len(batches) > 0
        assert len(parsed_models) == len(models)
        assert len(errors) == 0

    def test_pipeline_ordering_matches_granular(self, models_dir):
        models = scan_models(models_dir)

        # Consolidated
        dag_p, batches_p, _, _ = build_pipeline(models, ["raw"])

        # Granular
        dag_g = build_dag(models)
        batches_g = topo_sort(dag_g)

        assert batches_p == batches_g

    def test_pipeline_detects_validation_errors(self, models_dir):
        models = scan_models(models_dir)
        _, _, _, errors = build_pipeline(models, [])

        source_errors = [
            e for e in errors if e.error_type == "missing_source"
        ]
        assert len(source_errors) > 0

    def test_pipeline_parsed_models_have_refs(self, models_dir):
        models = scan_models(models_dir)
        _, _, parsed_models, _ = build_pipeline(models, ["raw"])

        fct = next(pm for pm in parsed_models if pm.name == "fct_revenue")
        assert "stg_orders" in fct.refs
        assert "stg_customers" in fct.refs

    def test_pipeline_with_select_exact(self, models_dir):
        models = scan_models(models_dir)
        _, batches, _, _ = build_pipeline(models, ["raw"], select="stg_orders")
        flat = [name for batch in batches for name in batch]
        assert flat == ["stg_orders"]

    def test_pipeline_with_select_descendants(self, models_dir):
        models = scan_models(models_dir)
        _, batches, _, _ = build_pipeline(models, ["raw"], select="stg_orders+")
        flat = [name for batch in batches for name in batch]
        assert "stg_orders" in flat
        assert "fct_revenue" in flat
        # stg_customers is NOT a descendant of stg_orders
        assert "stg_customers" not in flat

    def test_pipeline_with_select_none_returns_all(self, models_dir):
        models = scan_models(models_dir)
        _, batches_all, _, _ = build_pipeline(models, ["raw"])
        _, batches_none, _, _ = build_pipeline(models, ["raw"], select=None)
        assert batches_all == batches_none


class TestValidateDag:
    def test_validate_ok(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        errors = validate_dag(dag, models, ["raw"])
        assert len(errors) == 0

    def test_validate_missing_source(self, models_dir):
        models = scan_models(models_dir)
        dag = build_dag(models)
        # Don't declare any sources
        errors = validate_dag(dag, models, [])
        source_errors = [
            e for e in errors if e.error_type == "missing_source"
        ]
        assert len(source_errors) > 0
