import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('keyboard_config',Path(__file__).resolve().parents[1]/'system/keyboard_config.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
configure=module.configure

class KeyboardConfig(unittest.TestCase):
    def test_fresh_install(self):
        result=configure('')
        for line in ('[ids]\n*', 'capslock = overload(agents_capslock, f24)', '[agents_capslock]',
                     'j = up','k = down','l = left','semicolon = right','overload_tap_timeout = 250'):
            self.assertIn(line,result)
        self.assertEqual(result,configure(result))
    def test_preserves_unrelated_mappings_and_device_selection(self):
        original='[ids]\n1234:5678\n\n[main]\n# My settings\ncapslock = overload(control, esc)\nrightalt = compose\n\n[arrows]\nj = left\n\n[global]\noverload_tap_timeout = 100\n'
        result=configure(original)
        for text in ('1234:5678','# My settings','rightalt = compose','[arrows]\nj = left'):
            self.assertIn(text,result)
        self.assertNotIn('overload(control, esc)',result)
        self.assertNotIn('timeout = 100',result)
        self.assertEqual(result,configure(result))
    def test_rejects_ambiguous_or_missing_sections(self):
        for text in ('[main]\ncapslock = a\n', '[ids]\n*\n[main]\n[main]\n', '[ids]\n*\n[main]\ncapslock = a\ncapslock = b\n'):
            with self.assertRaises(ValueError): configure(text)
    def test_updates_owned_layer_and_preserves_other_keys(self):
        result=configure('[ids]\n*\n[agents_capslock]\nj = left\nx = delete')
        self.assertIn('j = up',result)
        self.assertIn('x = delete',result)
        self.assertEqual(result,configure(result))

class SystemTransaction(unittest.TestCase):
    def test_apply_failure_restores_existing_files(self):
        import sys
        import tempfile
        from unittest.mock import patch
        from subprocess import CompletedProcess
        directory=Path(__file__).resolve().parents[1]/'system'
        with patch.dict(sys.modules,{'keyboard_config':module}):
            spec=importlib.util.spec_from_file_location('install_system',directory/'install-system.py')
            setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            files=tuple(root/str(i)/name for i,name in enumerate( ('default.conf','keyd-attention','caps-led','attention.conf','agents-capslock')))
            for file in files:
                file.parent.mkdir(); file.write_text('original '+file.name)
            files[0].write_text('[ids]\n*\n[main]\ncapslock = esc\n')
            files[4].write_text('existing ALL=(root) NOPASSWD: /bin/true\n')
            originals={p:p.read_bytes() for p in files}
            binary=root/'new-binary';binary.write_text('new binary')
            failed=False
            def command(*args):
                nonlocal failed
                if args==('systemctl','restart','keyd') and not failed:
                    failed=True
                    raise RuntimeError('Simulated service start failure')
            def status(args,**kwargs):
                return CompletedProcess(args,0,'enabled\n','')
            constants=dict(zip(('CONFIG','BINARY','HELPER','OVERRIDE','SUDOERS'),files))
            with patch.multiple(setup,**constants,FILES=files,BACKUPS=root/'backups'), patch.object(setup,'run',side_effect=command), patch.object(setup.subprocess,'run',side_effect=status), patch.object(setup.pwd,'getpwnam'), patch.object(setup.shutil,'which',return_value='/usr/bin/command'):
                with self.assertRaisesRegex(RuntimeError,'Simulated'):
                    setup.install(binary,directory.parent,'testuser')
            self.assertTrue(failed)
            self.assertEqual(originals,{p:p.read_bytes() for p in files})
