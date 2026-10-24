"""人工合成 GST 布局测试；不冒充真实游戏存档运行验证。"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trainer.model import GameImage, GST_SIZE, RAM_OFFSET, OFFICER_BASE, PROVINCE_BASE, COUNTRY_BASE, STATS_BASE, NATIVE_HEADER

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / '霸王三国志-免登录版/roms/三國志II-霸王三国志.md'


def synthetic_gst():
    data = bytearray(GST_SIZE)
    data[:4] = b'GST@'

    def put(address, value, width=1):
        for n, byte in enumerate(value.to_bytes(width, 'big')):
            data[RAM_OFFSET + address+n] = byte

    for i in range(216):
        a = OFFICER_BASE+i*24
        put(a+9, 255)
        put(a+0x16, 65535, 2)
    for i in range(41):
        put(PROVINCE_BASE+i*34+22, 255)
    put(COUNTRY_BASE, 0xFF0000+OFFICER_BASE, 4)
    put(COUNTRY_BASE+4, 0xFF0000+PROVINCE_BASE, 4)
    put(PROVINCE_BASE+4, 0xFF0000+OFFICER_BASE, 4)
    put(PROVINCE_BASE+22, 0)
    put(OFFICER_BASE+9, 0)
    put(OFFICER_BASE+0x16, 7, 2)
    put(OFFICER_BASE+6, 90)
    put(OFFICER_BASE+7, 80)
    put(OFFICER_BASE+8, 70)
    put(OFFICER_BASE+10, 100)
    put(OFFICER_BASE+14, 73, 2)
    put(OFFICER_BASE+16, 4321, 2)
    put(OFFICER_BASE+18, 42)
    put(PROVINCE_BASE+16, 12345, 2)
    return data, put


def section(number, payload):
    return number.to_bytes(2, 'big') + len(payload).to_bytes(4, 'big') + payload


def synthetic_native(gst):
    ram = gst[RAM_OFFSET:RAM_OFFSET+65536]
    return NATIVE_HEADER + section(1, b'CPU unchanged\x00') + section(10, b'\x40' + ram) + section(0xFFFF, b'unknown section preserved')


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / '.rea_tmp')
        self.directory = Path(self.tmp.name)
        self.path = self.directory / 'synthetic.gs0'
        self.fixture, self.put = synthetic_gst()
        self.path.write_bytes(self.fixture)

    def tearDown(self):
        self.tmp.cleanup()

    def test_synthetic_big_endian_read(self):
        game = GameImage(self.path, ROM)
        self.assertFalse(game.ram_swapped)
        self.assertEqual(self.fixture[RAM_OFFSET+COUNTRY_BASE:RAM_OFFSET+COUNTRY_BASE+4],bytes.fromhex('00ff1052'))
        self.assertEqual(self.fixture[RAM_OFFSET+PROVINCE_BASE+16:RAM_OFFSET+PROVINCE_BASE+18],bytes.fromhex('3039'))
        officer = game.get_officers()[0]
        self.assertEqual((officer['intelligence'], officer['war'], officer['charm']), (90, 80, 70))
        self.assertEqual((officer['troops'], officer['arms'], officer['province'], officer['name_id']), (73, 4321, 0, 7))
        self.assertEqual(officer['training'],42)
        self.assertEqual(game.get_provinces()[0]['gold'], 12345)
        self.assertEqual(game.get_countries()[0]['officer_indices'], [0])

    def test_only_selected_bytes_change(self):
        game = GameImage(self.path)
        before = bytes(game.data)
        game.update_officer(0, {'war': 100, 'troops': 100, 'training':100})
        allowed = {RAM_OFFSET+OFFICER_BASE+offset for offset in (7,14,15,18)}
        actual = {i for i, (a,b) in enumerate(zip(before, game.data)) if a != b}
        self.assertTrue(actual)
        self.assertTrue(actual <= allowed)
        out = self.directory / 'edited.gs0'
        game.save(out)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(GameImage(out).get_officers()[0]['troops'], 100)
        self.assertEqual(GameImage(out).get_officers()[0]['training'],100)

    def test_resources_boundary_and_backup(self):
        game = GameImage(self.path)
        game.update_province(40, {'gold': 30000, 'food': 0, 'population': 65535})
        game.save(self.path)
        self.assertEqual(game.last_backup.read_bytes(), self.fixture)
        last = GameImage(self.path).get_provinces()[40]
        self.assertEqual((last['gold'], last['food'], last['population']), (30000, 0, 65535))

    def test_validation_atomic(self):
        game = GameImage(self.path)
        before = bytes(game.data)
        for changes in ({'war':101}, {'loyalty':-1}, {'arms':10001}, {'troops':101}, {'training':101}, {'training':-1}, {'training':True}, {'war':True}, {'war':1.5}, {'nation':1}, {'war':80,'charm':200}):
            with self.assertRaises(ValueError):
                game.update_officer(0, changes)
            self.assertEqual(bytes(game.data), before)
        for index in (-1,216,True,'0'):
            with self.assertRaises(ValueError):
                game.update_officer(index, {'war': 80})
        with self.assertRaises(ValueError):
            game.update_province(0, {'gold':30001})

    def test_opening_and_corrupt_states_rejected(self):
        blank = bytearray(GST_SIZE)
        blank[:4] = b'GST@'
        self.path.write_bytes(blank)
        with self.assertRaisesRegex(ValueError, '开场'):
            GameImage(self.path)
        self.path.write_bytes(self.fixture[:-1])
        with self.assertRaises(ValueError):
            GameImage(self.path)
        self.put(COUNTRY_BASE, 0xFF1053, 4)
        self.path.write_bytes(self.fixture)
        with self.assertRaisesRegex(ValueError, '指针'):
            GameImage(self.path)

    def test_cycle_rejected(self):
        self.put(OFFICER_BASE, 0xFF0000+OFFICER_BASE, 4)
        self.path.write_bytes(self.fixture)
        with self.assertRaisesRegex(ValueError, '循环'):
            GameImage(self.path)

    def test_rom_edit_reload_and_checksum(self):
        game = GameImage(ROM)
        before = bytes(game.data)
        self.assertEqual(len(game.get_officers()),352)
        game.update_officer(351, {'intelligence':100,'war':100,'charm':100})
        out = self.directory / 'edited.md'
        game.save(out)
        reloaded = GameImage(out)
        self.assertEqual(reloaded.get_officers()[351]['charm'],100)
        allowed = {0x18E,0x18F,STATS_BASE+351*3,STATS_BASE+351*3+1,STATS_BASE+351*3+2}
        self.assertTrue({i for i,(a,b) in enumerate(zip(before,game.data)) if a != b} <= allowed)
        checksum = sum(int.from_bytes(game.data[i:i+2],'big') for i in range(0x200,len(game.data),2)) & 65535
        self.assertEqual(int.from_bytes(game.data[0x18E:0x190],'big'),checksum)
        with self.assertRaises(ValueError):
            game.update_officer(0, {'troops':100})
        with self.assertRaises(ValueError):
            game.update_province(0, {'gold':100})

    def test_wrong_rom_and_unknown_signature_rejected(self):
        corrupt = bytearray(ROM.read_bytes())
        corrupt[0x4000] ^= 1
        path = self.directory/'wrong.md'
        path.write_bytes(corrupt)
        with self.assertRaisesRegex(ValueError,'版本'):
            GameImage(path)
        with self.assertRaises(ValueError):
            GameImage(self.path,path)
        path.write_bytes(b'unknown data')
        with self.assertRaises(ValueError):
            GameImage(path)

    def test_native_big_endian_read_edit_reload(self):
        original = synthetic_native(self.fixture)
        self.path.write_bytes(original)
        game = GameImage(self.path, ROM)
        self.assertEqual(game.kind, 'native')
        self.assertEqual(game.get_officers()[0]['troops'],73)
        self.assertEqual(game.get_provinces()[0]['gold'],12345)
        game.update_officer(0, {'war':100,'troops':100,'arms':10000,'training':100})
        game.update_province(0, {'food':30000})
        allowed = {game.ram_offset+OFFICER_BASE+n for n in (7,14,15,16,17,18)}
        allowed |= {game.ram_offset+PROVINCE_BASE+n for n in (18,19)}
        self.assertTrue({i for i,(a,b) in enumerate(zip(original,game.data)) if a != b} <= allowed)
        out = self.directory/'native.state'
        game.save(out)
        reloaded = GameImage(out)
        self.assertEqual(reloaded.get_officers()[0]['war'],100)
        self.assertEqual(reloaded.get_officers()[0]['training'],100)
        self.assertEqual(reloaded.get_provinces()[0]['food'],30000)
        self.assertEqual(reloaded.data[:game.ram_offset],original[:game.ram_offset])
        self.assertEqual(reloaded.data[game.ram_offset+65536:],original[game.ram_offset+65536:])

    def test_native_invalid_sections_rejected(self):
        valid = synthetic_native(self.fixture)
        cases = [valid[:7], valid[:-1], valid+b'\x00',
                 b'BLSTSZ\x01\x08'+valid[8:],
                 NATIVE_HEADER+section(10,b'\x40'+bytes(20)),
                 NATIVE_HEADER+section(1,b'cpu'),
                 valid+section(10,b'\x40'+bytes(65536)),
                 NATIVE_HEADER+section(10,b'\x20'+bytes(65536))]
        for data in cases:
            with self.subTest(size=len(data)):
                self.path.write_bytes(data)
                with self.assertRaises(ValueError):
                    GameImage(self.path)

    def test_native_opening_rejected(self):
        self.path.write_bytes(NATIVE_HEADER+section(10,b'\x40'+bytes(65536)))
        with self.assertRaisesRegex(ValueError,'开场'):
            GameImage(self.path)

    def test_battle_expanded_troops_rejected(self):
        self.put(OFFICER_BASE+14,101,2)
        for data in (self.fixture, synthetic_native(self.fixture)):
            self.path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'战斗'):
                GameImage(self.path)

    def test_nonstandard_swapped_gst_rejected(self):
        data = bytearray(self.fixture)
        ram = data[RAM_OFFSET:RAM_OFFSET+65536]
        ram[::2],ram[1::2] = ram[1::2],ram[::2]
        data[RAM_OFFSET:RAM_OFFSET+65536] = ram
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'指针'):
            GameImage(self.path)


if __name__ == '__main__':
    unittest.main()
