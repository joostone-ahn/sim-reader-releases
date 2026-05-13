# SIM Card Reader — User Guide

> Version: v1.0.0  
> Last updated: 2026-05-13

---

## Table of Contents

1. [Launch](#1-launch)
2. [Screen Layout](#2-screen-layout)
3. [Connecting](#3-connecting)
4. [Reading Files](#4-reading-files)
5. [Decoded Views](#5-decoded-views)
6. [ADM Verification](#6-adm-verification)
7. [Writing to Files](#7-writing-to-files)
8. [BER-TLV Files (URSP)](#8-ber-tlv-files-ursp)
9. [Export & Offline Mode](#9-export--offline-mode)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Launch

### Requirements

- PC/SC compatible smart card reader (e.g. HID OMNIKEY 3x21)
- SIM card

### How to Run

Double-click the exe file. The browser opens automatically at `http://127.0.0.1:8082`.

---

## 2. Screen Layout

### Header Bar

| Element | Description |
|---------|-------------|
| 🗂️ Load Dump | Load previous dump.json (offline mode) |
| 🔌 Connect | Connect to selected reader |
| ICCID / IMSI / MSISDN / HPLMNwAcT / IMPI / IMPU | Card info read from SIM |
| 📂 READ ALL FILES | Read entire file system + export |
| 🔐 VERIFY ADM | Opens ADM key verification popup |
| ADM1–4 dots | Gray = not verified, Green = verified |

### Main Layout

| Panel | Description |
|-------|-------------|
| 🗂️ SIM Files (left) | File tree browser |
| 📄 File Contents (right) | Selected file content (Decode/Raw toggle) |

---

## 3. Connecting

1. Insert SIM card into PC/SC reader
2. Select reader from the **Reader** dropdown (default: reader 0)
3. Click **🔌 Connect**

On connection, the tool automatically:
- Initializes card → reads EF.ICCID, EF.IMSI, EF.MSISDN, EF.HPLMNwAcT, EF.IMPI, EF.IMPU
- Displays card info in header
- Activates file tree

| Error | Cause |
|-------|-------|
| Reader not found | PC/SC reader not connected |
| No card in reader | No SIM card in the reader |

---

## 4. Reading Files

### Individual Read

Click any file in the tree to read it. Read method is determined automatically:

| Structure | Method |
|-----------|--------|
| Transparent (TF) | READ BINARY |
| Linear Fixed / Cyclic (LF/CF) | READ RECORD (sequential) |
| BER-TLV | RETRIEVE DATA (auto-continuation on SW=62xx) |

### Read All Files

Click **READ ALL FILES** to dump the entire file system (200–300 files across MF, ADF.USIM, ADF.ISIM, approximately 30 seconds). Auto-exports to `logs/<ICCID>/` on completion.

### File Tree

Files are grouped by application:

- **MF** — Master File (ICCID, DIR, ARR)
- **ADF.USIM** — USIM files (includes sub-DFs: DF.5GS, DF.GSM-ACCESS, etc.)
- **ADF.ISIM** — ISIM files

Each file entry shows:

| Column | Description |
|--------|-------------|
| File Name | File/folder name (tree indentation) |
| FID | File Identifier (hex) |
| Type | TF, LF, CF, BER-TLV, DF, ADF |
| ARR | Access Rule Reference record number |
| Size | File size (bytes) |
| Rec# | Number of records |

### Collapse / Expand

- ▼ 📂 / ▶ 📁 icons to collapse/expand individual DFs
- **Expand All / Collapse All** buttons for bulk toggle
- Default: MF sub-DFs collapsed, ADF.USIM/ADF.ISIM expanded

### Status Dots

| Color | Meaning |
|-------|---------|
| ⚪ Gray | Not yet read |
| 🟢 Green | Read OK (re-click shows cached value instantly) |
| 🔴 Red | Read failed (re-click retries) |

### Caching

- Read files are cached; re-click shows instantly
- After write, cache is cleared → auto re-read

---

## 5. Decoded Views

### Decode / Raw Toggle

- **🔍 Decode**: Structured view per file type
- **🔢 Raw**: Original hex data

### File-Specific Decoding

| File Type | Display Format |
|-----------|---------------|
| PLMN files (PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN) | MCC / MNC / AcT table |
| Service tables (UST, IST, EST) | Service number + name + True/False |
| ACC (Access Control Class) | Class 0–15 + True/False |
| ARR (Access Rule Reference) | Read/Update/Write/Activate/Deactivate conditions |
| URSP | Tree-formatted rules (Precedence, TD, RSD) |
| Other EFs | JSON (pySim-based) |

### Error Display

| SW | Description |
|----|-------------|
| 6982 | Security status not satisfied |
| 6A82 | File not found |
| 6981 | Command incompatible |
| 6983 | Authentication blocked |
| 6700 | Wrong length |
| 6A83 | Record not found |
| 6A84 | Not enough memory |
| 6D00 | INS not supported |
| 6E00 | Class not supported |

> On SW=6982, the file's ARR access conditions (Read/Update) are shown alongside the error, identifying which ADM key is needed.

### Copy Button

📋 Copy copies the current view to clipboard:
- Table: TSV (paste into Excel)
- JSON: Formatted text
- Raw: Hex string

---

## 6. ADM Verification

### How to Verify

1. Click **🔐 VERIFY ADM** in the header
2. Enter the required ADM key (16 hex chars, 8 bytes)
3. Click **Verify**

On success:
- Button turns green "Verified", input becomes read-only
- Header dot turns green
- Previously failed files (SW=6982) are auto re-read + dump re-saved

### Auto-fill (test_profile.json)

Place `test_profile.json` in the same folder as the exe. If MSISDN matches, ADM keys are auto-filled:

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

### Write Button State

| Condition | Write Button | Tooltip |
|-----------|-------------|---------|
| ALWAYS | ✅ Enabled | — |
| ADM verified | ✅ Enabled | — |
| ADM not verified | ❌ Disabled | "🔐 ADM1 verification required" |
| NEVER | ❌ Disabled | "🚫 Write not allowed (NEVER)" |
| No ARR info | ❌ Disabled | "🔐 ARR info not available" |

---

## 7. Writing to Files

### Prerequisites

- File must be read first
- ADM verification may be required depending on ARR conditions

### Editor Types

Automatically selected by file type:

#### Hex Editor (default)

- Direct hex input, real-time byte count
- Write enables only when length matches file size
- **↩ Restore** to revert

#### PLMN Editor

For PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN:

- **Table mode**: Type MCC / MNC / AcT directly
  - Empty rows → FFFFFF encoding
  - MCC/MNC must both be filled or both empty
- **Hex mode**: Direct hex editing
- Table ↔ Hex bidirectional sync

#### Service Table Editor (UST/IST/EST)

- Service number + 3GPP standard name + True/False dropdown
- Table ↔ Hex bidirectional sync

#### ACC Editor

- True/False dropdown for Class 0–15
- Auto-encoded as 16-bit bitmap

### Executing a Write

Click **✏️ Write** → UPDATE BINARY/RECORD sent → auto re-read after 1s → "✅ Done"

### Record Selection (Linear Fixed)

Record Number dropdown to select and write individual records.

---

## 8. BER-TLV Files (URSP)

### Reading

1. Request tag 0x80 data (RETRIEVE DATA)
2. On SW=62xx, continue fetching remaining chunks
3. Decode as URSP rule tree per 3GPP TS 24.526

> If URSP data is empty, the raw value reads as `8001FF` (tag=80, length=01, value=FF), and the Decode view shows `(empty — 0xFF)`.

### URSP Tree View

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

### BER-TLV Write

1. **Tag selection**: Choose existing tag or new tag 0x80
2. **Hex editing**: Full TLV format — tag (80) + BER-length + value
3. **Validation** (real-time):
   - `Hex data must start with tag 0x80` — first byte doesn't match selected tag
   - `Length mismatch: expected N bytes, got M bytes` — BER-length doesn't match actual value length
4. **Write**: DELETE DATA → SET DATA sequence
5. **↩ Restore**: Revert to original TLV value

> The Raw view value and the Write popup initial value are the same Full TLV hex.

### URSP Rule Analyzer

External tool: 🔗 https://huggingface.co/spaces/Joostone/ursp-rule-analyzer

---

## 9. Export & Offline Mode

### Auto-Export

On Read All Files completion, auto-saved to `logs/<ICCID>/` (next to the exe):

| File | Content |
|------|---------|
| dump.json | Full dump (raw + decoded) |
| dump.xlsx | Excel summary (Card Info, Files, Errors sheets) |
| decoded/*.json | Individual EF decode results |

### Offline Mode (Load Dump)

Click **Load Dump** to load a previous `dump.json`:
- Browse previous dumps without a SIM card
- File tree + decode views work identically
- ADM verification state restored

---

## 10. Troubleshooting

| Symptom | Solution |
|---------|----------|
| "Reader not found" | Check PC/SC reader USB connection; verify in Device Manager |
| "No card in reader" | Check SIM card insertion and contact cleanliness |
| Write button disabled | Hover button → tooltip shows required ADM key; verify it |
| Connection timeout | Reader-card contact issue; reconnect USB, try different slot |

---

**© 2026 JUSEOK AHN. All rights reserved.**
