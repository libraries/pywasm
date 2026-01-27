import typing


class _U:
    @staticmethod
    def encode(i: int) -> bytearray:
        # Encode the int i using unsigned leb128 and return the encoded bytearray.
        assert i >= 0
        r = bytearray()
        while True:
            b = i & 0x7f
            i = i >> 7
            if i == 0:
                r.append(b)
                return r
            r.append(0x80 | b)

    @staticmethod
    def decode(b: bytearray) -> int:
        # Decode the unsigned leb128 encoded bytearray.
        assert len(b) > 0
        r = 0
        for i, e in enumerate(b):
            r = r + ((e & 0x7f) << (i * 7))
        return r

    @staticmethod
    def decode_reader(r: typing.BinaryIO) -> typing.Tuple[int, int]:
        # Decode the unsigned leb128 encoded from a reader, it will return two values, the actual number and the number
        # of bytes read.
        a = bytearray()
        while True:
            b = r.read(1)
            if len(b) != 1:
                raise EOFError
            b = ord(b)
            a.append(b)
            if (b & 0x80) == 0:
                break
        return _U.decode(a), len(a)


class _I:
    @staticmethod
    def encode(i: int) -> bytearray:
        # Encode the int i using signed leb128 and return the encoded bytearray.
        r = bytearray()
        while True:
            b = i & 0x7f
            i = i >> 7
            if (i == 0 and b & 0x40 == 0) or (i == -1 and b & 0x40 != 0):
                r.append(b)
                return r
            r.append(0x80 | b)

    @staticmethod
    def decode(b: bytearray) -> int:
        # Decode the signed leb128 encoded bytearray.
        assert len(b) > 0
        r = 0
        for i, e in enumerate(b):
            r = r + ((e & 0x7f) << (i * 7))
        i = len(b) - 1
        e = b[i]
        if e & 0x40 != 0:
            r |= - (1 << (i * 7) + 7)
        return r

    @staticmethod
    def decode_reader(r: typing.BinaryIO) -> typing.Tuple[int, int]:
        # Decode the signed leb128 encoded from a reader, it will return two values, the actual number and the number
        # of bytes read.
        a = bytearray()
        while True:
            b = r.read(1)
            if len(b) != 1:
                raise EOFError
            b = ord(b)
            a.append(b)
            if (b & 0x80) == 0:
                break
        return _I.decode(a), len(a)


u = _U()
i = _I()
