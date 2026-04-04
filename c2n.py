from decimal import Decimal, getcontext

getcontext().prec = 28

DIGIT_MAP = {
    "零": 0,
    "壹": 1,
    "贰": 2,
    "叁": 3,
    "肆": 4,
    "伍": 5,
    "陆": 6,
    "柒": 7,
    "捌": 8,
    "玖": 9,
}
DIGIT_REV_MAP = {v: k for k, v in DIGIT_MAP.items() if k != "零"}


# ----------------------------------------------------------------------
# 小写转大写
# ----------------------------------------------------------------------
def number_to_chinese(amount: float) -> str:
    """
    数字转人民币大写金额
    """

    if amount == 0:
        return "零元整"

    integer_part = int(amount)
    decimal_part = amount - integer_part

    integer_str = _convert_integer_to_chinese(integer_part) if integer_part != 0 else ""
    decimal_str = _convert_decimal_to_chinese(decimal_part, integer_part == 0)

    if integer_str and decimal_str:
        return f"{integer_str}元{decimal_str}"
    elif integer_str:
        return f"{integer_str}元整"
    elif decimal_str:
        return decimal_str
    else:
        return "零元整"


def _convert_integer_to_chinese(n):
    if n == 0:
        return ""

    parts = []
    unit_big = ["", "万", "亿"]
    idx = 0
    while n > 0:
        section = n % 10000
        if section != 0:
            section_str = _convert_section(section)
            parts.append(section_str + unit_big[idx])
        else:
            parts.append(None)
        n //= 10000
        idx += 1

    parts.reverse()
    result_parts = []
    last_was_none = False
    for p in parts:
        if p is None:
            last_was_none = True
        else:
            if last_was_none and result_parts:
                result_parts.append("零")
            result_parts.append(p)
            last_was_none = False
    return "".join(result_parts)


def _convert_section(n):
    """转换 1~9999 的数字（不包含“零”前导）"""
    if n == 0:
        return ""

    # 将数字按位分解（千、百、十、个）
    units = ["仟", "佰", "拾", ""]
    # 获取每位数字（高位补零）
    digits = [int(d) for d in f"{n:04d}"]
    # 找到第一个非零位的位置
    start = 0
    while start < 4 and digits[start] == 0:
        start += 1

    result = []
    last_zero = False
    for i in range(start, 4):
        d = digits[i]
        if d == 0:
            # 中间零（且后面还有非零数字）才添加“零”
            if not last_zero and i < 3 and any(digits[j] != 0 for j in range(i + 1, 4)):
                result.append("零")
                last_zero = True
        else:
            digit_char = DIGIT_REV_MAP[d]
            unit_char = units[i]
            # 处理“拾”开头的特殊情况（如 10 应写“拾”，不是“壹拾”）
            if d == 1 and unit_char == "拾" and i == start:
                result.append("拾")
            else:
                result.append(digit_char + unit_char)
            last_zero = False
    return "".join(result)


def _convert_decimal_to_chinese(dec, integer_is_zero):
    fen = int(dec * 100 + 0.0001)  # 避免浮点误差导致的错误
    jiao = fen // 10
    fen = fen % 10

    parts = []
    if jiao == 0 and fen == 0:
        return ""

    if jiao != 0:
        parts.append(DIGIT_REV_MAP[jiao] + "角")
    if fen != 0:
        # 如果整数部分为0且角为0，前面不加“零”
        if jiao == 0 and not integer_is_zero:
            parts.append("零")
        parts.append(DIGIT_REV_MAP[fen] + "分")

    # 如果只有分且整数部分为0，直接返回“X分”，不加“零”
    if jiao == 0 and integer_is_zero:
        return "".join(parts)  # 此时 parts 为 ["X分"]

    return "".join(parts)


# ----------------------------------------------------------------------
# 大写转小写
# ----------------------------------------------------------------------
def chinese_to_number(amount_str: str) -> float:
    """
    人民币大写金额转阿拉伯数字金额
    """
    s = amount_str.strip().replace("圆", "元")
    if s.endswith("整"):
        s = s[:-1]

    if "元" in s:
        idx = s.index("元")
        int_part_str = s[:idx]
        dec_part_str = s[idx + 1 :]
    else:
        int_part_str = ""
        dec_part_str = s

    integer_val = _parse_integer_part(int_part_str) if int_part_str else 0
    decimal_val = _parse_decimal_part(dec_part_str) if dec_part_str else 0
    return float(integer_val) + float(decimal_val)


def _parse_integer_part(s):
    if not s:
        return 0
    if "亿" in s:
        idx = s.find("亿")
        left = s[:idx]
        right = s[idx + 1 :]
        return _parse_integer_part(left) * 100000000 + _parse_integer_part(right)
    if "万" in s:
        idx = s.find("万")
        left = s[:idx]
        right = s[idx + 1 :]
        return _parse_integer_part(left) * 10000 + _parse_integer_part(right)
    return _parse_small_number(s)


def _parse_small_number(s):
    if not s:
        return 0
    result = 0
    current = None
    unit_map = {"拾": 10, "佰": 100, "仟": 1000}
    for ch in s:
        if ch in DIGIT_MAP:
            current = DIGIT_MAP[ch]
        elif ch in unit_map:
            unit = unit_map[ch]
            if current is None:
                current = 1
            result += current * unit
            current = None
        elif ch == "零":
            continue
    if current is not None:
        result += current
    return result


def _parse_decimal_part(s):
    if not s:
        return Decimal(0)
    result = Decimal(0)
    current = None
    for ch in s:
        if ch in DIGIT_MAP:
            current = DIGIT_MAP[ch]
        elif ch == "角":
            if current is None:
                current = 1
            result += Decimal(current) * Decimal("0.1")
            current = None
        elif ch == "分":
            if current is None:
                current = 1
            result += Decimal(current) * Decimal("0.01")
            current = None
        elif ch == "零":
            continue
    return result


# ----------------------------------------------------------------------
# 测试
# ----------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        "陆拾圆叁角整",
        "壹拾陆圆叁角捌分",
        "壹拾陆圆柒角陆分",
        "壹佰圆整",
        "伍万贰仟零壹拾叁元壹角肆分",
        "壹仟零壹元整",
        "壹拾万元整",
        "叁分",
        "零元伍角",
        "零元整",
    ]

    print("大写 -> 数字")
    for case in test_cases:
        num = chinese_to_number(case)
        print(f"{case:30s} -> {num}")

    print("\n数字 -> 大写")
    numbers = [
        Decimal("60.30"),
        Decimal("16.38"),
        Decimal("16.76"),
        Decimal("100.00"),
        Decimal("52013.14"),
        Decimal("10001"),
        Decimal("100000"),
        Decimal("0.03"),
        Decimal("0.50"),
        Decimal("0"),
    ]
    for n in numbers:
        ch = number_to_chinese(float(n))
        print(f"{str(n):<15} -> {ch}")

    print("\n双向验证（随机金额）")
    test_amounts = [
        Decimal("0"),
        Decimal("0.01"),
        Decimal("0.1"),
        Decimal("1.23"),
        Decimal("10.00"),
        Decimal("100.01"),
        Decimal("1001.02"),
        Decimal("10000"),
        Decimal("100000.99"),
        Decimal("5201314.15"),
    ]
    for amt in test_amounts:
        ch_str = number_to_chinese(float(amt))
        back_num = chinese_to_number(ch_str)
        assert abs(amt - Decimal(str(back_num))) < Decimal("0.0001"), (
            f"Error: {amt} -> {ch_str} -> {back_num}"
        )
        print(f"{str(amt):12} -> {ch_str:30s} -> {back_num}")
