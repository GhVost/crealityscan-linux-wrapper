"""Read a PE32+ DLL's export table and give a stub DLL a matching forwarder table.

The SDK proxy must export exactly what the installed OrbbecSDK.dll exports, each
forwarding to the renamed original. Generating that table at install time from
the installed DLL makes the proxy independent of the CrealityScan version, with
no compiler on the user's machine. The DLL read here comes from the vendor
installer, so every offset is bounds-checked and sizes are capped.
"""
import struct

MAX_EXPORTS = 65536
MAX_NAME = 1024
DIR_EXPORT = 0


class PEError(ValueError):
    pass


def _u16(b, o):
    if o < 0 or o + 2 > len(b): raise PEError('truncated PE')
    return struct.unpack_from('<H', b, o)[0]


def _u32(b, o):
    if o < 0 or o + 4 > len(b): raise PEError('truncated PE')
    return struct.unpack_from('<I', b, o)[0]


def _align(n, a):
    return (n + a - 1) // a * a


class _PE:
    def __init__(self, data):
        self.b = data
        if data[:2] != b'MZ': raise PEError('not a PE file')
        pe = _u32(data, 0x3C)
        if data[pe:pe + 4] != b'PE\0\0': raise PEError('missing PE signature')
        self.coff = pe + 4
        self.nsections = _u16(data, self.coff + 2)
        opt_size = _u16(data, self.coff + 16)
        self.opt = self.coff + 20
        if _u16(data, self.opt) != 0x20B: raise PEError('only 64-bit (PE32+) DLLs are supported')
        self.ndirs = _u32(data, self.opt + 108)
        self.dirs = self.opt + 112
        if self.ndirs < 1 or self.dirs + 8 * self.ndirs > self.opt + opt_size: raise PEError('bad data directories')
        self.sections = self.opt + opt_size
        if self.nsections > 96: raise PEError('too many sections')
        self.table = []
        for i in range(self.nsections):
            s = self.sections + 40 * i
            vsize, va, rsize, rptr = (_u32(data, s + 8), _u32(data, s + 12), _u32(data, s + 16), _u32(data, s + 20))
            self.table.append((va, max(vsize, rsize), rptr, rsize))

    def offset(self, rva, size=1):
        for va, vsize, rptr, rsize in self.table:
            if va <= rva and rva + size <= va + min(vsize, rsize):
                off = rptr + rva - va
                if off + size > len(self.b): raise PEError('section beyond end of file')
                return off
        raise PEError(f'RVA {rva:#x} is outside the file')

    def cstring(self, rva):
        off = self.offset(rva)
        end = self.b.find(b'\0', off, off + MAX_NAME)
        if end < 0: raise PEError('unterminated or overlong export name')
        name = self.b[off:end]
        if not name or any(c < 0x21 or c > 0x7E for c in name): raise PEError('unexpected characters in export name')
        return name.decode('ascii')


def read_exports(data):
    """Return (ordinal_base, {ordinal: name or None}) for every exported function."""
    pe = _PE(data)
    rva, size = _u32(data, pe.dirs), _u32(data, pe.dirs + 4)
    if not rva or not size: return 1, {}
    d = pe.offset(rva, 40)
    base, nfuncs, nnames = _u32(data, d + 16), _u32(data, d + 20), _u32(data, d + 24)
    funcs, names, ords = _u32(data, d + 28), _u32(data, d + 32), _u32(data, d + 36)
    if nfuncs > MAX_EXPORTS or nnames > nfuncs: raise PEError('implausible export counts')
    eat = pe.offset(funcs, 4 * nfuncs) if nfuncs else 0
    result = {base + i: None for i in range(nfuncs) if _u32(data, eat + 4 * i)}
    if nnames:
        name_tab, ord_tab = pe.offset(names, 4 * nnames), pe.offset(ords, 2 * nnames)
        for i in range(nnames):
            index = _u16(data, ord_tab + 2 * i)
            if index >= nfuncs: raise PEError('export name points past the function table')
            if base + index in result:
                result[base + index] = pe.cstring(_u32(data, name_tab + 4 * i))
    return base, result


def add_forwarders(stub, dll_name, target, exports):
    """Return `stub` with a new .edata section exporting `exports` ((base, {ord: name})),
    each forwarded to the same name (or ordinal) in DLL `target`."""
    base, table = exports
    if not table: raise PEError('the original DLL exports nothing')
    pe = _PE(stub)
    data = bytearray(stub)
    if _u32(data, pe.dirs) or _u32(data, pe.dirs + 4): raise PEError('stub already has an export table')
    sect_align, file_align = _u32(data, pe.opt + 32), _u32(data, pe.opt + 36)
    headers = _u32(data, pe.opt + 60)
    new_header = pe.sections + 40 * pe.nsections
    first_raw = min((r for _, _, r, rs in pe.table if rs), default=headers)
    if new_header + 40 > min(headers, first_raw): raise PEError('no room for another section header')
    raw_end = max((r + rs for _, _, r, rs in pe.table), default=headers)
    if raw_end != len(data): raise PEError('stub has trailing data; refusing to append')

    va = _align(max(v + s for v, s, _, _ in pe.table), sect_align)
    first, last = min(table), max(table)
    if first < base: raise PEError('ordinal below base')
    count = last - base + 1
    named = sorted((n.encode(), o) for o, n in table.items() if n)

    # Layout: directory | EAT | name pointers | name ordinals | strings
    eat_off = 40
    names_off = eat_off + 4 * count
    ords_off = names_off + 4 * len(named)
    strings = bytearray()
    str_base = ords_off + 2 * len(named)

    def add_string(s):
        rva = va + str_base + len(strings)
        strings.extend(s + b'\0')
        return rva

    dll_rva = add_string(dll_name.encode())
    eat = [0] * count
    for o, n in table.items():
        eat[o - base] = add_string(f'{target}.{n}'.encode() if n else f'{target}.#{o}'.encode())
    name_rvas = [add_string(n) for n, _ in named]

    body = bytearray(struct.pack('<IIHHIIIIIII', 0, 0, 0, 0, dll_rva, base, count, len(named),
                                 va + eat_off, va + names_off, va + ords_off))
    body += struct.pack(f'<{count}I', *eat)
    body += struct.pack(f'<{len(named)}I', *name_rvas)
    body += struct.pack(f'<{len(named)}H', *(o - base for _, o in named))
    body += strings
    vsize = len(body)
    raw = bytes(body) + b'\0' * (_align(vsize, file_align) - vsize)

    struct.pack_into('<8sIIIIIIHHI', data, new_header, b'.edata', vsize, va, len(raw), len(data),
                     0, 0, 0, 0, 0x40000040)  # initialized data, readable
    struct.pack_into('<H', data, pe.coff + 2, pe.nsections + 1)
    struct.pack_into('<I', data, pe.opt + 8, _u32(data, pe.opt + 8) + len(raw))  # SizeOfInitializedData
    struct.pack_into('<I', data, pe.opt + 56, _align(va + vsize, sect_align))  # SizeOfImage
    struct.pack_into('<I', data, pe.opt + 64, 0)  # CheckSum: not required for DLLs
    struct.pack_into('<II', data, pe.dirs, va, vsize)
    return bytes(data) + raw
