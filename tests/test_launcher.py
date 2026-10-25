import tempfile
import unittest
import time
from pathlib import Path
from unittest.mock import patch
from trainer.model import GameImage
from trainer.launcher import select_emulator, build_launcher, write_launcher, restart_from_launcher, close_project_games
from trainer.app import Trainer
from test_model import ROOT, ROM, synthetic_gst, synthetic_native, section


class LauncherTests(unittest.TestCase):
    def test_device_types_choose_matching_emulator(self):
        for device,folder in [(2,'blastem-兼容模式'),(3,'blastem')]:
            with self.subTest(device=device),tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp') as tmp:
                data=synthetic_native(synthetic_gst()[0])
                for sid in (7,8):
                    data+=section(sid,bytes(5)+bytes([device])+bytes(46))
                p=Path(tmp)/'saved.state'
                p.write_bytes(data)
                image=GameImage(p,ROM)
                emulator,flags=select_emulator(image)
                self.assertEqual(emulator.parent.name,folder)
                self.assertEqual(bool(flags),device==2)
                output=Path(tmp)/'saved%test.state'
                script=write_launcher(image,output).read_bytes()
                self.assertIn(b'%%test',script)
                self.assertNotIn(b'\r\r\n',script)
                self.assertIn(folder.encode('utf8'),script)
                self.assertIn(b' -s ',script)
                self.assertNotIn(b'pause',script)

    def test_mixed_devices_are_explicitly_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp') as tmp:
            data=synthetic_native(synthetic_gst()[0])
            data+=section(7,bytes(5)+b'\x02')+section(8,bytes(5)+b'\x03')
            p=Path(tmp)/'mixed.state'
            p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'混合'):
                build_launcher(GameImage(p,ROM),p)

    def test_restart_closes_before_executing_exact_script(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp') as tmp:
            script=Path(tmp)/'中文 saved.bat'
            script.write_text('@echo off',encoding='utf8')
            actions=[]
            with patch('trainer.launcher.close_project_games',side_effect=lambda:actions.append('close')),patch('trainer.launcher.os.startfile',side_effect=lambda path:actions.append(path)):
                restart_from_launcher(script)
            self.assertEqual(actions,['close',str(script.resolve())])
            with patch('trainer.launcher.close_project_games',side_effect=OSError('not closed')),patch('trainer.launcher.os.startfile') as launch:
                with self.assertRaises(OSError):restart_from_launcher(script)
                launch.assert_not_called()
            with patch('trainer.launcher.close_project_games') as close:
                with self.assertRaises(OSError):restart_from_launcher(Path(tmp)/'missing.bat')
                close.assert_not_called()

    def test_close_scopes_executable_paths_and_does_not_force_kill(self):
        with patch('trainer.launcher.subprocess.run') as run:
            run.return_value.returncode=0
            close_project_games()
            args=run.call_args.args[0]
            env=run.call_args.kwargs['env']
            self.assertIn('CloseMainWindow',args[-1])
            self.assertIn('$paths -contains $_.Path',args[-1])
            self.assertNotIn('Stop-Process',args[-1])
            self.assertIn('blastem-兼容模式',env['BAWANG_RESTART_PATHS'])


class AutoRestartGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.rea_tmp')
        self.path=Path(self.tmp.name)/'result.md'
        self.app=Trainer()
        self.app.withdraw()

    def tearDown(self):
        self.app.update_idletasks()
        self.app.destroy()
        self.tmp.cleanup()

    def finish_restart(self):
        until=time.monotonic()+3
        while self.app.restarting and time.monotonic()<until:
            self.app.update()
            time.sleep(.01)
        self.assertFalse(self.app.restarting)

    def test_default_save_then_auto_restart_without_success_prompt(self):
        self.assertTrue(self.app.auto_restart.get())
        def launch(path):
            self.assertTrue(self.path.is_file())
            self.assertTrue(Path(path).is_file())
        with patch('trainer.app.filedialog.asksaveasfilename',return_value=str(self.path)),patch('trainer.app.restart_from_launcher',side_effect=launch) as restart,patch('trainer.app.messagebox.showinfo') as info:
            self.app.save_as()
            self.finish_restart()
            restart.assert_called_once_with(self.path.with_suffix('.md.启动.bat'))
            info.assert_not_called()
        self.assertFalse(self.app.dirty)

    def test_save_failure_keeps_game_running(self):
        self.app.dirty=True
        with patch('trainer.app.filedialog.asksaveasfilename',return_value=str(self.path)),patch.object(self.app.image,'save',side_effect=OSError('disk full')),patch('trainer.app.restart_from_launcher') as restart,patch('trainer.app.messagebox.showerror') as error:
            self.app.save_as()
            restart.assert_not_called()
            error.assert_called_once()
        self.assertTrue(self.app.dirty)

    def test_restart_failure_reports_saved_file_is_preserved(self):
        with patch('trainer.app.filedialog.asksaveasfilename',return_value=str(self.path)),patch('trainer.app.restart_from_launcher',side_effect=OSError('close failed')),patch('trainer.app.messagebox.showerror') as error:
            self.app.save_as()
            self.finish_restart()
            self.assertEqual(error.call_args.args[0],'已保存，但自动加载未完成')
        self.assertTrue(self.path.is_file())
        self.assertFalse(self.app.dirty)
