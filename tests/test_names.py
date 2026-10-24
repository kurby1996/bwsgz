import unittest
from pathlib import Path
from trainer.names import names_for_rom, rename_in_rom, resolve_name, encode_name, NAME_BASE, NAME_STRIDE, NAME_BYTES

ROM = Path(__file__).resolve().parents[1] / '霸王三国志-免登录版/roms/三國志II-霸王三国志.md'


class NameTests(unittest.TestCase):
    def test_names_roundtrip_preserves_other_bytes(self):
        rom = ROM.read_bytes()
        names = names_for_rom(rom)
        self.assertEqual(names[:3], ['曹操', '刘备', '孙坚'])
        self.assertEqual(len(names), 352)
        for index, name in enumerate(names):
            self.assertNotIn('〔', name)
            edited = bytearray(rom)
            rename_in_rom(edited, index, name)
            self.assertEqual(resolve_name(edited,index), name)
            offset = NAME_BASE + index*NAME_STRIDE
            self.assertEqual(edited[:offset], rom[:offset])
            self.assertEqual(edited[offset+NAME_BYTES:], rom[offset+NAME_BYTES:])

    def test_bad_names_and_traditional(self):
        rom = ROM.read_bytes()
        self.assertEqual(encode_name(rom, '劉備'), encode_name(rom, '刘备'))
        for text in ('', '曹操刘备', '🙂', 'A'):
            with self.assertRaises(ValueError):
                encode_name(rom,text)


if __name__=='__main__':
    unittest.main()
