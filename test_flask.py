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


if __name__ == "__main__":
    test_get_index()
    test_post_calculate_valid()
    test_post_calculate_invalid_r1()
    print("\nAll Flask smoke tests passed!")