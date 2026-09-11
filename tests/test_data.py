from app.data import group_by_category, load_scores


def test_loads_all_rows_from_snapshot():
    scores = load_scores()
    assert len(scores) == 29
    assert {s.category for s in scores} >= {"dranken", "groente_fruit", "vetten"}


def test_water_is_the_construction_zero():
    scores = load_scores()
    water = next(s for s in scores if s.food == "Water")
    assert water.latent == 0.0


def test_categories_are_ranked_highest_latent_first():
    grouped = group_by_category(load_scores())
    dranken = grouped["dranken"]
    latents = [r.latent for r in dranken]
    assert latents == sorted(latents, reverse=True)
    assert dranken[0].food == "Water"
    assert dranken[-1].food == "Cola"


def test_ul_flag_parsed_for_liver():
    grouped = group_by_category(load_scores())
    liver = next(r for r in grouped["vis_vlees_ei"] if r.food == "Runderlever gebakken")
    assert liver.ul_flags["vit_a_ug"] == "132% van bovengrens"
