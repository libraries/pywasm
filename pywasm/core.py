import ctypes
import io
import math
import pywasm.arith
import pywasm.leb128
import pywasm.log
import pywasm.opcode
import struct
import typing


class ValType:
    # Value types are encoded by a single byte.

    def __init__(self, data: int) -> None:
        assert data in [0x7f, 0x7e, 0x7d, 0x7c, 0x7b, 0x70, 0x6f]
        self.data = data

    def __eq__(self, value: object) -> bool:
        assert isinstance(value, self.__class__)
        return self.data == value.data

    def __hash__(self) -> int:
        return hash(self.data)

    def __repr__(self) -> str:
        return {
            0x7f: 'i32',
            0x7e: 'i64',
            0x7d: 'f32',
            0x7c: 'f64',
            0x7b: 'v128',
            0x70: 'ref.func',
            0x6f: 'ref.extern',
        }[self.data]

    @classmethod
    def i32(cls) -> typing.Self:
        return cls(0x7f)

    @classmethod
    def i64(cls) -> typing.Self:
        return cls(0x7e)

    @classmethod
    def f32(cls) -> typing.Self:
        return cls(0x7d)

    @classmethod
    def f64(cls) -> typing.Self:
        return cls(0x7c)

    @classmethod
    def v128(cls) -> typing.Self:
        return cls(0x7b)

    @classmethod
    def ref_func(cls) -> typing.Self:
        return cls(0x70)

    @classmethod
    def ref_extern(cls) -> typing.Self:
        return cls(0x6f)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(ord(r.read(1)))


class ValInst:
    # Values are represented by themselves.

    blen = 16

    def __init__(self, type: ValType, data: bytearray) -> None:
        assert len(data) == self.blen
        self.type = type
        self.data = data

    def __eq__(self, value: object) -> bool:
        assert isinstance(value, self.__class__)
        return self.type == value.type and self.data == value.data

    def __repr__(self) -> str:
        match self.type.data:
            case 0x7f:
                return f'{self.type} {self.into_i32()}'
            case 0x7e:
                return f'{self.type} {self.into_i64()}'
            case 0x7d:
                return f'{self.type} {self.into_f32()}'
            case 0x7c:
                return f'{self.type} {self.into_f64()}'
            case 0x7b:
                return f'{self.type} {self.into_v128().hex()}'
            case 0x70:
                body = repr(self.into_ref()) if self.data[4] != 0x00 else 'null'
                return f'{self.type} {body}'
            case 0x6f:
                body = repr(self.into_ref()) if self.data[4] != 0x00 else 'null'
                return f'{self.type} {body}'
            case _:
                raise Exception('unreachable')

    @classmethod
    def from_i32(cls, n: int) -> typing.Self:
        return cls(ValType.i32(), pywasm.arith.i32.into_bytearray(n) + bytearray(cls.blen - 4))

    @classmethod
    def from_i64(cls, n: int) -> typing.Self:
        return cls(ValType.i64(), pywasm.arith.i64.into_bytearray(n) + bytearray(cls.blen - 8))

    @classmethod
    def from_u32(cls, n: int) -> typing.Self:
        return cls(ValType.i32(), pywasm.arith.u32.into_bytearray(n) + bytearray(cls.blen - 4))

    @classmethod
    def from_u64(cls, n: int) -> typing.Self:
        return cls(ValType.i64(), pywasm.arith.u64.into_bytearray(n) + bytearray(cls.blen - 8))

    @classmethod
    def from_f32(cls, n: float) -> typing.Self:
        n = ctypes.c_float(n).value
        return cls(ValType.f32(), bytearray(struct.pack('<f', n)) + bytearray(cls.blen - 4))

    @classmethod
    def from_f32_u32(cls, n: int) -> typing.Self:
        o = cls.from_u32(n)
        o.type = ValType.f32()
        return o

    @classmethod
    def from_f64(cls, n: float) -> typing.Self:
        return cls(ValType.f64(), bytearray(struct.pack('<d', n)) + bytearray(cls.blen - 8))

    @classmethod
    def from_f64_u64(cls, n: int) -> typing.Self:
        o = cls.from_u64(n)
        o.type = ValType.f64()
        return o

    @classmethod
    def from_v128(cls, n: bytearray) -> typing.Self:
        assert len(n) == 16
        return cls(ValType.v128(), n + bytearray(cls.blen - 16))

    @classmethod
    def from_v128_i8(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 16
        data = bytearray().join([pywasm.arith.i8.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_u8(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 16
        data = bytearray().join([pywasm.arith.u8.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_i16(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 8
        data = bytearray().join([pywasm.arith.i16.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_u16(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 8
        data = bytearray().join([pywasm.arith.u16.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_i32(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 4
        data = bytearray().join([pywasm.arith.i32.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_u32(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 4
        data = bytearray().join([pywasm.arith.u32.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_i64(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 2
        data = bytearray().join([pywasm.arith.i64.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_u64(cls, n: typing.List[int]) -> typing.Self:
        assert len(n) == 2
        data = bytearray().join([pywasm.arith.u64.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_f32(cls, n: typing.List[float]) -> typing.Self:
        assert len(n) == 4
        data = bytearray().join([pywasm.arith.f32.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_v128_f64(cls, n: typing.List[float]) -> typing.Self:
        assert len(n) == 2
        data = bytearray().join([pywasm.arith.f64.into_bytearray(e) for e in n]) + bytearray(cls.blen - 16)
        return cls(ValType.v128(), data)

    @classmethod
    def from_ref(cls, type: ValType, n: int) -> typing.Self:
        return cls(type, bytearray(struct.pack('<i', n)) + bytearray([0x01]) + bytearray(cls.blen - 5))

    @classmethod
    def from_all(cls, type: ValType, n: typing.Any) -> typing.Self:
        match type.data:
            case 0x7f:
                return cls.from_i32(n)
            case 0x7e:
                return cls.from_i64(n)
            case 0x7d:
                return cls.from_f32(n)
            case 0x7c:
                return cls.from_f64(n)
            case 0x7b:
                return cls.from_v128(n)
            case 0x70:
                return cls.from_ref(type, n)
            case 0x6f:
                return cls.from_ref(type, n)
            case _:
                raise Exception('unreachable')

    def into_i32(self) -> int:
        return struct.unpack('<i', self.data[0:4])[0]

    def into_i64(self) -> int:
        return struct.unpack('<q', self.data[0:8])[0]

    def into_u32(self) -> int:
        return struct.unpack('<I', self.data[0:4])[0]

    def into_u64(self) -> int:
        return struct.unpack('<Q', self.data[0:8])[0]

    def into_f32(self) -> float:
        return struct.unpack('<f', self.data[0:4])[0]

    def into_f64(self) -> float:
        return struct.unpack('<d', self.data[0:8])[0]

    def into_v128(self) -> bytearray:
        return self.data[:16].copy()

    def into_v128_i8(self) -> typing.List[int]:
        return [pywasm.arith.i8.fit(e) for e in self.data]

    def into_v128_u8(self) -> typing.List[int]:
        return [pywasm.arith.u8.fit(e) for e in self.data]

    def into_v128_i16(self) -> typing.List[int]:
        return [pywasm.arith.i16.from_bytearray(bytearray(self.data[i:i + 2])) for i in range(0, 16, 2)]

    def into_v128_u16(self) -> typing.List[int]:
        return [pywasm.arith.u16.from_bytearray(bytearray(self.data[i:i + 2])) for i in range(0, 16, 2)]

    def into_v128_i32(self) -> typing.List[int]:
        return [pywasm.arith.i32.from_bytearray(bytearray(self.data[i:i + 4])) for i in range(0, 16, 4)]

    def into_v128_u32(self) -> typing.List[int]:
        return [pywasm.arith.u32.from_bytearray(bytearray(self.data[i:i + 4])) for i in range(0, 16, 4)]

    def into_v128_i64(self) -> typing.List[int]:
        return [pywasm.arith.i64.from_bytearray(bytearray(self.data[i:i + 8])) for i in range(0, 16, 8)]

    def into_v128_u64(self) -> typing.List[int]:
        return [pywasm.arith.u64.from_bytearray(bytearray(self.data[i:i + 8])) for i in range(0, 16, 8)]

    def into_v128_f32(self) -> typing.List[float]:
        return [pywasm.arith.f32.from_bytearray(bytearray(self.data[i:i + 4])) for i in range(0, 16, 4)]

    def into_v128_f64(self) -> typing.List[float]:
        return [pywasm.arith.f64.from_bytearray(bytearray(self.data[i:i + 8])) for i in range(0, 16, 8)]

    def into_ref(self) -> int:
        assert self.data[4] == 0x01
        return self.into_i32()

    def into_all(self) -> typing.Any:
        match self.type.data:
            case 0x7f:
                return self.into_i32()
            case 0x7e:
                return self.into_i64()
            case 0x7d:
                return self.into_f32()
            case 0x7c:
                return self.into_f64()
            case 0x7b:
                return self.into_v128()
            case 0x70:
                return self.into_ref()
            case 0x6f:
                return self.into_ref()
            case _:
                raise Exception('unreachable')

    @classmethod
    def zero(cls, type: ValType) -> typing.Self:
        return cls(type, bytearray(cls.blen))


class Bype:
    # Block types are encoded in special compressed form, by either the byte 0x40 indicating the empty type, as a
    # single value type, or as a type index encoded as a positive signed integer.

    def __init__(self, kind: int, data: int) -> None:
        assert kind in [0x00, 0x01, 0x02]
        self.kind = kind
        self.data = data

    def __eq__(self, value: object) -> bool:
        assert isinstance(value, self.__class__)
        return self.kind == value.kind and self.data == value.data

    def __repr__(self) -> str:
        if self.kind == 0x00:
            return 'empty'
        if self.kind == 0x01:
            return repr(ValType(self.data))
        return repr(self.data)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        n = ord(r.read(1))
        if n == 0x40:
            return cls(0x00, 0x40)
        if n in [0x7f, 0x7e, 0x7d, 0x7c, 0x7b, 0x70, 0x6f]:
            return cls(0x01, n)
        r.seek(-1, 1)
        return cls(0x02, pywasm.leb128.i.decode_reader(r)[0])


class Inst:
    # Instructions are encoded by opcodes. Each opcode is represented by a single byte, and is followed by the
    # instruction's immediate arguments, where present. The only exception are structured control instructions, which
    # consist of several opcodes bracketing their nested instruction sequences.

    def __init__(self, opcode: int, args: typing.List[typing.Any]) -> None:
        self.opcode = opcode
        self.args = args

    def __repr__(self) -> str:
        return self.into_single()

    def into_single(self) -> str:
        seps = [pywasm.opcode.name[self.opcode]]
        if self.opcode in [pywasm.opcode.block, pywasm.opcode.loop, pywasm.opcode.if_then]:
            seps.append(repr(self.args[0]))
            return ' '.join(seps)
        for e in self.args:
            seps.append(repr(e))
        return ' '.join(seps)

    def into_disasm(self, indent: int) -> None:
        prefix = ' ' * indent
        pywasm.log.debugln(f'{prefix}{self.into_single()}')
        if self.opcode in [pywasm.opcode.block, pywasm.opcode.loop, pywasm.opcode.if_then]:
            for e in self.args[1]:
                e.into_disasm(indent + 4)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        b = ord(r.read(1))
        if b >= 0xfc:
            e = pywasm.leb128.u.encode(pywasm.leb128.u.decode_reader(r)[0])
            b = int.from_bytes(bytearray([b]) + e)
        assert b in pywasm.opcode.name, hex(b)
        o = cls(b, [])
        match o.opcode:
            case pywasm.opcode.block:
                o.args.append(Bype.from_reader(r))
                o.args.append([])
                for _ in range(1 << 32):
                    i = cls.from_reader(r)
                    if i.opcode == pywasm.opcode.end:
                        break
                    o.args[1].append(i)
            case pywasm.opcode.loop:
                o.args.append(Bype.from_reader(r))
                o.args.append([])
                for _ in range(1 << 32):
                    i = cls.from_reader(r)
                    if i.opcode == pywasm.opcode.end:
                        break
                    o.args[1].append(i)
            case pywasm.opcode.if_then:
                o.args.append(Bype.from_reader(r))
                o.args.append([])
                o.args.append([])
                argidx = 1
                for _ in range(1 << 32):
                    i = cls.from_reader(r)
                    if i.opcode == pywasm.opcode.end:
                        break
                    if i.opcode == pywasm.opcode.else_fi:
                        argidx = 2
                        continue
                    o.args[argidx].append(i)
            case pywasm.opcode.br:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.br_if:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.br_table:
                o.args.append([pywasm.leb128.u.decode_reader(r)[0] for _ in range(pywasm.leb128.u.decode_reader(r)[0])])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.call:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.call_indirect:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.select_type:
                o.args.append([pywasm.leb128.u.decode_reader(r)[0] for _ in range(pywasm.leb128.u.decode_reader(r)[0])])
            case pywasm.opcode.local_get:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.local_set:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.local_tee:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.global_get:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.global_set:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_get:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_set:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.i32_load:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                # Alignment must not be larger than natural.
                assert o.args[0] < 3
            case pywasm.opcode.i64_load:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.f32_load:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.f64_load:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.i32_load8_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i32_load8_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i32_load16_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i32_load16_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64_load8_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i64_load8_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i64_load16_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64_load16_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64_load32_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.i64_load32_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.i32_store:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.i64_store:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.f32_store:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.f64_store:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.i32_store8:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i32_store16:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64_store8:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.i64_store16:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64_store32:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.memory_size:
                o.args.append(ord(r.read(1)))
            case pywasm.opcode.memory_grow:
                o.args.append(ord(r.read(1)))
            case pywasm.opcode.i32_const:
                o.args.append(pywasm.leb128.i.decode_reader(r)[0])
            case pywasm.opcode.i64_const:
                o.args.append(pywasm.leb128.i.decode_reader(r)[0])
            case pywasm.opcode.f32_const:
                # Python misinterpret 0x7fa00000 as 0x7fe00000, when encapsulate as built-in float type.
                # See: https://stackoverflow.com/questions/47961537/webassembly-f32-const-nan0x200000-means-0x7fa00000-or-0x7fe00000
                o.args.append(struct.unpack('<i', r.read(4))[0])
            case pywasm.opcode.f64_const:
                o.args.append(struct.unpack('<q', r.read(8))[0])
            case pywasm.opcode.ref_null:
                o.args.append(ord(r.read(1)))
            case pywasm.opcode.ref_func:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.memory_init:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert ord(r.read(1)) == 0x00
            case pywasm.opcode.data_drop:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.memory_copy:
                assert ord(r.read(1)) == 0x00
                assert ord(r.read(1)) == 0x00
            case pywasm.opcode.memory_fill:
                assert ord(r.read(1)) == 0x00
            case pywasm.opcode.table_init:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.elem_drop:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_copy:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_grow:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_size:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.table_fill:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.v128_load:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 5
            case pywasm.opcode.v128_load8x8_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load8x8_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load16x4_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load16x4_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load32x2_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load32x2_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_load8_splat:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 1
            case pywasm.opcode.v128_load16_splat:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.v128_load32_splat:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 3
            case pywasm.opcode.v128_load64_splat:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.v128_store:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 5
            case pywasm.opcode.v128_const:
                o.args.append(bytearray(r.read(16)))
            case pywasm.opcode.i8x16_shuffle:
                for _ in range(16):
                    o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                for e in o.args:
                    assert e < 32
            case pywasm.opcode.i8x16_extract_lane_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 16
            case pywasm.opcode.i8x16_extract_lane_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 16
            case pywasm.opcode.i8x16_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 16
            case pywasm.opcode.i16x8_extract_lane_s:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 8
            case pywasm.opcode.i16x8_extract_lane_u:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 8
            case pywasm.opcode.i16x8_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 8
            case pywasm.opcode.i32x4_extract_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.i32x4_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.i64x2_extract_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.i64x2_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.f32x4_extract_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.f32x4_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 4
            case pywasm.opcode.f64x2_extract_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.f64x2_replace_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[0] < 2
            case pywasm.opcode.v128_load8_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 16
            case pywasm.opcode.v128_load16_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 8
            case pywasm.opcode.v128_load32_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 4
            case pywasm.opcode.v128_load64_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 2
            case pywasm.opcode.v128_store8_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 16
            case pywasm.opcode.v128_store16_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 8
            case pywasm.opcode.v128_store32_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 4
            case pywasm.opcode.v128_store64_lane:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                assert o.args[2] < 2
            case pywasm.opcode.v128_load32_zero:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
            case pywasm.opcode.v128_load64_zero:
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
                o.args.append(pywasm.leb128.u.decode_reader(r)[0])
        return o


class Expr:
    # Function bodies, initialization values for globals, and offsets of element or data segments are given as
    # expressions, which are sequences of instructions terminated by an end marker.

    def __init__(self, data: typing.List[Inst]) -> None:
        self.data = data

    def __repr__(self) -> str:
        return repr(self.data)

    def into_disasm(self, indent: int) -> None:
        for e in self.data:
            e.into_disasm(indent)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        s = []
        for _ in range(1 << 32):
            i = Inst.from_reader(r)
            if i.opcode == pywasm.opcode.end:
                break
            s.append(i)
        return cls(s)


class LocalsDesc:
    # The locals declare a vector of mutable local variables and their types. These variables are referenced through
    # local indices in the function’s body. The index of the first local is the smallest index not referencing a
    # parameter.

    def __init__(self, n: int, type: ValType) -> None:
        self.n = n
        self.type = type

    def __repr__(self) -> str:
        return f'{self.n}x{self.type}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(pywasm.leb128.u.decode_reader(r)[0], ValType.from_reader(r))


class LocalsInst:
    # LocalsInst holds the values of function's locals (including arguments).

    def __init__(self, data: typing.List[ValInst]) -> None:
        self.data = data

    def __repr__(self) -> str:
        return repr(self.data)


class FuncType:
    # Function types are encoded by the byte 0x60 followed by the respective vectors of parameter and result types.
    # Function types classify the signature of functions, mapping a vector of parameters to a vector of results. They
    # are also used to classify the inputs and outputs of instructions.

    def __init__(self, args: typing.List[ValType], rets: typing.List[ValType]) -> None:
        self.args = args
        self.rets = rets

    def __eq__(self, value: object) -> bool:
        assert isinstance(value, self.__class__)
        return self.args == value.args and self.rets == value.rets

    def __repr__(self) -> str:
        return f'{self.args} -> {self.rets}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        assert ord(r.read(1)) == 0x60
        n = pywasm.leb128.u.decode_reader(r)[0]
        args = [ValType.from_reader(r) for _ in range(n)]
        n = pywasm.leb128.u.decode_reader(r)[0]
        rets = [ValType.from_reader(r) for _ in range(n)]
        return cls(args, rets)


class FuncDesc:
    # The funcs component of a module defines a vector of functions with the following structure.
    # The type of a function declares its signature by reference to a type defined in the module. The parameters of the
    # function are referenced through 0-based local indices in the function's body; they are mutable.
    # The locals declare a vector of mutable local variables and their types. These variables are referenced through
    # local indices in the function's body. The index of the first local is the smallest index not referencing a
    # parameter.
    # The body is an instruction sequence that upon termination must produce a stack matching the function type's
    # result type.
    # Functions are referenced through function indices, starting with the smallest index not referencing a function
    # import.

    def __init__(self, type: int, locals: typing.List[LocalsDesc], expr: Expr) -> None:
        self.type = type
        self.locals = locals
        self.expr = expr

    def __repr__(self) -> str:
        return f'{self.type} {self.locals}'

    @classmethod
    def from_reader_type(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(pywasm.leb128.u.decode_reader(r)[0], [], Expr([]))

    @classmethod
    def from_reader_code(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(0, [LocalsDesc.from_reader(r) for _ in range(pywasm.leb128.u.decode_reader(r)[0])], Expr.from_reader(r))


class Limits:
    # Limits are encoded with a preceding flag indicating whether a maximum is present.

    def __init__(self, n: int, m: int) -> None:
        self.n = n
        self.m = m

    def __repr__(self) -> str:
        m = 'inf' if self.m == 0 else repr(self.m)
        return f'[{self.n}, {m}]'

    def suit(self, value: typing.Self) -> bool:
        c1 = self.n >= value.n
        c2 = value.m == 0
        c3 = self.m != 0 and value.m != 0 and self.m <= value.m
        return c1 and (c2 or c3)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        flag = ord(r.read(1))
        return cls(pywasm.leb128.u.decode_reader(r)[0],  pywasm.leb128.u.decode_reader(r)[0] if flag else 0x00)


class MemType:
    # Memory types classify linear memories and their size range. The limits constrain the minimum and optionally the
    # maximum size of a memory. The limits are given in units of page size -- the constant 65536 – abbreviated 64k.

    def __init__(self, limits: Limits) -> None:
        self.limits = limits

    def __repr__(self) -> str:
        return repr(self.limits)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(Limits.from_reader(r))


class MemInst:
    # A memory instance is the runtime representation of a linear memory. It holds a vector of bytes and an optional
    # maximum size, if one was specified at the definition site of the memory.
    #
    # The length of the vector always is a multiple of the WebAssembly page size, which is defined to be the constant
    # 65536 – abbreviated 64Ki. Like in a memory type, the maximum size in a memory instance is given in units of this
    # page size.
    #
    # The bytes can be mutated through memory instructions, the execution of a data segment, or by external means
    # provided by the embedder.
    #
    # It is an invariant of the semantics that the length of the byte vector, divided by page size, never exceeds the
    # maximum size, if present.

    def __init__(self, type: MemType) -> None:
        self.type = type
        self.data = bytearray()
        self.size = 0
        self.grow(type.limits.n)

    def get_i32(self, addr: int) -> int:
        return struct.unpack('<i', self.data[addr:addr+4])[0]

    def get_i64(self, addr: int) -> int:
        return struct.unpack('<q', self.data[addr:addr+8])[0]

    def get_u8(self, addr: int) -> int:
        return self.data[addr]

    def get_u16(self, addr: int) -> int:
        return struct.unpack('<H', self.data[addr:addr+2])[0]

    def get_u32(self, addr: int) -> int:
        return struct.unpack('<I', self.data[addr:addr+4])[0]

    def get_u64(self, addr: int) -> int:
        return struct.unpack('<Q', self.data[addr:addr+8])[0]

    def get(self, addr: int, size: int) -> bytearray:
        return self.data[addr:addr+size].copy()

    def grow(self, n: int) -> None:
        if self.type.limits.m:
            assert self.size + n <= self.type.limits.m
        assert self.size + n <= 65536
        self.data.extend(bytearray(n * 64 * 1024))
        self.size += n

    def put_i32(self, addr: int, data: int) -> None:
        self.data[addr:addr+4] = struct.pack('<i', data)

    def put_i64(self, addr: int, data: int) -> None:
        self.data[addr:addr+8] = struct.pack('<q', data)

    def put_u8(self, addr: int, data: int) -> None:
        self.data[addr] = data

    def put_u16(self, addr: int, data: int) -> None:
        self.data[addr:addr+2] = struct.pack('<H', data)

    def put_u32(self, addr: int, data: int) -> None:
        self.data[addr:addr+4] = struct.pack('<I', data)

    def put_u64(self, addr: int, data: int) -> None:
        self.data[addr:addr+8] = struct.pack('<Q', data)

    def put(self, addr: int, data: bytearray) -> None:
        assert isinstance(data, bytearray)
        self.data[addr:addr+len(data)] = data.copy()

    def suit(self, l: Limits) -> bool:
        return Limits(self.size, self.type.limits.m).suit(l)


class TableType:
    # Table types classify tables over elements of element types within a size range. Like memories, tables are
    # constrained by limits for their minimum and optionally maximum size. The limits are given in numbers of entries.
    # The element type funcref is the infinite union of all function types. A table of that type thus contains
    # references to functions of heterogeneous type.

    def __init__(self, type: ValType, limits: Limits) -> None:
        assert type in [ValType.ref_func(), ValType.ref_extern()]
        self.type = type
        self.limits = limits

    def __repr__(self) -> str:
        return f'{self.type} {self.limits}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(ValType.from_reader(r), Limits.from_reader(r))


class TableInst:
    # A table instance is the runtime representation of a table. It holds a vector of function elements and an optional
    # maximum size, if one was specified in the table type at the table’s definition site.
    #
    # Each function element is either empty, representing an uninitialized table entry, or a function address. Function
    # elements can be mutated through the execution of an element segment or by external means provided by the embedder.
    #
    # It is an invariant of the semantics that the length of the element vector never exceeds the maximum size, if
    # present.

    def __init__(self, type: TableType) -> None:
        self.type = type
        self.elem: typing.List[ValInst] = []
        self.size = 0
        self.grow(type.limits.n, ValInst.zero(self.type.type))

    def grow(self, n: int, v: ValInst) -> None:
        if self.type.limits.m:
            assert self.size + n <= self.type.limits.m
        assert v.type == self.type.type
        self.elem.extend([v for _ in range(n)])
        self.size += n

    def suit(self, l: Limits) -> bool:
        return Limits(self.size, self.type.limits.m).suit(l)


class GlobalType:
    # Global types are encoded by their value type and a flag for their mutability.

    def __init__(self, type: ValType, mut: int) -> None:
        assert mut in [0x00, 0x01]
        self.type = type
        self.mut = mut

    def __repr__(self) -> str:
        prefix = ['const', 'var'][self.mut]
        return f'{prefix} {self.type}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(ValType.from_reader(r), ord(r.read(1)))


class GlobalDesc:
    # The globals component of a module defines a vector of global variables (or globals for short).

    def __init__(self, type: GlobalType, init: Expr) -> None:
        self.type = type
        self.init = init

    def __repr__(self) -> str:
        return repr(self.type)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        return cls(GlobalType.from_reader(r), Expr.from_reader(r))


class GlobalInst:
    # A global instance is the runtime representation of a global variable. It holds an individual value and a flag
    # indicating whether it is mutable. The value of mutable globals can be mutated through variable instructions or by
    # external means provided by the embedder.
    def __init__(self, data: ValInst, mut: int) -> None:
        assert mut in [0x00, 0x01]
        self.data = data
        self.mut = mut

    def __repr__(self) -> str:
        return f'{self.data}'


class Custom:
    # Custom sections have the id 0. They are intended to be used for debugging information or third-party extensions,
    # and are ignored by the WebAssembly semantics. Their contents consist of a name further identifying the custom
    # section, followed by an uninterpreted sequence of bytes for custom use.

    def __init__(self, name: str, data: bytearray) -> None:
        self.name = name
        self.data = data

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        n = pywasm.leb128.u.decode_reader(r)[0]
        return cls(r.read(n).decode(), bytearray(r.read(-1)))


class Import:
    # The imports component of a module defines a set of imports that are required for instantiation.
    #
    # Each import is labeled by a two-level name space, consisting of a module name and a name for an entity within
    # that module. Importable definitions are functions, tables, memories, and globals. Each import is specified by a
    # descriptor with a respective type that a definition provided during instantiation is required to match. Every
    # import defines an index in the respective index space. In each index space, the indices of imports go before the
    # first index of any definition contained in the module itself.

    def __init__(self, module: str, name: str, kind: int, desc: typing.Any) -> None:
        self.module = module
        self.name = name
        self.kind = kind
        self.desc = desc

    def __repr__(self) -> str:
        kind = {
            0x00: 'func',
            0x01: 'table',
            0x02: 'mem',
            0x03: 'global'
        }[self.kind]
        return f'{self.module}.{self.name} {kind} {self.desc}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        n = pywasm.leb128.u.decode_reader(r)[0]
        module = r.read(n).decode()
        n = pywasm.leb128.u.decode_reader(r)[0]
        name = r.read(n).decode()
        type = ord(r.read(1))
        desc = {
            0x00: lambda r: pywasm.leb128.u.decode_reader(r)[0],
            0x01: TableType.from_reader,
            0x02: MemType.from_reader,
            0x03: GlobalType.from_reader,
        }[type](r)
        return cls(module, name, type, desc)


class Extern:
    # An external value is the runtime representation of an entity that can be imported or exported. It is an address
    # denoting either a function instance, table instance, memory instance, or global instances in the shared store.

    def __init__(self, kind: int, data: int) -> None:
        assert kind in [0x00, 0x01, 0x02, 0x03]
        self.kind = kind
        self.data = data

    def __repr__(self) -> str:
        prefix = {
            0x00: 'func',
            0x01: 'table',
            0x02: 'mem',
            0x03: 'global',
        }[self.kind]
        return f'{prefix} {self.data}'


class ExportDesc:
    # The exports component of a module defines a set of exports that become accessible to the host environment once
    # the module has been instantiated.
    #
    # Each export is labeled by a unique name. Exportable definitions are functions, tables, memories, and globals,
    # which are referenced through a respective descriptor.

    def __init__(self, name: str, kind: int, desc: int) -> None:
        assert kind in [0x00, 0x01, 0x02, 0x03]
        self.name = name
        self.kind = kind
        self.desc = desc

    def __repr__(self) -> str:
        type_name = {
            0x00: 'func',
            0x01: 'table',
            0x02: 'mem',
            0x03: 'global'
        }[self.kind]
        return f'{self.name} {type_name} {self.desc}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        name = bytearray(r.read(pywasm.leb128.u.decode_reader(r)[0])).decode()
        kind = ord(r.read(1))
        desc = pywasm.leb128.u.decode_reader(r)[0]
        return cls(name, kind, desc)


class ExportInst:
    # An export instance is the runtime representation of an export. It defines the export's name and the associated
    # external value.

    def __init__(self, name: str, data: Extern) -> None:
        self.name = name
        self.data = data

    def __repr__(self):
        return f'{self.name} {self.data}'


class ElemDesc:
    # The initial contents of a table is uninitialized. The elem component of a module defines a vector of element
    # segments that initialize a subrange of a table, at a given offset, from a static vector of elements.
    # The offset is given by a constant expression.

    def __init__(self, kind: int, type: ValType, tidx: int, offset: Expr, init: typing.List[Expr]) -> None:
        assert kind >= 0x00
        assert kind <= 0x07
        self.kind = kind
        self.type = type
        self.tidx = tidx
        self.offset = offset
        self.init = init

    def __repr__(self) -> str:
        return f'{self.tidx}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        kind = pywasm.leb128.u.decode_reader(r)[0]
        type = ValType.ref_func()
        tidx = 0
        offset = Expr([])
        init = []
        match kind:
            case 0x00:
                offset = Expr.from_reader(r)
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    fidx = pywasm.leb128.u.decode_reader(r)[0]
                    expr = Expr([Inst(pywasm.opcode.ref_func, [fidx])])
                    init.append(expr)
            case 0x01:
                assert ord(r.read(1)) == 0x00
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    fidx = pywasm.leb128.u.decode_reader(r)[0]
                    expr = Expr([Inst(pywasm.opcode.ref_func, [fidx])])
                    init.append(expr)
            case 0x02:
                tidx = pywasm.leb128.u.decode_reader(r)[0]
                offset = Expr.from_reader(r)
                assert ord(r.read(1)) == 0x00
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    fidx = pywasm.leb128.u.decode_reader(r)[0]
                    expr = Expr([Inst(pywasm.opcode.ref_func, [fidx])])
                    init.append(expr)
            case 0x03:
                assert ord(r.read(1)) == 0x00
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    fidx = pywasm.leb128.u.decode_reader(r)[0]
                    expr = Expr([Inst(pywasm.opcode.ref_func, [fidx])])
                    init.append(expr)
            case 0x04:
                offset = Expr.from_reader(r)
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    expr = Expr.from_reader(r)
                    init.append(expr)
            case 0x05:
                type = ValType.from_reader(r)
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    expr = Expr.from_reader(r)
                    init.append(expr)
            case 0x06:
                tidx = pywasm.leb128.u.decode_reader(r)[0]
                offset = Expr.from_reader(r)
                type = ValType.from_reader(r)
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    expr = Expr.from_reader(r)
                    init.append(expr)
            case 0x07:
                type = ValType.from_reader(r)
                for _ in range(pywasm.leb128.u.decode_reader(r)[0]):
                    expr = Expr.from_reader(r)
                    init.append(expr)
        return cls(kind, type, tidx, offset, init)


class ElemInst:
    # An element instance is the runtime representation of an element segment. It holds a vector of references and
    # their common type.

    def __init__(self, type: ValType, data: typing.List[ValInst]) -> None:
        assert type in [ValType.ref_func(), ValType.ref_extern()]
        self.type = type
        self.data = data

    def __repr__(self) -> str:
        return f'{self.type}'


class DataDesc:
    # The initial contents of a memory are zero-valued bytes. The data component of a module defines a vector of data
    # segments that initialize a range of memory, at a given offset, with a static vector of bytes.
    # The offset is given by a constant expression.

    def __init__(self, kind: int, midx: int, offset: Expr, init: bytearray) -> None:
        # The initial integer can be interpreted as a bitfield. Bit 0 indicates a passive segment, bit 1 indicates the
        # presence of an explicit memory index for an active segment.
        # In the current version of WebAssembly, at most one memory may be defined or imported in a single module, so
        # all valid active data segments have a memory value of 0.
        assert kind in [0x00, 0x01, 0x02]
        assert midx == 0x00
        self.kind = kind
        self.midx = midx
        self.offset = offset
        self.init = init

    def __repr__(self) -> str:
        return f'{self.midx}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> typing.Self:
        kind = pywasm.leb128.u.decode_reader(r)[0]
        match kind:
            case 0x00:
                midx = 0
                offset = Expr.from_reader(r)
                init = bytearray(r.read(pywasm.leb128.u.decode_reader(r)[0]))
                return cls(kind, midx, offset, init)
            case 0x01:
                midx = 0
                offset = Expr([])
                init = bytearray(r.read(pywasm.leb128.u.decode_reader(r)[0]))
                return cls(kind, midx, offset, init)
            case 0x02:
                midx = pywasm.leb128.u.decode_reader(r)[0]
                offset = Expr.from_reader(r)
                init = bytearray(r.read(pywasm.leb128.u.decode_reader(r)[0]))
                return cls(kind, midx, offset, init)
            case _:
                raise Exception('unreachable')


class DataInst:
    # An data instance is the runtime representation of a data segment. It holds a vector of bytes.

    def __init__(self, data: bytearray) -> None:
        self.data = data

    def __repr__(self) -> str:
        return f'data'


class ModuleDesc:
    # The binary encoding of modules is organized into sections. Most sections correspond to one component of a module
    # record, except that function definitions are split into two sections, separating their type declarations in the
    # function section from their bodies in the code section.

    def __init__(
        self,
        type: typing.List[FuncType],
        func: typing.List[FuncDesc],
        tabl: typing.List[TableType],
        mems: typing.List[MemType],
        glob: typing.List[GlobalDesc],
        elem: typing.List[ElemDesc],
        data: typing.List[DataDesc],
        star: int,
        imps: typing.List[Import],
        exps: typing.List[ExportDesc]
    ):
        self.type = type
        self.func = func
        self.tabl = tabl
        self.mems = mems
        self.glob = glob
        self.elem = elem
        self.data = data
        self.star = star
        self.imps = imps
        self.exps = exps

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        assert bytearray(r.read(4)) == bytearray([0x00, 0x61, 0x73, 0x6d])
        assert bytearray(r.read(4)) == bytearray([0x01, 0x00, 0x00, 0x00])

        type: typing.List[FuncType] = []
        func: typing.List[FuncDesc] = []
        tabl: typing.List[TableType] = []
        mems: typing.List[MemType] = []
        glob: typing.List[GlobalDesc] = []
        elem: typing.List[ElemDesc] = []
        data: typing.List[DataDesc] = []
        star: int = -1
        imps: typing.List[Import] = []
        exps: typing.List[ExportDesc] = []

        for _ in range(32):
            section_id_byte = r.read(1)
            if not section_id_byte:
                break
            section_id = ord(section_id_byte)
            n = pywasm.leb128.u.decode_reader(r)[0]
            section_data = bytearray(r.read(n))
            assert len(section_data) == n
            section_reader = io.BytesIO(section_data)

            match section_id:
                case 0x00:
                    desc = Custom.from_reader(section_reader)
                    pywasm.log.debugln('section custom', desc.name)
                case 0x01:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = FuncType.from_reader(section_reader)
                        type.append(desc)
                        pywasm.log.debugln('section type', desc)
                case 0x02:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = Import.from_reader(section_reader)
                        imps.append(desc)
                        pywasm.log.debugln('section import', desc)
                case 0x03:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = FuncDesc.from_reader_type(section_reader)
                        func.append(desc)
                        pywasm.log.debugln('section func', desc.type)
                case 0x04:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = TableType.from_reader(section_reader)
                        tabl.append(desc)
                        pywasm.log.debugln('section table', desc)
                case 0x05:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = MemType.from_reader(section_reader)
                        mems.append(desc)
                        pywasm.log.debugln('section memory', desc)
                case 0x06:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = GlobalDesc.from_reader(section_reader)
                        glob.append(desc)
                        pywasm.log.debugln('section global', desc)
                case 0x07:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = ExportDesc.from_reader(section_reader)
                        exps.append(desc)
                        pywasm.log.debugln('section export', desc)
                case 0x08:
                    desc = pywasm.leb128.u.decode_reader(section_reader)[0]
                    star = desc
                    pywasm.log.debugln('section start', desc)
                case 0x09:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = ElemDesc.from_reader(section_reader)
                        elem.append(desc)
                        pywasm.log.debugln('section elem', desc)
                case 0x0a:
                    for i in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        size = pywasm.leb128.u.decode_reader(section_reader)[0]
                        desc = FuncDesc.from_reader_code(io.BytesIO(section_reader.read(size)))
                        func[i].locals = desc.locals
                        func[i].expr = desc.expr
                        pywasm.log.debugln('section code', desc)
                        desc.expr.into_disasm(4)
                case 0x0b:
                    for _ in range(pywasm.leb128.u.decode_reader(section_reader)[0]):
                        desc = DataDesc.from_reader(section_reader)
                        data.append(desc)
                        pywasm.log.debugln('section data', desc)
                case 0x0c:
                    n = pywasm.leb128.u.decode_reader(section_reader)[0]
                    pywasm.log.debugln('section data count', n)

        return cls(type, func, tabl, mems, glob, elem, data, star, imps, exps)


class ModuleInst:
    # A module instance is the runtime representation of a module. It is created by instantiating a module, and
    # collects runtime representations of all entities that are imported, defined, or exported by the module.

    def __init__(self) -> None:
        self.type: typing.List[FuncType] = []
        self.func: typing.List[int] = []
        self.tabl: typing.List[int] = []
        self.mems: typing.List[int] = []
        self.glob: typing.List[int] = []
        self.elem: typing.List[int] = []
        self.data: typing.List[int] = []
        self.exps: typing.List[ExportInst] = []


class FuncInst:
    # It effectively is a closure of the original function over the runtime module instance of its originating module.

    def __init__(self, type: FuncType, module: ModuleInst, code: FuncDesc) -> None:
        self.kind = 0x00
        self.type = type
        self.module = module
        self.code = code

    def __repr__(self) -> str:
        return f'{self.type}'


class FuncHost:
    # A host function is a function expressed outside WebAssembly but passed to a module as an import. The definition
    # and behavior of host functions are outside the scope of this specification. For the purpose of this
    # specification, it is assumed that when invoked, a host function behaves non-deterministically, but within certain
    # constraints that ensure the integrity of the runtime.

    def __init__(self, type: FuncType, hostcode: typing.Callable) -> None:
        self.kind = 0x01
        self.type = type
        self.hostcode = hostcode

    def __repr__(self) -> str:
        return self.hostcode.__name__


class Store:
    # The store represents all global state that can be manipulated by WebAssembly programs. It consists of the runtime
    # representation of all instances of functions, tables, memories, and globals that have been allocated during the
    # life time of the abstract machine

    def __init__(self):
        self.func: typing.List[FuncInst | FuncHost] = []
        self.tabl: typing.List[TableInst] = []
        self.mems: typing.List[MemInst] = []
        self.glob: typing.List[GlobalInst] = []
        self.elem: typing.List[ElemInst] = []
        self.data: typing.List[DataInst] = []

    def allocate_func_wasm(self, module: ModuleInst, func: FuncDesc) -> int:
        addr = len(self.func)
        type = module.type[func.type]
        inst = FuncInst(type, module, func)
        self.func.append(inst)
        return addr

    def allocate_func_host(self, func: FuncHost) -> int:
        addr = len(self.func)
        self.func.append(func)
        return addr

    def allocate_table(self, type: TableType) -> int:
        addr = len(self.tabl)
        inst = TableInst(type)
        self.tabl.append(inst)
        return addr

    def allocate_memory(self, type: MemType) -> int:
        addr = len(self.mems)
        inst = MemInst(type)
        self.mems.append(inst)
        return addr

    def allocate_global(self, type: GlobalType, data: ValInst) -> int:
        addr = len(self.glob)
        inst = GlobalInst(data, type.mut)
        self.glob.append(inst)
        return addr

    def allocate_elem(self, type: ValType, data: typing.List[ValInst]) -> int:
        addr = len(self.elem)
        inst = ElemInst(type, data)
        self.elem.append(inst)
        return addr

    def allocate_data(self, data: bytearray) -> int:
        addr = len(self.data)
        inst = DataInst(data)
        self.data.append(inst)
        return addr


class Label:
    # Labels carry an argument arity n and their associated branch target, which is expressed syntactically as an
    # instruction sequence.

    def __init__(self, arity: int, frame: int, value: int, carry: int, instr: typing.List[Inst], index: int) -> None:
        assert carry in [0x00, 0x01, 0x03]
        self.arity = arity
        self.frame = frame
        self.value = value
        self.carry = carry
        self.instr = instr
        self.index = index

    def __repr__(self) -> str:
        return f'{self.arity}'


class Frame:
    # Activation frames carry the return arity n of the respective function, hold the values of its locals
    # (including arguments) in the order corresponding to their static local indices, and a reference to the function's
    # own module instance.

    def __init__(self, module: ModuleInst, locals: LocalsInst, arity: int, label: int, value: int) -> None:
        self.module = module
        self.locals = locals
        self.arity = arity
        self.label = label
        self.value = value

    def __repr__(self) -> str:
        return f'{self.arity}'


class Stack:
    # Besides the store, most instructions interact with an implicit stack. The stack contains three kinds of entries:
    #
    # Values: the operands of instructions.
    # Labels: active structured control instructions that can be targeted by branches.
    # Activations: the call frames of active function calls.
    #
    # These entries can occur on the stack in any order during the execution of a program. Stack entries are described
    # by abstract syntax as follows.

    def __init__(self) -> None:
        self.value: typing.List[ValInst] = []
        self.label: typing.List[Label] = []
        self.frame: typing.List[Frame] = []


class Machine:
    # Execution behavior is defined in terms of an abstract machine that models the program state. It includes a stack,
    # which records operand values and control constructs, and an abstract store containing global state.

    def __init__(self) -> None:
        self.store = Store()
        self.stack = Stack()

    def allocate(
        self,
        module: ModuleDesc,
        extern: typing.List[Extern],
        globin: typing.List[ValInst],
        elemin: typing.List[typing.List[ValInst]]
    ) -> ModuleInst:
        inst = ModuleInst()
        inst.type = module.type
        for e in extern:
            match e.kind:
                case 0x00:
                    inst.func.append(e.data)
                case 0x01:
                    inst.tabl.append(e.data)
                case 0x02:
                    inst.mems.append(e.data)
                case 0x03:
                    inst.glob.append(e.data)
        for _, e in enumerate(module.func):
            addr = self.store.allocate_func_wasm(inst, e)
            inst.func.append(addr)
        for _, e in enumerate(module.tabl):
            addr = self.store.allocate_table(e)
            inst.tabl.append(addr)
        for _, e in enumerate(module.mems):
            addr = self.store.allocate_memory(e)
            inst.mems.append(addr)
        for i, e in enumerate(module.glob):
            addr = self.store.allocate_global(e.type, globin[i])
            inst.glob.append(addr)
        for i, e in enumerate(module.elem):
            addr = self.store.allocate_elem(e.type, elemin[i])
            inst.elem.append(addr)
        for i, e in enumerate(module.data):
            addr = self.store.allocate_data(e.init)
            inst.data.append(addr)
        for _, e in enumerate(module.exps):
            expi = ExportInst(e.name, Extern(e.kind, 0))
            match e.kind:
                case 0x00:
                    expi.data.data = inst.func[e.desc]
                case 0x01:
                    expi.data.data = inst.tabl[e.desc]
                case 0x02:
                    expi.data.data = inst.mems[e.desc]
                case 0x03:
                    expi.data.data = inst.glob[e.desc]
            inst.exps.append(expi)
        return inst

    def instance(self, module: ModuleDesc, extern: typing.List[Extern]) -> ModuleInst:
        assert len(module.imps) == len(extern)
        for a, b in zip(module.imps, extern):
            assert a.kind == b.kind
            match a.kind:
                case 0x00:
                    assert self.store.func[b.data].type == module.type[a.desc]
                case 0x01:
                    assert self.store.tabl[b.data].type.type == a.desc.type
                    assert self.store.tabl[b.data].suit(a.desc.limits)
                case 0x02:
                    assert self.store.mems[b.data].suit(a.desc.limits)
                case 0x03:
                    assert self.store.glob[b.data].data.type == a.desc.type
                    assert self.store.glob[b.data].mut == a.desc.mut
        globin: typing.List[ValInst] = []
        elemin: typing.List[typing.List[ValInst]] = []
        auxmod = ModuleInst()
        auxmod.func.extend([e.data for e in extern if e.kind == 0x00])
        auxmod.func.extend([len(self.store.func) + i for i in range(len(module.func))])
        auxmod.glob.extend([e.data for e in extern if e.kind == 0x03])
        self.stack.frame.append(Frame(auxmod, LocalsInst([]), 1, 0, 0))
        for i, e in enumerate(module.glob):
            pywasm.log.debugln('init global', e)
            self.stack.label.append(Label(1, 1, 0, 1, e.init.data, 0))
            self.evaluate()
            assert len(self.stack.frame) == 1
            assert len(self.stack.label) == 0
            assert len(self.stack.value) == 1
            rets = self.stack.value.pop()
            globin.append(rets)
        for i, e in enumerate(module.elem):
            pywasm.log.debugln('init elem', e)
            l: typing.List[ValInst] = []
            for f in e.init:
                self.stack.label.append(Label(1, 1, 0, 1, f.data, 0))
                self.evaluate()
                assert len(self.stack.frame) == 1
                assert len(self.stack.label) == 0
                assert len(self.stack.value) == 1
                rets = self.stack.value.pop()
                l.append(rets)
            elemin.append(l)
        self.stack.frame.pop()
        newmod = self.allocate(module, extern, globin, elemin)
        assert newmod.func == auxmod.func
        self.stack.frame.append(Frame(newmod, LocalsInst([]), 0, 0, 0))
        for i, e in enumerate(module.elem):
            if e.kind & 0x01 != 0x00:
                continue
            expr = []
            expr.extend(e.offset.data)
            expr.append(Inst(pywasm.opcode.i32_const, [0]))
            expr.append(Inst(pywasm.opcode.i32_const, [len(e.init)]))
            expr.append(Inst(pywasm.opcode.table_init, [i, e.tidx]))
            expr.append(Inst(pywasm.opcode.elem_drop, [i]))
            self.stack.label.append(Label(1, 1, 0, 1, expr, 0))
            self.evaluate()
            assert len(self.stack.frame) == 1
            assert len(self.stack.label) == 0
            assert len(self.stack.value) == 0
        for i, e in enumerate(module.elem):
            if e.kind & 0x03 != 0x03:
                continue
            expr = []
            expr.append(Inst(pywasm.opcode.elem_drop, [i]))
            self.stack.label.append(Label(1, 1, 0, 1, expr, 0))
            self.evaluate()
            assert len(self.stack.frame) == 1
            assert len(self.stack.label) == 0
            assert len(self.stack.value) == 0
        for i, e in enumerate(module.data):
            pywasm.log.debugln('init data', e)
            if e.kind & 0x01 != 0x00:
                continue
            expr = []
            expr.extend(e.offset.data)
            expr.append(Inst(pywasm.opcode.i32_const, [0]))
            expr.append(Inst(pywasm.opcode.i32_const, [len(e.init)]))
            expr.append(Inst(pywasm.opcode.memory_init, [i]))
            expr.append(Inst(pywasm.opcode.data_drop, [i]))
            self.stack.label.append(Label(1, 1, 0, 1, expr, 0))
            self.evaluate()
            assert len(self.stack.frame) == 1
            assert len(self.stack.label) == 0
            assert len(self.stack.value) == 0
        if module.star >= 0:
            expr = []
            expr.append(Inst(pywasm.opcode.call, [module.star]))
            self.stack.label.append(Label(1, 1, 0, 1, expr, 0))
            self.evaluate()
            assert len(self.stack.frame) == 1
            assert len(self.stack.label) == 0
            assert len(self.stack.value) == 0
        self.stack.frame.pop()
        return newmod

    def invocate(self, addr: int, args: typing.List[ValInst]) -> typing.List[ValInst]:
        func = self.store.func[addr]
        assert func.kind == 0x00
        assert isinstance(func, FuncInst)
        for a, b in zip(func.type.args, args):
            assert a == b.type
        self.stack.frame.append(Frame(ModuleInst(), LocalsInst([]), 0, 0, 0))
        pywasm.log.debugln('invocate', addr, args)
        locals = LocalsInst(args)
        for e in func.code.locals:
            locals.data.extend([ValInst.zero(e.type) for _ in range(e.n)])
        self.stack.frame.append(Frame(func.module, locals, len(func.type.rets), 0, 0))
        self.stack.label.append(Label(len(func.type.rets), 1, 0, 3, func.code.expr.data, 0))
        self.evaluate()
        rets = [self.stack.value.pop() for _ in range(len(func.type.rets))][::-1]
        for a, b in zip(func.type.rets, rets):
            assert a == b.type
        self.stack.frame.pop()
        assert len(self.stack.frame) == 0
        assert len(self.stack.label) == 0
        assert len(self.stack.value) == 0
        return rets

    def evaluate_br(self, l: int) -> None:
        assert len(self.stack.label) >= l + 1
        label = self.stack.label[-1 - l]
        assert len(self.stack.value) >= label.value + label.arity
        rets = [self.stack.value.pop() for _ in range(label.arity)][::-1]
        self.stack.frame = self.stack.frame[:label.frame]
        self.stack.label = self.stack.label[:len(self.stack.label)-l]
        match label.carry & 1:
            case 0x00:
                label.index = 0
            case 0x01:
                self.stack.label.pop()
        self.stack.value = self.stack.value[:label.value]
        self.stack.value.extend(rets)

    def evaluate_bype(self, bype: Bype) -> FuncType:
        match bype.kind:
            case 0x00:
                return FuncType([], [])
            case 0x01:
                return FuncType([], [ValType(bype.data)])
            case 0x02:
                return self.stack.frame[-1].module.type[bype.data]
            case _:
                raise Exception('unreachable')

    def evaluate_call(self, addr: int) -> None:
        func = self.store.func[addr]
        args = [self.stack.value.pop() for _ in range(len(func.type.args))][::-1]
        nret = len(func.type.rets)
        match func.kind:
            case 0x00:
                assert isinstance(func, FuncInst)
                assert len(self.stack.frame) < 1024
                locals = LocalsInst(args)
                for e in func.code.locals:
                    locals.data.extend([ValInst.zero(e.type) for _ in range(e.n)])
                self.stack.frame.append(Frame(
                    func.module,
                    locals,
                    nret,
                    len(self.stack.label),
                    len(self.stack.value),
                ))
                self.stack.label.append(Label(
                    nret,
                    len(self.stack.frame),
                    len(self.stack.value),
                    3,
                    func.code.expr.data,
                    0,
                ))
            case 0x01:
                assert isinstance(func, FuncHost)
                rets = func.hostcode(self, [e.into_all() for e in args])
                rets = [ValInst.from_all(a, b) for a, b in zip(func.type.rets, rets)]
                self.stack.value.extend(rets)
            case _:
                raise Exception('unreachable')

    def evaluate_mem_load(self, offset: int, size: int) -> bytearray:
        mems = self.store.mems[self.stack.frame[-1].module.mems[0]]
        addr = self.stack.value.pop().into_u32()
        addr = addr + offset
        assert addr + size <= len(mems.data)
        return mems.data[addr:addr+size]

    def evaluate_mem_save(self, offset: int, size: int) -> None:
        mems = self.store.mems[self.stack.frame[-1].module.mems[0]]
        data = self.stack.value.pop().data
        addr = self.stack.value.pop().into_u32()
        addr = addr + offset
        assert addr + size <= len(mems.data)
        mems.data[addr:addr+size] = data[:size]

    def evaluate(self) -> None:
        for _ in range(1 << 32):
            if not self.stack.label:
                break
            label = self.stack.label[-1]
            frame = self.stack.frame[-1]
            if label.index == len(label.instr):
                self.stack.label.pop()
                if label.carry & 2:
                    assert len(self.stack.value) == frame.value + frame.arity
                    self.stack.frame.pop()
                continue
            instr = label.instr[label.index]
            label.index += 1
            pywasm.log.debugln('    ', instr)
            match instr.opcode:
                case pywasm.opcode.unreachable:
                    assert 0
                case pywasm.opcode.nop:
                    assert 1
                case pywasm.opcode.block:
                    bype = self.evaluate_bype(instr.args[0])
                    assert len(self.stack.value) >= label.value + len(bype.args)
                    self.stack.label.append(Label(
                        len(bype.rets),
                        len(self.stack.frame),
                        len(self.stack.value) - len(bype.args),
                        1,
                        instr.args[1],
                        0,
                    ))
                case pywasm.opcode.loop:
                    bype = self.evaluate_bype(instr.args[0])
                    assert len(self.stack.value) >= label.value + len(bype.args)
                    self.stack.label.append(Label(
                        len(bype.args),
                        len(self.stack.frame),
                        len(self.stack.value) - len(bype.args),
                        0,
                        instr.args[1],
                        0,
                    ))
                case pywasm.opcode.if_then:
                    bype = self.evaluate_bype(instr.args[0])
                    cond = self.stack.value.pop().into_i32()
                    assert len(self.stack.value) >= label.value + len(bype.args)
                    aidx = 1 if cond != 0 else 2
                    self.stack.label.append(Label(
                        len(bype.rets),
                        len(self.stack.frame),
                        len(self.stack.value) - len(bype.args),
                        1,
                        instr.args[aidx],
                        0,
                    ))
                case pywasm.opcode.else_fi:
                    assert 0
                case pywasm.opcode.end:
                    assert 0
                case pywasm.opcode.br:
                    self.evaluate_br(instr.args[0])
                case pywasm.opcode.br_if:
                    if self.stack.value.pop().into_i32() != 0:
                        self.evaluate_br(instr.args[0])
                case pywasm.opcode.br_table:
                    a = self.stack.value.pop().into_u32()
                    b = instr.args[1]
                    if a < len(instr.args[0]):
                        b = instr.args[0][a]
                    self.evaluate_br(b)
                case pywasm.opcode.return_call:
                    assert len(self.stack.value) >= frame.value + frame.arity
                    rets = [self.stack.value.pop() for _ in range(frame.arity)][::-1]
                    self.stack.frame.pop()
                    self.stack.label = self.stack.label[:frame.label]
                    self.stack.value = self.stack.value[:frame.value]
                    self.stack.value.extend(rets)
                case pywasm.opcode.call:
                    addr = frame.module.func[instr.args[0]]
                    self.evaluate_call(addr)
                case pywasm.opcode.call_indirect:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[1]]]
                    type = frame.module.type[instr.args[0]]
                    addr = tabl.elem[self.stack.value.pop().into_u32()].into_ref()
                    assert self.store.func[addr].type == type
                    self.evaluate_call(addr)
                case pywasm.opcode.drop:
                    self.stack.value.pop()
                case pywasm.opcode.select:
                    c = self.stack.value.pop().into_i32()
                    b = self.stack.value.pop()
                    a = self.stack.value.pop()
                    d = a if c != 0 else b
                    self.stack.value.append(d)
                case pywasm.opcode.select_type:
                    c = self.stack.value.pop().into_i32()
                    b = self.stack.value.pop()
                    a = self.stack.value.pop()
                    assert a.type.data == instr.args[0][0]
                    assert b.type.data == instr.args[0][0]
                    d = a if c != 0 else b
                    self.stack.value.append(d)
                case pywasm.opcode.local_get:
                    a = self.stack.frame[-1].locals.data[instr.args[0]]
                    self.stack.value.append(a)
                case pywasm.opcode.local_set:
                    a = self.stack.value.pop()
                    self.stack.frame[-1].locals.data[instr.args[0]] = a
                case pywasm.opcode.local_tee:
                    a = self.stack.value[-1]
                    self.stack.frame[-1].locals.data[instr.args[0]] = a
                case pywasm.opcode.global_get:
                    glob = self.store.glob[frame.module.glob[instr.args[0]]]
                    self.stack.value.append(glob.data)
                case pywasm.opcode.global_set:
                    glob = self.store.glob[frame.module.glob[instr.args[0]]]
                    assert glob.mut == 0x01
                    glob.data = self.stack.value.pop()
                case pywasm.opcode.table_get:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    a = self.stack.value.pop().into_u32()
                    b = tabl.elem[a]
                    self.stack.value.append(b)
                case pywasm.opcode.table_set:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    a = self.stack.value.pop()
                    assert a.type == tabl.type.type
                    b = self.stack.value.pop().into_u32()
                    tabl.elem[b] = a
                case pywasm.opcode.i32_load:
                    a = ValInst(ValType.i32(), self.evaluate_mem_load(instr.args[1], 4) + bytearray(ValInst.blen - 4))
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load:
                    a = ValInst(ValType.i64(), self.evaluate_mem_load(instr.args[1], 8) + bytearray(ValInst.blen - 8))
                    self.stack.value.append(a)
                case pywasm.opcode.f32_load:
                    a = ValInst(ValType.f32(), self.evaluate_mem_load(instr.args[1], 4) + bytearray(ValInst.blen - 4))
                    self.stack.value.append(a)
                case pywasm.opcode.f64_load:
                    a = ValInst(ValType.f64(), self.evaluate_mem_load(instr.args[1], 8) + bytearray(ValInst.blen - 8))
                    self.stack.value.append(a)
                case pywasm.opcode.i32_load8_s:
                    a = ValInst.from_i32(struct.unpack('<b', self.evaluate_mem_load(instr.args[1], 1))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i32_load8_u:
                    a = ValInst.from_i32(struct.unpack('<B', self.evaluate_mem_load(instr.args[1], 1))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i32_load16_s:
                    a = ValInst.from_i32(struct.unpack('<h', self.evaluate_mem_load(instr.args[1], 2))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i32_load16_u:
                    a = ValInst.from_i32(struct.unpack('<H', self.evaluate_mem_load(instr.args[1], 2))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load8_s:
                    a = ValInst.from_i64(struct.unpack('<b', self.evaluate_mem_load(instr.args[1], 1))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load8_u:
                    a = ValInst.from_i64(struct.unpack('<B', self.evaluate_mem_load(instr.args[1], 1))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load16_s:
                    a = ValInst.from_i64(struct.unpack('<h', self.evaluate_mem_load(instr.args[1], 2))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load16_u:
                    a = ValInst.from_i64(struct.unpack('<H', self.evaluate_mem_load(instr.args[1], 2))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load32_s:
                    a = ValInst.from_i64(struct.unpack('<i', self.evaluate_mem_load(instr.args[1], 4))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_load32_u:
                    a = ValInst.from_i64(struct.unpack('<I', self.evaluate_mem_load(instr.args[1], 4))[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i32_store:
                    self.evaluate_mem_save(instr.args[1], 4)
                case pywasm.opcode.i64_store:
                    self.evaluate_mem_save(instr.args[1], 8)
                case pywasm.opcode.f32_store:
                    self.evaluate_mem_save(instr.args[1], 4)
                case pywasm.opcode.f64_store:
                    self.evaluate_mem_save(instr.args[1], 8)
                case pywasm.opcode.i32_store8:
                    self.evaluate_mem_save(instr.args[1], 1)
                case pywasm.opcode.i32_store16:
                    self.evaluate_mem_save(instr.args[1], 2)
                case pywasm.opcode.i64_store8:
                    self.evaluate_mem_save(instr.args[1], 1)
                case pywasm.opcode.i64_store16:
                    self.evaluate_mem_save(instr.args[1], 2)
                case pywasm.opcode.i64_store32:
                    self.evaluate_mem_save(instr.args[1], 4)
                case pywasm.opcode.memory_size:
                    mems = self.store.mems[frame.module.mems[0]]
                    size = mems.size
                    self.stack.value.append(ValInst.from_i32(size))
                case pywasm.opcode.memory_grow:
                    mems = self.store.mems[frame.module.mems[0]]
                    size = mems.size
                    incr = self.stack.value.pop().into_u32()
                    rets = -1
                    # Limit memory size to 64m.
                    cnda = size + incr <= 1024
                    cndb = mems.type.limits.m == 0 or size + incr <= mems.type.limits.m
                    if cnda and cndb:
                        rets = size
                        mems.grow(incr)
                    self.stack.value.append(ValInst.from_i32(rets))
                case pywasm.opcode.i32_const:
                    a = ValInst.from_i32(instr.args[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i64_const:
                    a = ValInst.from_i64(instr.args[0])
                    self.stack.value.append(a)
                case pywasm.opcode.f32_const:
                    a = ValInst.from_i32(instr.args[0])
                    a.type = ValType.f32()
                    self.stack.value.append(a)
                case pywasm.opcode.f64_const:
                    a = ValInst.from_i64(instr.args[0])
                    a.type = ValType.f64()
                    self.stack.value.append(a)
                case pywasm.opcode.i32_eqz:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_i32(a == 0)
                    self.stack.value.append(b)
                case pywasm.opcode.i32_eq:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a == b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_ne:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a != b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_lt_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_lt_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_gt_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_gt_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_le_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_le_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_ge_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_ge_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_eqz:
                    a = self.stack.value.pop().into_i64()
                    b = ValInst.from_i32(a == 0)
                    self.stack.value.append(b)
                case pywasm.opcode.i64_eq:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a == b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_ne:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a != b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_lt_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_lt_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_gt_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_gt_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_le_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_le_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_ge_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_ge_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_eq:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a == b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_ne:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a != b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_lt:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_gt:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_le:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_ge:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_eq:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a == b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_ne:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a != b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_lt:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a < b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_gt:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a > b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_le:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a <= b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_ge:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_i32(a >= b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_clz:
                    a = self.stack.value.pop().into_u32()
                    b = pywasm.arith.u32.clz(a)
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_ctz:
                    a = self.stack.value.pop().into_u32()
                    b = pywasm.arith.u32.ctz(a)
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_popcnt:
                    a = self.stack.value.pop().into_u32()
                    b = pywasm.arith.u32.popcnt(a)
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_add:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.add(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_sub:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.sub(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_mul:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.mul(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_div_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.div(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_div_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_u32(pywasm.arith.u32.div(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_rem_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.rem(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_rem_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_u32(pywasm.arith.u32.rem(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_and:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a & b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_or:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a | b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_xor:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(a ^ b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_shl:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.shl(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_shr_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_i32()
                    c = ValInst.from_i32(pywasm.arith.i32.shr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_shr_u:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_u32(pywasm.arith.u32.shr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_rotl:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_u32(pywasm.arith.u32.rotl(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_rotr:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_u32()
                    c = ValInst.from_u32(pywasm.arith.u32.rotr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_clz:
                    a = self.stack.value.pop().into_u64()
                    b = pywasm.arith.u64.clz(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_ctz:
                    a = self.stack.value.pop().into_u64()
                    b = pywasm.arith.u64.ctz(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_popcnt:
                    a = self.stack.value.pop().into_u64()
                    b = pywasm.arith.u64.popcnt(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_add:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.add(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_sub:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.sub(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_mul:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.mul(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_div_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.div(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_div_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_i64(pywasm.arith.u64.div(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_rem_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.rem(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_rem_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_u64(pywasm.arith.u64.rem(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_and:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(a & b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_or:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(a | b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_xor:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(a ^ b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_shl:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.shl(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_shr_s:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_i64()
                    c = ValInst.from_i64(pywasm.arith.i64.shr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_shr_u:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_u64(pywasm.arith.u64.shr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_rotl:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_u64(pywasm.arith.u64.rotl(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i64_rotr:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_u64()
                    c = ValInst.from_u64(pywasm.arith.u64.rotr(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.f32_abs:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f32(), a.data.copy())
                    b.data[3] = b.data[3] & 0x7f
                    self.stack.value.append(b)
                case pywasm.opcode.f32_neg:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f32(), a.data.copy())
                    b.data[3] = b.data[3] ^ 0x80
                    self.stack.value.append(b)
                case pywasm.opcode.f32_ceil:
                    a = self.stack.value.pop().into_f32()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.ceil(a))
                    c = ValInst.from_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_floor:
                    a = self.stack.value.pop().into_f32()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.floor(a))
                    c = ValInst.from_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_trunc:
                    a = self.stack.value.pop().into_f32()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.trunc(a))
                    c = ValInst.from_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_nearest:
                    a = self.stack.value.pop().into_f32()
                    b = a if math.isnan(a) or math.isinf(a) else float(round(a))
                    c = ValInst.from_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_sqrt:
                    a = self.stack.value.pop().into_f32()
                    b = math.sqrt(a) if a >= 0 else math.nan
                    c = ValInst.from_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_add:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_f32(a + b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_sub:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_f32(a - b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_mul:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_f32(a * b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32_div:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = pywasm.arith.f32.div(a, b)
                    d = ValInst.from_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32_min:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = pywasm.arith.f32.min(a, b)
                    d = ValInst.from_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32_max:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = pywasm.arith.f32.max(a, b)
                    d = ValInst.from_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32_copysign:
                    b = self.stack.value.pop().into_f32()
                    a = self.stack.value.pop().into_f32()
                    c = ValInst.from_f32(math.copysign(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.f64_abs:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f64(), a.data.copy())
                    b.data[7] = b.data[7] & 0x7f
                    self.stack.value.append(b)
                case pywasm.opcode.f64_neg:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f64(), a.data.copy())
                    b.data[7] = b.data[7] ^ 0x80
                    self.stack.value.append(b)
                case pywasm.opcode.f64_ceil:
                    a = self.stack.value.pop().into_f64()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.ceil(a))
                    c = ValInst.from_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_floor:
                    a = self.stack.value.pop().into_f64()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.floor(a))
                    c = ValInst.from_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_trunc:
                    a = self.stack.value.pop().into_f64()
                    b = a if math.isnan(a) or math.isinf(a) else float(math.trunc(a))
                    c = ValInst.from_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_nearest:
                    a = self.stack.value.pop().into_f64()
                    b = a if math.isnan(a) or math.isinf(a) else float(round(a))
                    c = ValInst.from_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_sqrt:
                    a = self.stack.value.pop().into_f64()
                    b = math.sqrt(a) if a >= 0 else math.nan
                    c = ValInst.from_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_add:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_f64(a + b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_sub:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_f64(a - b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_mul:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_f64(a * b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64_div:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = pywasm.arith.f64.div(a, b)
                    d = ValInst.from_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64_min:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = pywasm.arith.f64.min(a, b)
                    d = ValInst.from_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64_max:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = pywasm.arith.f64.max(a, b)
                    d = ValInst.from_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64_copysign:
                    b = self.stack.value.pop().into_f64()
                    a = self.stack.value.pop().into_f64()
                    c = ValInst.from_f64(math.copysign(a, b))
                    self.stack.value.append(c)
                case pywasm.opcode.i32_wrap_i64:
                    a = self.stack.value.pop().into_i64()
                    b = ValInst.from_i32(pywasm.arith.i32.fit(a))
                    self.stack.value.append(b)
                case pywasm.opcode.i32_trunc_f32_s:
                    a = self.stack.value.pop().into_f32()
                    b = int(a)
                    c = ValInst.from_i32(b)
                    assert c.into_i32() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_f32_u:
                    a = self.stack.value.pop().into_f32()
                    b = int(a)
                    c = ValInst.from_u32(b)
                    assert c.into_u32() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_f64_s:
                    a = self.stack.value.pop().into_f64()
                    b = int(a)
                    c = ValInst.from_i32(b)
                    assert c.into_i32() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_f64_u:
                    a = self.stack.value.pop().into_f64()
                    b = int(a)
                    c = ValInst.from_u32(b)
                    assert c.into_u32() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i64_extend_i32_s:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64_extend_i32_u:
                    a = self.stack.value.pop().into_u32()
                    b = ValInst.from_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64_trunc_f32_s:
                    a = self.stack.value.pop().into_f32()
                    b = int(a)
                    c = ValInst.from_i64(b)
                    assert c.into_i64() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_f32_u:
                    a = self.stack.value.pop().into_f32()
                    b = int(a)
                    c = ValInst.from_u64(b)
                    assert c.into_u64() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_f64_s:
                    a = self.stack.value.pop().into_f64()
                    b = int(a)
                    c = ValInst.from_i64(b)
                    assert c.into_i64() == b
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_f64_u:
                    a = self.stack.value.pop().into_f64()
                    b = int(a)
                    c = ValInst.from_u64(b)
                    assert c.into_u64() == b
                    self.stack.value.append(c)
                case pywasm.opcode.f32_convert_i32_s:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_f32(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f32_convert_i32_u:
                    a = self.stack.value.pop().into_u32()
                    b = ValInst.from_f32(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f32_convert_i64_s:
                    a = self.stack.value.pop().into_i64()
                    b = ValInst.from_f32(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f32_convert_i64_u:
                    a = self.stack.value.pop().into_u64()
                    b = ValInst.from_f32(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f32_demote_f64:
                    a = self.stack.value.pop().into_f64()
                    b = ValInst.from_f32(a)
                    self.stack.value.append(b)
                case pywasm.opcode.f64_convert_i32_s:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_f64(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f64_convert_i32_u:
                    a = self.stack.value.pop().into_u32()
                    b = ValInst.from_f64(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f64_convert_i64_s:
                    a = self.stack.value.pop().into_i64()
                    b = ValInst.from_f64(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f64_convert_i64_u:
                    a = self.stack.value.pop().into_u64()
                    b = ValInst.from_f64(float(a))
                    self.stack.value.append(b)
                case pywasm.opcode.f64_promote_f32:
                    a = self.stack.value.pop().into_f32()
                    b = ValInst.from_f64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32_reinterpret_f32:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.i32(), a.data.copy())
                    self.stack.value.append(b)
                case pywasm.opcode.i64_reinterpret_f64:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.i64(), a.data.copy())
                    self.stack.value.append(b)
                case pywasm.opcode.f32_reinterpret_i32:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f32(), a.data.copy())
                    self.stack.value.append(b)
                case pywasm.opcode.f64_reinterpret_i64:
                    a = self.stack.value.pop()
                    b = ValInst(ValType.f64(), a.data.copy())
                    self.stack.value.append(b)
                case pywasm.opcode.i32_extend8_s:
                    a = self.stack.value.pop().into_i32()
                    b = pywasm.arith.i8.fit(a)
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_extend16_s:
                    a = self.stack.value.pop().into_i32()
                    b = pywasm.arith.i16.fit(a)
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_extend8_s:
                    a = self.stack.value.pop().into_i64()
                    b = pywasm.arith.i8.fit(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_extend16_s:
                    a = self.stack.value.pop().into_i64()
                    b = pywasm.arith.i16.fit(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_extend32_s:
                    a = self.stack.value.pop().into_i64()
                    b = pywasm.arith.i32.fit(a)
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.ref_null:
                    a = ValInst.zero(ValType(instr.args[0]))
                    self.stack.value.append(a)
                case pywasm.opcode.ref_is_null:
                    a = self.stack.value.pop()
                    assert a.type in [ValType.ref_func(), ValType.ref_extern()]
                    b = 0x01 if a.data[4] == 0x00 else 0x00
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.ref_func:
                    a = frame.module.func[instr.args[0]]
                    b = ValInst.from_ref(ValType.ref_func(), a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32_trunc_sat_f32_s:
                    a = self.stack.value.pop().into_f32()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.i32.min, min(a, pywasm.arith.i32.max)))
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_sat_f32_u:
                    a = self.stack.value.pop().into_f32()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.u32.min, min(a, pywasm.arith.u32.max)))
                    c = ValInst.from_u32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_sat_f64_s:
                    a = self.stack.value.pop().into_f64()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.i32.min, min(a, pywasm.arith.i32.max)))
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32_trunc_sat_f64_u:
                    a = self.stack.value.pop().into_f64()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.u32.min, min(a, pywasm.arith.u32.max)))
                    c = ValInst.from_u32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_sat_f32_s:
                    a = self.stack.value.pop().into_f32()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.i64.min, min(a, pywasm.arith.i64.max)))
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_sat_f32_u:
                    a = self.stack.value.pop().into_f32()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.u64.min, min(a, pywasm.arith.u64.max)))
                    c = ValInst.from_u64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_sat_f64_s:
                    a = self.stack.value.pop().into_f64()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.i64.min, min(a, pywasm.arith.i64.max)))
                    c = ValInst.from_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64_trunc_sat_f64_u:
                    a = self.stack.value.pop().into_f64()
                    if math.isnan(a):
                        a = 0.0
                    b = int(max(pywasm.arith.u64.min, min(a, pywasm.arith.u64.max)))
                    c = ValInst.from_u64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.memory_init:
                    mems = self.store.mems[frame.module.mems[0]]
                    data = self.store.data[frame.module.data[instr.args[0]]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop().into_u32()
                    d = self.stack.value.pop().into_u32()
                    assert s + n <= len(data.data)
                    assert d + n <= len(mems.data)
                    mems.data[d:d+n] = data.data[s:s+n]
                case pywasm.opcode.data_drop:
                    data = self.store.data[frame.module.data[instr.args[0]]]
                    data.data.clear()
                case pywasm.opcode.memory_copy:
                    mems = self.store.mems[frame.module.mems[0]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop().into_u32()
                    d = self.stack.value.pop().into_u32()
                    assert s + n <= len(mems.data)
                    assert d + n <= len(mems.data)
                    mems.data[d:d+n] = mems.data[s:s+n]
                case pywasm.opcode.memory_fill:
                    mems = self.store.mems[frame.module.mems[0]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop().data[0]
                    d = self.stack.value.pop().into_u32()
                    assert d + n <= len(mems.data)
                    for i in range(n):
                        mems.data[d+i] = s
                case pywasm.opcode.table_init:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[1]]]
                    elem = self.store.elem[frame.module.elem[instr.args[0]]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop().into_u32()
                    d = self.stack.value.pop().into_u32()
                    assert s + n <= len(elem.data)
                    assert d + n <= len(tabl.elem)
                    tabl.elem[d:d+n] = elem.data[s:s+n]
                case pywasm.opcode.elem_drop:
                    # The instruction prevents further use of a passive element segment. This instruction is intended
                    # to be used as an optimization hint. After an element segment is dropped its elements can no
                    # longer be retrieved, so the memory used by this segment may be freed.
                    elem = self.store.elem[frame.module.elem[instr.args[0]]]
                    elem.data.clear()
                case pywasm.opcode.table_copy:
                    tabx = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    taby = self.store.tabl[frame.module.tabl[instr.args[1]]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop().into_u32()
                    d = self.stack.value.pop().into_u32()
                    assert s + n <= len(taby.elem)
                    assert d + n <= len(tabx.elem)
                    tabx.elem[d:d+n] = taby.elem[s:s+n]
                case pywasm.opcode.table_grow:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    size = tabl.size
                    incr = self.stack.value.pop().into_u32()
                    init = self.stack.value.pop()
                    rets = -1
                    cnda = size + incr <= 1024
                    cndb = tabl.type.limits.m == 0 or size + incr <= tabl.type.limits.m
                    if cnda and cndb:
                        rets = size
                        tabl.grow(incr, init)
                    self.stack.value.append(ValInst.from_i32(rets))
                case pywasm.opcode.table_size:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    size = tabl.size
                    self.stack.value.append(ValInst.from_i32(size))
                case pywasm.opcode.table_fill:
                    tabl = self.store.tabl[frame.module.tabl[instr.args[0]]]
                    n = self.stack.value.pop().into_u32()
                    s = self.stack.value.pop()
                    d = self.stack.value.pop().into_u32()
                    assert d + n <= len(tabl.elem)
                    for i in range(n):
                        tabl.elem[d+i] = s
                case pywasm.opcode.v128_load:
                    a = ValInst.from_v128(self.evaluate_mem_load(instr.args[1], 16))
                    self.stack.value.append(a)
                case pywasm.opcode.v128_load8x8_s:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(8):
                        n = a[i]
                        n = n - ((n & 0x80) << 1)
                        b.extend(bytearray(n.to_bytes(2, 'little', signed=True)))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load8x8_u:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(8):
                        n = a[i]
                        b.extend(bytearray(n.to_bytes(2, 'little')))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load16x4_s:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(4):
                        n = int.from_bytes(a[i*2:i*2+2], 'little')
                        n = n - ((n & 0x8000) << 1)
                        b.extend(bytearray(n.to_bytes(4, 'little', signed=True)))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load16x4_u:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(4):
                        n = int.from_bytes(a[i*2:i*2+2], 'little')
                        b.extend(bytearray(n.to_bytes(4, 'little')))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load32x2_s:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(2):
                        n = int.from_bytes(a[i*4:i*4+4], 'little')
                        n = n - ((n & 0x80000000) << 1)
                        b.extend(bytearray(n.to_bytes(8, 'little', signed=True)))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load32x2_u:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = bytearray()
                    for i in range(2):
                        n = int.from_bytes(a[i*4:i*4+4], 'little')
                        b.extend(bytearray(n.to_bytes(8, 'little')))
                    self.stack.value.append(ValInst.from_v128(b))
                case pywasm.opcode.v128_load8_splat:
                    a = self.evaluate_mem_load(instr.args[1], 1)
                    self.stack.value.append(ValInst.from_v128(a * 16))
                case pywasm.opcode.v128_load16_splat:
                    a = self.evaluate_mem_load(instr.args[1], 2)
                    self.stack.value.append(ValInst.from_v128(a * 8))
                case pywasm.opcode.v128_load32_splat:
                    a = self.evaluate_mem_load(instr.args[1], 4)
                    self.stack.value.append(ValInst.from_v128(a * 4))
                case pywasm.opcode.v128_load64_splat:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    self.stack.value.append(ValInst.from_v128(a * 2))
                case pywasm.opcode.v128_store:
                    self.evaluate_mem_save(instr.args[1], 16)
                case pywasm.opcode.v128_const:
                    a = ValInst.from_v128(instr.args[0])
                    self.stack.value.append(a)
                case pywasm.opcode.i8x16_shuffle:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = a + b
                    d = [c[instr.args[i]] for i in range(16)]
                    e = ValInst.from_v128_i8(d)
                    self.stack.value.append(e)
                case pywasm.opcode.i8x16_swizzle:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [a[b[i]] if b[i] < 16 else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_splat:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_v128_i8([pywasm.arith.i8.fit(a)] * 16)
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_splat:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_v128_i16([pywasm.arith.i16.fit(a)] * 8)
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_splat:
                    a = self.stack.value.pop().into_i32()
                    b = ValInst.from_v128_i32([a] * 4)
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_splat:
                    a = self.stack.value.pop().into_i64()
                    b = ValInst.from_v128_i64([a] * 2)
                    self.stack.value.append(b)
                case pywasm.opcode.f32x4_splat:
                    a = self.stack.value.pop().data[0:4]
                    b = ValInst.from_v128(a * 4)
                    self.stack.value.append(b)
                case pywasm.opcode.f64x2_splat:
                    a = self.stack.value.pop().data[0:8]
                    b = ValInst.from_v128(a * 2)
                    self.stack.value.append(b)
                case pywasm.opcode.i8x16_extract_lane_s:
                    a = self.stack.value.pop().into_v128_i8()
                    b = ValInst.from_i32(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i8x16_extract_lane_u:
                    a = self.stack.value.pop().into_v128_u8()
                    b = ValInst.from_i32(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i8x16_replace_lane:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i8()
                    a[instr.args[0]] = pywasm.arith.i8.fit(b)
                    c = ValInst.from_v128_i8(a)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_extract_lane_s:
                    a = self.stack.value.pop().into_v128_i16()
                    b = ValInst.from_i32(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_extract_lane_u:
                    a = self.stack.value.pop().into_v128_u16()
                    b = ValInst.from_i32(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_replace_lane:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i16()
                    a[instr.args[0]] = pywasm.arith.i16.fit(b)
                    c = ValInst.from_v128_i16(a)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_extract_lane:
                    a = self.stack.value.pop().into_v128_i32()
                    b = ValInst.from_i32(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_replace_lane:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    a[instr.args[0]] = b
                    c = ValInst.from_v128_i32(a)
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_extract_lane:
                    a = self.stack.value.pop().into_v128_i64()
                    b = ValInst.from_i64(a[instr.args[0]])
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_replace_lane:
                    b = self.stack.value.pop().into_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    a[instr.args[0]] = b
                    c = ValInst.from_v128_i64(a)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_extract_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[0]
                    c = ValInst(ValType.f32(), a[b * 4: b * 4 + 4] + bytearray(ValInst.blen - 4))
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_replace_lane:
                    b = self.stack.value.pop().into_u32()
                    a = self.stack.value.pop().into_v128()
                    c = instr.args[0]
                    a[c * 4: c * 4 + 4] = pywasm.arith.u32.into_bytearray(b)
                    d = ValInst(ValType.v128(), a)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_extract_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[0]
                    c = ValInst(ValType.f64(), a[b * 8: b * 8 + 8] + bytearray(ValInst.blen - 8))
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_replace_lane:
                    b = self.stack.value.pop().into_u64()
                    a = self.stack.value.pop().into_v128()
                    c = instr.args[0]
                    a[c * 8: c * 8 + 8] = pywasm.arith.u64.into_bytearray(b)
                    d = ValInst(ValType.v128(), a)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_eq:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] == b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_ne:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] != b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_lt_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] < b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_lt_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [-1 if a[i] < b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_gt_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] > b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_gt_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [-1 if a[i] > b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_le_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_le_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_ge_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_ge_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_eq:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] == b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_ne:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] != b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_lt_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] < b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_lt_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [-1 if a[i] < b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_gt_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] > b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_gt_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [-1 if a[i] > b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_le_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_le_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_ge_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_ge_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_eq:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] == b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_ne:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] != b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_lt_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] < b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_lt_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [-1 if a[i] < b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_gt_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] > b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_gt_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [-1 if a[i] > b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_le_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_le_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_ge_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_ge_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_eq:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] == b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_ne:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] != b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_lt:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] < b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_gt:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] > b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_le:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_ge:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_eq:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] == b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_ne:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] != b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_lt:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] < b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_gt:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] > b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_le:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_ge:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.v128_not:
                    a = self.stack.value.pop().into_v128()
                    b = ValInst.from_v128(bytearray([pywasm.arith.u8.fit(~e) for e in a]))
                    self.stack.value.append(b)
                case pywasm.opcode.v128_and:
                    b = self.stack.value.pop().into_v128()
                    a = self.stack.value.pop().into_v128()
                    c = ValInst.from_v128(bytearray([a[i] & b[i] for i in range(16)]))
                    self.stack.value.append(c)
                case pywasm.opcode.v128_andnot:
                    b = self.stack.value.pop().into_v128()
                    a = self.stack.value.pop().into_v128()
                    c = ValInst.from_v128(bytearray([a[i] & ~b[i] for i in range(16)]))
                    self.stack.value.append(c)
                case pywasm.opcode.v128_or:
                    b = self.stack.value.pop().into_v128()
                    a = self.stack.value.pop().into_v128()
                    c = ValInst.from_v128(bytearray([a[i] | b[i] for i in range(16)]))
                    self.stack.value.append(c)
                case pywasm.opcode.v128_xor:
                    b = self.stack.value.pop().into_v128()
                    a = self.stack.value.pop().into_v128()
                    c = ValInst.from_v128(bytearray([a[i] ^ b[i] for i in range(16)]))
                    self.stack.value.append(c)
                case pywasm.opcode.v128_bitselect:
                    c = self.stack.value.pop().into_v128()
                    b = self.stack.value.pop().into_v128()
                    a = self.stack.value.pop().into_v128()
                    d = ValInst.from_v128(bytearray([(a[i] & c[i]) | (b[i] & ~c[i]) for i in range(16)]))
                    self.stack.value.append(d)
                case pywasm.opcode.v128_any_true:
                    a = self.stack.value.pop().into_v128()
                    b = 1 if any(e != 0 for e in a) else 0
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.v128_load8_lane:
                    a = self.stack.value.pop().into_v128()
                    b = self.evaluate_mem_load(instr.args[1], 1)
                    c = instr.args[2]
                    a[1 * c: 1 * c + 1] = b
                    d = ValInst(ValType.v128(), a + bytearray(ValInst.blen - 16))
                    self.stack.value.append(d)
                case pywasm.opcode.v128_load16_lane:
                    a = self.stack.value.pop().into_v128()
                    b = self.evaluate_mem_load(instr.args[1], 2)
                    c = instr.args[2]
                    a[2 * c: 2 * c + 2] = b
                    d = ValInst(ValType.v128(), a + bytearray(ValInst.blen - 16))
                    self.stack.value.append(d)
                case pywasm.opcode.v128_load32_lane:
                    a = self.stack.value.pop().into_v128()
                    b = self.evaluate_mem_load(instr.args[1], 4)
                    c = instr.args[2]
                    a[4 * c: 4 * c + 4] = b
                    d = ValInst(ValType.v128(), a + bytearray(ValInst.blen - 16))
                    self.stack.value.append(d)
                case pywasm.opcode.v128_load64_lane:
                    a = self.stack.value.pop().into_v128()
                    b = self.evaluate_mem_load(instr.args[1], 8)
                    c = instr.args[2]
                    a[8 * c: 8 * c + 8] = b
                    d = ValInst(ValType.v128(), a + bytearray(ValInst.blen - 16))
                    self.stack.value.append(d)
                case pywasm.opcode.v128_store8_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[2]
                    a[:1] = a[1 * b: 1 * b + 1]
                    self.stack.value.append(ValInst.from_v128(a))
                    self.evaluate_mem_save(instr.args[1], 1)
                case pywasm.opcode.v128_store16_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[2]
                    a[:2] = a[2 * b: 2 * b + 2]
                    self.stack.value.append(ValInst.from_v128(a))
                    self.evaluate_mem_save(instr.args[1], 2)
                case pywasm.opcode.v128_store32_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[2]
                    a[:4] = a[4 * b: 4 * b + 4]
                    self.stack.value.append(ValInst.from_v128(a))
                    self.evaluate_mem_save(instr.args[1], 4)
                case pywasm.opcode.v128_store64_lane:
                    a = self.stack.value.pop().into_v128()
                    b = instr.args[2]
                    a[:8] = a[8 * b: 8 * b + 8]
                    self.stack.value.append(ValInst.from_v128(a))
                    self.evaluate_mem_save(instr.args[1], 8)
                case pywasm.opcode.v128_load32_zero:
                    a = self.evaluate_mem_load(instr.args[1], 4)
                    b = a + bytearray(ValInst.blen - 4)
                    c = ValInst.from_v128(b)
                    self.stack.value.append(c)
                case pywasm.opcode.v128_load64_zero:
                    a = self.evaluate_mem_load(instr.args[1], 8)
                    b = a + bytearray(ValInst.blen - 8)
                    c = ValInst.from_v128(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_demote_f64x2_zero:
                    a = self.stack.value.pop().into_v128_f64()
                    b = a + [0.0, 0.0]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_promote_low_f32x4:
                    a = self.stack.value.pop().into_v128_f32()
                    b = a[:2]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_abs:
                    a = self.stack.value.pop().into_v128_i8()
                    b = [pywasm.arith.i8.fit(abs(e)) for e in a]
                    c = ValInst.from_v128_i8(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_neg:
                    a = self.stack.value.pop().into_v128_i8()
                    b = [pywasm.arith.i8.fit(-e) for e in a]
                    c = ValInst.from_v128_i8(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_popcnt:
                    a = self.stack.value.pop().into_v128_u8()
                    b = [pywasm.arith.u8.popcnt(e) for e in a]
                    c = ValInst.from_v128_u8(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_all_true:
                    a = self.stack.value.pop().into_v128_i8()
                    b = 1 if all(e != 0 for e in a) else 0
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_bitmask:
                    a = self.stack.value.pop().into_v128_i8()
                    b = 0
                    for i in range(16):
                        if a[i] < 0:
                            b |= 1 << i
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_narrow_i16x8_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = a + b
                    d = [pywasm.arith.i8.sat(e) for e in c]
                    e = ValInst.from_v128_i8(d)
                    self.stack.value.append(e)
                case pywasm.opcode.i8x16_narrow_i16x8_u:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = a + b
                    d = [pywasm.arith.u8.sat(e) for e in c]
                    e = ValInst.from_v128_u8(d)
                    self.stack.value.append(e)
                case pywasm.opcode.f32x4_ceil:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.ceil(e)) for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_floor:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.floor(e)) for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_trunc:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.trunc(e)) for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_nearest:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [e if math.isnan(e) or math.isinf(e) else float(round(e)) for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_shl:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i8()
                    c = ValInst.from_v128_i8([pywasm.arith.i8.shl(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_shr_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i8()
                    c = ValInst.from_v128_i8([pywasm.arith.i8.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_shr_u:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_u8()
                    c = ValInst.from_v128_u8([pywasm.arith.u8.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_add:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [pywasm.arith.i8.add(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_add_sat_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [pywasm.arith.i8.add_sat(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_add_sat_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [pywasm.arith.u8.add_sat(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_u8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_sub:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [pywasm.arith.i8.sub(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_sub_sat_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [pywasm.arith.i8.sub_sat(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_sub_sat_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [pywasm.arith.u8.sub_sat(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_u8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_ceil:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.ceil(e)) for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_floor:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.floor(e)) for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_min_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [min(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_min_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [min(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_u8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_max_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [max(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_i8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i8x16_max_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [max(a[i], b[i]) for i in range(16)]
                    d = ValInst.from_v128_u8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_trunc:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [e if math.isnan(e) or math.isinf(e) else float(math.trunc(e)) for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i8x16_avgr_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [(a[i] + b[i] + 1) // 2 for i in range(16)]
                    d = ValInst.from_v128_u8(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_extadd_pairwise_i8x16_s:
                    a = self.stack.value.pop().into_v128_i8()
                    b = [a[i] + a[i+1] for i in range(0, 16, 2)]
                    c = ValInst.from_v128_i16(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_extadd_pairwise_i8x16_u:
                    a = self.stack.value.pop().into_v128_u8()
                    b = [a[i] + a[i+1] for i in range(0, 16, 2)]
                    c = ValInst.from_v128_u16(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_extadd_pairwise_i16x8_s:
                    a = self.stack.value.pop().into_v128_i16()
                    b = [a[i] + a[i+1] for i in range(0, 8, 2)]
                    c = ValInst.from_v128_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_extadd_pairwise_i16x8_u:
                    a = self.stack.value.pop().into_v128_u16()
                    b = [a[i] + a[i+1] for i in range(0, 8, 2)]
                    c = ValInst.from_v128_u32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_abs:
                    a = self.stack.value.pop().into_v128_i16()
                    b = [pywasm.arith.i16.fit(abs(e)) for e in a]
                    c = ValInst.from_v128_i16(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_neg:
                    a = self.stack.value.pop().into_v128_i16()
                    b = [pywasm.arith.i16.fit(-e) for e in a]
                    c = ValInst.from_v128_i16(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_q15mulr_sat_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.sat((a[i] * b[i] + 0x4000) >> 15) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_all_true:
                    a = self.stack.value.pop().into_v128_i16()
                    b = 1 if all(e != 0 for e in a) else 0
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_bitmask:
                    a = self.stack.value.pop().into_v128_i16()
                    b = 0
                    for i in range(8):
                        if a[i] < 0:
                            b |= 1 << i
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_narrow_i32x4_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = a + b
                    d = [pywasm.arith.i16.sat(e) for e in c]
                    e = ValInst.from_v128_i16(d)
                    self.stack.value.append(e)
                case pywasm.opcode.i16x8_narrow_i32x4_u:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = a + b
                    d = [pywasm.arith.u16.sat(e) for e in c]
                    e = ValInst.from_v128_u16(d)
                    self.stack.value.append(e)
                case pywasm.opcode.i16x8_extend_low_i8x16_s:
                    a = self.stack.value.pop().into_v128_i8()[:8]
                    b = ValInst.from_v128_i16(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_extend_high_i8x16_s:
                    a = self.stack.value.pop().into_v128_i8()[8:]
                    b = ValInst.from_v128_i16(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_extend_low_i8x16_u:
                    a = self.stack.value.pop().into_v128_u8()[:8]
                    b = ValInst.from_v128_i16(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_extend_high_i8x16_u:
                    a = self.stack.value.pop().into_v128_u8()[8:]
                    b = ValInst.from_v128_i16(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i16x8_shl:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i16()
                    c = ValInst.from_v128_i16([pywasm.arith.i16.shl(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_shr_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i16()
                    c = ValInst.from_v128_i16([pywasm.arith.i16.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_shr_u:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_u16()
                    c = ValInst.from_v128_u16([pywasm.arith.u16.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_add:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.add(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_add_sat_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.add_sat(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_add_sat_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [pywasm.arith.u16.add_sat(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_sub:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.sub(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_sub_sat_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.sub_sat(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_sub_sat_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [pywasm.arith.u16.sub_sat(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_nearest:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [e if math.isnan(e) or math.isinf(e) else float(round(e)) for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i16x8_mul:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i16.mul(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_min_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [min(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_min_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [min(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_max_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [max(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_max_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [max(a[i], b[i]) for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_avgr_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [(a[i] + b[i] + 1) // 2 for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_extmul_low_i8x16_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [a[i] * b[i] for i in range(8)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_extmul_high_i8x16_s:
                    b = self.stack.value.pop().into_v128_i8()
                    a = self.stack.value.pop().into_v128_i8()
                    c = [a[i] * b[i] for i in range(8, 16)]
                    d = ValInst.from_v128_i16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_extmul_low_i8x16_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [a[i] * b[i] for i in range(8)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i16x8_extmul_high_i8x16_u:
                    b = self.stack.value.pop().into_v128_u8()
                    a = self.stack.value.pop().into_v128_u8()
                    c = [a[i] * b[i] for i in range(8, 16)]
                    d = ValInst.from_v128_u16(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_abs:
                    a = self.stack.value.pop().into_v128_i32()
                    b = [pywasm.arith.i32.fit(abs(e)) for e in a]
                    c = ValInst.from_v128_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_neg:
                    a = self.stack.value.pop().into_v128_i32()
                    b = [pywasm.arith.i32.fit(-e) for e in a]
                    c = ValInst.from_v128_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_all_true:
                    a = self.stack.value.pop().into_v128_i32()
                    b = 1 if all(e != 0 for e in a) else 0
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_bitmask:
                    a = self.stack.value.pop().into_v128_i32()
                    b = 0
                    for i in range(4):
                        if a[i] < 0:
                            b |= 1 << i
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_extend_low_i16x8_s:
                    a = self.stack.value.pop().into_v128_i16()[:4]
                    b = ValInst.from_v128_i32(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_extend_high_i16x8_s:
                    a = self.stack.value.pop().into_v128_i16()[4:]
                    b = ValInst.from_v128_i32(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_extend_low_i16x8_u:
                    a = self.stack.value.pop().into_v128_u16()[:4]
                    b = ValInst.from_v128_i32(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_extend_high_i16x8_u:
                    a = self.stack.value.pop().into_v128_u16()[4:]
                    b = ValInst.from_v128_i32(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_shl:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = ValInst.from_v128_i32([pywasm.arith.i32.shl(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_shr_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = ValInst.from_v128_i32([pywasm.arith.i32.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_shr_u:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = ValInst.from_v128_u32([pywasm.arith.u32.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i32x4_add:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [pywasm.arith.i32.add(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_sub:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [pywasm.arith.i32.sub(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_mul:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [pywasm.arith.i32.mul(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_min_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [min(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_min_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [min(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_max_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [max(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_max_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [max(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_dot_i16x8_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [pywasm.arith.i32.fit(a[i*2] * b[i*2] + a[i*2+1] * b[i*2+1]) for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_extmul_low_i16x8_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [a[i] * b[i] for i in range(4)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_extmul_high_i16x8_s:
                    b = self.stack.value.pop().into_v128_i16()
                    a = self.stack.value.pop().into_v128_i16()
                    c = [a[i] * b[i] for i in range(4, 8)]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_extmul_low_i16x8_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [a[i] * b[i] for i in range(4)]
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_extmul_high_i16x8_u:
                    b = self.stack.value.pop().into_v128_u16()
                    a = self.stack.value.pop().into_v128_u16()
                    c = [a[i] * b[i] for i in range(4, 8)]
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_abs:
                    a = self.stack.value.pop().into_v128_i64()
                    b = [pywasm.arith.i64.fit(abs(e)) for e in a]
                    c = ValInst.from_v128_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_neg:
                    a = self.stack.value.pop().into_v128_i64()
                    b = [pywasm.arith.i64.fit(-e) for e in a]
                    c = ValInst.from_v128_i64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_all_true:
                    a = self.stack.value.pop().into_v128_i64()
                    b = 1 if all(e != 0 for e in a) else 0
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_bitmask:
                    a = self.stack.value.pop().into_v128_i64()
                    b = 0
                    for i in range(2):
                        if a[i] < 0:
                            b |= 1 << i
                    c = ValInst.from_i32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_extend_low_i32x4_s:
                    a = self.stack.value.pop().into_v128_i32()[:2]
                    b = ValInst.from_v128_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_extend_high_i32x4_s:
                    a = self.stack.value.pop().into_v128_i32()[2:]
                    b = ValInst.from_v128_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_extend_low_i32x4_u:
                    a = self.stack.value.pop().into_v128_u32()[:2]
                    b = ValInst.from_v128_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_extend_high_i32x4_u:
                    a = self.stack.value.pop().into_v128_u32()[2:]
                    b = ValInst.from_v128_i64(a)
                    self.stack.value.append(b)
                case pywasm.opcode.i64x2_shl:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i64()
                    c = ValInst.from_v128_i64([pywasm.arith.i64.shl(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_shr_s:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_i64()
                    c = ValInst.from_v128_i64([pywasm.arith.i64.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_shr_u:
                    b = self.stack.value.pop().into_i32()
                    a = self.stack.value.pop().into_v128_u64()
                    c = ValInst.from_v128_u64([pywasm.arith.u64.shr(e, b) for e in a])
                    self.stack.value.append(c)
                case pywasm.opcode.i64x2_add:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [pywasm.arith.i64.add(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_sub:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [pywasm.arith.i64.sub(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_mul:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [pywasm.arith.i64.mul(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_eq:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] == b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_ne:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] != b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_lt_s:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] < b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_gt_s:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] > b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_le_s:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] <= b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_ge_s:
                    b = self.stack.value.pop().into_v128_i64()
                    a = self.stack.value.pop().into_v128_i64()
                    c = [-1 if a[i] >= b[i] else 0 for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_extmul_low_i32x4_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [a[i] * b[i] for i in range(2)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_extmul_high_i32x4_s:
                    b = self.stack.value.pop().into_v128_i32()
                    a = self.stack.value.pop().into_v128_i32()
                    c = [a[i] * b[i] for i in range(2, 4)]
                    d = ValInst.from_v128_i64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_extmul_low_i32x4_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [a[i] * b[i] for i in range(2)]
                    d = ValInst.from_v128_u64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i64x2_extmul_high_i32x4_u:
                    b = self.stack.value.pop().into_v128_u32()
                    a = self.stack.value.pop().into_v128_u32()
                    c = [a[i] * b[i] for i in range(2, 4)]
                    d = ValInst.from_v128_u64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_abs:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [abs(e) for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_neg:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [-e for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_sqrt:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [math.sqrt(e) if e >= 0 else math.nan for e in a]
                    c = ValInst.from_v128_f32(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f32x4_add:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [a[i] + b[i] for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_sub:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [a[i] - b[i] for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_mul:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [a[i] * b[i] for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_div:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [pywasm.arith.f32.div(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_min:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [pywasm.arith.f32.min(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_max:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [pywasm.arith.f32.max(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_pmin:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [min(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_pmax:
                    b = self.stack.value.pop().into_v128_f32()
                    a = self.stack.value.pop().into_v128_f32()
                    c = [max(a[i], b[i]) for i in range(4)]
                    d = ValInst.from_v128_f32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_abs:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [abs(e) for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_neg:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [-e for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_sqrt:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [math.sqrt(e) if e >= 0 else math.nan for e in a]
                    c = ValInst.from_v128_f64(b)
                    self.stack.value.append(c)
                case pywasm.opcode.f64x2_add:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [a[i] + b[i] for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_sub:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [a[i] - b[i] for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_mul:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [a[i] * b[i] for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_div:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [pywasm.arith.f64.div(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_min:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [pywasm.arith.f64.min(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_max:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [pywasm.arith.f64.max(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_pmin:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [min(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_pmax:
                    b = self.stack.value.pop().into_v128_f64()
                    a = self.stack.value.pop().into_v128_f64()
                    c = [max(a[i], b[i]) for i in range(2)]
                    d = ValInst.from_v128_f64(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_trunc_sat_f32x4_s:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [0 if math.isnan(e) else e for e in a]
                    c = [int(max(pywasm.arith.i32.min, min(e, pywasm.arith.i32.max))) for e in b]
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_trunc_sat_f32x4_u:
                    a = self.stack.value.pop().into_v128_f32()
                    b = [0 if math.isnan(e) else e for e in a]
                    c = [int(max(pywasm.arith.u32.min, min(e, pywasm.arith.u32.max))) for e in b]
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f32x4_convert_i32x4_s:
                    a = self.stack.value.pop().into_v128_i32()
                    b = ValInst.from_v128_f32([float(e) for e in a])
                    self.stack.value.append(b)
                case pywasm.opcode.f32x4_convert_i32x4_u:
                    a = self.stack.value.pop().into_v128_u32()
                    b = ValInst.from_v128_f32([float(e) for e in a])
                    self.stack.value.append(b)
                case pywasm.opcode.i32x4_trunc_sat_f64x2_s_zero:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [0 if math.isnan(e) else e for e in a]
                    c = [int(max(pywasm.arith.i32.min, min(e, pywasm.arith.i32.max))) for e in b]
                    c.extend([0, 0])
                    d = ValInst.from_v128_i32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.i32x4_trunc_sat_f64x2_u_zero:
                    a = self.stack.value.pop().into_v128_f64()
                    b = [0 if math.isnan(e) else e for e in a]
                    c = [int(max(pywasm.arith.u32.min, min(e, pywasm.arith.u32.max))) for e in b]
                    c.extend([0, 0])
                    d = ValInst.from_v128_u32(c)
                    self.stack.value.append(d)
                case pywasm.opcode.f64x2_convert_low_i32x4_s:
                    a = self.stack.value.pop().into_v128_i32()[:2]
                    b = ValInst.from_v128_f64([float(e) for e in a])
                    self.stack.value.append(b)
                case pywasm.opcode.f64x2_convert_low_i32x4_u:
                    a = self.stack.value.pop().into_v128_u32()[:2]
                    b = ValInst.from_v128_f64([float(e) for e in a])
                    self.stack.value.append(b)
                case _:
                    assert 0


class Runtime:
    # A webassembly runtime manages Store, stack, and other runtime structure. They forming the WebAssembly abstract.

    def __init__(self) -> None:
        self.machine = Machine()
        self.imports: typing.Dict[str, typing.Dict[str, Extern]] = {}

    def allocate_func_host(self, type: FuncType, func: typing.Callable) -> Extern:
        # Allocate new instances of host functions.
        # Host functions are never allocated by the webassembly semantics itself, but may be allocated by the embedder.
        return Extern(0x00, self.machine.store.allocate_func_host(FuncHost(type, func)))

    def allocate_table(self, type: TableType) -> Extern:
        # Allocate new instances of tables.
        return Extern(0x01, self.machine.store.allocate_table(type))

    def allocate_memory(self, type: MemType) -> Extern:
        # Allocate new instances of memory.
        return Extern(0x02, self.machine.store.allocate_memory(type))

    def allocate_global(self, type: GlobalType, data: ValInst) -> Extern:
        # Allocate new instances of global.
        return Extern(0x03, self.machine.store.allocate_global(type, data))

    def exported_memory(self, module: ModuleInst, name: str) -> MemInst:
        # Get an exportable memory instance.
        inst = [e for e in module.exps if e.name == name][0].data
        assert inst.kind == 0x02
        addr = inst.data
        return self.machine.store.mems[addr]

    def exported_global(self, module: ModuleInst, name: str) -> GlobalInst:
        # Get an exportable global instance.
        inst = [e for e in module.exps if e.name == name][0].data
        assert inst.kind == 0x03
        addr = inst.data
        return self.machine.store.glob[addr]

    def instance(self, module: ModuleDesc) -> ModuleInst:
        # A module is instantiated with a list of external values supplying the required imports. Instantiation checks
        # that the module is valid and the provided imports match the declared types, and may fail with an error
        # otherwise. Instantiation can also result in a trap from initializing a table or memory from an active
        # segment or from executing the start function. It is up to the embedder to define how such conditions are
        # reported.
        extern: typing.List[Extern] = []
        for e in module.imps:
            extern.append(self.imports[e.module][e.name])
        return self.machine.instance(module, extern)

    def instance_from_file(self, path: str) -> ModuleInst:
        # Instantiated a module from a local file.
        with open(path, 'rb') as f:
            return self.instance(ModuleDesc.from_reader(f))

    def invocate(
        self,
        module: ModuleInst,
        func: str,
        args: typing.List[int | float | bytearray]
    ) -> typing.List:
        # Once a module has been instantiated, any exported function can be invoked externally via its function address
        # in the store and an appropriate list of argument values.
        func_addr = [e for e in module.exps if e.name == func][0].data.data
        func_inst = self.machine.store.func[func_addr]
        assert len(func_inst.type.args) == len(args)
        func_args = [ValInst.from_all(a, b) for a, b in zip(func_inst.type.args, args)]
        func_rets = self.machine.invocate(func_addr, func_args)
        rets = [e.into_all() for e in func_rets]
        return rets
