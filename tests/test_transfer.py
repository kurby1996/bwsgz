"""转国关联结构、字节保留、失败回滚与界面流程测试。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_model import synthetic_gst, synthetic_native, ROOT, ROM
from trainer.model import GameImage, OFFICER_BASE, PROVINCE_BASE, COUNTRY_BASE
from trainer.app import Trainer


def transfer_fixture():
    data, put = synthetic_gst()
    op = lambda i: 0xFF0000+OFFICER_BASE+i*24
    pp = lambda i: 0xFF0000+PROVINCE_BASE+i*34
    for i in range(10):
        a = OFFICER_BASE+i*24
        put(a+0x16,i,2)
        put(a+9,0 if i<6 else 1 if i<8 else 2)
        put(a+14,10+i,2)
        put(a+16,100+i,2)
        put(a+10,80)
    for p, indices, nation in [(0,[0,1,2,3],0),(1,[4,5],0),(2,[6,7],1),(3,[8,9],2)]:
        put(PROVINCE_BASE+p*34+4,op(indices[0]),4)
        put(PROVINCE_BASE+p*34+22,nation)
        for n,i in enumerate(indices):
            put(OFFICER_BASE+i*24,op(indices[n+1]) if n+1<len(indices) else 0,4)
    put(PROVINCE_BASE,pp(1),4)
    for c,r,p in [(0,0,0),(1,6,2),(2,8,3)]:
        put(COUNTRY_BASE+c*40,op(r),4)
        put(COUNTRY_BASE+c*40+4,pp(p),4)
    put(COUNTRY_BASE+8,op(1),4)
    return data


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp')
        self.directory = Path(self.tmp.name)
        self.fixture = transfer_fixture()

    def tearDown(self):
        self.tmp.cleanup()

    def load(self,native=False):
        p = self.directory/('source.state' if native else 'source.gst')
        p.write_bytes(synthetic_native(self.fixture) if native else self.fixture)
        return GameImage(p,ROM)

    def test_batch_both_formats_preservation_and_roundtrip(self):
        for native in (False,True):
            with self.subTest(native=native):
                game = self.load(native)
                before = bytes(game.data)
                old_stats = game.get_officers()
                moved = game.transfer_officers([1,2,4,1],1,2)
                self.assertEqual(moved,[1,2,4])
                ps = game.get_provinces()
                self.assertEqual([p['officer_indices'] for p in ps[:3]],[[0,3],[5],[6,7,1,2,4]])
                self.assertIsNone(game.get_countries()[0]['advisor_index'])
                self.assertEqual(game.get_countries()[1]['ruler_index'],6)
                for i in moved:
                    officer = game.get_officers()[i]
                    self.assertEqual((officer['nation'],officer['province']),(1,2))
                    for k in ('name_id','intelligence','war','charm','loyalty','troops','arms','training'):
                        self.assertEqual(officer[k],old_stats[i][k])
                allowed = set()
                for i in range(8):
                    allowed.update(game.ram_offset+OFFICER_BASE+i*24+n for n in range(4))
                for i in moved:
                    allowed.add(game.ram_offset+OFFICER_BASE+i*24+9)
                for p in range(3):
                    allowed.update(game.ram_offset+PROVINCE_BASE+p*34+n for n in range(4,8))
                allowed.update(game.ram_offset+COUNTRY_BASE+n for n in range(8,12))
                changed = {i for i,(a,b) in enumerate(zip(before,game.data)) if a!=b}
                self.assertTrue(changed)
                self.assertTrue(changed<=allowed)
                output = self.directory/('edited.state' if native else 'edited.gst')
                game.save(output)
                self.assertEqual(GameImage(output,ROM).get_provinces(),game.get_provinces())
                self.assertEqual(game.path.read_bytes(),before)

    def test_invalid_batch_is_atomic(self):
        for indices,nation,province in [([1,0],1,2),([4,5],1,2),([1],0,2),([1],15,2),
                                       ([1,215],1,2),([1,999],1,2),([1],True,2),([],1,2)]:
            with self.subTest(indices=indices,nation=nation,province=province):
                game = self.load()
                before = bytes(game.data)
                with self.assertRaises(ValueError):
                    game.transfer_officers(indices,nation,province)
                self.assertEqual(game.data,before)

    def test_same_nation_move_and_noop(self):
        game = self.load()
        before = bytes(game.data)
        self.assertEqual(game.transfer_officers([1,2],0,0),[])
        self.assertEqual(game.data,before)
        game.transfer_officers([1],0,1)
        self.assertEqual(game.get_countries()[0]['advisor_index'],1)
        self.assertEqual(game.get_provinces()[1]['officer_indices'],[4,5,1])

    def test_rom_transfer_rejected(self):
        with self.assertRaisesRegex(ValueError,'即时存档'):
            GameImage(ROM).transfer_officers([1],0,0)


class SortingAndTransferGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp')
        self.directory = Path(self.tmp.name)
        self.app = Trainer()
        self.app.auto_restart.set(False)
        self.app.withdraw()

    def tearDown(self):
        self.app.update_idletasks()
        self.app.destroy()
        self.tmp.cleanup()

    def test_numeric_sort_toggle_selection_and_refresh(self):
        a = self.app
        table = a.officer_table
        table.selection_set('0')
        # 2、10、100 会暴露按字符串排序的错误。
        for i,v in [(0,2),(1,10),(2,100)]:
            a.image.update_officer(i,{'war':v})
        a.refresh()
        a.sort_table('officer','war')
        values = [int(table.set(i,'war')) for i in table.get_children()]
        self.assertEqual(values,sorted(values))
        a.sort_table('officer','war')
        values = [int(table.set(i,'war')) for i in table.get_children()]
        self.assertEqual(values,sorted(values,reverse=True))
        self.assertEqual(table.selection(),('0',))
        a.query.set('曹')
        values = [int(table.set(i,'war')) for i in table.get_children()]
        self.assertEqual(values,sorted(values,reverse=True))
        self.assertIn('▼',table.heading('war','text'))

    def test_cross_filter_checks_transfer_and_save(self):
        a = self.app
        source = self.directory/'source.state'
        source.write_bytes(synthetic_native(transfer_fixture()))
        a.open_path(source)
        label = lambda ident: next(k for k,v in a.nations.items() if v==ident)
        a.transfer_nation.set(label(2))
        a.refresh_transfer_targets()
        a.nation.set(label(0))
        a.refresh()
        a.officer_table.selection_set('1')
        a.check_selected()
        a.nation.set(label(1))
        a.refresh()
        a.officer_table.selection_set('7')
        a.check_selected()
        self.assertEqual(a.checked_officers,{1,7})
        self.assertEqual(a.transfer_nation.get(),label(2))
        a.sort_table('officer','war')
        self.assertEqual(a.checked_officers,{1,7})
        a.transfer_checked()
        self.assertTrue(a.dirty)
        self.assertFalse(a.checked_officers)
        self.assertEqual(a.image.get_provinces()[3]['officer_indices'],[8,9,1,7])
        output = self.directory/'transfer.state'
        with patch('trainer.app.filedialog.asksaveasfilename',return_value=str(output)),patch('trainer.app.messagebox.showinfo'):
            a.save_as()
        reloaded = GameImage(output,ROM)
        self.assertEqual(reloaded.get_provinces()[3]['officer_indices'],[8,9,1,7])
        self.assertEqual(source.read_bytes(),synthetic_native(transfer_fixture()))

    def test_province_numeric_sort_and_missing_officer_fields(self):
        a = self.app
        a.sort_table('officer','loyalty')
        self.assertEqual(len(a.officer_table.get_children()),352)
        source = self.directory/'source.gst'
        source.write_bytes(transfer_fixture())
        a.open_path(source)
        a.sort_table('province','gold')
        values = [int(a.province_table.set(i,'gold')) for i in a.province_table.get_children()]
        self.assertEqual(values,sorted(values))
        a.sort_table('province','gold')
        values = [int(a.province_table.set(i,'gold')) for i in a.province_table.get_children()]
        self.assertEqual(values,sorted(values,reverse=True))


if __name__=='__main__':
    unittest.main()
