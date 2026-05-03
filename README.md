# Avorion Server Manager (Modern GUI) 🚀

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-1.2.1-orange.svg)

아보리온(Avorion) 데디케이티드 서버를 쉽고 세련되게 관리할 수 있는 파이썬 기반의 데스크톱 매니저입니다.

## ✨ 주요 기능

- **모던한 UI/UX**: CustomTkinter를 활용한 다크 모드 지원 및 카드형 레이아웃 인터페이스.
- **서버 제어**: 원클릭 서버 시작/중지 및 실시간 콘솔 로그 확인.
- **게임 설정 GUI 편집기**: `server.ini` 파일을 직접 열지 않고 UI에서 게임 규칙(난이도, 인원 등) 수정 가능. (New!)
- **실시간 자원 모니터링**: 서버 프로세스의 CPU 및 RAM 사용량을 대시보드에서 즉시 확인 가능.
- **자동 설치 및 업데이트**: SteamCMD 연동을 통해 아보리온 서버를 자동으로 설치하고 최신 버전으로 유지.
- **스마트 서버 로딩**: 기존 서버 폴더를 자동으로 인식하거나 새로운 서버 위치를 간편하게 지정.
- **디스코드 연동**: 서버 시작 및 종료 상태를 디스코드 웹훅(Webhook)을 통해 실시간 알림.
- **관리자 도구**: `/say` 명령어 커스텀 처리 등 게임 내 관리 편의 기능 제공.

## 🚀 시작하기

1. **저장소 클론**:
   ```bash
   git clone https://github.com/Koharu37/avorion-server-manager-python.git
   cd avorion-server-manager-python
   ```

2. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```

3. **실행**:
   ```bash
   python gui_app.py
   ```

## 🛠 빌드 방법 (Executable)

PyInstaller를 사용하여 단일 실행 파일(`.exe`)을 만들 수 있습니다.

```bash
pyinstaller --noconsole --onefile gui_app.py
```

## 📋 버전 관리 기준 (SemVer)

이 프로젝트는 **Semantic Versioning** 가이드를 따릅니다.
- **MAJOR**: 대규모 UI 개편 또는 구조적 변경
- **MINOR**: 신규 기능 추가 (예: 맵 시각화, 백업 기능 등)
- **PATCH**: 버그 수정 및 사소한 개선

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
