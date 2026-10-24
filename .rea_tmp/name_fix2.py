from pathlib import Path
p=Path('.rea_tmp/name_transcribe.py');s=p.read_text(encoding='utf8').replace('贞良 袁胤 贞越','真良 袁胤 真越');p.write_text(s,encoding='utf8')
