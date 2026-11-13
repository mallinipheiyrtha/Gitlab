# BJT Results: VB/VE/VC + SI Units — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม VB, VE, VC ในผลลัพธ์ และแสดงแรงดัน/กระแสด้วยหน่วย SI ที่เหมาะกับขนาดค่า

**Architecture:** เพิ่มฟิลด์โหนดใน `BiasResult` (คำนวณตามสมการที่เจ้าของโปรเจกต์กำหนด) และเพิ่ม Jinja filter `si` ที่เลือก prefix วิศวกรรม; template แสดง 7 แถวตามภาพ

**Tech Stack:** Python 3.15 / Flask 3.1 / Jinja2 / pytest

**Spec:** `docs/superpowers/specs/2026-11-13-bjt-results-si-units-design.md`

## Global Constraints

- สมการต้องตรงตาม spec ทุกตัว (VE = IE·RE, VB = VE + VBE, VC = VCC − IC·RC, VCE = VC − VE)
- ห้ามเปลี่ยนสูตร Thevenin/bisection หรือเกณฑ์แบ่งย่าน
- Cutoff: VE = 0, VC = VCC, VB = VTH
- หน่วย SI: prefix วิศวกรรม (p, n, µ, m, ฐาน, k, M, G), ทศนิยม 3 ตำแหน่งตัดศูนย์ท้าย, ใช้ `µ` (U+00B5)
- ต้องคง `id="results"`, ป้าย `แอกทีฟ`, ข้อความ `ตรงกัน`, ค่า IC `1.286` และ VCE `4.655` ที่เทสต์เดิมตรวจ
- คำสั่งเทสต์: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q`

## Review Focus

- ค่า IB น้อยมาก (เช่น 1 µA) → ต้องแสดง µA ไม่ใช่ 0.001 mA หรือ 0.000 mA
- ค่ากระแสเกิน 1 A → ต้องเปลี่ยนเป็น A ไม่ใช่ 1000 mA
- แรงดันติดลบ (เกิดได้ทางคณิตศาสตร์) → ต้องไม่พังและคงเครื่องหมายลบ
- ค่าเป็นศูนย์ (cutoff) → ต้องแสดง 0 พร้อมหน่วยฐาน ไม่ใช่ 0.000 µA
- ผล saturation/cutoff → ตารางต้องยังแสดง VB/VE/VC ครบและสอดคล้อง VCE = VC − VE

---

### Task 1: เพิ่ม VB/VE/VC ใน `BiasResult`

**Files:**
- Modify: `bjt_bias/bjt.py`
- Test: `bjt_bias/tests/test_bjt.py`

**Interfaces:**
- Produces: `BiasResult.vb_v`, `BiasResult.ve_v`, `BiasResult.vc_v` (float, โวลต์) ใช้ได้ทุก region
- Consumes: ฟิลด์เดิม `vcc`, `rc`, `re`, `vbe` ของ `BiasInput` และ `ib_a/ic_a/ie_a` ที่คำนวณอยู่แล้ว

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
def test_node_voltages_follow_equations_active():
    inp, _ = parse_inputs(VALID)
    r = solve_thevenin(inp)
    assert r.ve_v == pytest.approx(r.ie_a * inp.re)
    assert r.vb_v == pytest.approx(r.ve_v + inp.vbe)
    assert r.vc_v == pytest.approx(inp.vcc - r.ic_a * inp.rc)
    assert r.vce_v == pytest.approx(r.vc_v - r.ve_v)


def test_node_voltages_cutoff():
    inp, _ = parse_inputs({**VALID, "vbe": "11.9"})  # VBE < VCC แต่ทำให้ IB <= 0
    r = solve_thevenin(inp)
    assert r.region == "cutoff"
    assert r.ve_v == 0.0
    assert r.vc_v == pytest.approx(inp.vcc)
    assert r.vb_v == pytest.approx(r.vbb_v)


def test_node_voltages_saturation():
    inp, _ = parse_inputs({**VALID, "rc": "100000"})
    r = solve_thevenin(inp)
    assert r.region == "saturation"
    assert r.vce_v == pytest.approx(r.vc_v - r.ve_v)
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.venv\Scripts\python.exe -m pytest bjt_bias/tests -q -k node_voltages`
Expected: FAIL — `AttributeError: 'BiasResult' object has no attribute 've_v'`

- [ ] **Step 3: เพิ่มฟิลด์และคำนวณใน `bjt_bias/bjt.py`**

เพิ่ม `vb_v`, `ve_v`, `vc_v` ใน `BiasResult` (หลัง `vce_v`) และเติมค่าให้ครบทุกจุดที่สร้าง `BiasResult`
(active/saturation/cutoff ใน `solve_thevenin` และ `solve_numerical`) ตามสมการ:
`ve = ie * inp.re`, `vc = inp.vcc - ic * inp.rc`, `vb = ve + inp.vbe`;
กรณี cutoff ใช้ `vb = vbb`, `ve = 0.0`, `vc = inp.vcc` และ `vce = vc - ve`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m pytest bjt_bias/tests -q`
Expected: PASS ทั้งหมด

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/bjt.py bjt_bias/tests/test_bjt.py
git commit -m "feat(bjt): expose base, emitter and collector node voltages"
```

---

### Task 2: ตัวกรอง SI + ตารางผลลัพธ์ 7 แถว

**Files:**
- Modify: `bjt_bias/app.py`
- Modify: `bjt_bias/templates/index.html`
- Test: `test_flask.py`

**Interfaces:**
- Produces: `format_si(value: float, unit: str) -> str` ใน `bjt_bias/app.py` ลงทะเบียนเป็น filter `si`
  เรียกใน template: `{{ analysis.primary.ib_a|si("A") }}`
- Consumes: `analysis.primary.vb_v/ve_v/vc_v/vce_v/ib_a/ic_a/ie_a`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
def test_format_si_filter():
    from bjt_bias.app import format_si
    assert format_si(12.298e-6, "A") == "12.298 µA"
    assert format_si(1.286e-3, "A") == "1.286 mA"
    assert format_si(1.5, "A") == "1.5 A"
    assert format_si(0.0, "V") == "0 V"
    assert format_si(-0.2, "V") == "−0.2 V"


def test_results_table_shows_node_voltages_and_si_units():
    with app.test_client() as client:
        html = client.post("/calculate", data=VALID).get_data(as_text=True)
    for symbol in ("V<sub>B</sub>", "V<sub>E</sub>", "V<sub>C</sub>", "V<sub>CE</sub>"):
        assert symbol in html
    assert "µA" in html          # IB ของค่าตั้งต้นต้องเป็น µA
    assert "1.999" in html       # VB = VE + VBE
    assert "5.954" in html       # VC = VCC − IC·RC
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py -q -k "si or node_voltages"`
Expected: FAIL — `ImportError: cannot import name 'format_si'`

- [ ] **Step 3: เพิ่ม `format_si` ใน `bjt_bias/app.py`**

เลือก prefix จาก `[(1e9,"G"),(1e6,"M"),(1e3,"k"),(1,""),(1e-3,"m"),(1e-6,"µ"),(1e-9,"n"),(1e-12,"p")]`
โดยหาตัวแรกที่ `abs(value)/factor >= 1` (ค่า 0 → หน่วยฐาน) แล้วจัดรูปแบบด้วย `:.3f` ตัดศูนย์ท้าย
และใช้เครื่องหมายลบ Unicode `−` (U+2212) สำหรับค่าติดลบ ลงทะเบียนด้วย `@app.template_filter("si")`

- [ ] **Step 4: อัปเดตตารางผลลัพธ์ใน `index.html`**

แทนที่ 6 แถวเดิมด้วย 7 แถว: VB, VE, VC, VCE (หน่วย V) และ IB, IC, IE (หน่วย A) โดยใช้ filter `si`;
เพิ่มบรรทัดสรุปใต้ตาราง `VBB = {{ analysis.primary.vbb_v|si("V") }} · RB = {{ analysis.primary.rb_ohm|si("Ω") }}`;
เปลี่ยนตัวเลขในกล่อง "การตรวจสอบข้าม" ให้ใช้ filter `si` เช่นกัน

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m pytest test_flask.py bjt_bias/tests -q`
Expected: PASS ทั้งหมด

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html test_flask.py
git commit -m "feat(ui): show node voltages and SI-formatted results"
```
