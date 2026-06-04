#!/usr/bin/env python3
"""SIM Card Reader Web Application."""

import json
import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))
from export_to_excel import convert_to_excel
import pysim_wrapper

app = Flask(__name__)
app.secret_key = 'sim_reader_secret_key_2024'
app.json.sort_keys = False

VERSION = "v1.1.0"


def _json_default(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Data directory: next to exe in frozen mode, or project root/logs in dev
if getattr(sys, 'frozen', False):
    DATA_DIR = Path(sys.executable).parent / "logs"
else:
    DATA_DIR = Path(__file__).parent.parent / "logs"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sim/connect', methods=['POST'])
def sim_connect():
    try:
        reader = request.json.get('reader', 0)
        r = pysim_wrapper.connect(reader)
        if r['success']:
            session['connected'] = True
        return jsonify(r)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/verify_adm', methods=['POST'])
def verify_adm():
    try:
        adm_hex = request.json.get('adm', '').strip().replace(' ', '')
        adm_type = request.json.get('adm_type', 'ADM1')

        if len(adm_hex) != 16 or not all(c in '0123456789abcdefABCDEF' for c in adm_hex):
            return jsonify({'success': False, 'error': '⚠️ Invalid ADM value'})

        r = pysim_wrapper.verify_adm(adm_hex, adm_type)
        return jsonify(r)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/read_all', methods=['POST'])
def read_all():
    try:
        # ADM verification if provided
        adm = request.json.get('adm', '') if request.json else ''
        adm_type = request.json.get('adm_type', 'ADM1') if request.json else 'ADM1'
        if adm and len(adm) == 16:
            pysim_wrapper.verify_adm(adm, adm_type)

        r = pysim_wrapper.read_all()
        if not r['success']:
            return jsonify(r)

        data = r['data']

        # Process files: separate raw/body/bytes
        files = {}
        for path, fd in data.get("files", {}).items():
            raw = fd.pop("raw", None)
            body = fd.get("body")

            if raw is not None:
                fd["bytes"] = raw
            elif body is not None:
                if isinstance(body, dict) and all(str(k).isdigit() for k in body.keys()):
                    # BER-TLV: reconstruct raw hex
                    raw_hex = ""
                    for tag_str, val_hex in body.items():
                        tag = int(tag_str)
                        val_bytes = bytes.fromhex(val_hex)
                        raw_hex += f"{tag:02x}" if tag <= 0xFF else f"{tag:04x}"
                        length = len(val_bytes)
                        if length <= 0x7F:
                            raw_hex += f"{length:02x}"
                        elif length <= 0xFF:
                            raw_hex += f"81{length:02x}"
                        else:
                            raw_hex += f"82{length:04x}"
                        raw_hex += val_hex
                    fd["bytes"] = raw_hex
            files[path] = fd

        data["files"] = files

        # Auto-export
        export_path = None
        try:
            iccid = data.get('iccid') or 'unknown'
            card_dir = DATA_DIR / iccid
            card_dir.mkdir(parents=True, exist_ok=True)
            json_path = card_dir / "dump.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=_json_default)
            convert_to_excel(str(json_path))
            export_path = str(card_dir)
        except Exception as ex:
            print(f"[read_all] Auto-export failed: {ex}")

        return jsonify({'success': True, 'data': data, 'export_path': export_path})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/export', methods=['POST'])
def export_sim():
    try:
        data = request.json.get('data')
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400

        iccid = data.get('iccid', 'unknown')
        card_dir = DATA_DIR / iccid
        card_dir.mkdir(parents=True, exist_ok=True)

        json_path = card_dir / "dump.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        convert_to_excel(str(json_path))
        return jsonify({'success': True, 'path': str(card_dir)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/sim/read_ef', methods=['POST'])
def read_ef():
    """Read EF file(s)."""
    try:
        # ADM verification if provided
        adm = request.json.get('adm', '')
        adm_type = request.json.get('adm_type', 'ADM1')
        if adm and len(adm) == 16:
            pysim_wrapper.verify_adm(adm, adm_type)

        paths = request.json.get('paths', [])
        single_path = request.json.get('path', '')
        single_structure = request.json.get('structure', 'transparent')
        if single_path and not paths:
            paths = [single_path]

        if not paths:
            return jsonify({'success': False, 'error': 'Missing path'})

        results = {}
        for file_path in paths:
            structure = request.json.get('structures', {}).get(file_path, single_structure)
            r = pysim_wrapper.read_ef(file_path, structure)
            if r['success']:
                entry = {}
                if 'bytes' in r:
                    entry['bytes'] = r['bytes']
                if 'body' in r:
                    entry['body'] = r['body']
                results[file_path] = entry

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/service_map', methods=['POST'])
def service_map():
    """Return service table map for EF.UST or EF.IST."""
    try:
        ef_name = request.json.get('ef', '')
        if 'UST' in ef_name:
            from pySim.ts_31_102 import EF_UST_map
            return jsonify({'success': True, 'map': {str(k): v for k, v in EF_UST_map.items()}})
        elif 'IST' in ef_name:
            from pySim.ts_31_103 import EF_IST_map
            return jsonify({'success': True, 'map': {str(k): v for k, v in EF_IST_map.items()}})
        elif 'EST' in ef_name:
            from pySim.ts_31_102 import EF_EST_map
            return jsonify({'success': True, 'map': {str(k): v for k, v in EF_EST_map.items()}})
        else:
            return jsonify({'success': False, 'error': 'Unknown service table'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/write_tlv', methods=['POST'])
def write_tlv_route():
    """BER-TLV write: delete + set data for a tag."""
    try:
        file_path = request.json.get('path', '')
        tag = request.json.get('tag', '')
        data = request.json.get('data', '')
        adm = request.json.get('adm', '')
        adm_type = request.json.get('adm_type', 'ADM1')

        if not file_path or not tag or not data:
            return jsonify({'success': False, 'error': 'Missing path, tag or data'})

        if adm and len(adm) == 16:
            pysim_wrapper.verify_adm(adm, adm_type)

        r = pysim_wrapper.write_tlv(file_path, tag, data)
        return jsonify(r)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/decode_ursp', methods=['POST'])
def decode_ursp():
    """Decode URSP hex data using ursp.py"""
    try:
        from ursp import decode_ef_ursp, format_ursp_tree
        hex_data = request.json.get('hex', '')
        if not hex_data:
            return jsonify({'success': False, 'error': 'No hex data'})
        result = decode_ef_ursp(hex_data)
        if result.get('success'):
            result['tree'] = format_ursp_tree(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/read_tlv', methods=['POST'])
def read_tlv_route():
    """BER-TLV read: retrieve data for a tag."""
    try:
        file_path = request.json.get('path', '')
        tag = request.json.get('tag', '')
        adm = request.json.get('adm', '')
        adm_type = request.json.get('adm_type', 'ADM1')

        if not file_path or not tag:
            return jsonify({'success': False, 'error': 'Missing path or tag'})

        if adm and len(adm) == 16:
            pysim_wrapper.verify_adm(adm, adm_type)

        r = pysim_wrapper.read_tlv(file_path, tag)
        return jsonify(r)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/write_ef', methods=['POST'])
def write_ef():
    try:
        file_path = request.json.get('path', '')
        hex_data = request.json.get('hex', '').strip().replace(' ', '')
        adm = request.json.get('adm', '')
        adm_type = request.json.get('adm_type', 'ADM1')
        record_nr = request.json.get('record_nr', 0)
        structure = request.json.get('structure', 'transparent')

        if not file_path or not hex_data:
            return jsonify({'success': False, 'error': '⚠️ Missing path or hex data'})

        if adm and len(adm) == 16:
            pysim_wrapper.verify_adm(adm, adm_type)

        r = pysim_wrapper.write_ef(file_path, hex_data, structure, record_nr)
        return jsonify(r)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/sim/test_profile', methods=['POST'])
def test_profile():
    """Return ADM keys from test_profile.json matching the given MSISDN."""
    try:
        msisdn = request.json.get('msisdn', '').strip()
        if not msisdn:
            return jsonify({'success': False})

        profile_paths = [
            Path(__file__).parent.parent / "test_profile.json",
            Path(sys.executable).parent / "test_profile.json",
        ]
        for pp in profile_paths:
            if pp.exists():
                with open(pp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for profile in data.get("profiles", []):
                    pm = profile.get("msisdn", "")
                    if pm and (pm in msisdn or msisdn in pm):
                        keys = {}
                        for k in ("adm1", "adm2", "adm3", "adm4"):
                            if k in profile and profile[k]:
                                keys[k] = profile[k]
                        if keys:
                            return jsonify({'success': True, 'keys': keys})
                break
        return jsonify({'success': False})
    except Exception:
        return jsonify({'success': False})


if __name__ == '__main__':
    print("Starting SIM Card Reader Web App...")
    print(f"Version: {VERSION}")
    print("Access: http://127.0.0.1:8082")
    app.run(host='0.0.0.0', port=8082, debug=False)
