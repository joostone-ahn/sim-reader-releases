"""
decoder.py — URSP Rule Decoder & 3GPP TS 24.526 Constants

Single source of truth for URSP protocol parsing. Decodes hex data from
SIM EF_URSP files and DL NAS Transport messages into structured dicts.
Also provides spec constants used by encoder.py.

Public Decoders:
    decode_ef_ursp(hex_str, bytemap=None)
        Input: Full EF_URSP hex (80 tag included)
        Output: {success, plmn, pti, upsc, URSP rules}

    decode_dl_nas(hex_str, bytemap=None)
        Input: Full DL NAS Transport hex (68 05 start)
        Output: {success, plmn, pti, upsc, URSP rules}

Tree Rendering:
    format_ursp_tree(decoded)
        Input: decoded dict from above
        Output: indented tree text string

Bytemap:
    All parse functions accept an optional `bytemap` list parameter.
    When provided, each byte read is recorded as:
        {"idx": int, "dec": int, "hex": str, "desc": str}
    When None (default), no recording occurs — zero overhead.

Internal Parsers:
    _parse_rule(hb, idx, bytemap, rule_idx)  — single URSP rule
    _parse_td(hb, idx, td_end, bytemap)      — single TD component (25 types)
    _parse_rsd(hb, idx, bytemap, rule_idx, rsd_idx) — single RSD

Spec Constants (imported by encoder.py):
    TD_TYPES_BY_ID, RSD_TYPES_BY_ID, RSD_ZERO
    PROTOCOL_MAP, CONNECTION_CAPABILITY_MAP
    SSC_MODE_MAP, PDU_SESSION_TYPE_MAP, PREFERRED_ACCESS_TYPE_MAP
    PDU_SESSION_PAIR_ID_MAP, RSN_MAP, SST_STANDARD_VALUES
    ANDROID_OS_ID, IOS_OS_ID, LOCATION_AREA_TYPES, LOCATION_AREA_CELL_SIZES
    IOS_APP_CATEGORIES_REV, IOS_TRAFFIC_CATEGORIES_REV

References:
    - 3GPP TS 24.526: UE policies for 5G system
    - 3GPP TS 31.102: USIM application (EF_URSP structure)
    - 3GPP TS 24.501: NAS signaling
    - 3GPP TS 23.501: System architecture (SST standard values)
"""

import ipaddress

# ============================================================================
# Spec constants — 3GPP TS 24.526 Table 5.2 (TD/RSD component type identifiers)
# ============================================================================

TD_TYPES_BY_ID = {
    0x01: "Match-all",
    0x08: "OS Id + OS App Id",
    0x10: "IPv4 remote address",
    0x21: "IPv6 remote address/prefix length",
    0x30: "Protocol identifier/next header",
    0x50: "Single remote port",
    0x51: "Remote port range",
    0x52: "IP 3 tuple",
    0x60: "Security parameter index",
    0x70: "Type of service/traffic class",
    0x80: "Flow label",
    0x81: "Destination MAC address",
    0x83: "802.1Q C-TAG VID",
    0x84: "802.1Q S-TAG VID",
    0x85: "802.1Q C-TAG PCP/DEI",
    0x86: "802.1Q S-TAG PCP/DEI",
    0x87: "Ethertype",
    0x88: "DNN",
    0x90: "Connection capabilities",
    0x91: "Destination FQDN",
    0x92: "Regular expression",
    0xA0: "OS App Id",
    0xA1: "Destination MAC address range",
    0xA2: "PIN ID",
    0xA3: "Connectivity group ID",
}

RSD_TYPES_BY_ID = {
    0x01: "SSC mode",
    0x02: "S-NSSAI",
    0x04: "DNN",
    0x08: "PDU session type",
    0x10: "Preferred access type",
    0x11: "Multi-access preference",
    0x20: "Non-seamless non-3GPP offload indication",
    0x40: "Location criteria",
    0x80: "Time window",
    0x81: "5G ProSe layer-3 UE-to-network relay offload indication",
    0x82: "PDU session pair ID",
    0x83: "RSN",
    0x84: "5G ProSe multi-path preference",
}

RSD_ZERO = {"Multi-access preference", "Non-seamless non-3GPP offload indication",
            "5G ProSe layer-3 UE-to-network relay offload indication", "5G ProSe multi-path preference"}

LOCATION_AREA_TYPES = {0x01: "E-UTRA cell identities list", 0x02: "NR cell identities list",
                       0x03: "Global RAN node identities list", 0x04: "TAI list"}
LOCATION_AREA_CELL_SIZES = {0x01: 7, 0x02: 8, 0x03: 7, 0x04: None}

IOS_OS_ID = "4301D21197D942C9B1C2F67583C0F920"

IOS_APP_CATEGORIES_REV = {"6014": "gaming", "9000": "communication", "9001": "streaming"}
IOS_TRAFFIC_CATEGORIES_REV = {"1": "defaultslice", "2": "video", "3": "background",
                              "4": "voice", "5": "callsignaling", "6": "responsivedata",
                              "7": "avstreaming", "8": "responsiveav", "*": "wildcard"}

PROTOCOL_MAP = {0x01: "ICMP", 0x06: "TCP", 0x11: "UDP", 0x32: "ESP", 0x3A: "ICMPv6"}

CONNECTION_CAPABILITY_MAP = {
    0x01: "IMS", 0x02: "MMS", 0x04: "SUPL", 0x08: "Internet",
    0x10: "LCS user plane positioning", 0x20: "Operator specific",
    0xA1: "IoT delay-tolerant", 0xA2: "IoT non-delay-tolerant",
    0xA3: "Downlink streaming", 0xA4: "Uplink streaming",
    0xA5: "Vehicular communications", 0xA6: "Real time interactive",
    0xA7: "Unified communications", 0xA8: "Background",
    0xA9: "Mission critical communications", 0xAA: "Time critical communications",
    0xAB: "Low latency loss tolerant communications in un-acknowledged mode",
}

SSC_MODE_MAP = {0x01: "SSC mode 1", 0x02: "SSC mode 2", 0x03: "SSC mode 3"}
PDU_SESSION_TYPE_MAP = {0x01: "IPv4", 0x02: "IPv6", 0x03: "IPv4v6"}
PREFERRED_ACCESS_TYPE_MAP = {0x01: "3GPP access", 0x02: "Non-3GPP access"}
PDU_SESSION_PAIR_ID_MAP = {i: f"PDU session pair ID {i}" for i in range(7)}
RSN_MAP = {0x00: "v1", 0x01: "v2"}
SST_STANDARD_VALUES = {1: "eMBB", 2: "URLLC", 3: "MIoT", 4: "V2X", 5: "HMTC", 6: "HDLLC", 7: "GBRSS"}
ANDROID_OS_ID = "97A498E3FC925C9489860333D06E4E47"

# DSCP values per RFC 4594 (Configuration Guidelines for DiffServ Service Classes)
# Field structure: 3GPP TS 24.008 Table 10.5.162 (2 bytes: value + mask)
# DSCP definition: RFC 2474 (Definition of the Differentiated Services Field)
# PHB definitions:
#   - Class Selector (CS): RFC 2474 Section 4.2
#   - Assured Forwarding (AF): RFC 2597
#   - Expedited Forwarding (EF): RFC 3246
#   - Voice Admit (VA): RFC 5865
# Service class mapping: RFC 4594 Table 2
#
# Key: ToS byte value (DSCP << 2 per RFC 2474 Section 3)
# Value: "DSCP_keyword — Service Class Name"
DSCP_MAP = {
    0x00: ("CS0", "Best Effort"),
    0x20: ("CS1", "Scavenger"),
    0x28: ("AF11", "Assured Forwarding 11"),
    0x30: ("AF12", "Assured Forwarding 12"),
    0x38: ("AF13", "Assured Forwarding 13"),
    0x40: ("CS2", "OAM"),
    0x48: ("AF21", "Assured Forwarding 21"),
    0x50: ("AF22", "Assured Forwarding 22"),
    0x58: ("AF23", "Assured Forwarding 23"),
    0x60: ("CS3", "Signaling"),
    0x68: ("AF31", "Assured Forwarding 31"),
    0x70: ("AF32", "Assured Forwarding 32"),
    0x78: ("AF33", "Assured Forwarding 33"),
    0x80: ("CS4", "Real-Time Interactive"),
    0x88: ("AF41", "Assured Forwarding 41"),
    0x90: ("AF42", "Assured Forwarding 42"),
    0x98: ("AF43", "Assured Forwarding 43"),
    0xA0: ("CS5", "Broadcast Video"),
    0xA8: ("VA", "Voice Admit"),
    0xB8: ("EF", "Expedited Forwarding"),
    0xC0: ("CS6", "Network Control"),
    0xE0: ("CS7", "Network Control"),
}

# Mask presets for Type of service/traffic class matching
# Structure per 3GPP TS 24.008 Table 10.5.162:
#   Byte 1 = value, Byte 2 = mask (1=compare, 0=ignore)
# Mask semantics per RFC 2474 Section 3 (DS field = bits 7-2, ECN = bits 1-0)
TOS_MASK_MAP = {
    0xFC: "DSCP only, ignore ECN",
    0xFF: "Exact match, DSCP + ECN",
    0xE0: "IP Precedence only, top 3 bits",
}

# ============================================================================
# Helpers — low-level byte reading utilities + bytemap
# ============================================================================

def _bm(bytemap, idx, hb, desc):
    """Append one bytemap entry (dict) if bytemap is not None."""
    if bytemap is not None:
        bytemap.append({"idx": idx, "hex": hb[idx], "desc": desc})

def _bm_2byte_len(bytemap, hb, idx, desc, suffix=""):
    """Append 2-byte length bytemap entries. Returns the length value."""
    high = int(hb[idx], 16)
    low = int(hb[idx + 1], 16)
    total = (high << 8) + low
    if bytemap is not None:
        bytemap.append({"idx": idx, "hex": hb[idx], "desc": f"{desc}{suffix} [0]"})
        if high != 0:
            bytemap.append({"idx": idx + 1, "hex": hb[idx + 1], "desc": f"{desc}{suffix} [1]: {total}"})
        else:
            bytemap.append({"idx": idx + 1, "hex": hb[idx + 1], "desc": f"{desc}{suffix} [1]: {total}"})
    return total

def _bm_ascii(bytemap, hb, idx, length, prefix):
    """Append bytemap for ASCII bytes. Returns (string, new_idx)."""
    result = ''
    for i in range(length):
        if idx + i < len(hb):
            val = int(hb[idx + i], 16)
            char = chr(val) if 32 <= val <= 126 else '.'
            if bytemap is not None:
                bytemap.append({"idx": idx + i, "hex": hb[idx + i], "desc": f"{prefix} [{i}]: '{char}'"})
            result += chr(val)
    return result, idx + length

def _parse_ber_length(hb, idx):
    if idx >= len(hb):
        return 0, idx
    first = int(hb[idx], 16)
    if first <= 0x7F:
        return first, idx + 1
    elif first == 0x81:
        return int(hb[idx + 1], 16), idx + 2
    elif first == 0x82:
        return (int(hb[idx + 1], 16) << 8) + int(hb[idx + 2], 16), idx + 3
    return 0, idx + 1

def _u16(hb, idx):
    return (int(hb[idx], 16) << 8) + int(hb[idx + 1], 16), idx + 2

def _u8(hb, idx):
    return int(hb[idx], 16), idx + 1

def _read_ascii(hb, idx, length):
    return ''.join(chr(int(hb[idx + i], 16)) for i in range(length) if idx + i < len(hb)), idx + length

# ============================================================================
# Public decoders — EF_URSP and DL NAS Transport
# ============================================================================

def decode_ef_ursp(hex_str, bytemap=None):
    """Decode SIM EF_URSP hex (starts with 80 tag).

    Args:
        hex_str: Full EF_URSP hex string (80 tag included)
        bytemap: Optional list to accumulate byte-level descriptions

    Returns:
        dict with keys: success, plmn, pti, upsc, URSP rules
    """
    if not hex_str or len(hex_str) < 10:
        return {'success': False, 'error': 'Hex data too short'}
    try:
        hb = [hex_str[i:i+2].upper() for i in range(0, len(hex_str), 2)]
        idx = 0

        # 80 tag
        _bm(bytemap, idx, hb, "URSP Rules data object tag")
        idx += 1

        # BER-TLV length
        first = int(hb[idx], 16)
        if first <= 0x7F:
            _bm(bytemap, idx, hb, f"URSP Rules length: {first}")
            total_len = first; idx += 1
        elif first == 0x81:
            _bm(bytemap, idx, hb, "URSP Rules length (long form, 1 byte follows)")
            idx += 1
            total_len = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"URSP Rules length: {total_len}")
            idx += 1
        elif first == 0x82:
            _bm(bytemap, idx, hb, "URSP Rules length (long form, 2 bytes follow)")
            idx += 1
            high = int(hb[idx], 16); low = int(hb[idx + 1], 16)
            total_len = (high << 8) + low
            _bm(bytemap, idx, hb, "URSP Rules length [0]")
            _bm(bytemap, idx + 1, hb, f"URSP Rules length [1]: {total_len}")
            idx += 2
        else:
            total_len = 0; idx += 1

        # PLMN (3 bytes)
        n0 = int(hb[idx], 16); n1 = int(hb[idx + 1], 16); n2 = int(hb[idx + 2], 16)
        mcc = f"{n0 & 0x0F}{(n0 >> 4) & 0x0F}{n1 & 0x0F}"
        mnc3 = (n1 >> 4) & 0x0F
        mnc = f"{n2 & 0x0F}{(n2 >> 4) & 0x0F}"
        if mnc3 != 0xF:
            mnc += str(mnc3)
        mcc_str = mcc; mnc_str = mnc
        _bm(bytemap, idx, hb, f"MCC digit 2, MCC digit 1 (PLMN: {mcc_str}/{mnc_str})")
        _bm(bytemap, idx + 1, hb, "MNC digit 3, MCC digit 3")
        _bm(bytemap, idx + 2, hb, "MNC digit 2, MNC digit 1")
        idx += 3

        # URSP rules block length (BER-TLV)
        ursp_block_len, idx = _parse_ber_length(hb, idx)

        # Parse URSP rules
        ursp_end = idx + ursp_block_len
        rules = []
        rule_idx = 0
        while idx < ursp_end and idx < len(hb):
            rule, idx = _parse_rule(hb, idx, bytemap, rule_idx)
            if rule:
                rules.append(rule)
            rule_idx += 1

        return {
            'success': True,
            'plmn': mcc + mnc,
            'pti': None,
            'upsc': None,
            'URSP rules': rules,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def decode_dl_nas(hex_str, bytemap=None):
    """Decode DL NAS Transport hex (starts with 68 05).

    Args:
        hex_str: Full DL NAS Transport hex string
        bytemap: Optional list to accumulate byte-level descriptions

    Returns:
        dict with keys: success, plmn, pti, upsc, URSP rules
    """
    if not hex_str or len(hex_str) < 20:
        return {'success': False, 'error': 'Hex data too short'}
    try:
        hb = [hex_str[i:i+2].upper() for i in range(0, len(hex_str), 2)]
        idx = 0

        # NAS message header
        _bm(bytemap, idx, hb, "DL NAS Transport")
        idx += 1

        _bm(bytemap, idx, hb, "Payload container type: UE policy container")
        idx += 1

        # Payload container length (2 bytes)
        _bm_2byte_len(bytemap, hb, idx, "Length of payload container contents")
        idx += 2

        # PTI
        _bm(bytemap, idx, hb, "Procedure transaction identity (PTI)")
        pti = hb[idx]; idx += 1

        # Message type
        _bm(bytemap, idx, hb, "UE policy delivery service message type: MANAGE UE POLICY COMMAND")
        idx += 1

        # UE policy section management list length
        _bm_2byte_len(bytemap, hb, idx, "Length of UE policy section management list contents")
        idx += 2

        # UE policy section management sublist length
        _bm_2byte_len(bytemap, hb, idx, "Length of UE policy section management sublist")
        idx += 2

        # PLMN (3 bytes)
        n0 = int(hb[idx], 16); n1 = int(hb[idx + 1], 16); n2 = int(hb[idx + 2], 16)
        mcc = f"{n0 & 0x0F}{(n0 >> 4) & 0x0F}{n1 & 0x0F}"
        mnc3 = (n1 >> 4) & 0x0F
        mnc = f"{n2 & 0x0F}{(n2 >> 4) & 0x0F}"
        if mnc3 != 0xF:
            mnc += str(mnc3)
        mcc_str = mcc; mnc_str = mnc
        _bm(bytemap, idx, hb, f"MCC digit 2, MCC digit 1 (PLMN: {mcc_str}/{mnc_str})")
        _bm(bytemap, idx + 1, hb, "MNC digit 3, MCC digit 3")
        _bm(bytemap, idx + 2, hb, "MNC digit 2, MNC digit 1")
        idx += 3

        # Instruction contents length
        _bm_2byte_len(bytemap, hb, idx, "Instruction contents length")
        idx += 2

        # UPSC (2 bytes)
        _bm(bytemap, idx, hb, "UPSC [0]")
        _bm(bytemap, idx + 1, hb, "UPSC [1]")
        upsc = hb[idx] + hb[idx + 1]; idx += 2

        # UE policy part contents length
        pol_len = _bm_2byte_len(bytemap, hb, idx, "UE policy part contents length")
        idx += 2

        # UE policy part type (0x01 = URSP)
        _bm(bytemap, idx, hb, "UE policy part type: URSP")
        idx += 1

        # Parse URSP rules
        ursp_end = idx + pol_len - 1
        rules = []
        rule_idx = 0
        while idx < ursp_end and idx < len(hb):
            rule, idx = _parse_rule(hb, idx, bytemap, rule_idx)
            if rule:
                rules.append(rule)
            rule_idx += 1

        return {
            'success': True,
            'plmn': mcc + mnc,
            'pti': pti,
            'upsc': upsc,
            'URSP rules': rules,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================================================
# Rule parser — outputs final normalized form directly
# ============================================================================

def _parse_rule(hb, idx, bytemap=None, rule_idx=0):
    rule_len = _bm_2byte_len(bytemap, hb, idx, "Length of URSP rule", f" {rule_idx + 1}")
    idx += 2
    rule_end = idx + rule_len

    pv = int(hb[idx], 16)

    _bm(bytemap, idx, hb, f"precedence_value of URSP rule: {pv}")

    idx += 1

    # Traffic descriptor
    td_len = _bm_2byte_len(bytemap, hb, idx, "Length of traffic descriptor")
    idx += 2
    td_end = idx + td_len
    td_list = []
    if td_len > 0:
        while idx < td_end and idx < len(hb):
            comp, idx = _parse_td(hb, idx, td_end, bytemap)
            if comp:
                td_list.append(comp)
    else:
        td_list.append({'type': 'Match-all'})

    # Route selection descriptor list
    rsd_len = _bm_2byte_len(bytemap, hb, idx, "Length of route selection descriptor list")
    idx += 2
    rsd_end = idx + rsd_len
    rsd_list = []
    rsd_count = 0
    while idx < rsd_end and idx < len(hb):
        rsd, idx = _parse_rsd(hb, idx, bytemap, rule_idx, rsd_count)
        if rsd:
            rsd_list.append(rsd)
        rsd_count += 1

    return {
        'Precedence value': pv,
        'Traffic descriptor': td_list,
        'Route selection descriptor list': rsd_list,
    }, rule_end

# ============================================================================
# TD component parser — returns normalized form directly
# ============================================================================

def _parse_td(hb, idx, td_end, bytemap=None):
    if idx >= td_end or idx >= len(hb):
        return None, idx

    _bm(bytemap, idx, hb, f"TD component type: {TD_TYPES_BY_ID.get(int(hb[idx], 16), 'Unknown')}")
    type_id, idx = _u8(hb, idx)
    type_name = TD_TYPES_BY_ID.get(type_id, f"Unknown(0x{type_id:02X})")

    if type_name == "Match-all":
        return {'type': type_name}, idx

    elif type_name == "OS Id + OS App Id":
        for i in range(16):
            _bm(bytemap, idx + i, hb, f"OS Id [{i}]")
        os_id = ''.join(hb[idx:idx + 16]); idx += 16
        app_len = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"OS App Id length: {app_len}")

        idx += 1
        app_id, idx = _bm_ascii(bytemap, hb, idx, app_len, "OS App Id")
        if os_id == ANDROID_OS_ID:
            return {'type': type_name, 'value': {'OS': 'Android', 'Slice Category': app_id}}, idx
        elif os_id == IOS_OS_ID:
            parts = app_id.split('.', 1)
            if len(parts) == 2:
                traffic_code, app_code = parts[0], parts[1]
                app_name = IOS_APP_CATEGORIES_REV.get(app_code)
                traffic_name = IOS_TRAFFIC_CATEGORIES_REV.get(traffic_code)
                app_cat = f"{app_name}-{app_code}" if app_name else f"custom-{app_code}"
                traffic_cat = f"{traffic_name}-{traffic_code}" if traffic_name else f"wildcard-{traffic_code}"
                return {'type': type_name, 'value': {'OS': 'iOS', 'App Category': app_cat, 'Traffic Category': traffic_cat}}, idx
            return {'type': type_name, 'value': {'OS': 'iOS', 'OS App Id': app_id}}, idx
        uid = f"{os_id[0:8]}-{os_id[8:12]}-{os_id[12:16]}-{os_id[16:20]}-{os_id[20:32]}"
        return {'type': type_name, 'value': {'OS': uid, 'OS App Id': app_id}}, idx

    elif type_name == "IPv4 remote address":
        for i in range(4):
            _bm(bytemap, idx + i, hb, f"IPv4 address [{i}]")
        addr = '.'.join(str(int(hb[idx + i], 16)) for i in range(4)); idx += 4
        for i in range(4):
            _bm(bytemap, idx + i, hb, f"IPv4 subnet mask [{i}]")
        mask = '.'.join(str(int(hb[idx + i], 16)) for i in range(4)); idx += 4
        return {'type': type_name, 'value': {'IPv4 address': addr, 'Subnet mask': mask}}, idx

    elif type_name == "IPv6 remote address/prefix length":
        for i in range(16):
            _bm(bytemap, idx + i, hb, f"IPv6 address [{i}]")
        v6 = int(''.join(hb[idx:idx + 16]), 16); idx += 16
        pfx = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"IPv6 prefix length: {pfx}")

        idx += 1
        return {'type': type_name, 'value': {'IPv6 address': str(ipaddress.IPv6Address(v6)), 'Prefix length': pfx}}, idx

    elif type_name == "Protocol identifier/next header":
        p = int(hb[idx], 16)
        _bm(bytemap, idx, hb, f"Protocol identifier/next header: {PROTOCOL_MAP.get(p, str(p))}")
        idx += 1
        return {'type': type_name, 'value': PROTOCOL_MAP.get(p, str(p))}, idx

    elif type_name == "Single remote port":
        _bm(bytemap, idx, hb, "Port number [0]")
        _bm(bytemap, idx + 1, hb, "Port number [1]")
        port, idx = _u16(hb, idx)
        return {'type': type_name, 'value': port}, idx

    elif type_name == "Remote port range":
        _bm(bytemap, idx, hb, "Port range low limit [0]")
        _bm(bytemap, idx + 1, hb, "Port range low limit [1]")
        lo, idx = _u16(hb, idx)
        _bm(bytemap, idx, hb, "Port range high limit [0]")
        _bm(bytemap, idx + 1, hb, "Port range high limit [1]")
        hi, idx = _u16(hb, idx)
        return {'type': type_name, 'value': {'Remote port low': lo, 'Remote port high': hi}}, idx

    elif type_name == "IP 3 tuple":
        bitmap = int(hb[idx], 16)
        _bm(bytemap, idx, hb, f"IP 3 tuple - Information bitmap: 0b{format(bitmap, '08b')}")
        idx += 1
        r = {'IP 3 tuple bitmap': format(bitmap, '08b')}
        if bitmap & 0x01:
            for i in range(4):
                _bm(bytemap, idx + i, hb, f"IP 3 tuple - IPv4 address [{i}]")
            r['IPv4 address'] = '.'.join(str(int(hb[idx + i], 16)) for i in range(4)); idx += 4
            for i in range(4):
                _bm(bytemap, idx + i, hb, f"IP 3 tuple - IPv4 subnet mask [{i}]")
            r['Subnet mask'] = '.'.join(str(int(hb[idx + i], 16)) for i in range(4)); idx += 4
        if bitmap & 0x02:
            for i in range(16):
                _bm(bytemap, idx + i, hb, f"IP 3 tuple - IPv6 address [{i}]")
            r['IPv6 address'] = str(ipaddress.IPv6Address(int(''.join(hb[idx:idx + 16]), 16))); idx += 16
            pfx = int(hb[idx], 16)

            _bm(bytemap, idx, hb, f"IP 3 tuple - IPv6 prefix length: {pfx}")

            idx += 1; r['Prefix length'] = pfx
        if bitmap & 0x04:
            pid = int(hb[idx], 16)
            key = 'Protocol identifier' if (bitmap & 0x01) else ('Next header' if (bitmap & 0x02) else 'Protocol identifier/Next header')
            _bm(bytemap, idx, hb, f"IP 3 tuple - {key}: {PROTOCOL_MAP.get(pid, str(pid))}")
            idx += 1
            r[key] = PROTOCOL_MAP.get(pid, str(pid))
        if bitmap & 0x08:
            _bm(bytemap, idx, hb, "IP 3 tuple - Single remote port [0]")
            _bm(bytemap, idx + 1, hb, "IP 3 tuple - Single remote port [1]")
            port, idx = _u16(hb, idx); r['Remote port'] = port
        if bitmap & 0x10:
            _bm(bytemap, idx, hb, "IP 3 tuple - Port range low limit [0]")
            _bm(bytemap, idx + 1, hb, "IP 3 tuple - Port range low limit [1]")
            lo, idx = _u16(hb, idx)
            _bm(bytemap, idx, hb, "IP 3 tuple - Port range high limit [0]")
            _bm(bytemap, idx + 1, hb, "IP 3 tuple - Port range high limit [1]")
            hi, idx = _u16(hb, idx)
            r['Remote port low'] = lo; r['Remote port high'] = hi
        return {'type': type_name, 'value': r}, idx

    elif type_name == "Security parameter index":
        for i in range(4):
            _bm(bytemap, idx + i, hb, f"Security parameter index byte [{i}]")
        spi = 0
        for i in range(4): spi = (spi << 8) + int(hb[idx + i], 16)
        idx += 4
        return {'type': type_name, 'value': f"0x{spi:08X}"}, idx

    elif type_name == "Type of service/traffic class":
        v = int(hb[idx], 16)
        dscp_entry = DSCP_MAP.get(v & 0xFC)
        dscp_desc = f"({dscp_entry[1]})" if dscp_entry else ""
        _bm(bytemap, idx, hb, f"Type of service/traffic class value: {v:02X} {dscp_desc}")
        idx += 1
        mask = int(hb[idx], 16)
        mask_desc = TOS_MASK_MAP.get(mask, "")
        mask_str = f"({mask_desc})" if mask_desc else ""
        _bm(bytemap, idx, hb, f"Type of service/traffic class mask: {mask:02X} {mask_str}")
        idx += 1
        # Return as dict so _render_value_tree handles display
        val_display = f"{v:02X} {dscp_desc}" if dscp_desc else f"{v:02X}"
        mask_display = f"{mask:02X} {mask_str}" if mask_str else f"{mask:02X}"
        return {'type': type_name, 'value': {'Value': val_display, 'Mask': mask_display}}, idx

    elif type_name == "Flow label":
        for i in range(3):
            _bm(bytemap, idx + i, hb, f"Flow label byte [{i}]")
        fl = 0
        for i in range(3): fl = (fl << 8) + int(hb[idx + i], 16)
        idx += 3
        return {'type': type_name, 'value': f"0x{fl:05X}"}, idx

    elif type_name == "Destination MAC address":
        for i in range(6):
            _bm(bytemap, idx + i, hb, f"Destination MAC address [{i}]")
        mac = ':'.join(hb[idx + i] for i in range(6)); idx += 6
        return {'type': type_name, 'value': mac}, idx

    elif type_name in ("802.1Q C-TAG VID", "802.1Q S-TAG VID"):
        tag = "C-TAG" if "C-TAG" in type_name else "S-TAG"
        _bm(bytemap, idx, hb, f"{tag} VID (high byte)")
        _bm(bytemap, idx + 1, hb, f"{tag} VID (low byte)")
        v, idx = _u16(hb, idx)
        return {'type': type_name, 'value': v}, idx

    elif type_name in ("802.1Q C-TAG PCP/DEI", "802.1Q S-TAG PCP/DEI"):
        tag = "C-TAG" if "C-TAG" in type_name else "S-TAG"
        v = int(hb[idx], 16)
        _bm(bytemap, idx, hb, f"{tag} PCP/DEI: {v:02X}")
        idx += 1
        return {'type': type_name, 'value': f"0x{v:02X}"}, idx

    elif type_name == "Ethertype":
        _bm(bytemap, idx, hb, "Ethertype (high byte)")
        _bm(bytemap, idx + 1, hb, "Ethertype (low byte)")
        v, idx = _u16(hb, idx)
        return {'type': type_name, 'value': f"0x{v:04X}"}, idx

    elif type_name == "DNN":
        dnn_len = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"DNN length: {dnn_len}")

        idx += 1
        apn_len = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"APN length: {apn_len}")

        idx += 1
        name, idx = _bm_ascii(bytemap, hb, idx, apn_len, "APN value")
        return {'type': type_name, 'value': name}, idx

    elif type_name == "Connection capabilities":
        n = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"Number of connection capabilities: {n}")

        idx += 1
        caps = []
        for _ in range(n):
            cid = int(hb[idx], 16)
            if cid in CONNECTION_CAPABILITY_MAP:
                cap_name = CONNECTION_CAPABILITY_MAP[cid]
            elif 0x20 <= cid <= 0xA0:
                cap_name = f"Operator specific (0x{cid:02X})"
            else:
                cap_name = f"Unknown (0x{cid:02X})"
            _bm(bytemap, idx, hb, f"Connection capability: {cap_name}")
            caps.append(cap_name)
            idx += 1
        return {'type': type_name, 'value': caps}, idx

    elif type_name == "Destination FQDN":
        flen = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"Destination FQDN length: {flen}")

        idx += 1
        name, idx = _bm_ascii(bytemap, hb, idx, flen, "Destination FQDN")
        return {'type': type_name, 'value': name}, idx

    elif type_name == "Regular expression":
        rlen = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"Regex length: {rlen}")

        idx += 1
        expr, idx = _bm_ascii(bytemap, hb, idx, rlen, "Regex")
        return {'type': type_name, 'value': expr}, idx

    elif type_name == "OS App Id":
        alen = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"OS App Id length: {alen}")

        idx += 1
        name, idx = _bm_ascii(bytemap, hb, idx, alen, "OS App Id")
        return {'type': type_name, 'value': name}, idx

    elif type_name == "Destination MAC address range":
        for i in range(6):
            _bm(bytemap, idx + i, hb, f"Destination MAC address range low limit [{i}]")
        lo = ':'.join(hb[idx + i] for i in range(6)); idx += 6
        for i in range(6):
            _bm(bytemap, idx + i, hb, f"Destination MAC address range high limit [{i}]")
        hi = ':'.join(hb[idx + i] for i in range(6)); idx += 6
        return {'type': type_name, 'value': {'Low limit': lo, 'High limit': hi}}, idx

    elif type_name == "PIN ID":
        plen = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"PIN ID length: {plen}")

        idx += 1
        name, idx = _bm_ascii(bytemap, hb, idx, plen, "PIN ID")
        return {'type': type_name, 'value': name}, idx

    elif type_name == "Connectivity group ID":
        glen = int(hb[idx], 16)

        _bm(bytemap, idx, hb, f"Connectivity group ID length: {glen}")

        idx += 1
        name, idx = _bm_ascii(bytemap, hb, idx, glen, "Group ID")
        return {'type': type_name, 'value': name}, idx

    else:
        if idx < len(hb):
            _bm(bytemap, idx, hb, f"{type_name} length (unknown type)")
            skip, idx = _u8(hb, idx); idx += skip
        return {'type': type_name, 'value': ''}, idx

# ============================================================================
# RSD parser — returns normalized form directly
# ============================================================================

def _parse_rsd(hb, idx, bytemap=None, rule_idx=0, rsd_idx=0):
    rsd_len = _bm_2byte_len(bytemap, hb, idx, "Length of route selection descriptor", f" {rsd_idx + 1}")
    idx += 2
    rsd_end = idx + rsd_len

    pv = int(hb[idx], 16)

    _bm(bytemap, idx, hb, f"precedence_value of route selection descriptor: {pv}")

    idx += 1

    cont_len = _bm_2byte_len(bytemap, hb, idx, "Length of route selection descriptor contents")
    idx += 2
    cont_end = idx + cont_len

    components = []
    while idx < cont_end and idx < len(hb):
        type_id = int(hb[idx], 16)
        type_name = RSD_TYPES_BY_ID.get(type_id, f"Unknown(0x{type_id:02X})")
        _bm(bytemap, idx, hb, f"RSD component type: {type_name}")
        idx += 1

        if type_name in RSD_ZERO:
            components.append({'type': type_name})

        elif type_name == "SSC mode":
            v = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"SSC mode value: {SSC_MODE_MAP.get(v, str(v))}")
            idx += 1
            components.append({'type': type_name, 'value': SSC_MODE_MAP.get(v, str(v))})

        elif type_name == "S-NSSAI":
            slen = int(hb[idx], 16)

            _bm(bytemap, idx, hb, f"S-NSSAI length: {slen}")

            idx += 1
            sst = int(hb[idx], 16)
            sst_name = SST_STANDARD_VALUES.get(sst, '')
            sst_display = f"{sst:02X} ({sst_name})" if sst_name else format(sst, '02X')
            _bm(bytemap, idx, hb, f"SST value: {sst_display}")
            idx += 1
            if slen == 4:
                _bm(bytemap, idx, hb, "SD value [0]")
                _bm(bytemap, idx + 1, hb, "SD value [1]")
                _bm(bytemap, idx + 2, hb, "SD value [2]")
                sd = (int(hb[idx], 16) << 16) | (int(hb[idx + 1], 16) << 8) | int(hb[idx + 2], 16); idx += 3
                components.append({'type': type_name, 'value': {'SST': sst_display, 'SD': format(sd, '06X')}})
            else:
                components.append({'type': type_name, 'value': {'SST': sst_display}})

        elif type_name == "DNN":
            dlen = int(hb[idx], 16)

            _bm(bytemap, idx, hb, f"DNN length: {dlen}")

            idx += 1
            alen = int(hb[idx], 16)

            _bm(bytemap, idx, hb, f"APN length: {alen}")

            idx += 1
            name, idx = _bm_ascii(bytemap, hb, idx, alen, "APN value")
            components.append({'type': type_name, 'value': name})

        elif type_name == "PDU session type":
            v = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"PDU session type value: {PDU_SESSION_TYPE_MAP.get(v, str(v))}")
            idx += 1
            components.append({'type': type_name, 'value': PDU_SESSION_TYPE_MAP.get(v, str(v))})

        elif type_name == "Preferred access type":
            v = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"Preferred access type value: {PREFERRED_ACCESS_TYPE_MAP.get(v, str(v))}")
            idx += 1
            components.append({'type': type_name, 'value': PREFERRED_ACCESS_TYPE_MAP.get(v, str(v))})

        elif type_name == "PDU session pair ID":
            v = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"PDU session pair ID value: {PDU_SESSION_PAIR_ID_MAP.get(v, str(v))}")
            idx += 1
            components.append({'type': type_name, 'value': PDU_SESSION_PAIR_ID_MAP.get(v, str(v))})

        elif type_name == "RSN":
            v = int(hb[idx], 16)
            _bm(bytemap, idx, hb, f"RSN value: {RSN_MAP.get(v, str(v))}")
            idx += 1
            components.append({'type': type_name, 'value': RSN_MAP.get(v, str(v))})

        elif type_name == "Location criteria":
            loc_len = int(hb[idx], 16)

            _bm(bytemap, idx, hb, f"Length of location criteria: {loc_len}")

            idx += 1
            loc_end = idx + loc_len
            result = {}
            while idx < loc_end and idx < len(hb):
                loc_type_id = int(hb[idx], 16)
                loc_type_name = LOCATION_AREA_TYPES.get(loc_type_id, f"Unknown(0x{loc_type_id:02X})")
                _bm(bytemap, idx, hb, f"Type of location area: {loc_type_name}")
                idx += 1
                cell_size = LOCATION_AREA_CELL_SIZES.get(loc_type_id, 8)
                area_dict = {}
                if loc_type_id == 0x04:
                    # Parse TAI list IE (TS 24.501 9.11.3.9)
                    # Structure: length(1 byte) + partial list contents
                    # Output structure: {"Partial list N": {"type": X, "num": Y, "PLMN": "MCC/MNC", "TAC 1": "hex", ...}}
                    tai_len = int(hb[idx], 16)

                    _bm(bytemap, idx, hb, f"Length of TAI list contents: {tai_len}")

                    idx += 1
                    tai_end = idx + tai_len
                    partial_idx = 0
                    TAI_LIST_TYPE_NAMES = {0: "non-consecutive", 1: "consecutive", 2: "different PLMNs"}
                    while idx < tai_end and idx < len(hb):
                        type_num = int(hb[idx], 16)
                        list_type = (type_num >> 5) & 0x07
                        num_elements = (type_num & 0x1F) + 1
                        list_type_name = TAI_LIST_TYPE_NAMES.get(list_type, "reserved")
                        _bm(bytemap, idx, hb, f"Partial tracking area identity list - Type of list: {list_type}({list_type_name} TAC values), Number of elements: {num_elements}")
                        idx += 1
                        partial_idx += 1
                        partial_dict = {}
                        partial_dict["Type of list"] = f"{list_type} ({list_type_name} TAC)" if list_type <= 1 else f"{list_type} ({list_type_name})"
                        partial_dict["Number of elements"] = num_elements
                        # Read PLMN (3 bytes)
                        plmn_hex = ''
                        plmn_start_idx = idx
                        for b in range(3):
                            if idx < len(hb):
                                plmn_hex += hb[idx]; idx += 1
                        # Parse MCC/MNC from nibble-swap PLMN
                        plmn_str = ""
                        if len(plmn_hex) == 6:
                            n0 = int(plmn_hex[0:2], 16); n1 = int(plmn_hex[2:4], 16); n2 = int(plmn_hex[4:6], 16)
                            mcc = f"{n0 & 0x0F}{(n0 >> 4) & 0x0F}{n1 & 0x0F}"
                            mnc3 = (n1 >> 4) & 0x0F
                            mnc = f"{n2 & 0x0F}{(n2 >> 4) & 0x0F}"
                            if mnc3 != 0x0F: mnc += str(mnc3)
                            plmn_str = f"{mcc}/{mnc}"
                        _bm(bytemap, plmn_start_idx, hb, f"TAI list - MCC digit 2, MCC digit 1 (PLMN: {plmn_str})")
                        _bm(bytemap, plmn_start_idx + 1, hb, "TAI list - MNC digit 3, MCC digit 3")
                        _bm(bytemap, plmn_start_idx + 2, hb, "TAI list - MNC digit 2, MNC digit 1")
                        partial_dict["PLMN"] = plmn_str
                        if list_type == 0x00:
                            # Type 0: same PLMN, list of TACs
                            for t in range(num_elements):
                                tac_hex = ''
                                for b in range(3):
                                    if idx < len(hb):
                                        _bm(bytemap, idx, hb, f"TAC {t + 1} [{b}]")
                                        tac_hex += hb[idx]; idx += 1
                                partial_dict[f"TAC {t + 1}"] = tac_hex
                        elif list_type == 0x01:
                            # Type 1: same PLMN, consecutive TACs (first TAC only in encoding)
                            tac_hex = ''
                            for b in range(3):
                                if idx < len(hb):
                                    _bm(bytemap, idx, hb, f"TAC of the first TAI belonging to the partial list [{b}]")
                                    tac_hex += hb[idx]; idx += 1
                            partial_dict["TAC (first)"] = tac_hex
                        elif list_type == 0x02:
                            # Type 2: different PLMNs
                            tac_hex = ''
                            for b in range(3):
                                if idx < len(hb):
                                    _bm(bytemap, idx, hb, f"TAC 1 [{b}]")
                                    tac_hex += hb[idx]; idx += 1
                            partial_dict[f"TAI 1"] = f"{plmn_str}/{tac_hex}"
                            for t in range(1, num_elements):
                                p_hex = ''
                                p_start_idx = idx
                                for b in range(3):
                                    if idx < len(hb):
                                        p_hex += hb[idx]; idx += 1
                                p_str = ""
                                if len(p_hex) == 6:
                                    n0 = int(p_hex[0:2], 16); n1 = int(p_hex[2:4], 16); n2 = int(p_hex[4:6], 16)
                                    mcc2 = f"{n0 & 0x0F}{(n0 >> 4) & 0x0F}{n1 & 0x0F}"
                                    mnc3_2 = (n1 >> 4) & 0x0F
                                    mnc2 = f"{n2 & 0x0F}{(n2 >> 4) & 0x0F}"
                                    if mnc3_2 != 0x0F: mnc2 += str(mnc3_2)
                                    p_str = f"{mcc2}/{mnc2}"
                                _bm(bytemap, p_start_idx, hb, f"TAI list - MCC digit 2, MCC digit 1 (PLMN: {p_str})")
                                _bm(bytemap, p_start_idx + 1, hb, "TAI list - MNC digit 3, MCC digit 3")
                                _bm(bytemap, p_start_idx + 2, hb, "TAI list - MNC digit 2, MNC digit 1")
                                t_hex = ''
                                for b in range(3):
                                    if idx < len(hb):
                                        _bm(bytemap, idx, hb, f"TAC {t + 1} [{b}]")
                                        t_hex += hb[idx]; idx += 1
                                partial_dict[f"TAI {t + 1}"] = f"{p_str}/{t_hex}"
                        area_dict[f"Partial TAI list {partial_idx}"] = partial_dict
                else:
                    # ECI (7 bytes), NCI (8 bytes), Global gNB ID (7 bytes)
                    # Format: PLMN(3 bytes) + Cell ID (remaining bytes)
                    # Output: {"NR cell id 1": {"PLMN": "MCC/MNC", "NCI": "hex"}, ...}
                    cell_elem_name = 'NR cell id' if loc_type_id == 0x02 else 'E-UTRA cell id' if loc_type_id == 0x01 else 'Global gNB id'
                    cell_id_label = 'NCI' if loc_type_id == 0x02 else 'ECI' if loc_type_id == 0x01 else 'gNB ID'
                    num_cells = int(hb[idx], 16)

                    _bm(bytemap, idx, hb, f"Number of {loc_type_name}: {num_cells}")

                    idx += 1
                    for c in range(num_cells):
                        cell_hex = ''
                        for b in range(cell_size):
                            if idx < len(hb):
                                _bm(bytemap, idx, hb, f"{cell_elem_name} {c + 1} [{b}]")
                                cell_hex += hb[idx]; idx += 1
                        # Parse PLMN (first 6 hex = 3 bytes) + remaining as cell id
                        cell_dict = {}
                        if len(cell_hex) >= 6:
                            plmn_part = cell_hex[:6]
                            cell_id_part = cell_hex[6:]
                            n0 = int(plmn_part[0:2], 16); n1 = int(plmn_part[2:4], 16); n2 = int(plmn_part[4:6], 16)
                            mcc = f"{n0 & 0x0F}{(n0 >> 4) & 0x0F}{n1 & 0x0F}"
                            mnc3 = (n1 >> 4) & 0x0F
                            mnc = f"{n2 & 0x0F}{(n2 >> 4) & 0x0F}"
                            if mnc3 != 0x0F: mnc += str(mnc3)
                            cell_dict["PLMN"] = f"{mcc}/{mnc}"
                            cell_dict[cell_id_label] = cell_id_part
                        else:
                            cell_dict[cell_id_label] = cell_hex
                        area_dict[f"{cell_elem_name} {c + 1}"] = cell_dict
                result[loc_type_name] = area_dict
            components.append({'type': type_name, 'value': result})

        elif type_name == "Time window":
            import datetime
            start_int = 0
            for b in range(4):
                _bm(bytemap, idx, hb, f"Starttime integer [{b}]")
                start_int = (start_int << 8) | int(hb[idx], 16); idx += 1
            for b in range(4):
                _bm(bytemap, idx, hb, f"Starttime fraction [{b}]")
                idx += 1
            stop_int = 0
            for b in range(4):
                _bm(bytemap, idx, hb, f"Stoptime integer [{b}]")
                stop_int = (stop_int << 8) | int(hb[idx], 16); idx += 1
            for b in range(4):
                _bm(bytemap, idx, hb, f"Stoptime fraction [{b}]")
                idx += 1
            try:
                start_iso = datetime.datetime.fromtimestamp(start_int).strftime('%Y-%m-%dT%H:%M:%S')
                stop_iso = datetime.datetime.fromtimestamp(stop_int).strftime('%Y-%m-%dT%H:%M:%S')
            except (OSError, OverflowError, ValueError):
                start_iso = f"epoch:{start_int}"
                stop_iso = f"epoch:{stop_int}"
            components.append({'type': type_name, 'value': {'Starttime': start_iso, 'Stoptime': stop_iso}})

        else:
            if idx < len(hb):
                skip = int(hb[idx], 16)

                _bm(bytemap, idx, hb, f"{type_name} length: {skip}")

                idx += 1; idx += skip
            components.append({'type': type_name, 'value': ''})

    return {
        'Precedence value': pv,
        'Route selection descriptor contents': components,
    }, rsd_end

# ============================================================================
# Tree renderer — public, produces indented tree text from decoded result
# ============================================================================

# Single point of control for indent width (characters per level).
# Change this value to resize the entire tree uniformly.
_INDENT = 3

# Derived connector strings
_PIPE = "│" + " " * (_INDENT - 1)   # "│  "  (active continuation)
_SPACE = " " * _INDENT               # "   "  (inactive continuation)
_TEE = "├─"
_ELBOW = "└─"

def _branch(is_last):
    """Return (connector, continuation) for a tree branch.

    connector: _TEE or _ELBOW (the visible fork character)
    continuation: _PIPE or _SPACE (prefix for child lines)
    """
    if is_last:
        return _ELBOW, _SPACE
    return _TEE, _PIPE

def _render_value_tree(value, prefix, cont):
    """Render a structured value (dict/list) as tree sub-items, recursively."""
    lines = []
    if isinstance(value, dict):
        items = list(value.items())
        for i, (k, v) in enumerate(items):
            p, c = _branch(i == len(items) - 1)
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{cont}{p} {k}")
                lines.extend(_render_value_tree(v, f"{prefix}{cont}", c))
            else:
                lines.append(f"{prefix}{cont}{p} {k}: {v}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            p, _ = _branch(i == len(value) - 1)
            lines.append(f"{prefix}{cont}{p} {item}")
    return lines

def format_ursp_tree(decoded):
    """Render decoded URSP rules as indented tree text string.

    All levels use _INDENT-character wide indent units via _branch().
    Change _INDENT at the top to resize the entire tree uniformly.
    """
    if not decoded or 'URSP rules' not in decoded:
        return ''
    rules = decoded['URSP rules']
    result = ['URSP Rules']

    for ri, rule in enumerate(rules):
        pv = rule['Precedence value']
        rp, rc = _branch(ri == len(rules) - 1)
        result.append(f"{rp} URSP rule {ri + 1}")
        result.append(f"{rc}{_TEE} Precedence: {pv}")

        # Traffic descriptor
        td_list = rule.get('Traffic descriptor', [])
        is_match_all = len(td_list) == 1 and td_list[0].get('type') == 'Match-all'
        if not td_list or is_match_all:
            result.append(f"{rc}{_TEE} Traffic descriptor")
            result.append(f"{rc}{_PIPE}{_ELBOW} Match-all")
        else:
            result.append(f"{rc}{_TEE} Traffic descriptor")
            for ti, td in enumerate(td_list):
                tp, tc = _branch(ti == len(td_list) - 1)
                tv = td.get('value', '')
                if td['type'] == 'Match-all':
                    result.append(f"{rc}{_PIPE}{tp} {td['type']}")
                elif isinstance(tv, (dict, list)):
                    result.append(f"{rc}{_PIPE}{tp} {td['type']}")
                    result.extend(_render_value_tree(tv, f"{rc}{_PIPE}", tc))
                else:
                    result.append(f"{rc}{_PIPE}{tp} {td['type']}: {tv}")

        # Route selection descriptor list
        rsd_list = rule.get('Route selection descriptor list', [])
        result.append(f"{rc}{_ELBOW} Route selection descriptor list")
        for si, rsd in enumerate(rsd_list):
            sp, sc = _branch(si == len(rsd_list) - 1)
            conts = rsd.get('Route selection descriptor contents', [])
            result.append(f"{rc}{_SPACE}{sp} Route selection descriptor {si + 1}")
            result.append(f"{rc}{_SPACE}{sc}{_TEE} Precedence: {rsd['Precedence value']}")
            result.append(f"{rc}{_SPACE}{sc}{_ELBOW} Route selection descriptor contents")
            for ci, comp in enumerate(conts):
                cp, cc = _branch(ci == len(conts) - 1)
                cv = comp.get('value')
                if cv is None:
                    result.append(f"{rc}{_SPACE}{sc}{_SPACE}{cp} {comp['type']}")
                elif isinstance(cv, (dict, list)):
                    result.append(f"{rc}{_SPACE}{sc}{_SPACE}{cp} {comp['type']}")
                    result.extend(_render_value_tree(cv, f"{rc}{_SPACE}{sc}{_SPACE}", cc))
                else:
                    result.append(f"{rc}{_SPACE}{sc}{_SPACE}{cp} {comp['type']}: {cv}")

    return '\n'.join(result)
