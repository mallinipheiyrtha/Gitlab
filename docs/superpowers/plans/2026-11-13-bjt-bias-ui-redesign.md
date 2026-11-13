# BJT Bias Web App UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยนหน้าตาเว็บ Flask ของ BJT DC Bias ให้เป็นเลย์เอาต์ 3 คอลัมน์แบบ Lab 02 ตามภาพ mockup โดยไม่เปลี่ยนสูตรหรือตัวเลขคำนวณใด ๆ

**Architecture:** เขียน `bjt_bias/templates/index.html` ใหม่ทั้งไฟล์ (CSS ฝังในหน้า + แผนภาพวงจรเป็น inline SVG ไม่ใช้ JavaScript) เพิ่ม Jinja filter หนึ่งตัวใน `bjt_bias/app.py` เพื่อจัดรูปแบบค่าความต้านทานที่แสดงบนแผนภาพ `bjt_bias/bjt.py` ไม่ถูกแก้

**Tech Stack:** Python 3.15 / Flask 3.1 / Jinja2 / pytest

**Spec:** `docs/superpowers/specs/2026-11-13-bjt-bias-ui-redesign-design.md`

## Global Constraints

- ห้ามแก้ `bjt_bias/bjt.py` หรือสูตร/ค่าคำนวณ/การแบ่งย่านใด ๆ
- ฟิลด์ฟอร์มต้องคงชื่อ `vcc`, `r1`, `r2`, `rc`, `re`, `beta`, `vbe` และหน่วย V/Ω ตรงตัว (ไม่มี dropdown แปลงหน่วย, ไม่แปลงค่าอินพุต)
- ห้ามใช้ JavaScript และห้ามโหลด asset/CDN ภายนอก
- ผลลัพธ์แสดงเฉพาะเมื่อ `analysis is not none` และ element ผลลัพธ์ต้องมี `id="results"`
- ป้ายย่านต้องมีคำไทย: `แอกทีฟ`, `แซทเทอเรชัน`, `คัตออฟ`
- ค่าตั้งต้นต้องคำนวณได้ IC 1.286 mA และ VCE 4.655 V (ห้าม format จนตัวเลขเปลี่ยน)
- คำสั่งรันเทสต์: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q` (workdir = ราก repo)

## Review Focus

- อินพุตที่ไม่ใช่ตัวเลขหรือว่าง → หน้าต้องไม่พัง error ขึ้นที่ช่องนั้น และไม่มีผลลัพธ์โผล่
- ค่าความต้านทาน ≥ 1,000,000 Ω → ต้องแสดงเป็น MΩ ไม่ใช่ 1000 kΩ
- ผลตรวจสอบข้ามไม่ตรงกัน → กล่องสรุปต้องเป็นสถานะ "ไม่ตรงกัน" (ห้ามเขียว)
- คำเตือนภาษาไทยยาว (saturation/cutoff) → ต้องแสดงเต็มข้อความในแถบสถานะ ไม่ถูกตัดหาย
- ค่าที่ผู้ใช้กรอกต้องคงอยู่ในฟอร์มหลัง submit ที่ผิดพลาด (ห้ามรีเซ็ตเป็นค่าเริ่มต้น)

---

### Task 1: โครงหน้าใหม่ทั้งหน้า + แสดง error รายช่อง + ผลลัพธ์

**Files:**
- Modify: `bjt_bias/templates/index.html` (เขียนใหม่ทั้งไฟล์)
- Test: `test_flask.py`

**Interfaces:**
- Consumes: จาก `bjt_bias/app.py` — `render_template("index.html", values: dict[str,str], errors: dict[str,str], analysis: dict|None)`; `analysis.primary` (`.vbb_v`, `.rb_ohm`, `.ib_a`, `.ic_a`, `.ie_a`, `.vce_v`, `.region`, `.warning`), `analysis.check` (`.ic_a`, `.vce_v`), `analysis.comparison` (`.agrees`, `.delta_ic_a`, `.delta_vce_v`)
- Produces: คลาส CSS ที่ Task 2/3 ใช้ซ้ำ — `.app`, `.topbar`, `.grid`, `.card`, `.card-head`, `.field-row`, `.field-label`, `.field-input`, `.unit`, `.field-error`, `.btn-calculate`, `.results-table`, `.region-badge`, `.check-box`, `.goal-bar`; marker `data-state="agrees"` / `data-state="disagrees"` บน `.check-box`; `.grid` มี 3 คอลัมน์ และมี placeholder การ์ดวงจร `<section class="card circuit-card">` ที่ Task 2 เติมเนื้อหา

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่านใน `test_flask.py`**

เพิ่มต่อท้ายไฟล์ก่อนบล็อก `if __name__ == "__main__":`

```python
from types import SimpleNamespace
from flask import render_template
from bjt_bias.app import app as flask_app

VALID = {
    "vcc": "12", "r1": "47000", "r2": "10000", "rc": "4700",
    "re": "1000", "beta": "100", "vbe": "0.7",
}


def _stub_analysis(region="active", warning=None, agrees=True):
    primary = SimpleNamespace(
        vbb_v=2.105, rb_ohm=8245.6, ib_a=1.3e-5, ic_a=1.286e-3,
        ie_a=1.299e-3, vce_v=4.655, region=region, warning=warning,
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
    assert "DC Bias Results" in html
    assert "Week 2 Goal" in html


def test_post_invalid_r1_shows_error_and_keeps_value():
    with app.test_client() as client:
        html = client.post("/calculate", data={**VALID, "r1": "0"}).get_data(as_text=True)
    assert "ต้องมากกว่า 0" in html
    assert 'id="results"' not in html
    assert 'name="r1"' in html and 'value="0"' in html


def test_post_non_numeric_shows_error():
    with app.test_client() as client:
        html = client.post("/calculate", data={**VALID, "rc": "abc"}).get_data(as_text=True)
    assert "ต้องเป็นตัวเลข" in html
    assert 'name="rc"' in html and 'value="abc"' in html
    assert 'id="results"' not in html


def test_results_region_label_is_thai():
    with app.test_client() as client:
        html = client.post("/calculate", data=VALID).get_data(as_text=True)
    assert "แอกทีฟ" in html
    assert 'id="results"' in html


def test_results_warning_rendered_in_full():
    html = render_template(
        "index.html", values=VALID, errors={},
        analysis=_stub_analysis(region="saturation",
                                warning="ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง"),
    )
    assert "แซทเทอเรชัน" in html
    assert "ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง" in html


def test_results_disagreement_state():
    html = render_template("index.html", values=VALID, errors={},
                           analysis=_stub_analysis(agrees=False))
    assert 'data-state="disagrees"' in html
    assert "ไม่ตรงกัน" in html
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py -q`
Expected: FAIL (ขาด "Lab 02", "Input Parameters", ข้อความ error, `data-state`, ฯลฯ)

- [ ] **Step 3: เขียน `bjt_bias/templates/index.html` ใหม่**

โครงที่ต้องมี (CSS ฝังใน `<style>`):

1. `:root` ตัวแปรสี: teal `#0f766e` (ปุ่ม/ไอคอน), ฟ้าอ่อน `#e8f1fb` (กรอบ header/footer), เขียว `#dcfce7`/`#15803d` (สถานะปกติ), ส้ม `#ffedd5`/`#c2410c` (เตือน), แดง `#fee2e2`/`#b91c1c` (คัตออฟ), พื้นหลัง `#f5f8fc`, การ์ด `#ffffff`, เส้นขอบ `#e2e8f0`
2. `.topbar` — ไอคอนชิป inline SVG + `h1` "Lab 02: BJT DC Bias Web App" + บรรทัดรอง `ENG29 2121 – Common Emitter (Voltage Divider Bias)`; กรอบขวา `.course-badge` มีไอคอน `</>` และข้อความ "Computer Programming for Electrical Engineers"
3. `.grid` — `display:grid; grid-template-columns: 1fr 1.15fr 1fr; gap:1rem;` และ `@media (max-width:1100px){ .grid{grid-template-columns:1fr} }`
4. การ์ดซ้าย `h2` "Input Parameters" + form `method="post" action="/calculate"` วน 7 ช่องด้วยลิสต์ `(name, label, unit)`:
   `vcc → "V_CC (Supply Voltage)" / V`, `r1 → "R_1 (Upper Divider)" / Ω`, `r2 → "R_2 (Lower Divider)" / Ω`, `rc → "R_C (Collector Resistor)" / Ω`, `re → "R_E (Emitter Resistor)" / Ω`, `beta → "β (Current Gain)" / –`, `vbe → "V_BE (Base-Emitter Voltage)" / V`
   แต่ละช่อง: `<label for="{{ name }}">`, `<input type="text" id="{{ name }}" name="{{ name }}" value="{{ values[name] }}" required>`, `.unit` แสดงหน่วย, และ `{% if errors[name] %}<p class="field-error">{{ errors[name] }}</p>{% endif %}`
   ปุ่ม `.btn-calculate` เต็มความกว้าง ข้อความ "คำนวณ DC Bias" + ไอคอนเครื่องคิดเลข inline SVG
5. การ์ดกลาง `<section class="card circuit-card"><h2>Circuit: Common-Emitter Amplifier</h2>` — Task 2 เติม SVG
6. การ์ดขวา `id="results"` แสดงเฉพาะเมื่อ `analysis is not none`; `h2` "DC Bias Results"; ตาราง `.results-table` 6 แถวสลับสี: VBB (`%.3f V`), RB (`%.1f Ω`), IB (`%.3f mA` จาก `ib_a*1000`), IC (mA), IE (mA), VCE (`%.3f V`)
7. ใต้ตาราง: `.region-badge` แสดง `แอกทีฟ (Active)` / `แซทเทอเรชัน (Saturation)` / `คัตออฟ (Cutoff)` ตาม `analysis.primary.region` (`active`/`saturation`/`cutoff`) และถ้ามี `warning` แสดงใน `<p class="region-warning">` เต็มข้อความ
8. `.check-box` มี `data-state="{{ 'agrees' if analysis.comparison.agrees else 'disagrees' }}"` ข้อความ `ผลลัพธ์ตรงกัน (Agrees)` หรือ `ผลลัพธ์ไม่ตรงกัน (Disagrees)` พร้อมบรรทัด IC/VCE ของ Thevenin และเชิงตัวเลข และ delta ทั้งสองค่า (ข้อความเดิมจากเทมเพลตเก่า)
9. `.goal-bar` ท้ายหน้า — หัวข้อ "Week 2 Goal" + คำอธิบายเป้าหมายแล็บภาษาไทย (สร้างเว็บ Flask รับพารามิเตอร์วงจรและคำนวณไบแอส DC ของ common-emitter แบบแบ่งแรงดัน)
10. คง `lang="th"`, `<meta charset="utf-8">`, ชื่อ `<title>` เดิม, ไม่มี `<script>`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q`
Expected: PASS ทั้งหมด (ยกเว้นเทสต์ของ Task 2 ที่ยังไม่มี)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/templates/index.html test_flask.py
git commit -m "feat(ui): rebuild BJT bias page with Lab 02 three-column layout"
```

---

### Task 2: แผนภาพวงจร (SVG) + filter จัดรูปแบบค่าความต้านทาน

**Files:**
- Modify: `bjt_bias/app.py` (เพิ่ม `format_ohm` + `app.template_filter`)
- Modify: `bjt_bias/templates/index.html` (เติม SVG ในการ์ดกลาง)
- Test: `test_flask.py`

**Interfaces:**
- Produces: `format_ohm(raw: object) -> str` ใน `bjt_bias/app.py` ลงทะเบียนเป็น Jinja filter ชื่อ `ohm`; ค่าที่คืน: `< 1000` → `"470 Ω"`, `>= 1000 และ < 1e6` → `"47 kΩ"` / `"2.2 kΩ"` (ใช้ `{:g}` ตัดศูนย์ท้าย), `>= 1e6` → `"2.2 MΩ"`, แปลงไม่ได้/ว่าง/None → `"—"`
- Consumes: `values` จาก Task 1

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
def test_format_ohm_filter():
    from bjt_bias.app import format_ohm
    assert format_ohm("47000") == "47 kΩ"
    assert format_ohm("2200") == "2.2 kΩ"
    assert format_ohm("470") == "470 Ω"
    assert format_ohm("2200000") == "2.2 MΩ"
    assert format_ohm("abc") == "—"
    assert format_ohm("") == "—"


def test_get_renders_circuit_values():
    with app.test_client() as client:
        html = client.get("/").get_data(as_text=True)
    assert "Circuit: Common-Emitter Amplifier" in html
    assert "47 kΩ" in html   # r1 ค่าเริ่มต้น 47000 Ω
    assert "22 kΩ" not in html  # กันการ hard-code ค่าจากภาพ mockup
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py -q -k "format_ohm or circuit"`
Expected: FAIL — `ImportError: cannot import name 'format_ohm'`

- [ ] **Step 3: เพิ่ม `format_ohm` ใน `bjt_bias/app.py`**

วางหลัง `app = Flask(__name__)` — รับค่าดิบจากฟอร์ม (string), `float()` ใน `try/except (TypeError, ValueError)`, ตรวจ `math.isfinite`, แล้วเลือกหน่วย Ω/kΩ/MΩ ตามช่วง พร้อม `@app.template_filter("ohm")`

- [ ] **Step 4: เติม SVG ในการ์ดกลางของ `index.html`**

SVG แนวตั้ง viewBox ประมาณ `0 0 360 420`: ราง VCC ด้านบน, R1 ระหว่าง VCC กับโหนดฐาน, R2 จากโหนดฐานลง GND, RC จาก VCC ลงคอลเลกเตอร์, Q1 (วงกลม NPN + ลูกศร emitter), RE จากอีมิเตอร์ลง GND, สัญลักษณ์ GND ทั้งสองจุด; ป้ายกำกับใช้ค่าจริง: `V_CC = {{ values.vcc }} V`, `R_1 {{ values.r1|ohm }}`, `R_2 {{ values.r2|ohm }}`, `R_C {{ values.rc|ohm }}`, `R_E {{ values.re|ohm }}`, `Q1 NPN (β = {{ values.beta }})`; ใส่ `role="img"` และ `<title>` ว่า "Voltage-divider bias circuit"

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q`
Expected: PASS ทั้งหมด

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html test_flask.py
git commit -m "feat(ui): add circuit diagram with formatted component values"
```

---

### Task 3: เก็บรายละเอียดหน้าตา + ตรวจสอบด้วยตา

**Files:**
- Modify: `bjt_bias/templates/index.html`

**Interfaces:**
- Consumes: คลาสทั้งหมดจาก Task 1–2 (ไม่เปลี่ยนชื่อคลาสหรือ marker แล้ว)

- [ ] **Step 1: ปรับ CSS ให้ใกล้ภาพ**

ตรวจ: ระยะห่างการ์ด 16px, มุมโค้ง 14px, เงาบาง, ฟอนต์ system-ui ขนาด 15–16px, label เอียงแบบคณิต (`font-style:italic` เฉพาะตัวแปร), input สูง 38–40px ชิดขวาเป็นกล่องหน่วย, ตารางผลลัพธ์แถวคี่พื้น `#eef4fb`, ตัวเลขผลลัพธ์หนาชิดขวา, ปุ่ม teal เต็มความกว้างมีไอคอน, แถบ Week 2 Goal พื้นฟ้าอ่อนขอบมน, และ `:focus-visible` ring รอบ input/ปุ่มให้เห็นชัดตอนใช้คีย์บอร์ด

- [ ] **Step 2: รันเทสต์ทั้งหมดอีกครั้ง**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q`
Expected: PASS ทั้งหมด

- [ ] **Step 3: ตรวจด้วยตาในเบราว์เซอร์**

รันเซิร์ฟเวอร์ (ถ้ายังไม่รัน): `.venv\Scripts\python.exe -m flask --app bjt_bias.app run`
เปิด `http://127.0.0.1:5000/` แล้วกด "คำนวณ DC Bias" ด้วยค่าตั้งต้น — ต้องเห็น 3 คอลัมน์, วงจรมีค่า 47 kΩ/10 kΩ/4.7 kΩ/1 kΩ, ผลลัพธ์ IC 1.286 mA / VCE 4.655 V, ป้าย "แอกทีฟ (Active)", กล่องเขียว "ผลลัพธ์ตรงกัน", แถบ Week 2 Goal; ย่อหน้าต่างให้แคบกว่า 1100px แล้วต้องเรียงเป็นคอลัมน์เดียว

- [ ] **Step 4: Commit**

```bash
git add bjt_bias/templates/index.html
git commit -m "style(ui): polish Lab 02 layout spacing and responsive behavior"
```
