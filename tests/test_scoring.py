from services.scoring_service import calculate, interpret


def judge(score, **cats):
    base = {"clarity": score, "storytelling": score, "business": score, "innovation": score, "technical": score}
    base.update(cats)
    return {"overall_score": score, "category_scores": base}


def test_weighted_formula():
    r = calculate({"a": judge(0, clarity=100, storytelling=0, business=0, innovation=0, technical=0)})
    assert r["overall_score"] == 25.0  # clarity alone is 25%
    r = calculate({"a": judge(80)})
    assert r["overall_score"] == 80.0


def test_all_weights_add_up():
    r = calculate({"a": judge(100)})
    assert r["overall_score"] == 100.0


def test_averages_across_judges():
    r = calculate({"a": judge(40), "b": judge(60), "c": judge(80)})
    assert r["category_scores"]["clarity"] == 60.0
    assert r["overall_score"] == 60.0
    assert r["judge_scores"] == {"a": 40, "b": 60, "c": 80}
    assert not r["partial"]


def test_missing_value_is_skipped_not_zero():
    a = judge(80)
    b = judge(60)
    b["category_scores"]["business"] = None
    r = calculate({"a": a, "b": b})
    assert r["category_scores"]["business"] == 80.0  # NOT (80+0)/2
    assert r["partial"] and r["notes"]


def test_category_missing_everywhere_rescales_weights():
    a = judge(70)
    a["category_scores"]["technical"] = None
    r = calculate({"a": a})
    assert r["category_scores"]["technical"] is None
    assert r["overall_score"] == 70.0  # still 70, not dragged down by a fake 0
    assert any("rescaled" in n for n in r["notes"])


def test_out_of_range_rejected():
    a = judge(70)
    a["category_scores"]["clarity"] = 150
    r = calculate({"a": a})
    assert r["category_scores"]["clarity"] is None


def test_incomplete_judges_noted():
    r = calculate({"a": judge(50)}, expected_judges=3)
    assert r["partial"] and any("1 of 3" in n for n in r["notes"])


def test_no_data():
    r = calculate({})
    assert r["overall_score"] is None and r["interpretation"] == "Not available"


def test_interpretation_bands():
    cases = {0: "Critical", 39: "Critical", 39.9: "Critical", 40: "Needs major improvement", 59: "Needs major improvement",
             60: "Developing", 74: "Developing", 75: "Strong", 89: "Strong", 90: "Excellent", 100: "Excellent"}
    for score, label in cases.items():
        assert interpret(score) == label, score
