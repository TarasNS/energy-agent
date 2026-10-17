from pathlib import Path

from energy_harness.config import POC_ROOT, load_settings


def test_loads_shipped_config_with_env_overrides():
    settings = load_settings(
        POC_ROOT / "config.yaml",
        env={"OPENROUTER_API_KEY": "sk-test", "ENERGY_HARNESS_MODELS": "a/b:free, openrouter/free"},
    )
    assert settings.api_key == "sk-test"
    assert settings.models == ["a/b:free", "openrouter/free"]
    assert settings.parks_file == POC_ROOT / "parks.yaml"
    assert settings.budget.requests_per_day == 50


def test_shipped_chain_starts_with_primary_and_ends_with_router():
    settings = load_settings(POC_ROOT / "config.yaml", env={})
    assert settings.api_key is None
    assert settings.models[0] == "openai/gpt-oss-120b:free"
    assert settings.models[-1] == "openrouter/free"
    assert all(m.endswith(":free") or m == "openrouter/free" for m in settings.models)


def test_relative_paths_resolve_against_config_dir(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("models: [x/y:free]\nparks_file: p.yaml\nruns_dir: out\n")
    settings = load_settings(cfg, env={})
    assert settings.parks_file == tmp_path / "p.yaml"
    assert settings.runs_dir == tmp_path / "out"
