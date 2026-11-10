# BJT Common-Emitter DC Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เว็บแอป Flask หน้าเดียวที่คำนวณ DC operating point ของวงจร BJT common-emitter แบบแบ่งแรงดัน พร้อมตรวจสอบข้อมูล คำเตือนย่านการทำงาน และการคำนวณตรวจทานอิสระ

**Architecture:** แยกตรรกะวิศวกรรมล้วนไว้ใน `bjt.py` (ไม่ import Flask) ใช้ dataclass เป็นอินพุต/เอาต์พุต และมี solver สองชุดคือสูตรปิดแบบเทวินินกับ bisection เชิงตัวเลข จากนั้น `app.py` เป็นชั้นบาง ๆ ที่แปลงฟอร์มเป็น `BiasInput` แล้ว render ด้วย Jinja

**Tech Stack:** Python 3.14.2, Flask 3.1.x, Jinja2, pytest, HTML/CSS ล้วน (ไม่มี JavaScript)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- ทำงานบน branch `feature/bjt-bias` (สร้างไว้แล้ว)
- Python ใช้ `py`; ทุกคำสั่งเทสต์/รันใช้ `.venv\Scripts\python.exe`
- git ไม่อยู่ใน PATH ใช้ `& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe"`
- หน่วย SI ภายใน: V, Ω, A; แสดงกระแสเป็น mA (3 ตำแหน่ง) และแรงดันเป็น V (3 ตำแหน่ง)
- `VCE_SAT_V = 0.2` คงที่
- ข้อความ validation และคำเตือนต้องตรงตาม spec ทุกตัวอักษร
- `bjt.py` ห้าม import Flask
- ห้ามแก้หรือลบ `electrical.py`, `test_electrical.py`, `README.md` ที่ root
- ไม่มี JavaScript, ฐานข้อมูล, session, ไลบรารีคำนวณเพิ่ม
- route ตอบ HTTP 200 ทั้งกรณีสำเร็จและข้อมูลผิดพลาด

## Review Focus

1. ผู้ใช้กรอกความต้านทานเป็น kΩ (47 แทน 47000) แล้วได้ผลผิดโดยไม่รู้ → ฟอร์มต้องมีหน่วย Ω ชัดเจน (เทสต์ใน Task 4 ตรวจว่ามี "Ω" ในหน้า)
2. ค่า `inf` / `nan` → ต้องได้ข้อผิดพลาดรายช่อง ไม่ใช่ 500 (Task 1)
3. `VBE` นอกช่วง `(0, VCC)` → ต้องถูกปฏิเสธ (Task 1)
4. แซทเทอเรชันที่คำนวณได้ `VCE` ติดลบ → ต้อง render พร้อมคำเตือน ไม่ crash (Task 2, Task 5)
5. ทศนิยมจุลภาค `12,5` → ต้องได้ "ต้องเป็นตัวเลข" ไม่ใช่ 500 (Task 1)

## File Structure

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `bjt_bias/__init__.py` | ทำให้เป็น package ว่าง ๆ |
| `bjt_bias/bjt.py` | dataclass, validation, solver สองชุด, การเปรียบเทียบ |
| `bjt_bias/app.py` | Flask app, route `GET /` และ `POST /calculate` |
| `bjt_bias/templates/index.html` | ฟอร์มและส่วนผลลัพธ์ |
| `bjt_bias/static/style.css` | สไตล์ทั้งหมด |
| `bjt_bias/tests/test_bjt.py` | เทสต์ตรรกะวิศวกรรม |
| `bjt_bias/tests/test_app.py` | เทสต์ route |
| `bjt_bias/requirements.txt` | Flask, pytest |
| `bjt_bias/README.md` | วิธีติดตั้ง/รัน/ทดสอบ และข้อจำกัด |

---

### Task 1: Scaffold, venv และการตรวจสอบข้อมูล

**Files:**
- Create: `bjt_bias/__init__.py`
- Create: `bjt_bias/requirements.txt`
- Create: `bjt_bias/bjt.py`
- Test: `bjt_bias/tests/test_bjt.py`

**Interfaces:**
- Produces: `FIELDS: tuple[str, ...]` = `("vcc", "r1", "r2", "rc", "re", "beta", "vbe")`
- Produces: `BiasInput(vcc, r1, r2, rc, re, beta, vbe)` dataclass แบบ frozen
- Produces: `ValidationError(errors: dict[str, str])` มี attribute `.errors`
- Produces: `parse_inputs(raw: Mapping[str, str]) -> BiasInput` (raise `ValidationError`)
- Produces: `validate(inp: BiasInput) -> dict[str, str]`

- [ ] **Step 1: สร้างไฟล์ตั้งต้นและ venv**

`bjt_bias/__init__.py` เป็นไฟล์ว่าง

`bjt_bias/requirements.txt`:
```
Flask>=3.1,<4
pytest>=8.3
```

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r bjt_bias\requirements.txt
```

- [ ] **Step 2: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `bjt_bias/tests/test_bjt.py`:

```python
import pytest

from bjt_bias.bjt import BiasInput, ValidationError, parse_inputs

VALID = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}


def test_parse_inputs_returns_bias_input():
    assert parse_inputs(VALID) == BiasInput(
        vcc=12.0, r1=47000.0, r2=10000.0, rc=4700.0, re=1000.0, beta=100.0, vbe=0.7
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("vcc", "0", "ต้องมากกว่า 0"),
        ("vcc", "-1", "ต้องมากกว่า 0"),
        ("r1", "0", "ต้องมากกว่า 0"),
        ("r2", "-5", "ต้องมากกว่า 0"),
        ("rc", "0", "ต้องมากกว่า 0"),
        ("re", "0", "ต้องมากกว่า 0"),
        ("beta", "0", "ต้องมากกว่า 0"),
        ("vbe", "0", "ต้องอยู่ระหว่าง 0 ถึง VCC"),
        ("vbe", "12", "ต้องอยู่ระหว่าง 0 ถึง VCC"),
        ("r1", "abc", "ต้องเป็นตัวเลข"),
        ("r1", "", "กรุณากรอกค่านี้"),
        ("vcc", "inf", "ต้องเป็นตัวเลขจำกัด"),
        ("vcc", "nan", "ต้องเป็นตัวเลขจำกัด"),
        ("vcc", "12,5", "ต้องเป็นตัวเลข"),
    ],
)
def test_validation_errors(field, value, message):
    data = dict(VALID)
    data[field] = value
    with pytest.raises(ValidationError) as excinfo:
        parse_inputs(data)
    assert message in excinfo.value.errors[field]


def test_validation_collects_all_errors():
    data = dict(VALID)
    data["r1"] = "0"
    data["beta"] = "-1"
    with pytest.raises(ValidationError) as excinfo:
        parse_inputs(data)
    assert set(excinfo.value.errors) == {"r1", "beta"}
```

- [ ] **Step 3: รันเทสต์ให้เห็นว่า fail**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias.bjt'`

- [ ] **Step 4: implement `bjt_bias/bjt.py`**

สร้าง dataclass, `ValidationError`, `parse_inputs`, `validate` ตามนี้:
- `parse_inputs` วนตาม `FIELDS`, ตัด whitespace, ช่องว่าง → `กรุณากรอกค่านี้`
- `float()` ล้มเหลว → `ต้องเป็นตัวเลข`; `math.isfinite` เป็นเท็จ → `ต้องเป็นตัวเลขจำกัด`
- เก็บ error ทุกช่องก่อน; ถ้าไม่มี error จึงเรียก `validate`
- `validate`: `vcc`, `r1`, `r2`, `rc`, `re`, `beta` ต้อง `> 0` → `ต้องมากกว่า 0`
- `vbe` ต้อง `0 < vbe < vcc` (ตรวจเฉพาะเมื่อ `vcc > 0`) → `ต้องอยู่ระหว่าง 0 ถึง VCC`
- ถ้ามี error ให้ `raise ValidationError(errors)`; `ValidationError.__init__` เก็บ `self.errors = dict(errors)`

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: PASS ทั้งหมด

- [ ] **Step 6: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/__init__.py bjt_bias/requirements.txt bjt_bias/bjt.py bjt_bias/tests/test_bjt.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "feat: add BJT input validation"
```

---

### Task 2: สูตรปิดแบบเทวินินและการแบ่งย่าน

**Files:**
- Modify: `bjt_bias/bjt.py`
- Test: `bjt_bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput`, `parse_inputs`
- Produces: `BiasResult(vbb_v, rb_ohm, ib_a, ic_a, ie_a, vce_v, region, warning)` dataclass แบบ frozen
- Produces: `VCE_SAT_V = 0.2`, `CUTOFF_WARNING`, `SATURATION_WARNING`
- Produces: `solve_thevenin(inp: BiasInput) -> BiasResult`
- Produces (ภายใน): `_make_result(inp, vbb, rb, ib) -> BiasResult` ใช้ร่วมกับ Task 3

- [ ] **Step 1: เพิ่มเทสต์ที่ยังไม่ผ่าน**

ต่อท้าย `bjt_bias/tests/test_bjt.py`:

```python
from bjt_bias.bjt import solve_thevenin


def test_known_active_case():
    result = solve_thevenin(parse_inputs(VALID))
    assert result.region == "active"
    assert result.warning is None
    assert result.vbb_v == pytest.approx(2.10526, rel=1e-4)
    assert result.rb_ohm == pytest.approx(8245.61, rel=1e-4)
    assert result.ib_a == pytest.approx(1.28634e-5, rel=1e-3)
    assert result.ic_a == pytest.approx(1.28634e-3, rel=1e-3)
    assert result.ie_a == pytest.approx(1.29921e-3, rel=1e-3)
    assert result.vce_v == pytest.approx(4.655, rel=1e-3)


def test_cutoff_case():
    data = dict(VALID, r1="100000", r2="1000")
    result = solve_thevenin(parse_inputs(data))
    assert result.region == "cutoff"
    assert result.ib_a == 0.0
    assert result.ic_a == 0.0
    assert result.ie_a == 0.0
    assert result.vce_v == pytest.approx(12.0)
    assert "คัตออฟ" in result.warning


def test_saturation_case():
    data = dict(VALID, r1="10000", r2="10000", rc="1000", re="100")
    result = solve_thevenin(parse_inputs(data))
    assert result.region == "saturation"
    assert result.vce_v < 0
    assert "แซทเทอเรชัน" in result.warning
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: FAIL — `ImportError: cannot import name 'solve_thevenin'`

- [ ] **Step 3: implement**

เพิ่มใน `bjt_bias/bjt.py`:
- `VCE_SAT_V = 0.2`
- `CUTOFF_WARNING = "ทรานซิสเตอร์อยู่ในย่านคัตออฟ (IB = 0) — ไม่มีกระแสสะสม"`
- `SATURATION_WARNING = "ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง"`
- `BiasResult` ตาม Interfaces
- `solve_thevenin`: คำนวณ `vbb`, `rb`, `ib` ตามสูตรใน spec แล้วเรียก `_make_result(inp, vbb, rb, ib)`
- `_make_result`: ถ้า `ib <= 0` คืน cutoff (`ic=ie=0`, `vce=inp.vcc`); ไม่งั้นคำนวณ `ic`, `ie`, `vce`; ถ้า `vce <= VCE_SAT_V` คืน saturation พร้อมคำเตือน; ไม่งั้น active (`warning=None`)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: PASS ทั้งหมด

- [ ] **Step 5: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/bjt.py bjt_bias/tests/test_bjt.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "feat: add Thevenin DC bias solver and region warnings"
```

---

### Task 3: Solver เชิงตัวเลข การเปรียบเทียบ และ `analyze`

**Files:**
- Modify: `bjt_bias/bjt.py`
- Test: `bjt_bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput`, `BiasResult`, `solve_thevenin`, `_make_result`
- Produces: `solve_numerical(inp: BiasInput) -> BiasResult`
- Produces: `compare_results(primary: BiasResult, check: BiasResult, rel_tol: float = 1e-6) -> dict` โดยมีคีย์ `agrees`, `delta_ic_a`, `delta_vce_v`
- Produces: `analyze(inp: BiasInput) -> dict` โดยมีคีย์ `primary`, `check`, `comparison`

- [ ] **Step 1: เพิ่มเทสต์ที่ยังไม่ผ่าน**

ต่อท้าย `bjt_bias/tests/test_bjt.py`:

```python
from bjt_bias.bjt import BiasResult, analyze, compare_results, solve_numerical


def _input(**overrides):
    params = dict(
        vcc=12.0, r1=47000.0, r2=10000.0, rc=4700.0, re=1000.0, beta=100.0, vbe=0.7
    )
    params.update(overrides)
    return BiasInput(**params)


def test_numerical_matches_thevenin_across_grid():
    cases = [
        _input(),
        _input(vcc=5.0, r1=10000.0, r2=2200.0, rc=1000.0, re=220.0, beta=50.0),
        _input(vcc=24.0, r1=100000.0, r2=22000.0, rc=4700.0, re=1000.0, beta=300.0),
        _input(r1=100000.0, r2=1000.0),
        _input(r1=10000.0, r2=10000.0, rc=1000.0, re=100.0),
    ]
    for inp in cases:
        comparison = compare_results(solve_thevenin(inp), solve_numerical(inp))
        assert comparison["agrees"] is True


def test_numerical_cutoff_has_zero_current():
    result = solve_numerical(_input(r1=100000.0, r2=1000.0))
    assert result.ic_a == pytest.approx(0.0, abs=1e-12)


def test_compare_detects_mismatch():
    primary = BiasResult(0.0, 0.0, 0.0, 1e-3, 1e-3, 5.0, "active", None)
    check = BiasResult(0.0, 0.0, 0.0, 2e-3, 2e-3, 4.0, "active", None)
    assert compare_results(primary, check)["agrees"] is False


def test_analyze_returns_primary_check_and_comparison():
    analysis = analyze(_input())
    assert set(analysis) == {"primary", "check", "comparison"}
    assert analysis["comparison"]["agrees"] is True
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: FAIL — `ImportError: cannot import name 'solve_numerical'`

- [ ] **Step 3: implement**

เพิ่มใน `bjt_bias/bjt.py` (bisection เป็นอัลกอริทึมที่เทสต์ไม่ได้กำหนดรูปแบบ จึงให้โครงไว้):

```python
def _base_kcl(inp: BiasInput, vb: float) -> float:
    ib = max(0.0, vb - inp.vbe) / ((1 + inp.beta) * inp.re)
    return (inp.vcc - vb) / inp.r1 - vb / inp.r2 - ib


def solve_numerical(inp: BiasInput) -> BiasResult:
    low, high = 0.0, inp.vcc
    for _ in range(200):
        mid = (low + high) / 2
        if _base_kcl(inp, mid) > 0:
            low = mid
        else:
            high = mid
    vb = (low + high) / 2
    vbb = inp.vcc * inp.r2 / (inp.r1 + inp.r2)
    rb = inp.r1 * inp.r2 / (inp.r1 + inp.r2)
    ib = max(0.0, vb - inp.vbe) / ((1 + inp.beta) * inp.re)
    return _make_result(inp, vbb, rb, ib)
```

`compare_results`: ใช้ `abs(a - b) <= max(1e-9, rel_tol * max(abs(a), abs(b)))` กับทั้ง `ic_a` และ `vce_v`; `agrees` เป็น AND ของทั้งคู่; คืน delta เป็นค่าสัมบูรณ์

`analyze`: คืน `{"primary": solve_thevenin(inp), "check": solve_numerical(inp), "comparison": compare_results(...)}`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py -v
```
Expected: PASS ทั้งหมด

- [ ] **Step 5: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/bjt.py bjt_bias/tests/test_bjt.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "feat: add independent numerical solver and cross-check"
```

---

### Task 4: Flask app, ฟอร์ม และ CSS (`GET /`)

**Files:**
- Create: `bjt_bias/app.py`
- Create: `bjt_bias/templates/index.html`
- Create: `bjt_bias/static/style.css`
- Test: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `FIELDS`, `ValidationError`, `analyze`, `parse_inputs`
- Produces: `app: Flask` และ `DEFAULTS: dict[str, str]`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `bjt_bias/tests/test_app.py`:

```python
import pytest

from bjt_bias.app import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_index_shows_form_with_defaults(client):
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
        assert f'name="{name}"' in html
    assert 'value="47000"' in html
    assert "Ω" in html
    assert "BJT" in html
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_app.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias.app'`

- [ ] **Step 3: implement**

`bjt_bias/app.py`:

```python
from flask import Flask, render_template

from .bjt import FIELDS, ValidationError, analyze, parse_inputs

app = Flask(__name__)

DEFAULTS = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}


@app.get("/")
def index():
    return render_template("index.html", values=DEFAULTS, errors={}, analysis=None)
```

`bjt_bias/templates/index.html` ต้องมี:
- `<form method="post" action="{{ url_for('calculate') }}">` (route จะมีใน Task 5)
- input 7 ตัว `name` ตรงกับ `FIELDS`, `type="text"`, `inputmode="decimal"`, `value="{{ values.<field> }}"`
- ป้ายกำกับระบุหน่วย: `VCC (V)`, `R1 (Ω)`, `R2 (Ω)`, `RC (Ω)`, `RE (Ω)`, `beta`, `VBE (V)`
- แสดง `errors.<field>` ใน `<p class="error">` ถ้ามี
- `<section id="results">` แสดงเฉพาะเมื่อ `analysis` ไม่เป็น None (Task 5 จะทดสอบ)
- ในส่วนผลลัพธ์ใช้ `region_labels = {"active": "แอกทีฟ (Active)", "saturation": "แซทเทอเรชัน (Saturation)", "cutoff": "คัตออฟ (Cutoff)"}`

`bjt_bias/static/style.css`: ฟอนต์ระบบ, `max-width: 900px`, ฟอร์มเป็น grid, `.error` สีแดง, `.warning` สีส้ม, `.region-active/.region-saturation/.region-cutoff` คนละสี

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_app.py -v
```
Expected: PASS

- [ ] **Step 5: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/static/style.css bjt_bias/tests/test_app.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "feat: add Flask form page"
```

---

### Task 5: `POST /calculate` และการแสดงผลลัพธ์

**Files:**
- Modify: `bjt_bias/app.py`
- Modify: `bjt_bias/templates/index.html`
- Test: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `parse_inputs`, `analyze`, `ValidationError.errors`
- Produces: route `calculate` สำหรับ `url_for('calculate')`

- [ ] **Step 1: เพิ่มเทสต์ที่ยังไม่ผ่าน**

ต่อท้าย `bjt_bias/tests/test_app.py`:

```python
VALID = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}


def test_calculate_valid_input_shows_results(client):
    response = client.post("/calculate", data=VALID)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="results"' in html
    assert "1.286" in html
    assert "4.655" in html
    assert "แอกทีฟ" in html
    assert "ตรงกัน" in html


def test_calculate_invalid_input_shows_field_error(client):
    data = dict(VALID, r1="0")
    response = client.post("/calculate", data=data)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "ต้องมากกว่า 0" in html
    assert 'id="results"' not in html
    assert 'value="0"' in html


def test_calculate_non_numeric_input_shows_error(client):
    data = dict(VALID, vcc="abc")
    response = client.post("/calculate", data=data)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "ต้องเป็นตัวเลข" in html
    assert 'id="results"' not in html


def test_calculate_cutoff_shows_warning(client):
    data = dict(VALID, r1="100000", r2="1000")
    response = client.post("/calculate", data=data)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "คัตออฟ" in html


def test_calculate_saturation_shows_warning(client):
    data = dict(VALID, r1="10000", r2="10000", rc="1000", re="100")
    response = client.post("/calculate", data=data)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "แซทเทอเรชัน" in html
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่า fail**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_app.py -v
```
Expected: FAIL — POST `/calculate` ตอบ 405

- [ ] **Step 3: implement**

เพิ่มใน `bjt_bias/app.py`:

```python
from flask import request


@app.post("/calculate")
def calculate():
    values = {name: request.form.get(name, "") for name in FIELDS}
    try:
        bias_input = parse_inputs(values)
    except ValidationError as error:
        return render_template(
            "index.html", values=values, errors=error.errors, analysis=None
        )
    return render_template(
        "index.html", values=values, errors={}, analysis=analyze(bias_input)
    )
```

ใน `index.html` ส่วน `id="results"` ต้องแสดง:
- ป้ายย่าน: `analysis.primary.region` พร้อมข้อความจาก `region_labels`
- คำเตือน: `analysis.primary.warning` ถ้ามี
- ตารางผล: `VBB` (V), `RB` (Ω), `IB`/`IC`/`IE` (mA), `VCE` (V) โดยคูณกระแสด้วย 1000 และ format 3 ตำแหน่ง
- แผงตรวจทาน: ค่า `analysis.check.ic_a * 1000` (mA) และ `analysis.check.vce_v` (V), `delta_ic_a * 1000`, `delta_vce_v`, และข้อความ `ตรงกัน` เมื่อ `analysis.comparison.agrees` เป็นจริง ไม่งั้น `ไม่ตรงกัน`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests -v
```
Expected: PASS ทั้งหมด

- [ ] **Step 5: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/tests/test_app.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "feat: calculate and render DC operating point"
```

---

### Task 6: README, เทสต์独立性 และเดโม localhost

**Files:**
- Create: `bjt_bias/README.md`
- Test: `bjt_bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: ทุกส่วนก่อนหน้า

- [ ] **Step 1: เพิ่มเทสต์ว่า `bjt.py` ไม่ import Flask**

ต่อท้าย `bjt_bias/tests/test_bjt.py`:

```python
import subprocess
import sys


def test_engineering_module_does_not_import_flask():
    code = (
        "import sys; import bjt_bias.bjt; "
        "print('flask' in sys.modules)"
    )
    output = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert output.stdout.strip() == "False"
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าผ่าน (หรือ fail ถ้ามี import หลุด)**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests\test_bjt.py::test_engineering_module_does_not_import_flask -v
```
Expected: PASS

- [ ] **Step 3: เขียน `bjt_bias/README.md`**

ต้องมีหัวข้อ: ภาพรวมและขอบเขต, หน่วย (V, Ω, mA, ใช้จุดทศนิยม), สูตรที่ใช้, กฎการแบ่งย่าน, วิธีติดตั้ง, วิธีรัน, วิธีทดสอบ, ข้อจำกัด (ไม่มี AC/transient, แซทเทอเรชันใช้สมการแอกทีฟ), และตัวอย่างค่าตั้งต้นพร้อมผลที่คาดหวัง (IC ≈ 1.286 mA, VCE ≈ 4.655 V)

คำสั่งใน README:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r bjt_bias\requirements.txt
.venv\Scripts\python.exe -m pytest bjt_bias\tests -v
.venv\Scripts\python.exe -m flask --app bjt_bias.app run
```

- [ ] **Step 4: รันเทสต์ทั้งหมด**

```powershell
.venv\Scripts\python.exe -m pytest bjt_bias\tests -v
```
Expected: PASS ทั้งหมด

- [ ] **Step 5: เปิด localhost และตรวจสอบ**

```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m","flask","--app","bjt_bias.app","run","--port","5000" -WindowStyle Hidden
Start-Sleep -Seconds 3
(Invoke-WebRequest -Uri "http://127.0.0.1:5000" -UseBasicParsing).StatusCode
```
Expected: `200` และหน้าเว็บแสดงฟอร์ม

ตรวจ POST ด้วย:
```powershell
(Invoke-WebRequest -Uri "http://127.0.0.1:5000/calculate" -Method Post -Body @{vcc="12";r1="47000";r2="10000";rc="4700";re="1000";beta="100";vbe="0.7"} -UseBasicParsing).Content -match "1.286"
```
Expected: `True`

จากนั้นหยุดเซิร์ฟเวอร์:
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*flask*bjt_bias.app*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

- [ ] **Step 6: commit**

```powershell
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" add bjt_bias/README.md bjt_bias/tests/test_bjt.py
& "C:\Users\B6813918\AppData\Local\Programs\Git\cmd\git.exe" commit -m "docs: add BJT bias app README and independence test"
```

---

## หลังจบแผน

ใช้ `superpowers:finishing-a-development-branch` เพื่อ merge `feature/bjt-bias` เข้า `main`
และ push ขึ้น `origin/main` ตามที่เจ้าของงานต้องการในวันนี้
