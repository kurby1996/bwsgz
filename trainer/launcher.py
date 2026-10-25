"""根据原生存档的手柄类型选择同一套模拟器配置。"""
from pathlib import Path
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / '霸王三国志-免登录版/roms/三國志II-霸王三国志.md'


def select_emulator(image):
    devices = {}
    if image.kind == 'native':
        # 官方 io.c: io_serialize 前五字节为端口寄存器，第六字节为
        # device_type。枚举 2=三键手柄，3=六键手柄。分节 7/8=端口1/2。
        pos = 8
        while pos < len(image.data):
            section = int.from_bytes(image.data[pos:pos+2],'big')
            size = int.from_bytes(image.data[pos+2:pos+6],'big')
            if section in (7,8):
                if size < 6:
                    raise ValueError('存档的手柄分节不完整，无法生成匹配的启动脚本。')
                devices[section] = image.data[pos+11]
            pos += 6+size
    kinds = set(devices.values())
    if kinds and kinds not in ({2},{3}):
        raise ValueError('存档使用混合或特殊手柄设备，当前两套配置无法匹配。')
    compatibility = kinds != {3}
    folder = 'blastem-兼容模式' if compatibility else 'blastem'
    emulator = ROOT / '霸王三国志-免登录版' / folder / 'blastem.exe'
    if not emulator.is_file():
        raise ValueError('找不到与存档手柄类型匹配的模拟器：'+str(emulator))
    return emulator, '-r J -g ' if compatibility else ''


def build_launcher(image, saved_path):
    emulator, flags = select_emulator(image)
    escaped_path = str(Path(saved_path).resolve()).replace('%','%%')
    arguments = f'"{escaped_path}"' if image.kind=='rom' else f'-s "{escaped_path}" "{ROM}"'
    return ('@echo off\nsetlocal DisableDelayedExpansion\nchcp 65001 >nul\n'
            f'cd /d "{emulator.parent}"\nstart "" "{emulator}" {flags}{arguments}\n')


def write_launcher(image, saved_path):
    target = Path(saved_path)
    launcher = target.with_suffix(target.suffix+'.启动.bat')
    # 直接写字节，避免 Windows 文本换行转换把 CRLF 再变成 CRCRLF。
    launcher.write_bytes(build_launcher(image,target).replace('\n','\r\n').encode('utf-8'))
    return launcher


_CLOSE_GAME_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$paths = @(ConvertFrom-Json $env:BAWANG_RESTART_PATHS)
$games = @(Get-Process -Name blastem -ErrorAction SilentlyContinue | Where-Object {
    $paths -contains $_.Path
})
foreach ($game in $games) {
    if (-not $game.HasExited) {
        if (-not $game.CloseMainWindow()) {
            throw "Cannot close game window (PID $($game.Id))."
        }
    }
}
foreach ($game in $games) {
    if (-not $game.WaitForExit(10000)) {
        throw "Game has not exited (PID $($game.Id))."
    }
}
'''


def close_project_games():
    """正常关闭本项目的两套 BlastEm，等待退出；不强杀其他进程。"""
    env = os.environ.copy()
    env['BAWANG_RESTART_PATHS'] = json.dumps([
        str(ROOT/'霸王三国志-免登录版'/folder/'blastem.exe')
        for folder in ('blastem','blastem-兼容模式')
    ],ensure_ascii=False)
    try:
        result = subprocess.run(
            ['powershell.exe','-NoProfile','-NonInteractive','-Command',_CLOSE_GAME_SCRIPT],
            env=env,capture_output=True,timeout=25,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired as e:
        raise OSError('等待游戏退出超时。保存文件已保留，请关闭游戏后手动运行启动文件。') from e
    if result.returncode:
        raise OSError('未能正常关闭游戏，可能有弹窗等待处理。保存文件已保留，请关闭游戏后手动运行启动文件。')


def restart_from_launcher(launcher):
    """保存完成后调用：先关闭旧实例，再执行这次保存的启动脚本。"""
    launcher = Path(launcher).resolve()
    if not launcher.is_file() or launcher.suffix.lower()!='.bat':
        raise OSError('启动文件不存在；未关闭游戏。')
    if os.name!='nt':
        raise OSError('自动退出并启动游戏目前仅支持 Windows。')
    close_project_games()
    os.startfile(str(launcher))
