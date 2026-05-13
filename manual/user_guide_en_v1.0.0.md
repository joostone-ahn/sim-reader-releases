# SIM Card Reader — User Guide

> Version: v2.0.0  
> Last updated: 2026-05-13

---

## Table of Contents

1. [Overview](#1-overview)
2. [Screen Layout](#2-screen-layout)
3. [Installation & Launch](#3-installation--launch)
4. [Connecting to a Reader](#4-connecting-to-a-reader)
5. [Browsing SIM Files](#5-browsing-sim-files)
6. [Reading Files](#6-reading-files)
7. [Decoded Views](#7-decoded-views)
8. [ADM Verification](#8-adm-verification)
9. [Writing to Files](#9-writing-to-files)
10. [BER-TLV Files (URSP)](#10-ber-tlv-files-ursp)
11. [Export & Offline Mode](#11-export--offline-mode)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Overview

SIM Card Reader is a web-based application for reading, writing, and decoding SIM/USIM/ISIM card files via a PC/SC smart card reader. Launch the application and it opens automatically in your browser.

**Key capabilities:**
- Read and auto-decode 200+ EF files across MF, ADF.USIM, and ADF.ISIM
- Write to EF files with ARR-based access control enforcement
- BER-TLV tag-based read/write (URSP, IMSConfigData, etc.)
- URSP rule tree decoding (3GPP TS 24.526)
- Full file system dump → JSON + Excel auto-export
- Offline dump loading (browse previous dumps without a SIM card)

---

## 2. Screen Layout

Launch the application and the browser opens automatically at `http://127.0.0.1:8082`.

### Header Bar

| Element | Description |
|---------|-------------|
| 📡 SIM Card Reader | App title |
| Reader dropdown | Lists available PC/SC readers |
| 🔌 Connect | Initiates connection to the selected reader |
| ICCID / IMSI / MSISDN | Subscriber info read from SIM after connection |
| 🔐 VERIFY ADM | Opens ADM key verification popup |
| ADM1–4 dots | Gray = not verified, Green = verified |

### Main Layout

| Panel | Description |
|-------|-------------|
| 🗂️ SIM Files (left) | File tree browser |
| 📄 File Contents (right) | Displays content of the selected file (Decode/Raw toggle) |

---

## 3. Installation & Launch

### Requirements

- **Python 3.10+**
- PC/SC compatible smart card reader (e.g. HID OMNIKEY 3x21)
- SIM card

### macOS / Linux

```bash
git clone https://github.com/joostone-ahn/sim-reader.git
cd sim-reader
bash run/run.command
```

Or double-click `run/run.command`. On first run, a virtual environment is created and dependencies are installed automatically.

### Windows (EXE)

Download the latest exe from [Releases](https://github.com/joostone-ahn/sim-reader-releases/releases) and run it.

---

## 4. Connecting to a Reader

### Selecting a Reader

1. Insert a SIM card into the PC/SC reader
2. Select the reader from the **Reader** dropdown (default: reader 0)

### Connection Sequence

Click **🔌 Connect** to start the automatic connection sequence:

1. Connect to PC/SC reader and initialize card
2. Select MF → Read EF.ICCID
3. Select ADF.USIM → Read EF.IMSI, EF.MSISDN, EF.HPLMNwAcT
4. Select ADF.ISIM → Read EF.IMPI, EF.IMPU
5. Display card info in header

When connection completes:
- Button changes to **⚡ Connected**
- File tree becomes active
- ADM verification area appears

### Error Handling

| Error | Cause |
|-------|-------|
| Reader not found | PC/SC reader not connected |
| No card in reader | No SIM card in the reader |

---

## 5. Browsing SIM Files

### File Tree

The SIM Files panel displays files grouped by application:

- **MF** — Master File (ICCID, DIR, ARR)
- **ADF.USIM** — USIM application files (includes sub-DFs: DF.5GS, DF.GSM-ACCESS, etc.)
- **ADF.ISIM** — ISIM application files

### File Entry Information

Each file entry displays:
- FID (4-digit hex)
- File name
- Structure type abbreviation (TF = Transparent, LF = Linear Fixed, CF = Cyclic, BER-TLV)

### Collapsing / Expanding

- Click any DF header to collapse or expand its child EFs
- Use **▼ Expand All / ▶ Collapse All** buttons to toggle all at once

### Status Dots

| Color | Meaning |
|-------|---------|
| ⚪ Gray | Not yet read |
| 🟢 Green | Read successfully (clicking again shows cached value instantly) |
| 🔴 Red | Read failed (clicking again retries) |

---

## 6. Reading Files

### Individual Read

Click any file in the tree to read it. The read method is determined automatically by file structure:

- **Transparent**: READ BINARY
- **Linear Fixed / Cyclic**: READ RECORD (sequential read of each record)
- **BER-TLV**: RETRIEVE DATA (automatic continuation on SW=62xx)

### Read All Files

Click **READ ALL FILES** to dump the entire file system using `fsdump_custom --json`:

- Walks through all DFs (MF, ADF.USIM, ADF.ISIM) and reads every EF
- Outputs raw hex + decoded JSON simultaneously
- Auto-exports to `logs/<ICCID>/` on completion

### Caching

Once a file is read, it is cached:
- Clicking the same file again displays the cached value instantly
- After a write operation, the cache is cleared and the file is automatically re-read

---

## 7. Decoded Views

### Decode / Raw Toggle

Use the toggle at the top of the File Contents panel to switch display modes:

- **🔍 Decode**: Structured view tailored to the file type
- **🔢 Raw**: Original hex data

### File-Specific Decode Views

| File Type | Display Format |
|-----------|---------------|
| PLMN files (PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, EHPLMN) | MCC / MNC / AcT table |
| Service tables (UST, IST, EST) | Service number + name + True/False status |
| ACC (Access Control Class) | Class 0–15 + True/False status |
| ARR (Access Rule Reference) | Read/Update/Write/Activate/Deactivate conditions table |
| URSP | Tree-formatted rule display (Precedence, TD, RSD) |
| Other EFs | JSON structure (pySim-based decoding) |

### Error Display

When a read fails, the SW code and its description are shown:

| SW | Description |
|----|-------------|
| 6982 | Security status not satisfied |
| 6A82 | File not found |
| 6981 | Command incompatible |
| 6983 | Authentication blocked |
| 6700 | Wrong length |

**On SW=6982**: The file's ARR access conditions are displayed alongside the error, helping identify which ADM key is required.

### Copy Button

Click **📋 Copy** to copy the current view to clipboard:
- Table views: TSV format (paste directly into Excel)
- JSON views: Formatted JSON text
- Raw view: Hex string

---

## 8. ADM Verification

### Opening the ADM Popup

Click the **🔐 VERIFY ADM** button in the header bar.

### ADM1–ADM4 Verification

The popup shows four independent ADM key input fields:
- Each ADM key is 16 hex characters (8 bytes)
- Character count shown in real-time (e.g., `(12/16)`)
- **Verify** button enables when 16 valid hex characters are entered
- On successful verification:
  - Button turns green and shows "Verified"
  - Corresponding ADM dot in the header turns green
  - Write button state is immediately refreshed

### Auto-fill (test_profile.json)

If `test_profile.json` exists and contains a profile matching the current MSISDN, ADM keys are automatically filled.

File format:
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

### Write Button Control

| Condition | Write Button | Tooltip |
|-----------|-------------|---------|
| ALWAYS | ✅ Enabled | (none) |
| ADM verified | ✅ Enabled | (none) |
| ADM not verified | ❌ Disabled | "🔐 ADM1 verification required" |
| NEVER | ❌ Disabled | "🚫 Write not allowed (NEVER)" |
| No ARR info | ❌ Disabled | "🔐 ARR info not available" |

---

## 9. Writing to Files

### Prerequisites

1. The file must be read first (loads current data and metadata)
2. Write availability is determined by ARR access conditions

### Editor Types

The appropriate editor is automatically selected based on file type:

#### Hex Editor (default)

- Direct hex input
- Real-time byte count display (e.g., `(20/20)`)
- Write button enables only when data length matches expected file size
- **↩ Restore** button reverts to the original value

#### PLMN Editor

Applies to PLMNwAcT, OPLMNwAcT, HPLMNwAcT, FPLMN, and EHPLMN files:

- **Table mode**: MCC / MNC / AcT input table
- **Hex mode**: Direct hex editing
- **Table ↔ Hex toggle**: Bidirectional sync

#### Service Table Editor (UST/IST/EST)

- **Table mode**: Service number + name + True/False dropdown
- **Hex mode**: Direct hex editing
- 3GPP standard service names loaded automatically

#### ACC Editor

- True/False dropdown for each of Class 0–15
- Automatically encoded as 16-bit bitmap

### Executing a Write

Once you modify a value, click **✏️ Write** to:

1. Send UPDATE BINARY or UPDATE RECORD
2. After 1 second, the file is automatically re-read to confirm
3. On success: "✅ Done" is displayed

### Record Selection (Linear Fixed)

For Linear Fixed files, a **Record Number** dropdown allows selecting and writing individual records.

---

## 10. BER-TLV Files (URSP)

### Reading

BER-TLV files (e.g., EF.URSP) are read using RETRIEVE DATA:

1. Request tag 0x80 data
2. On SW=62xx, continue with repeated RETRIEVE DATA to fetch remaining chunks
3. All chunks are concatenated and decoded as a URSP rule tree per 3GPP TS 24.526

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

1. **Tag selection**: Choose a tag from the dropdown
2. **Hex data editing**: Full TLV format (tag + BER-length + value)
3. **Validation**: Tag match + BER-length verification
4. **Write execution**: DELETE DATA + SET DATA in sequence
5. **↩ Restore**: Reverts to the original TLV value

### URSP Rule Analyzer

External URSP analysis tool: 🔗 https://huggingface.co/spaces/Joostone/ursp-rule-analyzer

---

## 11. Export & Offline Mode

### Auto-Export

When Read All Files completes, data is automatically saved to `logs/<ICCID>/`:

| File | Content |
|------|---------|
| dump.json | Full dump (raw + decoded) |
| dump.xlsx | Excel summary (Card Info, Files, Errors sheets) |
| decoded/*.json | Individual EF decode results |

### Offline Mode (Load Dump)

Click **Load Dump** to load a previously saved `dump.json`:
- Browse previous dumps without a SIM card
- File tree + decode views work identically
- ADM verification state is restored from the dump

---

## 12. Troubleshooting

### "Reader not found"

- Verify the PC/SC reader is connected via USB
- macOS: Run `pcsctest` to check reader recognition
- Windows: Check Device Manager for smart card reader

### "No card in reader"

- Ensure the SIM card is properly inserted in the reader
- Check that card contacts are clean

### Write button disabled

- Hover over the button to see the tooltip — it shows which ADM key is required
- Verify the correct ADM key in the ADM popup
- Files with NEVER condition cannot be written

### Connection timeout

- Possible poor contact between reader and card
- Disconnect and reconnect USB
- Try a different reader slot

### pySim-related errors

- Try reinstalling: `pip install -e src/pysim`
- Verify Python 3.10+ version

---

**© 2026 JUSEOK AHN. All rights reserved.**
