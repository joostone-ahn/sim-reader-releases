"""In-process pySim wrapper for SIM card communication.

Provides direct API calls to pySim internals without subprocess.
Works in both development (source) and frozen (PyInstaller exe) environments.

Public API:
    connect(reader_num) → dict
    is_connected() → bool
    verify_adm(adm_hex, adm_type) → dict
    read_ef(file_path, structure) → dict
    write_ef(file_path, hex_data, structure, record_nr) → dict
    write_tlv(file_path, tag, data) → dict
    read_tlv(file_path, tag) → dict
    read_all() → dict
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

# Ensure pySim is importable
_pysim_path = str(Path(__file__).parent / "pysim")
if _pysim_path not in sys.path:
    sys.path.insert(0, _pysim_path)

from pySim.transport.pcsc import PcscSimLink
from pySim.app import init_card
from pySim.exceptions import SwMatchError, NoCardError, ReaderError
from pySim.filesystem import CardEF, CardDF, CardADF, LinFixedEF, TransparentEF, BerTlvEF
from osmocom.utils import h2b, b2h
from osmocom.tlv import bertlv_parse_one, bertlv_encode_len

logger = logging.getLogger(__name__)

# Global state
_sl = None       # PcscSimLink (transport)
_rs = None       # RuntimeState
_card = None     # CardBase


def connect(reader_num: int = 0) -> dict:
    """Connect to a PC/SC reader and initialize the card.

    Returns:
        dict: {success, info: {iccid, imsi, msisdn, hplmn, impi, impu}, error}
    """
    global _sl, _rs, _card

    try:
        # Close previous connection
        if _sl:
            try:
                _sl.disconnect()
            except Exception:
                pass
            _sl = None
            _rs = None
            _card = None

        opts = argparse.Namespace(pcsc_dev=reader_num, pcsc_regex=None, pcsc_shared=False)
        _sl = PcscSimLink(opts)

        rs, card = init_card(_sl)
        if not rs:
            return {'success': False, 'error': 'Card initialization failed'}

        _rs = rs
        _card = card
        lchan = _rs.lchan[0]

        info = {'iccid': '', 'imsi': '', 'msisdn': '', 'hplmn': '', 'impi': '', 'impu': ''}

        # ICCID
        try:
            lchan.select('MF')
            lchan.select('EF.ICCID')
            data, _ = lchan.read_binary()
            dec = lchan.selected_file.decode_hex(data)
            info['iccid'] = dec.get('iccid', '')
            if info['iccid']:
                _rs.identity['ICCID'] = info['iccid']
        except Exception as e:
            logger.warning("ICCID: %s", e)

        # IMSI
        try:
            lchan.select('MF')
            lchan.select('ADF.USIM')
            lchan.select('EF.IMSI')
            data, _ = lchan.read_binary()
            dec = lchan.selected_file.decode_hex(data)
            info['imsi'] = dec.get('imsi', '')
        except Exception as e:
            logger.warning("IMSI: %s", e)

        # MSISDN
        try:
            lchan.select('MF')
            lchan.select('ADF.USIM')
            lchan.select('EF.MSISDN')
            num_rec = lchan.selected_file_num_of_rec() or 1
            for i in range(1, num_rec + 1):
                data, _ = lchan.read_record(i)
                try:
                    dec = lchan.selected_file.decode_record_hex(data, i)
                    if dec and dec.get('dialing_nr'):
                        nr = dec['dialing_nr']
                        alpha = dec.get('alpha_id', '')
                        info['msisdn'] = f"{nr}({alpha})" if alpha else nr
                        break
                except Exception:
                    pass
        except Exception as e:
            logger.warning("MSISDN: %s", e)

        # HPLMNwAcT
        try:
            lchan.select('MF')
            lchan.select('ADF.USIM')
            lchan.select('EF.HPLMNwAcT')
            data, _ = lchan.read_binary()
            if data and len(data) >= 10:
                raw = data.upper()
                if raw[:6] != 'FFFFFF':
                    mcc = raw[1] + raw[0] + raw[3]
                    mnc_d3 = raw[2]
                    mnc = raw[5] + raw[4]
                    if mnc_d3 != 'F':
                        mnc += mnc_d3
                    info['hplmn'] = f"{mcc}/{mnc}({raw[6:10]})"
        except Exception as e:
            logger.warning("HPLMNwAcT: %s", e)

        # IMPI
        try:
            lchan.select('MF')
            lchan.select('ADF.ISIM')
            lchan.select('EF.IMPI')
            data, _ = lchan.read_binary()
            dec = lchan.selected_file.decode_hex(data)
            info['impi'] = dec.get('nai', '')
        except Exception as e:
            logger.warning("IMPI: %s", e)

        # IMPU
        try:
            lchan.select('MF')
            lchan.select('ADF.ISIM')
            lchan.select('EF.IMPU')
            num_rec = lchan.selected_file_num_of_rec() or 1
            for i in range(1, num_rec + 1):
                data, _ = lchan.read_record(i)
                try:
                    dec = lchan.selected_file.decode_record_hex(data, i)
                    if dec and dec.get('impu'):
                        info['impu'] = dec['impu']
                        break
                except Exception:
                    pass
        except Exception as e:
            logger.warning("IMPU: %s", e)

        return {'success': True, 'info': info}

    except ReaderError:
        return {'success': False, 'error': 'Reader not found'}
    except NoCardError:
        return {'success': False, 'error': 'No card in reader'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def is_connected() -> bool:
    return _rs is not None


def verify_adm(adm_hex: str, adm_type: str = 'ADM1') -> dict:
    """Verify ADM key. adm_hex: 16-char hex (8 bytes)."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    chv_map = {'ADM1': 0x0A, 'ADM2': 0x0B, 'ADM3': 0x0C, 'ADM4': 0x0D, 'ADM5': 0x0E}
    chv_num = chv_map.get(adm_type, 0x0A)

    try:
        _rs.lchan[0].scc.verify_chv(chv_num, h2b(adm_hex))
        _rs.adm_verified = True
        return {'success': True}
    except SwMatchError as e:
        return {'success': False, 'error': f"⚠️ {e.sw_actual}: {e.description or 'Verification failed'}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def read_ef(file_path: str, structure: str = 'transparent') -> dict:
    """Read a single EF. Returns {success, bytes, body, error}."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    lchan = _rs.lchan[0]
    try:
        _select_path(lchan, file_path)

        if structure in ('linear_fixed', 'cyclic'):
            raw_list, dec_list = _read_records_raw_dec(lchan)
            return _json_safe({'success': True, 'bytes': raw_list, 'body': dec_list})
        elif structure == 'ber_tlv':
            tags = lchan.retrieve_tags()
            raw_hex = ''
            body = {}
            for t in tags:
                raw_tlv, value_hex, dec = _retrieve_data_raw_dec(lchan, t)
                raw_hex += raw_tlv
                body[str(t)] = value_hex
            return _json_safe({'success': True, 'bytes': raw_hex, 'body': body})
        else:
            raw, dec = _read_binary_raw_dec(lchan)
            return _json_safe({'success': True, 'bytes': raw, 'body': dec})

    except SwMatchError as e:
        return {'success': False, 'error': f"⚠️ {e.sw_actual}: {e.description or ''}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def write_ef(file_path: str, hex_data: str, structure: str = 'transparent', record_nr: int = 0) -> dict:
    """Write to an EF. Returns {success, error}."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    lchan = _rs.lchan[0]
    try:
        _select_path(lchan, file_path)
        _rs.conserve_write = False

        if structure in ('linear_fixed', 'cyclic') and record_nr > 0:
            lchan.update_record(record_nr, hex_data)
        else:
            lchan.update_binary(hex_data)

        return {'success': True}
    except SwMatchError as e:
        return {'success': False, 'error': f"⚠️ {e.sw_actual}: {e.description or 'Write failed'}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def write_tlv(file_path: str, tag: str, data: str) -> dict:
    """Write BER-TLV (delete + set). data = value hex only."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    lchan = _rs.lchan[0]
    try:
        _select_path(lchan, file_path)
        tag_int = int(tag.replace('0x', '').replace('0X', ''), 16)

        # Delete existing
        try:
            lchan.scc.set_data([], tag_int, '')
        except Exception:
            pass

        # Set new data
        lchan.scc.set_data([], tag_int, data)
        return {'success': True}

    except SwMatchError as e:
        return {'success': False, 'error': f"⚠️ {e.sw_actual}: {e.description or 'Write failed'}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def read_tlv(file_path: str, tag: str) -> dict:
    """Read a single BER-TLV tag. Returns {success, data, decoded, empty}."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    lchan = _rs.lchan[0]
    try:
        _select_path(lchan, file_path)
        tag_int = int(tag.replace('0x', '').replace('0X', ''), 16)
        raw_tlv, value_hex, dec = _retrieve_data_raw_dec(lchan, tag_int)
        return {'success': True, 'data': value_hex, 'decoded': dec}

    except SwMatchError as e:
        if e.sw_actual == '6a88':
            return {'success': True, 'data': '', 'empty': True}
        return {'success': False, 'error': f"⚠️ {e.sw_actual}: {e.description or ''}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def read_all() -> dict:
    """Read entire file system. Returns {success, data, error}."""
    if not _rs:
        return {'success': False, 'error': 'Not connected'}

    lchan = _rs.lchan[0]
    result = {
        'name': _card.name if _card else '',
        'atr': _rs.identity.get('ATR', ''),
        'eid': _rs.identity.get('EID', None),
        'iccid': _rs.identity.get('ICCID', None) or _rs.identity.get('iccid', None),
        'aids': {x.aid: {} for x in _rs.mf.applications.values()},
        'files': {},
    }

    try:
        lchan.select('MF')
        # Add MF itself as first entry
        result['files']['MF'] = {
            'path': ['MF'],
            'fcp_raw': str(lchan.selected_file_fcp_hex) if lchan.selected_file_fcp_hex else '',
            'fcp': lchan.selected_file_fcp or {},
        }
        _walk_dump(lchan, result)
        # Ensure all values are JSON-serializable
        result = _json_safe(result)
        return {'success': True, 'data': result}
    except Exception as e:
        if result['files']:
            result = _json_safe(result)
            return {'success': True, 'data': result}
        return {'success': False, 'error': str(e)}


# ============================================================================
# Internal helpers
# ============================================================================

def _json_safe(obj):
    """Recursively convert bytes/bytearray to hex strings for JSON serialization."""
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _select_path(lchan, file_path: str):
    """Navigate to a file by path string like MF/ADF.USIM/EF.IMSI."""
    parts = file_path.split('/')
    lchan.select('MF')
    for part in parts[1:]:
        lchan.select(part)


def _walk_dump(lchan, result: dict):
    """Recursively walk FS and dump all files (mirrors pySim-shell __walk logic)."""
    files = lchan.selected_file.get_selectables(flags=['FNAMES', 'ANAMES'])
    for name, file_obj in files.items():
        if isinstance(file_obj, CardDF):
            # DF/ADF: select, recurse, then go back up
            try:
                lchan.select(name)
                path_str = lchan.selected_file.fully_qualified_path_str(True)

                # Recurse first to check if there are any child files
                child_count_before = len(result['files'])
                # Add DF entry
                result['files'][path_str] = {
                    'path': lchan.selected_file.fully_qualified_path(True),
                    'fcp_raw': str(lchan.selected_file_fcp_hex) if lchan.selected_file_fcp_hex else '',
                    'fcp': lchan.selected_file_fcp or {},
                }
                _walk_dump(lchan, result)
                child_count_after = len(result['files'])

                # Remove empty DFs (no child files added)
                if child_count_after == child_count_before + 1:
                    del result['files'][path_str]

                lchan.select_file(lchan.selected_file.parent)
            except Exception:
                pass
        elif isinstance(file_obj, CardEF):
            # EF: dump it
            _dump_single_file(lchan, name, result)


def _dump_single_file(lchan, filename: str, result: dict):
    """Select and dump a single EF, then return to parent."""
    try:
        fcp_dec = lchan.select(filename)
        if not lchan.selected_file_fcp_hex:
            lchan.select_file(lchan.selected_file.parent)
            return

        file_obj = lchan.selected_file
        path_str = file_obj.fully_qualified_path_str(True)
        res = {
            'path': file_obj.fully_qualified_path(True),
            'fcp_raw': str(lchan.selected_file_fcp_hex),
            'fcp': fcp_dec,
        }

        structure = lchan.selected_file_structure()
        if structure == 'transparent':
            raw, body = _read_binary_raw_dec(lchan)
            res['raw'] = raw
            res['body'] = body
        elif structure in ('cyclic', 'linear_fixed'):
            raw_list, dec_list = _read_records_raw_dec(lchan)
            res['raw'] = raw_list
            res['body'] = dec_list
        elif structure == 'ber_tlv':
            tags = lchan.retrieve_tags()
            body = {}
            for t in tags:
                try:
                    _, value_hex, _ = _retrieve_data_raw_dec(lchan, t)
                    body[t] = value_hex
                except Exception:
                    pass
            res['body'] = body

        result['files'][path_str] = res

    except SwMatchError as e:
        # Build correct path for the failed file
        parent_path = lchan.selected_file.fully_qualified_path_str(True)
        path_str = parent_path + '/' + filename if parent_path else filename
        result['files'][path_str] = {
            'path': (lchan.selected_file.fully_qualified_path(True) or []) + [filename],
            'fcp_raw': '',
            'fcp': {},
            'error': {'sw_actual': e.sw_actual, 'sw_expected': e.sw_expected, 'message': e.description or ''}
        }
    except Exception:
        pass
    finally:
        # Always return to parent DF
        try:
            if isinstance(lchan.selected_file, CardEF):
                lchan.select_file(lchan.selected_file.parent)
        except Exception:
            pass


def _read_binary_raw_dec(lchan):
    """Read transparent EF → (raw_hex, decoded_dict)."""
    data, _ = lchan.read_binary()
    try:
        dec = lchan.selected_file.decode_hex(data)
    except Exception as e:
        dec = {"_decode_error": str(e)}
    return str(data), dec


def _read_records_raw_dec(lchan):
    """Read all records → (raw_list, decoded_list)."""
    num_of_rec = lchan.selected_file_num_of_rec()
    raw_list, dec_list = [], []
    if num_of_rec:
        for recnr in range(1, 1 + num_of_rec):
            try:
                data, _ = lchan.read_record(recnr)
                raw_list.append(str(data))
                try:
                    dec = lchan.selected_file.decode_record_hex(data, recnr)
                except Exception as e:
                    dec = {"_decode_error": str(e)}
                dec_list.append(dec)
            except SwMatchError:
                break
    return raw_list, dec_list


def _retrieve_data_raw_dec(lchan, tag_int: int):
    """Retrieve BER-TLV tag → (raw_tlv_hex, value_hex, decoded_dict)."""
    data, _ = lchan.retrieve_data(tag_int)
    raw_tlv = str(data)
    try:
        _, _, val, _ = bertlv_parse_one(h2b(data))
        value_hex = b2h(val)
    except Exception:
        value_hex = data
    decode_method = getattr(lchan.selected_file, 'decode_tag_data', None)
    if callable(decode_method):
        try:
            dec = decode_method('%02x' % tag_int, value_hex)
        except Exception:
            dec = {'raw': value_hex}
    else:
        dec = {'raw': value_hex}
    return raw_tlv, value_hex, dec


# ============================================================================
# CLI entry point (standalone usage)
# ============================================================================

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    import argparse as ap
    parser = ap.ArgumentParser(description="SIM card file system dump")
    parser.add_argument("-p", "--reader", type=int, default=0)
    args = parser.parse_args()

    r = connect(args.reader)
    if not r['success']:
        print(f"Connection failed: {r['error']}")
        sys.exit(1)

    print(f"Connected: {r['info']}")
    r = read_all()
    if r['success']:
        print(json.dumps(r['data'], indent=2, ensure_ascii=False))
    else:
        print(f"Read all failed: {r['error']}")
