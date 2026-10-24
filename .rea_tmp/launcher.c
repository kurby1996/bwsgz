#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
int WINAPI wWinMain(HINSTANCE a,HINSTANCE b,PWSTR args,int show){
 wchar_t dir[32768],exe[32768],cmd[32768];
 GetModuleFileNameW(NULL,dir,32768);
 wchar_t *slash=wcsrchr(dir,L'\\'); if(!slash)return 1; *slash=0;
 wcscat(dir,L"\\runtime");
 swprintf(exe,32768,L"%ls\\XiaoJi.exe",dir);
 swprintf(cmd,32768,L"\"%ls\" %ls",exe,args);
 SetCurrentDirectoryW(dir);
 STARTUPINFOW si={sizeof(si)}; PROCESS_INFORMATION pi={0};
 if(!CreateProcessW(exe,cmd,NULL,NULL,FALSE,0,NULL,dir,&si,&pi)){
  wchar_t msg[256];swprintf(msg,256,L"Unable to launch XiaoJi. Windows error: %lu",GetLastError());
  MessageBoxW(NULL,msg,L"XiaoJi",MB_ICONERROR);return 2;
 }
 CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return 0;
}
