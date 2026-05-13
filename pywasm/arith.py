import ctypes
import math
import struct


class I:
    def __init__(self, blen: int) -> None:
        self.bits_length = blen * 8
        self.byte_length = blen
        self.mask = (1 << self.bits_length) - 1
        self.mask_sign = 1 << (self.bits_length - 1)
        self.max = (1 << (self.bits_length - 1)) - 1
        self.min = -1 << (self.bits_length - 1)

    def from_bytearray(self, data: bytearray) -> int:
        assert len(data) == self.byte_length
        return int.from_bytes(data, 'little', signed=True)

    def into_bytearray(self, n: int) -> bytearray:
        return bytearray(n.to_bytes(self.byte_length, 'little', signed=True))

    def fit(self, n: int) -> int:
        n = n & self.mask
        n = n - ((n & self.mask_sign) << 1)
        return n

    def sat(self, n: int) -> int:
        return max(min(n, self.max), self.min)

    def add(self, a: int, b: int) -> int:
        return self.fit(a + b)

    def add_sat(self, a: int, b: int) -> int:
        return self.sat(a + b)

    def sub(self, a: int, b: int) -> int:
        return self.fit(a - b)

    def sub_sat(self, a: int, b: int) -> int:
        return self.sat(a - b)

    def mul(self, a: int, b: int) -> int:
        return self.fit(a * b)

    def div(self, a: int, b: int) -> int:
        assert a != self.min or b != -1
        # Python's default division of integers is return the floor (towards negative infinity) with no
        # ability to change that. You can read the BDFL's reason why.
        # See: https://python-history.blogspot.com/2010/08/why-pythons-integer-division-floors.html
        # But in webassembly, it requires do truncation towards zero.
        return a // b if a * b > 0 else (a + (-a % b)) // b

    def rem(self, a: int, b: int) -> int:
        return a % b if a * b > 0 else -(-a % b)

    def shl(self, a: int, b: int) -> int:
        return self.fit(a << (b & (self.bits_length - 1)))

    def shr(self, a: int, b: int) -> int:
        return self.fit(a >> (b & (self.bits_length - 1)))


class U:
    def __init__(self, blen: int) -> None:
        self.bits_length = blen * 8
        self.byte_length = blen
        self.mask = (1 << self.bits_length) - 1
        self.mask_sign = 1 << (self.bits_length - 1)
        self.max = self.mask
        self.min = 0

    def from_bytearray(self, data: bytearray) -> int:
        assert len(data) == self.byte_length
        return int.from_bytes(data, 'little', signed=False)

    def into_bytearray(self, n: int) -> bytearray:
        return bytearray(n.to_bytes(self.byte_length, 'little', signed=False))

    def fit(self, n: int) -> int:
        return n & self.mask

    def sat(self, n: int) -> int:
        return max(min(n, self.max), self.min)

    def add(self, a: int, b: int) -> int:
        return self.fit(a + b)

    def add_sat(self, a: int, b: int) -> int:
        return self.sat(a + b)

    def sub(self, a: int, b: int) -> int:
        return self.fit(a - b)

    def sub_sat(self, a: int, b: int) -> int:
        return self.sat(a - b)

    def mul(self, a: int, b: int) -> int:
        return self.fit(a * b)

    def div(self, a: int, b: int) -> int:
        return a // b

    def rem(self, a: int, b: int) -> int:
        return a % b

    def shl(self, a: int, b: int) -> int:
        return self.fit(a << (b & (self.bits_length - 1)))

    def shr(self, a: int, b: int) -> int:
        return self.fit(a >> (b & (self.bits_length - 1)))

    def rotl(self, a: int, b: int) -> int:
        b = b % self.bits_length
        return ((a << b) & self.mask) | (a >> (self.bits_length - b))

    def rotr(self, a: int, b: int) -> int:
        b = b % self.bits_length
        return (a >> b) | ((a << (self.bits_length - b)) & self.mask)

    def clz(self, a: int) -> int:
        b = 0
        for _ in range(self.bits_length):
            if a & self.mask_sign != 0:
                break
            b += 1
            a = a << 1
        return b

    def ctz(self, a: int) -> int:
        b = 0
        for _ in range(self.bits_length):
            if a & 1 != 0:
                break
            b += 1
            a = a >> 1
        return b

    def popcnt(self, a: int) -> int:
        b = 0
        for _ in range(self.bits_length):
            if a & 1 != 0:
                b += 1
            a = a >> 1
        return b


class F32:
    def __init__(self):
        pass

    def from_bytearray(self, data: bytearray) -> float:
        assert len(data) == 4
        return struct.unpack('<f', data)[0]

    def into_bytearray(self, n: float) -> bytearray:
        return bytearray(struct.pack('<f', ctypes.c_float(n).value))

    def fit(self, n: float) -> float:
        return ctypes.c_float(n).value

    def div(self, a: float, b: float) -> float:
        return self.fit(f64.div(a, b))

    def min(self, a: float, b: float) -> float:
        return self.fit(f64.min(a, b))

    def max(self, a: float, b: float) -> float:
        return self.fit(f64.max(a, b))


class F64:
    def __init__(self):
        pass

    def from_bytearray(self, data: bytearray) -> float:
        assert len(data) == 8
        return struct.unpack('<d', data)[0]

    def into_bytearray(self, n: float) -> bytearray:
        return bytearray(struct.pack('<d', n))

    def fit(self, n: float) -> float:
        return n

    def div(self, a: float, b: float) -> float:
        match b:
            case 0:
                s = +1 if math.copysign(1, a) == math.copysign(1, b) else -1
                c = math.copysign(math.inf, s)
                if a == 0 or math.isnan(a):
                    c = math.copysign(math.nan, s)
            case _:
                c = a / b
        return c

    def min(self, a: float, b: float) -> float:
        c = min(a, b)
        if math.isnan(a):
            c = a
        if math.isnan(b):
            c = b
        return c

    def max(self, a: float, b: float) -> float:
        c = max(a, b)
        if math.isnan(a):
            c = a
        if math.isnan(b):
            c = b
        return c


i8 = I(1)
u8 = U(1)
i16 = I(2)
u16 = U(2)
i32 = I(4)
i64 = I(8)
u32 = U(4)
u64 = U(8)
f32 = F32()
f64 = F64()
