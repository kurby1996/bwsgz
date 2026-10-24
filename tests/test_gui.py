"""构造界面并调用其编辑流程；不替代游戏内存档回放或目视布局验证。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from trainer.app import Trainer, ROM, ROOT
from trainer.model import GameImage
from test_model import synthetic_gst, synthetic_native


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp')
        self.directory = Path(self.tmp.name)
        self.app = Trainer()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.tmp.cleanup()

    def test_rom_selection_apply_rename_save_reload(self):
        a = self.app
        self.assertEqual(len(a.officer_table.get_children()),352)
        self.assertEqual(a.officer_table.item('0')['values'][1], '曹操')
        self.assertEqual(a.tabs.tab(1,'state'),'disabled')
        a.officer_table.selection_set('0','1')
        flag,value,*_ = a.fields[('officer','war')]
        flag.set(True)
        value.set('100')
        a.apply('officer')
        self.assertEqual([o['war'] for o in a.image.get_officers()[:3]],[100,100,90])
        a.officer_table.selection_set('0')
        a.rename.set('刘备')
        a.rename_selected()
        target = self.directory/'改名能力.md'
        with patch('trainer.app.filedialog.asksaveasfilename',return_value=str(target)), patch('trainer.app.messagebox.showinfo'):
            a.save_as()
        self.assertTrue(target.exists())
        self.assertTrue(target.with_suffix('.md.启动.bat').exists())
        reloaded = GameImage(target)
        self.assertEqual(reloaded.get_officers()[0]['war'],100)
        self.assertNotEqual(reloaded.data, ROM.read_bytes())
        self.assertFalse(a.dirty)

    def test_native_country_resources_and_invalid_batch_atomic(self):
        a = self.app
        gst,_ = synthetic_gst()
        source = self.directory/'test.state'
        source.write_bytes(synthetic_native(gst))
        a.open_path(source)
        self.assertEqual(a.image.kind,'native')
        self.assertEqual(len(a.officer_table.get_children()),1)
        a.nation.set(next(label for label,ident in a.nations.items() if ident==0))
        a.refresh()
        self.assertEqual(a.province_table.get_children(),('0',))
        a.province_table.selection_set('0')
        flag,value,*_ = a.fields[('province','gold')]
        flag.set(True)
        value.set('30000')
        a.apply('province')
        self.assertEqual(a.image.get_provinces()[0]['gold'],30000)
        before = bytes(a.image.data)
        a.officer_table.selection_set('0')
        flag,value,*_ = a.fields[('officer','troops')]
        flag.set(True)
        value.set('101')
        with patch('trainer.app.messagebox.showerror') as error:
            a.apply('officer')
        error.assert_called_once()
        self.assertEqual(a.image.data,before)
        self.assertEqual(source.read_bytes(),synthetic_native(gst))


if __name__=='__main__':
    unittest.main()
