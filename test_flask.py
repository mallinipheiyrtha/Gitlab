"""Quick smoke test for the BJT Flask app."""
from bjt_bias.app import app


def test_get_index():
    with app.test_client() as client:
        resp = client.get("/")
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            assert f'name="{name}"' in html, f"Missing name={name}"
        assert "BJT" in html
        assert "Ω" in html
        print("  GET /: OK")


def test_post_calculate_valid():
    with app.test_client() as client:
        valid = {
            "vcc": "12",
            "r1": "47000",
            "r2": "10000",
            "rc": "4700",
            "re": "1000",
            "beta": "100",
            "vbe": "0.7",
        }
        resp = client.post("/calculate", data=valid)
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert "id='results'" in html or 'id="results"' in html, "Missing results section"
        assert "1.286" in html, "Missing IC ~1.286 mA"
        assert "4.655" in html, "Missing VCE ~4.655 V"
        assert "แอกทีฟ" in html, "Missing active region"
        assert "ตรงกัน" in html, "Missing agreement check"
        print("  POST /calculate (valid): OK")


def test_post_calculate_invalid_r1():
    with app.test_client() as client:
        valid = {
            "vcc": "12",
            "r1": "47000",
            "r2": "10000",
            "rc": "4700",
            "re": "1000",
            "beta": "100",
            "vbe": "0.7",
        }
        resp = client.post("/calculate", data={**valid, "r1": "0"})
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert "ต้องมากกว่า 0" in html, "Missing validation error"
        assert "id='results'" not in html, "Results should not show on error"
        print("  POST /calculate (r1=0): OK")


from types import SimpleNamespace

from flask import render_template

VALID = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}


def _stub_analysis(region="active", warning=None, agrees=True):
    """Build an analysis dict shaped like bjt_bias.app.analyze() output."""
    primary = SimpleNamespace(
        vbb_v=2.105,
        rb_ohm=8245.6,
        ib_a=1.3e-5,
        ic_a=1.286e-3,
        ie_a=1.299e-3,
        vce_v=4.655,
        region=region,
        warning=warning,
    )
    check = SimpleNamespace(ic_a=1.286e-3, vce_v=4.655)
    comparison = {"agrees": agrees, "delta_ic_a": 2.17e-19, "delta_vce_v": 0.0}
    return {"primary": primary, "check": check, "comparison": comparison}


def test_get_layout_sections():
    with app.test_client() as client:
        html = client.get("/").get_data(as_text=True)
    assert "Lab 02: BJT DC Bias Web App" in html
    assert "ENG29 2121" in html
    assert "Input Parameters" in html
    assert "Circuit: Common-Emitter Amplifier" in html
    assert "Week 2 Goal" in html


def test_post_invalid_r1_shows_error_and_keeps_value():
    with app.test_client() as client:
        html = client.post("/calculate", data={**VALID, "r1": "0"}).get_data(
            as_text=True
        )
    assert "ต้องมากกว่า 0" in html
    assert 'id="results"' not in html
    assert 'name="r1"' in html and 'value="0"' in html


def test_post_non_numeric_shows_error():
    with app.test_client() as client:
        html = client.post("/calculate", data={**VALID, "rc": "abc"}).get_data(
            as_text=True
        )
    assert "ต้องเป็นตัวเลข" in html
    assert 'name="rc"' in html and 'value="abc"' in html
    assert 'id="results"' not in html


def test_results_region_label_is_thai():
    with app.test_client() as client:
        html = client.post("/calculate", data=VALID).get_data(as_text=True)
    assert "DC Bias Results" in html
    assert "แอกทีฟ" in html
    assert 'id="results"' in html


def test_results_warning_rendered_in_full():
    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            values=VALID,
            errors={},
            analysis=_stub_analysis(
                region="saturation",
                warning=(
                    "ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — "
                    "ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง"
                ),
            ),
        )
    assert "แซทเทอเรชัน" in html
    assert "ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง" in html


def test_results_disagreement_state():
    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            values=VALID,
            errors={},
            analysis=_stub_analysis(agrees=False),
        )
    assert 'data-state="disagrees"' in html
    assert "ไม่ตรงกัน" in html


if __name__ == "__main__":
    test_get_index()
    test_post_calculate_valid()
    test_post_calculate_invalid_r1()
    print("\nAll Flask smoke tests passed!")