"""霸王三国志离线编辑后端。标准 GST 和 BlastEm native 主 RAM 均为 CPU 大端。"""
from pathlib import Path
import hashlib
import os
import tempfile
from datetime import datetime


ROM_SIZE = 0x100000
GST_SIZE = 0x22478
RAM_OFFSET = 0x2478
NATIVE_HEADER = b'BLSTSZ\x01\x07'
OFFICER_BASE, OFFICER_STRIDE, OFFICER_COUNT = 0x1052, 24, 216
PROVINCE_BASE, PROVINCE_STRIDE, PROVINCE_COUNT = 0x2712, 34, 41
COUNTRY_BASE, COUNTRY_STRIDE, COUNTRY_COUNT = 0x2492, 40, 16
NAME_BASE, STATS_BASE, NAME_COUNT = 0x4C8D4, 0x4DED4, 352
ROM_SHA256 = 'e70f0a92c205ea432080cc48c18d1d43b7fc4d45464ed7fb218b119096e7cdd9'
NORMALIZED_SHA256 = 'cdb75a636c823718fdf897fa130671de4de132aeba60f8036e33017854d772e6'


def validate_rom(data):
    if len(data) != ROM_SIZE or data[0x100:0x110] != b'SEGA MEGA DRIVE ' or data[0x180:0x18E] != b'GM T-76023 -10':
        raise ValueError('不是受支持的霸王三国志标准 ROM（需要本项目的 1MB .md 文件）。')
    check = bytearray(data)
    check[0x18E:0x190] = bytes(2)
    check[NAME_BASE:STATS_BASE + NAME_COUNT * 3] = bytes(STATS_BASE + NAME_COUNT * 3 - NAME_BASE)
    if hashlib.sha256(check).hexdigest() != NORMALIZED_SHA256:
        raise ValueError('ROM 版本不匹配或程序区域已损坏；为避免写错地址，已拒绝编辑。')


class GameImage:
    """文件载入不写原档；save 备份已有目标，再原子替换。数值均为游戏原始单位。"""

    def __init__(self, path, rom_path=None):
        self.path = Path(path).resolve()
        self.data = bytearray(self.path.read_bytes())
        self.last_backup = None
        self.rom_data = None
        self.ram_offset = RAM_OFFSET
        # BlastEm gst.c 的 RAM 读写使用 read_be_16/write_be_16；寄存器虽为
        # 小端，不能据此推断 RAM 为 word-swapped。仅支持标准大端 RAM。
        self.ram_swapped = False
        if self.data[:4] == b'GST@':
            self.kind = 'gst'
            if len(self.data) != GST_SIZE:
                raise ValueError('GST 即时存档长度不受支持或文件已截断。')
            if rom_path is not None:
                self.rom_data = bytearray(Path(rom_path).read_bytes())
                validate_rom(self.rom_data)
            self._validate_state()
        elif self.data.startswith(b'BLSTSZ'):
            self.kind = 'native'
            self.ram_swapped = False
            self._parse_native()
            if rom_path is not None:
                self.rom_data = bytearray(Path(rom_path).read_bytes())
                validate_rom(self.rom_data)
            self._validate_state()
        else:
            validate_rom(self.data)
            self.kind = 'rom'
            self.rom_data = self.data

    def _parse_native(self):
        if self.data[:8] != NATIVE_HEADER:
            raise ValueError('BlastEm 即时存档版本不受支持。')
        offset = 8
        ram = None
        while offset < len(self.data):
            if len(self.data) - offset < 6:
                raise ValueError('BlastEm 即时存档分节头已截断。')
            section_id = int.from_bytes(self.data[offset:offset+2], 'big')
            size = int.from_bytes(self.data[offset+2:offset+6], 'big')
            payload = offset + 6
            end = payload + size
            if end > len(self.data):
                raise ValueError('BlastEm 即时存档分节长度越界或文件已截断。')
            if section_id == 10:
                if ram is not None:
                    raise ValueError('BlastEm 即时存档存在重复的主 RAM 分节。')
                if size != 65537 or self.data[payload] != 64:
                    raise ValueError('BlastEm 主 RAM 分节大小不受支持，必须为 64KB。')
                ram = payload + 1
            offset = end
        if ram is None:
            raise ValueError('BlastEm 即时存档缺少主 RAM 分节。')
        self.ram_offset = ram

    def _u8(self, address):
        return self.data[self.ram_offset + address]

    def _u16(self, address):
        return (self._u8(address) << 8) | self._u8(address + 1)

    def _u32(self, address):
        return (self._u16(address) << 16) | self._u16(address + 2)

    def _put(self, address, value, width=1):
        for n, byte in enumerate(value.to_bytes(width, 'big')):
            logical = address + n
            self.data[self.ram_offset + logical] = byte

    @staticmethod
    def _index(index, count):
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < count:
            raise ValueError('记录编号超出范围。')

    @staticmethod
    def _pointer(value, base, stride, count):
        if value == 0:
            return None
        offset = value - (0xFF0000 + base)
        if offset < 0 or offset % stride or offset // stride >= count:
            raise ValueError('即时存档中的链表指针无效，可能并非本游戏存档或字节序不受支持。')
        return offset // stride

    def _officer_pointer(self, value):
        return self._pointer(value, OFFICER_BASE, OFFICER_STRIDE, OFFICER_COUNT)

    def _province_pointer(self, value):
        return self._pointer(value, PROVINCE_BASE, PROVINCE_STRIDE, PROVINCE_COUNT)

    def _chain(self, head, base, stride, count):
        result = []
        while head:
            index = self._pointer(head, base, stride, count)
            if index in result:
                raise ValueError('即时存档链表存在循环，已拒绝编辑。')
            result.append(index)
            head = self._u32(base + index * stride)
        return result

    def _validate_state(self):
        active = 0
        active_rulers = set()
        for index in range(COUNTRY_COUNT):
            address = COUNTRY_BASE + index * COUNTRY_STRIDE
            ruler = self._officer_pointer(self._u32(address))
            self._officer_pointer(self._u32(address + 8))
            provinces = self._chain(self._u32(address + 4), PROVINCE_BASE, PROVINCE_STRIDE, PROVINCE_COUNT)
            if ruler is not None:
                active += 1
                active_rulers.add(ruler)
                if self._u8(OFFICER_BASE + ruler * OFFICER_STRIDE + 9) != index:
                    raise ValueError('君主与国家归属不一致，存档结构不受支持。')
            for province in provinces:
                if self._u8(PROVINCE_BASE + province * PROVINCE_STRIDE + 0x16) != index:
                    raise ValueError('州与国家归属不一致，存档结构不受支持。')
        if not active:
            raise ValueError('这是尚未开始剧本的开场即时存档。请进入内政地图后重新保存即时存档。')
        owned_officers = set()
        for index in range(PROVINCE_COUNT):
            address = PROVINCE_BASE + index * PROVINCE_STRIDE
            nation = self._u8(address + 0x16)
            if nation != 255 and nation >= COUNTRY_COUNT:
                raise ValueError('州的国家编号无效。')
            for officer in self._chain(self._u32(address + 4), OFFICER_BASE, OFFICER_STRIDE, OFFICER_COUNT):
                if officer in owned_officers:
                    raise ValueError('同一武将出现在多个州，存档结构不受支持。')
                owned_officers.add(officer)
        for index in range(OFFICER_COUNT):
            address = OFFICER_BASE + index * OFFICER_STRIDE
            self._officer_pointer(self._u32(address))
            name_id = self._u16(address + 0x16)
            if name_id >= NAME_COUNT and name_id not in (0xFFFF, 0xFFFE, 0xFFFD):
                raise ValueError('武将身份编号超出本 ROM 范围。')
            # ROM 0x15A40–0x15A76 内政兵力上限100；0x1588A–0x15898
            # 转入战斗时原地乘100。战斗态不能按内政结构编辑。
            if index in owned_officers | active_rulers and self._u16(address + 14) > 100:
                raise ValueError('活动武将兵力超过内政上限，可能是战斗中或非战略状态存档。请返回内政地图后重新保存即时存档。')

    def get_officers(self):
        if self.kind == 'rom':
            return [dict(index=i, name_id=i, nation=None, province=None,
                         intelligence=self.data[STATS_BASE+i*3], war=self.data[STATS_BASE+i*3+1],
                         charm=self.data[STATS_BASE+i*3+2], loyalty=None, troops=None, arms=None, training=None)
                    for i in range(NAME_COUNT)]
        location = {o: p['index'] for p in self.get_provinces() for o in p['officer_indices']}
        result = []
        for i in range(OFFICER_COUNT):
            a = OFFICER_BASE + i * OFFICER_STRIDE
            result.append(dict(index=i, name_id=self._u16(a+0x16), nation=self._u8(a+9),
                               province=location.get(i), intelligence=self._u8(a+6), war=self._u8(a+7),
                               charm=self._u8(a+8), loyalty=self._u8(a+10), troops=self._u16(a+14), arms=self._u16(a+16), training=self._u8(a+18)))
        return result

    def get_provinces(self):
        if self.kind == 'rom':
            return []
        result = []
        for i in range(PROVINCE_COUNT):
            a = PROVINCE_BASE + i*PROVINCE_STRIDE
            nation = self._u8(a+22)
            result.append(dict(index=i,nation=nation,
                gold=self._u16(a+16),food=self._u16(a+18),population=self._u16(a+20),
                land=self._u8(a+28),civil_loyalty=self._u8(a+29),flood_control=self._u8(a+30),
                horses=self._u8(a+31),price=self._u8(a+32),
                trust=self._u8(COUNTRY_BASE+nation*COUNTRY_STRIDE+12) if nation<COUNTRY_COUNT else None,
                officer_indices=self._chain(self._u32(a+4),OFFICER_BASE,24,OFFICER_COUNT),
                free_officer_indices=self._chain(self._u32(a+8),OFFICER_BASE,24,OFFICER_COUNT)))
        return result

    def get_countries(self):
        if self.kind == 'rom':
            return []
        provinces = self.get_provinces()
        result = []
        for i in range(COUNTRY_COUNT):
            a = COUNTRY_BASE + i * COUNTRY_STRIDE
            ps = [p for p in provinces if p['nation'] == i]
            result.append(dict(index=i, ruler_index=self._officer_pointer(self._u32(a)),
                               advisor_index=self._officer_pointer(self._u32(a+8)),
                               province_indices=[p['index'] for p in ps],
                               officer_indices=[o for p in ps for o in p['officer_indices']]))
        return result

    @staticmethod
    def _changes(changes, fields):
        for key, value in changes.items():
            if key not in fields:
                raise ValueError('此类文件不支持修改字段：' + str(key))
            maximum = fields[key][2]
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
                raise ValueError(f'{key} 必须为 0 至 {maximum} 的整数。')

    def update_officer(self, index, changes):
        self._index(index, NAME_COUNT if self.kind == 'rom' else OFFICER_COUNT)
        fields = dict(intelligence=(6, 1, 100), war=(7, 1, 100), charm=(8, 1, 100))
        if self.kind != 'rom':
            # 内政补兵 clamp=100；进入战斗前会乘100（ROM 0x15A40/0x1588A）。
            # 武器采购 clamp=10000（ROM 0x1DF5A）。只编辑内政地图即时存档。
            fields.update(loyalty=(10, 1, 100), troops=(14, 2, 100), arms=(16, 2, 10000), training=(18, 1, 100))
        self._changes(changes, fields)
        for key, value in changes.items():
            offset, width, _ = fields[key]
            if self.kind == 'rom':
                self.data[STATS_BASE + index * 3 + offset - 6] = value
            else:
                self._put(OFFICER_BASE + index * OFFICER_STRIDE + offset, value, width)

    def update_province(self, index, changes):
        if self.kind == 'rom':
            raise ValueError('州资源需要进入剧本后的即时存档。')
        self._index(index, PROVINCE_COUNT)
        # ROM 0xEF90–0xF03E: 民=州+1D，土=+1C，水=+1E，
        # 信=国家+C，马=州+1F，相=+20；价格更新0x3D35A/388限制20..70。
        fields = dict(gold=(16,2,30000),food=(18,2,30000),population=(20,2,65535),
                      land=(28,1,100),civil_loyalty=(29,1,100),flood_control=(30,1,100),
                      horses=(31,1,100),price=(32,1,70),trust=(12,1,100))
        self._changes(changes, fields)
        if 'price' in changes and changes['price']<20:
            raise ValueError('相场必须为 20 至 70 的整数。')
        nation = self._u8(PROVINCE_BASE+index*PROVINCE_STRIDE+22)
        if 'trust' in changes and (nation>=COUNTRY_COUNT or self._u32(COUNTRY_BASE+nation*COUNTRY_STRIDE)==0):
            raise ValueError('无主州没有国家共享的“信”；请筛选存续国家后修改。')
        for key, value in changes.items():
            offset, width, _ = fields[key]
            address = COUNTRY_BASE+nation*COUNTRY_STRIDE+offset if key=='trust' else PROVINCE_BASE+index*PROVINCE_STRIDE+offset
            self._put(address,value,width)

    def transfer_officers(self, indices, nation, province):
        """内政存档中搬移在职武将；整批预检并原子更新州链表与国家归属。

        州 +4 指向首将（太守），将 +0 指向下一将；目标按末尾追加保留
        原太守。君主不可单独转国，原州不可搬空；转出的军师清除原国任命。
        返回实际改变州位置的武将编号；不会写入磁盘。
        """
        if self.kind == 'rom':
            raise ValueError('转国需要读取内政地图的即时存档，不能在新开局 ROM 模式使用。')
        self._validate_state()
        self._index(nation, COUNTRY_COUNT)
        self._index(province, PROVINCE_COUNT)
        chosen = []
        for index in indices:
            self._index(index, OFFICER_COUNT)
            if index not in chosen:
                chosen.append(index)
        if not chosen:
            raise ValueError('请先勾选要转入的武将。')
        countries = self.get_countries()
        destination = countries[nation]
        if destination['ruler_index'] is None or province not in destination['province_indices']:
            raise ValueError('目标必须是存续国家及其所属州。')
        head = self._u32(COUNTRY_BASE + nation * COUNTRY_STRIDE + 4)
        if province not in self._chain(head, PROVINCE_BASE, PROVINCE_STRIDE, PROVINCE_COUNT):
            raise ValueError('目标州不在该国领州名单中，已拒绝转入。')
        provinces = self.get_provinces()
        lists = {p['index']:list(p['officer_indices']) for p in provinces}
        location = {o:p['index'] for p in provinces for o in p['officer_indices']}
        rulers = {c['ruler_index'] for c in countries if c['ruler_index'] is not None}
        moving = []
        for index in chosen:
            source = location.get(index)
            if source is None or provinces[source]['nation'] == 255:
                raise ValueError(f'编号 {index+1} 不在在职武将名单中；当前只支持在职武将调动。')
            address = OFFICER_BASE + index * OFFICER_STRIDE
            if self._u8(address+9) != provinces[source]['nation']:
                raise ValueError(f'编号 {index+1} 的国家与州名单不一致，已拒绝转国。')
            if source == province:
                continue
            if index in rulers:
                raise ValueError(f'编号 {index+1} 是君主，不能单独调动。请取消勾选该君主。')
            moving.append(index)
        affected = {location[i] for i in moving}
        for index in moving:
            lists[location[index]].remove(index)
        for source in affected:
            if not lists[source]:
                raise ValueError(f'第 {source+1} 州会没有任何在职武将。请至少保留一名武将驻守。')
        if not moving:
            return []
        lists[province].extend(moving)
        # 所有源州的最后一人、君主及目标验证完成后才触碰字节。
        original = self.data
        self.data = bytearray(original)
        try:
            for p in affected | {province}:
                chain = lists[p]
                pointer = lambda i: 0xFF0000 + OFFICER_BASE + i * OFFICER_STRIDE
                self._put(PROVINCE_BASE + p * PROVINCE_STRIDE + 4, pointer(chain[0]) if chain else 0, 4)
                for n, index in enumerate(chain):
                    following = pointer(chain[n+1]) if n+1 < len(chain) else 0
                    self._put(OFFICER_BASE + index * OFFICER_STRIDE, following, 4)
            for index in moving:
                self._put(OFFICER_BASE + index * OFFICER_STRIDE + 9, nation)
            for country in countries:
                advisor = country['advisor_index']
                if country['index'] != nation and advisor in moving:
                    self._put(COUNTRY_BASE + country['index'] * COUNTRY_STRIDE + 8, 0, 4)
            self._validate_state()
        except Exception:
            self.data = original
            raise
        return moving

    def save(self, path):
        target = Path(path).resolve()
        if self.kind == 'rom':
            validate_rom(self.data)
            checksum = sum(int.from_bytes(self.data[i:i+2], 'big') for i in range(0x200, len(self.data), 2)) & 65535
            self.data[0x18E:0x190] = checksum.to_bytes(2, 'big')
        else:
            if self.kind == 'native':
                self._parse_native()
            self._validate_state()
        if target.exists():
            backup = target.with_name(target.name + '.' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak')
            with backup.open('xb') as output:
                output.write(target.read_bytes())
            self.last_backup = backup
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.' + target.name, suffix='.tmp', delete=False) as output:
                temporary = Path(output.name)
                output.write(self.data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return target
