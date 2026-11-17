# Computer Programming for Electrical Engineers — Labs

## Lab 03 — BJT DC Bias Web App (Flask)

เว็บแอป Flask สำหรับคำนวณจุดทำงานกระแสตรง (DC operating point) ของ BJT
แบบ common-emitter 3 โหมด:

1. **Voltage Divider Bias** — แบบแบ่งแรงดัน (ค่าเริ่มต้น)
2. **Fixed Bias** — ไบอัสฐานคงที่ผ่าน RB
3. **Emitter Bias** — ไบอัสผ่าน RB และมี RE ที่อิมิตเตอร์

ผู้ใช้เลือกโหมดจากแท็บบนหน้าเว็บ กรอกเฉพาะค่าที่วงจรนั้นต้องใช้ แล้วได้ผลลัพธ์
พร้อมหน่วย (V, mA, µA) มีการตรวจสอบอินพุตตามโหมด และมีคำเตือนเมื่อทรานซิสเตอร์
ไม่อยู่ในย่านแอกทีฟ

- โค้ดแอป: [`bjt_bias/`](bjt_bias/)
- วิธีติดตั้ง/รัน/ทดสอบ: [`bjt_bias/README.md`](bjt_bias/README.md)
- ผลตรวจรับ A1–A5 ผ่านเบราว์เซอร์: [`docs/validation.md`](docs/validation.md)
- ภาพหลักฐานจากเบราว์เซอร์: [`docs/evidence/`](docs/evidence/)
- คำนวณอ้างอิงอิสระ (Emitter Bias): [`docs/reference_emitter.py`](docs/reference_emitter.py)

รันเว็บ:

```powershell
py -3.7 -m flask --app bjt_bias.app run
```

เปิด http://127.0.0.1:5000 แล้วเลือกโหมดที่ต้องการ
(`/?mode=divider`, `/?mode=fixed`, `/?mode=emitter`)

ทดสอบ:

```powershell
py -3.7 -m pytest bjt_bias/tests test_flask.py -q
```

## DC Circuit Calculator (Lab 1)

ใช้สำหรับแลป compro ไฟฟ้า

โปรแกรมคำนวณวงจรไฟฟ้ากระแสตรงสำหรับแหล่งจ่ายแรงดันและตัวต้านทานหนึ่งตัว โดยคำนวณกระแสไฟฟ้าและกำลังไฟฟ้าจาก:

- กระแสไฟฟ้า: `I = V / R`
- กำลังไฟฟ้า: `P = V * I`

## วิธีใช้งาน

รันโปรแกรมด้วย Python:

```bash
python electrical.py
```

ป้อนแรงดันไฟฟ้าเป็นโวลต์ (V) และความต้านทานเป็นโอห์ม (ohm) โปรแกรมจะแสดงกระแสไฟฟ้าเป็นแอมแปร์ (A) และกำลังไฟฟ้าเป็นวัตต์ (W)

แรงดันต้องเป็นตัวเลขตั้งแต่ 0 ขึ้นไป และความต้านทานต้องมากกว่า 0 หากป้อนค่าที่ไม่ถูกต้อง โปรแกรมจะแจ้งข้อผิดพลาดแทนการคำนวณ

## ทดสอบ

รัน Unit Tests ด้วยคำสั่ง:

```bash
python -m unittest -v test_electrical
```
