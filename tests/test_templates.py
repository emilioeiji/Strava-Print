from strava_print.layouts.templates import available_templates, load_template


def test_templates_load() -> None:
    for name in available_templates():
        assert load_template(name).width_mm > 0
