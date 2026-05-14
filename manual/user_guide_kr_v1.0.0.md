# SIM Card Reader — 사용자 가이드

> 버전: v1.0.0  
> 최종 수정: 2026-05-13

---

## 목차

1. [실행](#1-실행)
2. [화면 구성](#2-화면-구성)
3. [연결하기](#3-연결하기)
4. [파일 읽기](#4-파일-읽기)
5. [디코딩 뷰](#5-디코딩-뷰)
6. [ADM 인증](#6-adm-인증)
7. [파일 쓰기](#7-파일-쓰기)
8. [BER-TLV 파일 (URSP)](#8-ber-tlv-파일-ursp)
9. [덤프 내보내기 및 오프라인 모드](#9-덤프-내보내기-및-오프라인-모드)
10. [문제 해결](#10-문제-해결)

---

## 1. 실행

### 준비물

- PC/SC 호환 스마트카드 리더 (예: HID OMNIKEY 3x21)
- SIM 카드

### 실행 방법

exe 파일을 더블클릭하면 브라우저가 자동으로 열리며 `http://127.0.0.1:8082` 에 접속됩니다.

---

## 2. 화면 구성

### 상단 헤더 바

| 영역 | 설명 |
|------|------|
| 🗂️ Load Dump | 이전 dump.json 로드 (오프라인 모드) |
| 🔌 Connect | 선택한 리더로 연결 |
| ICCID / IMSI / MSISDN / HPLMNwAcT / IMPI / IMPU | 연결 후 SIM에서 읽은 카드 정보 |
| 📂 READ ALL FILES | 전체 파일시스템 읽기 + 내보내기 |
| 🔐 VERIFY ADM | ADM 키 인증 팝업 |
| ADM1~4 상태 점 | 회색=미인증, 초록=인증 완료 |

### 메인 레이아웃

| 패널 | 설명 |
|------|------|
| 🗂️ SIM Files (좌측) | 파일 트리 탐색기 |
| 📄 File Contents (우측) | 선택한 파일의 내용 (Decode/Raw 토글) |

---

## 3. 연결하기

1. PC/SC 리더에 SIM 카드를 삽입합니다
2. **Reader** 드롭다운에서 리더를 선택합니다 (기본값: 0번)
3. **🔌 Connect** 클릭

연결 시 자동으로 수행되는 작업:
- 카드 초기화 → EF.ICCID, EF.IMSI, EF.MSISDN, EF.HPLMNwAcT, EF.IMPI, EF.IMPU 읽기
- 헤더에 카드 정보 표시
- 파일 트리 활성화

| 에러 | 원인 |
|------|------|
| Reader not found | PC/SC 리더가 연결되지 않음 |
| No card in reader | 리더에 SIM 카드가 없음 |

---

## 4. 파일 읽기

### 개별 읽기

파일 트리에서 파일을 클릭하면 자동으로 읽기가 시작됩니다. 읽기 방식은 파일 구조에 따라 자동 결정:

| 구조 | 읽기 방식 |
|------|-----------|
| Transparent (TF) | READ BINARY |
| Linear Fixed / Cyclic (LF/CF) | READ RECORD (각 레코드 순차) |
| BER-TLV | RETRIEVE DATA (SW=62xx 연속 응답 자동 처리) |

### 전체 읽기 (Read All Files)

**READ ALL FILES** 버튼 클릭 시 MF, ADF.USIM, ADF.ISIM의 모든 EF를 한 번에 읽습니다 (200~300개, 약 20초 소요). 완료 후 자동으로 `logs/<ICCID>/`에 내보내기됩니다.

### 파일 트리

파일이 애플리케이션별로 그룹화되어 표시됩니다:

- **MF** — Master File (ICCID, DIR, ARR)
- **ADF.USIM** — USIM 파일 (DF.5GS, DF.GSM-ACCESS 등 하위 DF 포함)
- **ADF.ISIM** — ISIM 파일

각 파일 항목에 표시되는 정보:

| 컬럼 | 설명 |
|------|------|
| File Name | 파일/폴더명 (트리 들여쓰기) |
| FID | File Identifier (hex) |
| Type | TF, LF, CF, BER-TLV, DF, ADF |
| ARR | Access Rule Reference 레코드 번호 |
| Size | 파일 크기 (바이트) |
| Rec# | 레코드 수 |

### 접기/펼치기

- ▼ 📂 / ▶ 📁 아이콘으로 개별 DF 접기/펼치기
- **Expand All / Collapse All** 버튼으로 전체 토글
- 기본: MF 하위 DF는 접힘, ADF.USIM/ADF.ISIM은 펼침

### 상태 점

| 색상 | 의미 |
|------|------|
| ⚪ 회색 | 미읽기 |
| 🟢 초록 | 읽기 성공 (재클릭 시 캐시 즉시 표시) |
| 🔴 빨강 | 읽기 실패 (재클릭 시 재시도) |

### 캐싱

- 한 번 읽은 파일은 캐시되어 재클릭 시 즉시 표시
- 쓰기 후 캐시 삭제 → 자동 재읽기

---

## 5. 디코딩 뷰

### Decode / Raw 토글

- **🔍 Decode**: 파일 타입에 맞는 구조화된 뷰
- **🔢 Raw**: 원본 hex 데이터

### 파일별 디코딩

| 파일 타입 | 표시 형식 |
|-----------|-----------|
| PLMN 파일 (PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN) | MCC / MNC / AcT 테이블 |
| 서비스 테이블 (UST, IST, EST) | 서비스 번호 + 이름 + True/False |
| ACC (Access Control Class) | Class 0~15 + True/False |
| ARR (Access Rule Reference) | Read/Update/Write/Activate/Deactivate 조건 |
| URSP | 트리 형태 규칙 (Precedence, TD, RSD) |
| 기타 EF | JSON (pySim 기반) |

### 에러 표시

| SW | 설명 |
|----|------|
| 6982 | Security status not satisfied |
| 6A82 | File not found |
| 6981 | Command incompatible |
| 6983 | Authentication blocked |
| 6700 | Wrong length |
| 6A83 | Record not found |
| 6A84 | Not enough memory |
| 6D00 | INS not supported |
| 6E00 | Class not supported |

> SW=6982 발생 시 해당 파일의 ARR 접근 조건(Read/Update)이 함께 표시되어 필요한 ADM 키를 바로 확인할 수 있습니다.

### Copy 버튼

📋 Copy로 현재 뷰를 클립보드에 복사:
- 테이블: TSV (Excel 붙여넣기 가능)
- JSON: 포맷된 텍스트
- Raw: hex 문자열

---

## 6. ADM 인증

### 인증 방법

1. 헤더의 **🔐 VERIFY ADM** 클릭
2. ADM1~4 중 필요한 키 입력 (16자리 hex, 8바이트)
3. **Verify** 클릭

인증 성공 시:
- 버튼이 초록색 "Verified"로 변경
- 입력란 읽기 전용 전환
- 헤더 상태 점 초록색 변경
- 이전에 6982로 실패했던 파일들이 자동 재읽기 + 덤프 재저장

### 자동 채우기 (test_profile.json)

exe와 같은 폴더에 `test_profile.json`이 있고 MSISDN이 매칭되면 ADM 키가 자동 채워집니다:

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

### Write 버튼 상태

| 조건 | Write 버튼 | 툴팁 |
|------|-----------|------|
| ALWAYS | ✅ 활성화 | — |
| ADM 인증 완료 | ✅ 활성화 | — |
| ADM 미인증 | ❌ 비활성화 | "🔐 ADM1 verification required" |
| NEVER | ❌ 비활성화 | "🚫 Write not allowed (NEVER)" |
| ARR 정보 없음 | ❌ 비활성화 | "🔐 ARR info not available" |

---

## 7. 파일 쓰기

### 전제 조건

- 파일을 먼저 읽어야 합니다
- ARR 조건에 따라 ADM 인증이 필요할 수 있습니다

### 에디터 종류

파일 타입에 따라 자동 선택됩니다:

#### Hex 에디터 (기본)

- 직접 hex 입력, 바이트 수 실시간 표시
- 파일 크기와 일치해야 Write 활성화
- **↩ Restore**로 원래 값 복원

#### PLMN 에디터

PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN:

- **Table 모드**: MCC / MNC / AcT 직접 입력
  - 빈 행 → FFFFFF 인코딩
  - MCC/MNC 둘 다 입력 또는 둘 다 비워야 함
- **Hex 모드**: 직접 hex 편집
- Table ↔ Hex 양방향 동기화

#### 서비스 테이블 에디터 (UST/IST/EST)

- 서비스 번호 + 3GPP 표준 서비스명 + True/False 드롭다운
- Table ↔ Hex 양방향 동기화

#### ACC 에디터

- Class 0~15 각각 True/False 드롭다운
- 16비트 비트맵 자동 인코딩

### 쓰기 실행

**✏️ Write** 클릭 → UPDATE BINARY/RECORD 전송 → 1초 후 자동 재읽기 → "✅ Done"

### Record 선택 (Linear Fixed)

Record Number 드롭다운으로 레코드 선택 → 개별 쓰기 가능

---

## 8. BER-TLV 파일 (URSP)

### 읽기

1. tag 0x80 데이터 요청 (RETRIEVE DATA)
2. SW=62xx 시 연속 요청으로 이어받기
3. 3GPP TS 24.526 기반 URSP 규칙 트리로 디코딩

> URSP 데이터가 비어있는 경우 raw 값은 `8001FF` (tag=80, length=01, value=FF)로 읽히며, Decode 뷰에서는 `(empty — 0xFF)` 로 표시됩니다.

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

1. **Tag 선택**: 드롭다운에서 기존 태그 선택 (또는 새 태그 0x80)
2. **Hex 편집**: Full TLV 형식 — tag (80) + BER-length + value
3. **유효성 검증** (실시간):
   - `Hex data must start with tag 0x80` — 첫 바이트가 선택된 태그와 불일치
   - `Length mismatch: expected N bytes, got M bytes` — BER-length와 실제 value 길이 불일치
4. **Write**: DELETE DATA → SET DATA 순서 실행
5. **↩ Restore**: 원래 TLV 값 복원

> Raw 뷰에서 보이는 값과 Write 팝업의 초기값은 동일한 Full TLV hex입니다.

### URSP Rule Analyzer

외부 분석 도구: 🔗 https://huggingface.co/spaces/Joostone/ursp-rule-analyzer

---

## 9. 덤프 내보내기 및 오프라인 모드

### 자동 내보내기

Read All Files 완료 시 exe와 같은 경로의 `logs/<ICCID>/`에 자동 저장:

| 파일 | 내용 |
|------|------|
| dump.json | 전체 덤프 (raw + decoded) |
| dump.xlsx | Excel 요약 (Card Info, Files, Errors 시트) |
| decoded/*.json | 개별 EF 디코딩 결과 |

### 오프라인 모드 (Load Dump)

**Load Dump** 버튼으로 이전 `dump.json`을 로드:
- SIM 카드 없이 이전 덤프 열람
- 파일 트리 + 디코딩 뷰 동일하게 동작
- ADM 인증 상태 복원

---

## 10. 문제 해결

| 증상 | 해결 |
|------|------|
| "Reader not found" | PC/SC 리더 USB 연결 확인, 장치 관리자에서 스마트카드 리더 확인 |
| "No card in reader" | SIM 카드 삽입 상태 및 접점 확인 |
| Write 버튼 비활성화 | 버튼 hover → 툴팁에서 필요한 ADM 키 확인 후 인증 |
| 연결 타임아웃 | 리더-카드 접촉 불량, USB 재연결, 다른 슬롯 시도 |

---

**© 2026 JUSEOK AHN. All rights reserved.**
