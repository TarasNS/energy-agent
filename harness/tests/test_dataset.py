from harness.dataset import build


# Generated with:
#   node -e "console.log(JSON.stringify(require('./tools/kpi-lab/data.js').build().assets[0].daily[0]))"
JS_FIRST_DAY_NORTH = {
    "date": "2026-06-01",
    "poaKwhM2": 4.82,
    "expectedMwh": 39.512,
    "actualMwh": 36.027,
    "availHours": 24,
    "outageHours": 0,
    "curtailedMwh": 0,
}


def test_same_seed_same_numbers():
    assert build() == build()


def test_shape_and_label():
    d = build()
    assert d["label"] == "SYNTHETIC: not Nordic Solar data"
    assert d["period"] == {"start": "2026-06-01", "end": "2026-06-30", "days": 30}
    assert [a["id"] for a in d["assets"]] == ["north", "south", "battery"]


def test_matches_the_javascript_dataset():
    # Values the JS chat showed for seed 20260601; a mismatch means the port drifted.
    d = build()
    north = d["assets"][0]["daily"][0]
    assert north == JS_FIRST_DAY_NORTH
