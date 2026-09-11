from app.dashboard import build_dashboard


def test_dashboard_indexes_every_food_by_slug():
    dash = build_dashboard()
    total = sum(len(entries) for entries in dash.by_category.values())
    assert total == 29
    assert len(dash.by_slug) == 29


def test_dashboard_entry_verdict_matches_rank():
    dash = build_dashboard()
    dranken = dash.by_category["dranken"]
    assert [e.score.food for e in dranken] == [
        "Water", "Zwarte koffie", "Light cola", "Sinaasappelsap", "Bouillon bereid", "Cola",
    ]
    assert dranken[0].verdict.tier == "top"
    assert dranken[0].verdict.rank == 1
    assert dranken[-1].verdict.tier == "low"
    assert dranken[-1].verdict.of == 6


def test_by_slug_lookup_resolves_to_the_right_category():
    dash = build_dashboard()
    entry = dash.by_slug["cola"]
    assert entry.score.food == "Cola"
    assert entry.score.category == "dranken"


def test_liver_is_top_tier_but_still_carries_a_ul_flag():
    dash = build_dashboard()
    entry = dash.by_slug["runderlever-gebakken"]
    assert entry.verdict.tier == "top"
    assert any(f["kind"] == "ul" for f in entry.verdict.flags)
