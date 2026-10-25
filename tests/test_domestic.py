"""州城面板映射、国家共享信、边界与批量内政编辑验证。"""
import tempfile
import unittest
from pathlib import Path
from test_model import ROOT, ROM, RAM_OFFSET, synthetic_native
from test_transfer import transfer_fixture
from trainer.model import GameImage, PROVINCE_BASE, COUNTRY_BASE
from trainer.app import Trainer


def domestic_fixture():
    data=transfer_fixture()
    data[RAM_OFFSET+PROVINCE_BASE+28:RAM_OFFSET+PROVINCE_BASE+33]=bytes([51,52,53,54,55])
    data[RAM_OFFSET+COUNTRY_BASE+12]=67
    data[RAM_OFFSET+COUNTRY_BASE+40+12]=18
    return data


class DomesticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp')
        self.directory=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self,native=False):
        p=self.directory/('source.state' if native else 'source.gst')
        data=domestic_fixture()
        p.write_bytes(synthetic_native(data) if native else data)
        return GameImage(p,ROM)

    def test_display_mapping_shared_trust_and_roundtrip(self):
        for native in (False,True):
            with self.subTest(native=native):
                game=self.load(native)
                p=game.get_provinces()[0]
                self.assertEqual([p[k] for k in ('land','civil_loyalty','flood_control','horses','price','trust')],[51,52,53,54,55,67])
                before=bytes(game.data)
                game.update_province(0,dict(gold=29999,food=28888,population=60000,land=99,
                    civil_loyalty=98,flood_control=97,horses=96,price=20,trust=95))
                provinces=game.get_provinces()
                self.assertEqual(provinces[0]['civil_loyalty'],98)
                self.assertEqual(provinces[1]['trust'],95)
                self.assertEqual(provinces[2]['trust'],18)
                self.assertIsNone(provinces[4]['trust'])
                allowed={game.ram_offset+PROVINCE_BASE+n for n in (*range(16,22),*range(28,33))}
                allowed.add(game.ram_offset+COUNTRY_BASE+12)
                actual={i for i,(a,b) in enumerate(zip(before,game.data)) if a!=b}
                self.assertTrue(actual)
                self.assertTrue(actual<=allowed)
                output=self.directory/('edited.state' if native else 'edited.gst')
                game.save(output)
                self.assertEqual(GameImage(output,ROM).get_provinces(),provinces)
                self.assertEqual(game.path.read_bytes(),before)

    def test_ranges_and_unowned_shared_field_are_atomic(self):
        game=self.load()
        for changes in [dict(land=101),dict(civil_loyalty=-1),dict(flood_control=True),dict(horses=101),
                        dict(price=19),dict(price=71),dict(trust=101),dict(trust=1.5),dict(gold=1,price=0)]:
            before=bytes(game.data)
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                game.update_province(0,changes)
            self.assertEqual(game.data,before)
        before=bytes(game.data)
        with self.assertRaisesRegex(ValueError,'无主州'):
            game.update_province(4,dict(land=100,trust=100))
        self.assertEqual(game.data,before)
        game.update_province(0,dict(land=0,civil_loyalty=0,flood_control=0,horses=0,trust=0,price=70))
        self.assertEqual(game.get_provinces()[0]['price'],70)


class DomesticGuiTests(unittest.TestCase):
    def test_country_batch_domestic_edit_and_sort(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp') as tmp:
            p=Path(tmp)/'source.state'
            p.write_bytes(synthetic_native(domestic_fixture()))
            a=Trainer()
            a.withdraw()
            a.auto_restart.set(False)
            try:
                a.open_path(p)
                a.nation.set(next(k for k,v in a.nations.items() if v==0))
                a.refresh()
                self.assertEqual(a.province_table.get_children(),('0','1'))
                a.province_table.selection_set(a.province_table.get_children())
                for k,v in dict(civil_loyalty=98,land=99,flood_control=97,trust=100,horses=96,price=70).items():
                    flag,value,*_=a.fields[('province',k)]
                    flag.set(True)
                    value.set(str(v))
                a.apply('province')
                self.assertTrue(a.dirty)
                for row in ('0','1'):
                    for k,v in dict(civil_loyalty=98,land=99,flood_control=97,trust=100,horses=96,price=70).items():
                        self.assertEqual(int(a.province_table.set(row,k)),v)
                self.assertEqual(a.image.get_provinces()[2]['trust'],18)
                self.assertEqual(a.province_table.set('0','officers'),'4')
                self.assertEqual(a.province_table.set('0','free_officers'),'0')
                a.sort_table('province','land')
                self.assertIn('▲',a.province_table.heading('land','text'))
                self.assertEqual(p.read_bytes(),synthetic_native(domestic_fixture()))
            finally:
                a.update_idletasks()
                a.destroy()
