from pathlib import Path
p=Path('.rea_tmp/name_transcribe.py');s=p.read_text(encoding='utf8');s=s.replace('孙桓 马休','孙权 马休').replace('孙恒 夏侯朗','孙桓 夏侯朗').replace('番荣 孙翊','审荣 孙翊').replace('关休 吴班','张休 吴班').replace('吕霸 傅士仁','吕朗 傅士仁').replace('严舆 潘濬','庞义 潘濬').replace('真良 袁胤 真越','贞良 袁胤 贞越');p.write_text(s,encoding='utf8')
