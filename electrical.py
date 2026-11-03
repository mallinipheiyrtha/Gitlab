import math


def analyze_dc(voltage_v, resistance_ohm):
    voltage_v = float(voltage_v)
    resistance_ohm = float(resistance_ohm)

    if not math.isfinite(voltage_v) or voltage_v < 0:
        raise ValueError("แรงดันต้องเป็นตัวเลขตั้งแต่ 0 ขึ้นไป")
    if not math.isfinite(resistance_ohm) or resistance_ohm <= 0:
        raise ValueError("ความต้านทานต้องเป็นตัวเลขมากกว่า 0")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


def main():
    try:
        voltage_v = input("แรงดันไฟฟ้า (V): ")
        resistance_ohm = input("ความต้านทาน (ohm): ")
        result = analyze_dc(voltage_v, resistance_ohm)
    except ValueError as error:
        print(f"ข้อมูลไม่ถูกต้อง: {error}")
        return 1

    print(f"กระแสไฟฟ้า: {result['current_a']:.4f} A")
    print(f"กำลังไฟฟ้า: {result['power_w']:.4f} W")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())