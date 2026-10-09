"""FR-08: BKT mastery сервисийн тест."""

from app.services import mastery as m


def test_bkt_update_moves_in_right_direction():
    p = 0.5
    up = m.bkt_update(p, True, learn=0.1, guess=0.1, slip=0.1)
    down = m.bkt_update(p, False, learn=0.1, guess=0.1, slip=0.1)
    assert up > p > down


def test_bkt_update_is_clamped():
    p = m.bkt_update(0.99999, True, learn=0.5, guess=0.1, slip=0.1)
    assert p <= 1 - m.EPS
    # 1.0 дээр гацахгүй: буруу хариулт бууруулж чадна
    assert m.bkt_update(p, False, learn=0.0, guess=0.1, slip=0.1) < p


def test_params_fallback_to_default(tmp_path, monkeypatch):
    m.load_bkt_params.cache_clear()
    monkeypatch.setattr(m.settings, "bkt_params_path", str(tmp_path / "missing.yaml"))
    assert m.params_for("T01") == m.DEFAULT_PARAMS
    m.load_bkt_params.cache_clear()


def test_params_from_yaml(tmp_path, monkeypatch):
    (tmp_path / "bkt.yaml").write_text(
        "default:\n  prior: 0.3\n  learn: 0.2\n  guess: 0.1\n  slip: 0.1\n"
        "topics:\n  T01:\n    prior: 0.5\n",
        encoding="utf-8",
    )
    m.load_bkt_params.cache_clear()
    monkeypatch.setattr(m.settings, "bkt_params_path", str(tmp_path / "bkt.yaml"))
    assert m.params_for("T01")["prior"] == 0.5
    assert m.params_for("T01")["learn"] == 0.2  # default-аас өвлөнө
    assert m.params_for("T02")["prior"] == 0.3
    m.load_bkt_params.cache_clear()
