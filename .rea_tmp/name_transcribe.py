from pathlib import Path
names='''曹操 刘备 孙坚 袁绍 袁术 马腾 刘焉 刘表 董卓 公孙瓒
陶谦 韩馥 孔融 王朗 刘繇 徐荣 李傕 高沛 刘璋 公孙越
田丰 袁熙 袁谭 袁尚 郭图 颜良 高干 高览 焦触 潘凤
审配 张颌 沮授 陈宫 夏侯渊 夏侯惇 曹洪 曹昂 曹仁 乐进
关羽 张飞 真良 袁胤 真越 曹纯 贾诩 王允 韩嵩 许靖
黄祖 贾华 吕布 虞翻 程普 孙策 黄盖 韩遂 韩当 阚泽
纪灵 蔡瑁 严颜 朱治 韩暹 宋忠 辛评 张资 黄权 侯选
邓义 文聘 高定 李严 吴兰 蔡勋 刘磐 华雄 朱然 丁奉
朱灵 钟繇 郭汜 乐就 程银 张南 吕公 曹豹 孙乾 太史慈
张英 张勋 陈震 赵岑 吴懿 李儒 张任 马延 赵范 夏侯恩
文丑 陈登 陈武 陈兰 成宜 周泰 逢纪 董和 伊籍 董旻
李肃 张郃 许昌 糜竺 糜芳 武安国 蒋义渠 樊稠 毛玠 孟达
杨怀 刘勋 雷同 刘岱 王粲 梁刚 凌操 吕凯 吕义 胡轸
李异 冷苞 王匡 华歆 李通 李典 李丰 雷薄 张邈 张允
吕建 杨秋 李珪 王累 张济 宋宪 张绣 吕范 黄琬 吕虔
张鲁 杨奉 张松 阎圃 荀恽 荀谌 张辽 于禁 周瑜 吕蒙
郭嘉 徐晃 王楷 郭淮 夏侯楙 程昱 典韦 桓楷 马超 满宠
陈矫 郝萌 魏延 许汜 魏续 侯成 马铁 王威 霍峻 周仓
陈嬉 淳于琼 赵云 张卫 毕志 王忠 高顺 简雍 张横 李恢
徐庶 马岱 庞德 梁兴 邓贤 费诗 王修 韩浩 马玩 傅干
杨昂 杜袭 杨平 杨松 杨任 杨柏 甘宁 法正 庞统 刘度
董衡 辛毗 刘晔 潘璋 顾雍 刘巴 宋谦 李堪 吕常 廖化
孙权 马休 刘琮 鲁肃 刘琦 司马懿 董袭 孙瑜 凌统 张昭
陆绩 韩玄 许褚 郝昭 孙桓 夏侯朗 陆逊 曹真 张纮 关平
审荣 孙翊 吕旷 典满 朱桓 郭奕 牛金 杨修 蔡和 严畯
谭雄 诸葛瑾 赵统 杨洪 吕翔 诸葛亮 马忠 徐商 步骘 徐盛
蔡仲 贾逵 杨龄 程秉 尚举 全琮 金旋 曹休 陈群 黄忠
王平 邢道荣 薛综 蒋琬 曹彰 夏侯威 夏侯德 关兴 张休 吴班
夏侯尚 曹丕 曹植 张苞 尚宠 刘循 陈应 刘封 周鲂 陈式
赵应 庞柔 马良 张承 张温 刘延 关索 鲍龙 孟获 雍闿
夏侯惠 邓芝 董允 马谡 孟优 费祎 朵思王 刘豹 阿会喃 赵累
张疑 吕朗 傅士仁 张达 费观 金环结 范疆 庞义 潘濬 董荼奴
张著 杨仪 沙摩可 张虎 谢旌 朱褒 文钦 孙礼 陈泰 公孙渊
曹睿 邓艾 毋丘俭 郭攸之 夏侯和 诸葛恪 张翼 傅彤 尹默 王双
程武 鲍信 姜维 刘禅 孙登 司马师 诸葛诞 司马昭 钟会 曹叡
孙和 孙亮'''.split()
print('count',len(names))
Path('.rea_tmp/name_transcription.txt').write_text('\n'.join(names),encoding='utf8')
b=Path('霸王三国志-免登录版/roms/三國志II-霸王三国志.md').read_bytes()
chars={};conf=[]
for i,name in enumerate(names):
 raw=b[0x4c8d4+i*16:0x4c8d4+i*16+6]
 codes=[int.from_bytes(raw[n:n+2],'big') for n in (0,2,4) if raw[n:n+2]!=b'\0\0']
 if len(codes)!=len(name): print('bad length',i,name,codes)
 for c,ch in zip(codes,name):
  if c in chars and chars[c]!=ch:conf.append((i,name,hex(c),chars[c],ch))
  chars[c]=ch
print('conflicts',conf)
import json
Path('.rea_tmp/name_map_initial.json').write_text(json.dumps({f'{c:04X}':ch for c,ch in chars.items()},ensure_ascii=False,indent=2),encoding='utf8')
