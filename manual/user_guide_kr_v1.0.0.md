# SIM Card Reader — 사용자 가이드

> 버전: v2.0.0  
> 최종 수정: 2026-05-13

---

## 목차

1. [개요](#1-개요)
2. [화면 구성](#2-화면-구성)
3. [설치 및 실행](#3-설치-및-실행)
4. [연결하기](#4-연결하기)
5. [파일 탐색](#5-파일-탐색)
6. [파일 읽기](#6-파일-읽기)
7. [디코딩 뷰](#7-디코딩-뷰)
8. [ADM 인증](#8-adm-인증)
9. [파일 쓰기](#9-파일-쓰기)
10. [BER-TLV 파일 (URSP)](#10-ber-tlv-파일-ursp)
11. [덤프 내보내기 및 오프라인 모드](#11-덤프-내보내기-및-오프라인-모드)
12. [문제 해결](#12-문제-해결)

---

## 1. 개요

SIM Card Reader는 PC/SC 스마트카드 리더를 통해 SIM/USIM/ISIM 카드 파일을 읽고, 쓰고, 디코딩하는 웹 기반 도구입니다. 실행하면 웹 브라우저에서 동작합니다.

**주요 기능:**
- 200개 이상의 EF 파일 읽기 및 자동 디코딩
- ARR 기반 접근 제어를 적용한 EF 파일 쓰기
- BER-TLV 태그 기반 읽기/쓰기 (URSP, IMSConfigData 등)
- URSP 규칙 트리 디코딩 (3GPP TS 24.526)
- 전체 파일시스템 덤프 → JSON + Excel 자동 내보내기
- 오프라인 덤프 로드 (카드 없이 이전 덤프 열람)

---

## 2. 화면 구성

실행하면 자동으로 브라우저가 열리며 `http://127.0.0.1:8082` 에 접속됩니다.

### 상단 헤더 바

| 영역 | 설명 |
|------|------|
| 📡 SIM Card Reader | 앱 타이틀 |
| Reader 드롭다운 | 사용 가능한 PC/SC 리더 목록 |
| 🔌 Connect | 선택한 리더로 연결 시작 |
| ICCID / IMSI / MSISDN | 연결 후 SIM에서 읽은 가입자 정보 |
| 🔐 VERIFY ADM | ADM 키 인증 팝업 열기 |
| ADM1~4 상태 점 | 회색=미인증, 초록=인증 완료 |

### 메인 레이아웃

| 패널 | 설명 |
|------|------|
| 🗂️ SIM Files (좌측) | 파일 트리 탐색기 |
| 📄 File Contents (우측) | 선택한 파일의 내용 표시 (Decode/Raw 토글) |

---

## 3. 설치 및 실행

### 요구 사항

- **Python 3.10+**
- PC/SC 호환 스마트카드 리더 (예: HID OMNIKEY 3x21)
- SIM 카드

### macOS / Linux

```bash
git clone https://github.com/joostone-ahn/sim-reader.git
cd sim-reader
bash run/run.command
```

또는 `run/run.command` 파일을 더블클릭합니다.

첫 실행 시 가상환경 생성 및 의존성 설치가 자동으로 진행됩니다.

### Windows (EXE)

[Releases](https://github.com/joostone-ahn/sim-reader-releases/releases) 페이지에서 최신 exe를 다운로드하여 실행합니다.

---

## 4. 연결하기

### 리더 선택

1. PC/SC 리더에 SIM 카드를 삽입합니다
2. **Reader** 드롭다운에서 리더를 선택합니다 (기본값: 0번 리더)

### 연결 과정

**🔌 Connect** 버튼을 클릭하면 다음 과정이 자동으로 진행됩니다:

1. PC/SC 리더 연결 및 카드 초기화
2. MF 선택 → EF.ICCID 읽기
3. ADF.USIM 선택 → EF.IMSI, EF.MSISDN, EF.HPLMNwAcT 읽기
4. ADF.ISIM 선택 → EF.IMPI, EF.IMPU 읽기
5. 카드 정보를 헤더에 표시

연결이 완료되면:
- 버튼이 **⚡ Connected** 로 변경됩니다
- 파일 트리가 활성화됩니다
- ADM 인증 영역이 표시됩니다

### 에러 처리

| 에러 | 원인 |
|------|------|
| Reader not found | PC/SC 리더가 연결되지 않음 |
| No card in reader | 리더에 SIM 카드가 없음 |

---

## 5. 파일 탐색

### 파일 트리

SIM Files 패널에 파일이 애플리케이션별로 그룹화되어 표시됩니다:

- **MF** — Master File (ICCID, DIR, ARR)
- **ADF.USIM** — USIM 애플리케이션 파일 (DF.5GS, DF.GSM-ACCESS 등 하위 DF 포함)
- **ADF.ISIM** — ISIM 애플리케이션 파일

### 파일 항목 정보

각 파일 항목에는 다음이 표시됩니다:
- FID (4자리 hex)
- 파일명
- 구조 타입 약어 (TF=Transparent, LF=Linear Fixed, CF=Cyclic, BER-TLV)

### 접기/펼치기

- 각 DF 헤더를 클릭하면 하위 EF를 접거나 펼 수 있습니다
- **▼ Expand All / ▶ Collapse All** 버튼으로 전체 토글

### 상태 점 (Status Dot)

| 색상 | 의미 |
|------|------|
| ⚪ 회색 | 아직 읽지 않음 |
| 🟢 초록 | 읽기 성공 (클릭 시 캐시된 값 즉시 표시) |
| 🔴 빨강 | 읽기 실패 (클릭 시 재시도) |

---

## 6. 파일 읽기

### 개별 읽기

파일 트리에서 파일을 클릭하면 읽기가 시작됩니다.

읽기 방식은 파일 구조에 따라 자동 결정됩니다:
- **Transparent**: READ BINARY
- **Linear Fixed / Cyclic**: READ RECORD (각 레코드 순차)
- **BER-TLV**: RETRIEVE DATA (SW=62xx 연속 응답 자동 처리)

### 전체 읽기 (Read All Files)

**READ ALL FILES** 버튼을 클릭하면 `fsdump_custom --json` 명령으로 전체 파일시스템을 한 번에 읽습니다.

- MF, ADF.USIM, ADF.ISIM의 모든 EF를 순회
- 각 EF에 대해 raw hex + decoded JSON 동시 출력
- 완료 후 `logs/<ICCID>/`에 자동 내보내기

### 캐싱

한 번 읽은 파일은 캐시됩니다:
- 같은 파일을 다시 클릭하면 즉시 표시
- 쓰기 후에는 캐시가 삭제되고 자동으로 다시 읽기

---

## 7. 디코딩 뷰

### Decode / Raw 토글

File Contents 패널 상단의 토글로 표시 모드를 전환합니다:

- **🔍 Decode**: 파일 타입에 맞는 구조화된 뷰
- **🔢 Raw**: 원본 hex 데이터

### 파일별 디코딩 뷰

| 파일 타입 | 표시 형식 |
|-----------|-----------|
| PLMN 파일 (PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN) | MCC / MNC / AcT 테이블 |
| 서비스 테이블 (UST, IST, EST) | 서비스 번호 + 이름 + True/False 상태 |
| ACC (Access Control Class) | Class 0~15 + True/False 상태 |
| ARR (Access Rule Reference) | Read/Update/Write/Activate/Deactivate 조건 테이블 |
| URSP | 트리 형태 규칙 표시 (Precedence, TD, RSD) |
| 기타 EF | JSON 구조 (pySim 기반 디코딩) |

### 에러 표시

읽기 실패 시 SW 코드와 설명이 표시됩니다:

| SW | 설명 |
|----|------|
| 6982 | Security status not satisfied |
| 6A82 | File not found |
| 6981 | Command incompatible |
| 6983 | Authentication blocked |
| 6700 | Wrong length |

**SW=6982 시**: 해당 파일의 ARR 접근 조건이 함께 표시되어 필요한 ADM 키를 바로 확인할 수 있습니다.

### Copy 버튼

**📋 Copy** 버튼으로 현재 표시된 내용을 클립보드에 복사합니다:
- 테이블 뷰: TSV 형식 (Excel에 붙여넣기 가능)
- JSON 뷰: 포맷된 JSON 텍스트
- Raw 뷰: hex 문자열

---

## 8. ADM 인증

### ADM 팝업 열기

헤더의 **🔐 VERIFY ADM** 버튼을 클릭합니다.

### ADM1~ADM4 인증

팝업에 4개의 독립적인 ADM 키 입력란이 표시됩니다:
- 각 ADM 키는 16자리 hex (8바이트)
- 입력 시 실시간으로 글자 수 카운트 표시 (예: `(12/16)`)
- 16자리 유효한 hex가 입력되면 **Verify** 버튼 활성화
- 인증 성공 시:
  - 버튼이 초록색 "Verified"로 변경
  - 헤더의 해당 ADM 상태 점이 초록색으로 변경
  - Write 버튼 상태가 즉시 갱신

### 자동 채우기 (test_profile.json)

`test_profile.json` 파일이 존재하고 현재 MSISDN과 매칭되는 프로파일이 있으면, ADM 키가 자동으로 채워집니다.

파일 형식:
```json
{
  "profiles": [
    {
      "msisdn": "821012345678",
      "adm1": "0123456789ABCDEF"
    }
  ]
}
```

### Write 버튼 제어

| 조건 | Write 버튼 | 툴팁 |
|------|-----------|------|
| ALWAYS | ✅ 활성화 | (없음) |
| ADM 인증 완료 | ✅ 활성화 | (없음) |
| ADM 미인증 | ❌ 비활성화 | "🔐 ADM1 verification required" |
| NEVER | ❌ 비활성화 | "🚫 Write not allowed (NEVER)" |
| ARR 정보 없음 | ❌ 비활성화 | "🔐 ARR info not available" |

---

## 9. 파일 쓰기

### 전제 조건

1. 파일을 먼저 읽어야 합니다
2. ARR 접근 조건에 따라 Write 가능 여부가 결정됩니다

### 에디터 종류

파일 타입에 따라 적절한 에디터가 자동으로 선택됩니다:

#### Hex 에디터 (기본)

- 직접 hex 입력
- 바이트 수 실시간 표시 (예: `(20/20)`)
- 파일 크기와 일치해야 Write 버튼 활성화
- **↩ Restore** 버튼으로 원래 값 복원

#### PLMN 에디터

PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN 파일에 적용:

- **Table 모드**: MCC / MNC / AcT 입력 테이블
- **Hex 모드**: 직접 hex 편집
- **Table ↔ Hex 토글**: 양방향 동기화

#### 서비스 테이블 에디터 (UST/IST/EST)

- **Table 모드**: 서비스 번호 + 이름 + True/False 드롭다운
- **Hex 모드**: 직접 hex 편집
- 3GPP 표준 서비스명 자동 로드

#### ACC 에디터

- Class 0~15 각각에 True/False 드롭다운
- 16비트 비트맵으로 자동 인코딩

### 쓰기 실행

값을 수정한 후 **✏️ Write** 버튼을 클릭하면:

1. UPDATE BINARY 또는 UPDATE RECORD 전송
2. 1초 후 자동으로 파일을 다시 읽어 결과 확인
3. 성공 시 "✅ Done" 표시

### Record 선택 (Linear Fixed)

Linear Fixed 파일의 경우 **Record Number** 드롭다운으로 레코드를 선택하여 개별 쓰기가 가능합니다.

---

## 10. BER-TLV 파일 (URSP)

### 읽기

BER-TLV 파일(예: EF.URSP)은 RETRIEVE DATA로 읽습니다:

1. tag 0x80 데이터 요청
2. SW=62xx 시 연속 RETRIEVE DATA로 이어받기
3. 전체 데이터를 3GPP TS 24.526 기반으로 URSP 규칙 트리로 디코딩

### URSP 트리 뷰

```
URSP Rules
├─ URSP rule 1
│  ├─ Precedence: 0
│  ├─ Traffic descriptor
│  │  └─ OS Id + OS App Id
│  │     ├─ OS: Android
│  │     └─ Slice Category: ENTERPRISE
│  └─ Route selection descriptor list
│     └─ Route selection descriptor 1
│        ├─ Precedence: 255
│        └─ Route selection descriptor contents
│           └─ S-NSSAI
│              ├─ SST: 01 (eMBB)
│              └─ SD: 000001
```

### BER-TLV 쓰기

1. **Tag 선택**: 드롭다운에서 태그 선택
2. **Hex 데이터 편집**: 전체 TLV 형식 (tag + BER-length + value)
3. **유효성 검증**: 태그 일치 + BER-length 검증
4. **Write 실행**: DELETE DATA + SET DATA 순서로 실행
5. **↩ Restore**: 원래 TLV 값으로 복원

### URSP Rule Analyzer

외부 URSP 분석 도구: 🔗 https://huggingface.co/spaces/Joostone/ursp-rule-analyzer

---

## 11. 덤프 내보내기 및 오프라인 모드

### 자동 내보내기

Read All Files 완료 시 자동으로 `logs/<ICCID>/`에 저장됩니다:

| 파일 | 내용 |
|------|------|
| dump.json | 전체 덤프 (raw + decoded) |
| dump.xlsx | Excel 요약 (Card Info, Files, Errors 시트) |
| decoded/*.json | 개별 EF 디코딩 결과 |

### 오프라인 모드 (Load Dump)

**Load Dump** 버튼으로 이전에 저장한 `dump.json`을 로드할 수 있습니다:
- SIM 카드 없이 이전 덤프 열람 가능
- 파일 트리 + 디코딩 뷰 동일하게 동작
- ADM 인증 상태도 복원

---

## 12. 문제 해결

### "Reader not found"

- PC/SC 리더가 USB로 연결되어 있는지 확인
- macOS: `pcsctest` 명령으로 리더 인식 확인
- Windows: 장치 관리자에서 스마트카드 리더 확인

### "No card in reader"

- SIM 카드가 리더에 올바르게 삽입되어 있는지 확인
- 카드 접점이 깨끗한지 확인

### Write 버튼 비활성화

- 버튼에 마우스를 올려 툴팁 확인 — 필요한 ADM 키가 표시됩니다
- ADM 팝업에서 해당 키를 인증하세요
- NEVER 조건인 파일은 쓰기 불가

### 연결 타임아웃

- 리더와 카드 접촉 불량 가능성
- USB 케이블 분리 후 재연결
- 다른 리더 슬롯 시도

### pySim 관련 에러

- `pip install -e src/pysim` 재설치 시도
- Python 3.10+ 버전 확인

---

**© 2026 JUSEOK AHN. All rights reserved.**
