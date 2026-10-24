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
        return [dict(index=i, nation=self._u8(PROVINCE_BASE+i*34+22),
                     gold=self._u16(PROVINCE_BASE+i*34+16), food=self._u16(PROVINCE_BASE+i*34+18),
                     population=self._u16(PROVINCE_BASE+i*34+20),
                     officer_indices=self._chain(self._u32(PROVINCE_BASE+i*34+4), OFFICER_BASE, 24, OFFICER_COUNT))
                for i in range(PROVINCE_COUNT)]

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
        fields = dict(gold=(16, 2, 30000), food=(18, 2, 30000), population=(20, 2, 65535))
        self._changes(changes, fields)
        for key, value in changes.items():
            offset, width, _ = fields[key]
            self._put(PROVINCE_BASE + index * PROVINCE_STRIDE + offset, value, width)

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
