"""Custom Chinese font codec for this exact ROM translation.

The mapping is transcribed from the ROM's own 16x16 glyphs, not GBK/SJIS.
Unknown codes stay visible as hexadecimal placeholders rather than guessed names.
"""
from __future__ import annotations

import json
from pathlib import Path

NAME_BASE = 0x4C8D4
NAME_COUNT = 352
NAME_STRIDE = 16
NAME_BYTES = 7

_TABLE = json.loads(Path(__file__).with_name("names.json").read_text(encoding="utf-8"))
CHARACTERS = {int(k, 16): v for k, v in _TABLE["characters"].items()}
CHARACTERS.update({0x8168: "智", 0x8167: "力", 0x8160: "武", 0x8166: "魅",
                   0x8162: "忠", 0x8163: "诚", 0x8164: "士", 0x8165: "兵",
                   0x8175: "训", 0x8176: "练", 0x82A2: "装"})
_ENCODE = {}
for _code, _char in sorted(CHARACTERS.items()):
    _ENCODE.setdefault(_char, _code)

# Accept common traditional forms as input too; emitted glyphs are always the
# original ROM glyph. A character outside the verified map is rejected.
_SIMPLIFIED = "刘孙坚绍术马腾焉表董瓒谦韩馥刘繇荣傕沛璋丰熙谭尚颜览触凤审张颌沮宫渊惇洪昂仁乐关飞胤贾诩纯允嵩许黄华吕虞翻程盖遂阚纪灵蔡瑁严暹宋评资权邓义聘钟汜银南乾慈英勋陈赵范丑兰周逢旻肃郃昌糜竺蒋樊稠杨怀岱粲梁刚凯轸异苞匡歆通典薄邈济绣琬虔鲁奉松阎荀恽谌辽于禁瑜蒙郭晃楷淮楙昱韦桓超宠矫萌魏续铁威峻仓嬉琼云卫毕忠顺简雍横恢庶庞兴贤费诗修浩玩傅干袭柏宁统度衡毗晔潘璋顾巴谦堪常廖桓琮肃琦懿袭瑜凌昭陆绩玄褚郝逊真纮平翊旷满奕畯谭诸葛瑾翔亮骘贾逵龄秉举琮旋休群忠邢综琬彰德苞鲂式应柔良承温延索鲍获闿惠芝允谡优祎朵思豹喃累疑朗士达观环结疆濬荼奴著仪摩虎谢旌褒钦礼泰睿艾毋俭攸翼彤尹默双维禅登师诞昭会叡和" 
_TRADITIONAL = "劉孫堅紹術馬騰焉表董瓚謙韓馥劉繇榮傕沛璋豐熙譚尚顏覽觸鳳審張頜沮宮淵惇洪昂仁樂關飛胤賈詡純允嵩許黃華呂虞翻程蓋遂闞紀靈蔡瑁嚴暹宋評資權鄧義聘鍾汜銀南乾慈英勳陳趙範醜蘭周逢旻肅郃昌糜竺蔣樊稠楊懷岱粲梁剛凱軫異苞匡歆通典薄邈濟繡琬虔魯奉松閻荀惲諶遼于禁瑜蒙郭晃楷淮楙昱韋桓超寵矯萌魏續鐵威峻倉嬉瓊雲衛畢忠順簡雍橫恢庶龐興賢費詩修浩玩傅干襲柏寧統度衡毗曄潘璋顧巴謙堪常廖桓琮肅琦懿襲瑜凌昭陸績玄褚郝遜真紘平翊曠滿奕畯譚諸葛瑾翔亮騭賈逵齡秉舉琮旋休群忠邢綜琬彰德苞魴式應柔良承溫延索鮑獲闓惠芝允謖優禕朵思豹喃累疑朗士達觀環結疆濬荼奴著儀摩虎謝旌褒欽禮泰睿艾毋儉攸翼彤尹默雙維禪登師誕昭會叡和"
assert len(_SIMPLIFIED) == len(_TRADITIONAL)
for _simple, _trad in zip(_SIMPLIFIED, _TRADITIONAL):
    if _simple in _ENCODE:
        _ENCODE.setdefault(_trad, _ENCODE[_simple])
for _trad, _simple in {"備": "备", "練": "练", "訓": "训", "裝": "装", "誠": "诚", "鍾": "钟", "丕": "丕"}.items():
    if _simple in _ENCODE:
        _ENCODE.setdefault(_trad, _ENCODE[_simple])


def _check_rom(rom: bytes | bytearray) -> None:
    if len(rom) != 0x100000 or rom[0x100:0x104] != b"SEGA":
        raise ValueError("请选择本游戏的标准 1MB MD ROM，不能使用交错 SMD 文件。")


def resolve_name(rom: bytes | bytearray, name_id: int) -> str:
    _check_rom(rom)
    if not isinstance(name_id, int) or not 0 <= name_id < NAME_COUNT:
        return f"未知武将 #{name_id}"
    start = NAME_BASE + name_id * NAME_STRIDE
    raw = rom[start:start + 6]
    parts = []
    for offset in (0, 2, 4):
        code = int.from_bytes(raw[offset:offset + 2], "big")
        if code == 0:
            break
        parts.append(CHARACTERS.get(code, f"〔{code:04X}〕"))
    return "".join(parts) or f"武将 #{name_id}"


def names_for_rom(rom: bytes | bytearray) -> list[str]:
    return [resolve_name(rom, i) for i in range(NAME_COUNT)]


def encode_name(rom: bytes | bytearray, text: str) -> bytes:
    _check_rom(rom)
    if not isinstance(text, str) or not 1 <= len(text) <= 3:
        raise ValueError("游戏姓名仅支持 1 至 3 个汉字。")
    unknown = [ch for ch in text if ch not in _ENCODE]
    if unknown:
        raise ValueError("原游戏字库尚未收录或尚未确认这些字：" + "、".join(dict.fromkeys(unknown)))
    return b"".join(_ENCODE[ch].to_bytes(2, "big") for ch in text).ljust(NAME_BYTES, b"\0")


def rename_in_rom(rom: bytearray, name_id: int, text: str) -> None:
    if not isinstance(rom, bytearray):
        raise TypeError("改名需要可写的 bytearray ROM。")
    if not isinstance(name_id, int) or not 0 <= name_id < NAME_COUNT:
        raise ValueError("武将姓名编号超出范围。")
    encoded = encode_name(rom, text)
    start = NAME_BASE + name_id * NAME_STRIDE
    rom[start:start + NAME_BYTES] = encoded


def supported_characters() -> str:
    return "".join(sorted(set(CHARACTERS.values())))


def glyph_bitmap(rom: bytes | bytearray, code: int) -> list[list[int]]:
    """Return the exact 16x16 1bpp ROM glyph, for UI or evidence rendering."""
    _check_rom(rom)
    if code >= 0x841E:
        start = 0xFD000 + (code - 0x841E) * 32
    elif code >= 0x831E:
        start = 0x5A000 + (code - 0x831E) * 32
    else:
        start = 0x55896 + (code - 0x8140) * 32
    if code < 0x8140 or start < 0 or start + 32 > len(rom):
        raise ValueError("字码超出 ROM 字库范围。")
    raw = rom[start:start + 32]
    bitmap = [[0] * 16 for _ in range(16)]
    for tile in range(4):
        for row in range(8):
            for col in range(8):
                bitmap[tile // 2 * 8 + row][tile % 2 * 8 + col] = int(bool(raw[tile * 8 + row] & (128 >> col)))
    return bitmap
