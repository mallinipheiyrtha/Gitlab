# BJT Common-Emitter DC Bias Calculator

## ภาพรวมและขอบเขต
แอปพลิเคชันเว็บหน้าเดียว (Flask) สำหรับคำนวณจุดทำงานกระแสตรง (DC operating point)
ของวงจรไบแอส common-emitter **สามแบบ** (Lab 03):

1. **Voltage Divider Bias** — แบบแบ่งแรงดัน (ค่าเริ่มต้น, ต่อยอดจาก Lab 02)
2. **Fixed Bias** — ไบอัสฐานคงที่ผ่าน RB
3. **Emitter Bias** — ไบอัสผ่าน RB และมี RE ป้อนกลับที่อิมิตเตอร์

ผู้ใช้เลือกโหมดจากแท็บบนหน้าเว็บ กรอกเฉพาะค่าที่วงจรนั้นต้องใช้ แล้วได้ผลลัพธ์
พร้อมหน่วย มีการตรวจสอบข้อมูล มีคำเตือนเมื่อทรานซิสเตอร์ไม่อยู่ในย่านแอกทีฟ
และโหมด Divider/Emitter มีการคำนวณตรวจทานอิสระอีกวิธีหนึ่ง

**ผลการตรวจรับ A1–A5 ผ่านเบราว์เซอร์:** ดู [docs/validation.md](../docs/validation.md)

**ขอบเขต (ตามที่กำหนดไว้):**
- **ทำ:** คำนวณ DC operating point เฉยๆ ไม่มี AC, transient, load line, กราฟ, ตัวแก้ไขวงจร, FET, เอาท์พุตกำลังไฟฟ้า
- **ไม่ทำ:** AC analysis, transient analysis, circuit editor, FET, database, JavaScript

## หน่วย
- แรงดัน: โวลต์ (V) — ใช้จุดทศนิยม (.)
- ความต้านทาน: โอห์ม (Ω)
- กระแส: มิลลิแอมแปร์ (mA) — แสดงผล 3 ตำแหน่งทางทศนิยม
- VCE: โวลต์ (V) — แสดงผล 3 ตำแหน่งทางทศนิยม

## โหมดและฟิลด์ที่ใช้
| โหมด | ฟิลด์ที่ต้องกรอก | เปิดด้วย |
|------|------------------|----------|
| Voltage Divider Bias | VCC, R1, R2, RC, RE, β, VBE | `/?mode=divider` (ค่าเริ่มต้น) |
| Fixed Bias | VCC, RB, RC, β, VBE | `/?mode=fixed` |
| Emitter Bias | VCC, RB, RC, RE, β, VBE | `/?mode=emitter` |

การสลับโหมดใช้ลิงก์ GET (โหลดฟอร์มใหม่) ไม่ใช้ JavaScript และฟอร์มจะส่ง
`mode` ที่เลือกไปกับ POST เสมอ ฟิลด์ที่ไม่เกี่ยวข้องกับโหมดจะไม่ถูกตรวจสอบ
และไม่ทำให้การคำนวณผิดพลาด

## สูตรที่ใช้

ทุกโหมดใช้ความสัมพันธ์ร่วมกัน:
$I_C = \beta I_B$, $I_E = (1 + \beta)I_B$, $V_E = I_E R_E$,
$V_C = V_{CC} - I_C R_C$, $V_B = V_E + V_{BE}$, $V_{CE} = V_C - V_E$

1. **Voltage Divider Bias (ค่าเริ่มต้น):**
   - $V_{BB} = V_{CC} \cdot \frac{R_2}{R_1 + R_2}$
   - $R_B = R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}$
   - $I_B = \frac{V_{BB} - V_{BE}}{R_B + (1 + \beta)R_E}$

2. **Fixed Bias:**
   - $I_B = \frac{V_{CC} - V_{BE}}{R_B}$
   - ไม่มี RE ดังนั้น $V_E = 0$ และ $V_B = V_{BE}$

3. **Emitter Bias:**
   - $I_B = \frac{V_{CC} - V_{BE}}{R_B + (1 + \beta)R_E}$

### การคำนวณตรวจทานอิสระ
- **Divider:** bisection บน KCL ที่โหนดฐาน
  $f(V_B) = \frac{V_{CC} - V_B}{R_1} - \frac{V_B}{R_2} - \frac{\max(0, V_B - V_{BE})}{(1 + \beta)R_E} = 0$
- **Emitter:** bisection บน KCL ที่โหนดฐาน
  $f(V_B) = \frac{V_{CC} - V_B}{R_B} - \frac{\max(0, V_B - V_{BE})}{(1 + \beta)R_E} = 0$
- ใช้วิธีแบ่งครึ่งช่วง (bisection) 200 รอบ แล้วคำนวณ $I_B, I_C, I_E, V_{CE}$
- เปรียบเทียบกับสูตรปิดโดยมี tolerance $10^{-6}$ (สัมพัทธ์)
- **Fixed Bias** ไม่มีการตรวจทานข้าม เพราะไม่มีลูปป้อนกลับที่ทำให้สมการ
  self-consistent แบบสองวิธี

### รูปแบบผลลัพธ์
ทุกโหมดคืน `BiasResult` โครงเดียวกับ Lab 2 (มี `vb_v`, `ve_v`, `vc_v`,
`vce_v`, `ic_a`, `warning` ฯลฯ) และมีเมธอด `as_lab_dict()` สำหรับแปลงเป็น
dict กลางของ Lab 03:

```python
{"vb_v": ..., "ve_v": ..., "vc_v": ..., "vce_v": ..., "ic_ma": ..., "warning": ...}
```

แรงดันเป็นโวลต์ กระแส `ic_ma` เป็นมิลลิแอมแปร์ และ `warning` เป็น `None`
เมื่อทรานซิสเตอร์อยู่ในย่านแอกทีฟ

## กฎการแบ่งย่านการทำงาน
- $I_B \leq 0$ → **คัตออฟ** (IC = IE = 0, VCE = VCC)
- $V_{CE} \leq 0.2\text{ V}$ → **แซทเทอเรชัน** (รายงานค่าจากสมการแอกทีฟพร้อมคำเตือน)
- ในกรณีอื่น → **แอกทีฟ**

ข้อความคำเตือนที่แสดง:
- คัตออฟ: `ทรานซิสเตอร์อยู่ในย่านคัตออฟ (IB = 0) — ไม่มีกระแสสะสม`
- แซทเทอเรชัน: `ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง`
- แอกทีฟ: ไม่มีคำเตือน

## ข้อจำกัดสำคัญ
- ไม่มี AC analysis, transient analysis, หกราฟ load line
- ไม่มีตัวแก้ไขวงจร
- ไม่มีฐานข้อมูล
- ไม่มี JavaScript
- ความต้านทานต้องกรอกเป็นโอห์ม (Ω) โดยตรง (ไม่ใช่ kΩ)
- ค่าทศนิยมต้องใช้จุด (.) ไม่ใช่ comma (,)

## วิธีติดตั้ง
```powershell
# 1. สร้าง virtual environment
py -m venv .venv

# 2. เข้าใช้งาน
.venv\Scripts\activate

# 3. ติดตั้ง dependencies
.venv\Scripts\python.exe -m pip install -r bjt_bias/requirements.txt

# 4. รันเทสต์อัตโนมัติ (46 ข้อ)
.venv\Scripts\python.exe -m pytest bjt_bias/tests test_flask.py -q
```

## วิธีรัน
```powershell
# 1. เข้าใช้งาน venv (ถ้ายังไม่ได้เปิด)
.venv\Scripts\activate

# 2. รันแอปพลิเคชัน
.venv\Scripts\python.exe -m flask --app bjt_bias.app run

# 3. เปิดเว็บบราวเซอร์ที่ http://127.0.0.1:5000
```

## วิธีทดสอบ
```powershell
# รันจาก root ของ repository
.venv\Scripts\python.exe -m pytest bjt_bias/tests test_flask.py -q
```

ผลการตรวจรับผ่านเบราว์เซอร์ (A1–A5) และการคำนวณอ้างอิงอิสระ:
ดู [docs/validation.md](../docs/validation.md)

### ตัวอย่างค่าตั้งต้น — Voltage Divider Bias
- เปิด `http://127.0.0.1:5000/?mode=divider`
- ใส่ค่า: `VCC=12, R1=47000, R2=10000, RC=4700, RE=1000, beta=100, VBE=0.7`
- ผลลัพธ์คาดหวัง:
  - $V_B \approx 1.999\text{ V}$, $V_E \approx 1.299\text{ V}$, $V_C \approx 5.954\text{ V}$
  - $I_B \approx 12.863\ \mu\text{A}$
  - $I_C \approx 1.286\text{ mA}$
  - $I_E \approx 1.299\text{ mA}$
  - $V_{CE} \approx 4.655\text{ V}$
  - ย่าน: **แอกทีฟ** (Active)
  - การตรวจสอบ: **ตรงกัน** (Agrees)

### ตัวอย่างค่าตั้งต้น — Fixed Bias
- เปิด `http://127.0.0.1:5000/?mode=fixed`
- ใส่ค่า: `VCC=12, RB=1000000, RC=2200, beta=100, VBE=0.7`
- ผลลัพธ์คาดหวัง: $I_C \approx 1.130\text{ mA}$, $V_{CE} \approx 9.514\text{ V}$,
  $V_E = 0\text{ V}$ (แอกทีฟ)

### ตัวอย่างค่าตั้งต้น — Emitter Bias
- เปิด `http://127.0.0.1:5000/?mode=emitter`
- ใส่ค่า: `VCC=12, RB=1000000, RC=2200, RE=1000, beta=100, VBE=0.7`
- ผลลัพธ์คาดหวัง: $I_C \approx 1.026\text{ mA}$, $V_{CE} \approx 8.705\text{ V}$
  (แอกทีฟ, การตรวจสอบตรงกัน)
- ถ้าเปลี่ยน `RE=2000` จะได้ $I_C \approx 0.940\text{ mA}$,
  $V_{CE} \approx 8.033\text{ V}$ (IC ลดลงตามที่คาด)

## ข้อจำกัด
- กรอกความต้านทานเป็นตัวเลขโอห์มโดยตรง (เช่น 47000 ไม่ใช่ 47)
- ใช้จุดทศนิยม (เช่น 0.7 ไม่ใช่ 0,7)
- แอปนี้สำหรับการเรียนการสอนแล็บอย่าง ENG29 2121 เท่านั้น ไม่รับการใช้งานเพื่อวัตถุประสงค์อื่นที่ซับซ้อนกว่า