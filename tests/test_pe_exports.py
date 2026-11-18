"""Export-table copying for the SDK proxy, on synthetic PE files."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import pe_exports  # noqa: E402


def stub(sections=1, trailing=b''):
    """A minimal PE32+ DLL: headers (0x400) and one 0x200-byte code section."""
    b = bytearray(0x400 + 0x200 * sections)
    b[:2] = b'MZ'; struct.pack_into('<I', b, 0x3C, 0x80)
    b[0x80:0x84] = b'PE\0\0'
    coff = 0x84
    struct.pack_into('<HHIIIHH', b, coff, 0x8664, sections, 0, 0, 0, 240, 0x2022)
    opt = coff + 20
    struct.pack_into('<H', b, opt, 0x20B)
    struct.pack_into('<II', b, opt + 32, 0x1000, 0x200)            # alignments
    struct.pack_into('<II', b, opt + 56, 0x1000 * (sections + 1), 0x400)  # SizeOfImage, SizeOfHeaders
    struct.pack_into('<I', b, opt + 108, 16)
    for i in range(sections):
        struct.pack_into('<8sIIII', b, opt + 240 + 40 * i, b'.text', 0x10, 0x1000 * (i + 1), 0x200, 0x400 + 0x200 * i)
    return bytes(b) + trailing


class PEExportTests(unittest.TestCase):
    def test_forwarders_round_trip_with_gaps_and_ordinal_only(self):
        table = {5: 'b_second', 6: None, 8: 'a_first', 9: '??0Thing@@QEAA@XZ'}
        out = pe_exports.add_forwarders(stub(), 'OrbbecSDK.dll', 'OrbbecSDK-stock', (5, table))
        self.assertEqual(pe_exports.read_exports(out), (5, table))
        self.assertIn(b'OrbbecSDK-stock.#6\0', out)
        self.assertIn(b'OrbbecSDK-stock.a_first\0', out)
        # A second pass must not stack another export table.
        with self.assertRaisesRegex(pe_exports.PEError, 'already has'):
            pe_exports.add_forwarders(out, 'x.dll', 'y', (1, {1: 'z'}))

    def test_stub_without_exports_reads_empty(self):
        self.assertEqual(pe_exports.read_exports(stub()), (1, {}))

    def test_refuses_malformed_or_unsuitable_input(self):
        for data in (b'', b'MZ' + b'\0' * 100, stub()[:0x90]):
            with self.assertRaises(pe_exports.PEError):
                pe_exports.read_exports(data)
        with self.assertRaisesRegex(pe_exports.PEError, 'trailing'):
            pe_exports.add_forwarders(stub(trailing=b'sig'), 'a.dll', 'b', (1, {1: 'f'}))
        with self.assertRaisesRegex(pe_exports.PEError, 'exports nothing'):
            pe_exports.add_forwarders(stub(), 'a.dll', 'b', (1, {}))

    def test_rejects_hostile_export_directory(self):
        table = {1: 'ok'}
        out = bytearray(pe_exports.add_forwarders(stub(), 'a.dll', 'b', (1, table)))
        edata = 0x600  # appended section's file offset
        struct.pack_into('<I', out, edata + 20, 10**6)  # NumberOfFunctions
        with self.assertRaisesRegex(pe_exports.PEError, 'implausible|outside'):
            pe_exports.read_exports(bytes(out))


if __name__ == '__main__':
    unittest.main()
