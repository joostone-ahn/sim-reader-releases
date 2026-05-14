# 📡 SIM Card Reader

A web-based tool for reading, writing, and decoding SIM/USIM/ISIM card files via PC/SC smart card reader.

![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)

---

## 💡 Why This Tool?

SIM profiles are complex — nibble-swapped BCD PLMNs, dense service bitmaps, nested BER-TLV URSP policies. Raw hex editing is error-prone and unfriendly.

This tool **auto-decodes** everything into readable formats (PLMN tables, service ON/OFF lists, URSP rule trees) and provides **user-friendly write editors** per file type — PLMN table input, service toggles, ACC checkboxes, BER-TLV tag selector with length validation. No manual hex construction needed.

---

## ⚡ Key Features

- **Full file system dump** — reads 200+ EF files across MF, ADF.USIM, ADF.ISIM in a single pass (~20 seconds)
- **Auto-decoding** — structured JSON output for PLMN, service tables, URSP, ACC, ARR, and more
- **ARR security conditions** — shows required ADM key before writing; auto-enforces access control
- **BER-TLV read/write** — tag-based RETRIEVE DATA + DELETE/SET DATA (URSP, IMSConfigData)
- **URSP tree decoder** — 3GPP TS 24.526 compliant rule visualization
- **EF write editors** — PLMN table, service table (UST/IST/EST), ACC, hex, BER-TLV editors
- **Auto-export** — dump.json + dump.xlsx + individual decoded JSON files per ICCID
- **Offline mode** — load and browse previous dumps without a SIM card

---

## 💻 Download

Download the latest exe from [Releases](https://github.com/joostone-ahn/sim-reader-releases/releases).

---

## 📖 How to Use

See the User Guide for detailed instructions:
- [English](https://github.com/joostone-ahn/sim-reader-releases/blob/main/manual/user_guide_en_v1.0.0.md)
- [한국어](https://github.com/joostone-ahn/sim-reader-releases/blob/main/manual/user_guide_kr_v1.0.0.md)

---

## 📚 References

- 3GPP TS 31.102 — USIM application
- 3GPP TS 31.103 — ISIM application
- 3GPP TS 102.221 — UICC-Terminal interface
- 3GPP TS 24.526 — UE policies (URSP)
- ISO/IEC 7816-4 — Smart card commands
- [pySim by Osmocom](https://gitea.osmocom.org/sim-card/pysim) — Base SIM toolkit (GPLv2)

---

## 👤 Author

**JUSEOK AHN (안주석)**  
**Email**: ajs3013@lguplus.co.kr  
**Organization**: LG U+  
**Role**: Technical Specialist, Telecommunications Engineer

---

## 📄 License

© 2026 JUSEOK AHN <ajs3013@lguplus.co.kr>. All rights reserved.

### Third-party

`pySim` by [Osmocom](https://gitea.osmocom.org/sim-card/pysim) — licensed under GPLv2.
