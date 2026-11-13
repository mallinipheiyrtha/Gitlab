# BJT Common-Emitter DC Bias Calculator

## ภาพรวมและขอบเขต
แอปพลิเคーションเว็บหน้าเดียว (Flask) สำหรับคำนวณจุดทำงานกระแสตรง (DC operating point)
ของวงจรไบแอสแบบทั่วไป (common-emitter) แบบแบ่งแรงดัน (voltage-divider bias)
ผู้ใช้กรอกค่าองค์ประกอบวงจร แล้วได้ผลลัพธ์พร้อมหน่วย มีการตรวจสอบข้อมูล
มีคำเตือนเมื่อทรานซิสเตอร์ไม่อยู่ในย่านแอกทีฟ และมีการคำนวณตรวจทานอีกวิธีหนึ่ง

**ขอบเขต (ตามที่กำหนดไว้):**
- **ทำ:** คำนวณ DC operating point เฉยๆ ไม่มี AC, transient, load line, กราฟ, ตัวแก้ไขวงจร, FET, เอาท์พุตกำลังไฟฟ้า
- **ไม่ทำ:** AC analysis, transient analysis, circuit editor, FET, database, JavaScript

## หน่วย
- แรงดัน: โวลต์ (V) — ใช้จุดทศนิยม (.)
- ความต้านทาน: โอห์ม (Ω)
- กระแส: มิลลิแอมแปร์ (mA) — แสดงผล 3 ตำแหน่งทางทศนิยม
- VCE: โวลต์ (V) — แสดงผล 3 ตำแหน่งทางทศนิยม

## สูตรที่ใช้
1. **แบบจำลอง Thevenin (หลัก):** 
   - $V_{BB} = V_{CC} \cdot \frac{R_2}{R_1 + R_2}$
   - $R_B = R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}$
   - $I_B = \frac{V_{BB} - V_{BE}}{R_B + (1 + \beta)R_E}$
   - $I_C = \beta I_B$, $I_E = (1 + \beta)I_B$
   - $V_{CE} = V_{CC} - I_C R_C - I_E R_E$

2. **การคำนวณตรวจทานอิสระ (bisection KCL):**
   - แก้สมการ $f(V_B) = \frac{V_{CC} - V_B}{R_1} - \frac{V_B}{R_2} - \frac{\max(0, V_B - V_{BE})}{(1 + \beta)R_E} = 0$
   - ใช้วิธีแบ่งครึ่งช่วง (bisection) 200 รอบ
   - นำ $V_B$ ที่ได้มาใช้คำนวณ $I_B, I_C, I_E, V_{CE}$ เฉพาะเจาะจง
   - เปรียบเทียบผลลัพธ์กับแบบจำลอง Thevenin โดยมี tolerance $10^{-6}$ (สัมพัทธ์)

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

# 4. รันเทสต์อัตโนมัติ
.venv\Scripts\python.exe -m pytest bjt_bias/tests -v
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
.venv\Scripts\python.exe -m pytest bjt_bias/tests -v
```

### ตัวอย่างค่าตั้งต้น
- ใส่ค่า: `VCC=12, R1=47000, R2=10000, RC=4700, RE=1000, beta=100, VBE=0.7`
- ผลลัพธ์คาดหวัง:
  - $V_B \approx 1.999\text{ V}$, $V_E \approx 1.299\text{ V}$, $V_C \approx 5.954\text{ V}$
  - $I_B \approx 12.863\ \mu\text{A}$
  - $I_C \approx 1.286\text{ mA}$
  - $I_E \approx 1.299\text{ mA}$
  - $V_{CE} \approx 4.655\text{ V}$
  - ย่าน: **แอกทีฟ** (Active)
  - การตรวจสอบ: **ตรงกัน** (Agrees)

## ข้อจำกัด
- กรอกความต้านทานเป็นตัวเลขโอห์มโดยตรง (เช่น 47000 ไม่ใช่ 47)
- ใช้จุดทศนิยม (เช่น 0.7 ไม่ใช่ 0,7)
- แอปนี้สำหรับการเรียนการสอนแล็บอย่าง ENG29 2121 เท่านั้น ไม่รับการใช้งานเพื่อวัตถุประสงค์อื่นที่ซับซ้อนกว่า