import platform
import uuid

from flask import Blueprint, jsonify, request, send_file, after_this_request

hardware = Blueprint('hardware', __name__)

# ------------------------------------------------------------------


def get_mac_address():
    return ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                     for i in range(0, 8*6, 8)][::-1])

AUTHORIZED_DEVICES = {
    "a.vue": {
        "hostnames": ["A-PC"],
        "macs": ["00:1A:2B:3C:4D:5E"]
    },
    "b.vue": {
        "hostnames": ["B-PC"],
        "macs": ["00:1A:2B:3C:4D:FF"]
    }
}

@hardware.route('/hardware-id', methods=['GET'])
def check_authorization():
    target = request.args.get('target')  # e.g., a.vue
    current_hostname = platform.node()
    current_mac = get_mac_address().lower()

    auth = AUTHORIZED_DEVICES.get(target)

    if not auth:
        return jsonify({
            "status": "error",
            "message": f"Unknown target '{target}'"
        }), 400

    is_authorized = (current_hostname in auth["hostnames"]) or (current_mac in [mac.lower() for mac in auth["macs"]])

    return jsonify({
        "target": target,
        "authorized": is_authorized,
        "hostname": current_hostname,
        "mac": current_mac
    })