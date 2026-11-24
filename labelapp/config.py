"""Central constants."""
import os
# Printers are discovered by scan (see printer.scan); the chosen one is stored in STATE_FILE.
ADV_SERVICES = ("0000af30-0000-1000-8000-00805f9b34fb", "0000ff00-0000-1000-8000-00805f9b34fb")
GATT_SERVICE = "0000ff00-0000-1000-8000-00805f9b34fb"
NAME_PATTERN = r"^(M[012]|Q|D|T0|P12)"   # candidate name prefixes (any name containing "phomemo" also matches)
STATE_DIR = os.environ.get("LABELAPP_STATE_DIR") or os.path.expanduser("~/Library/Application Support/BeanLabels")
STATE_FILE = os.path.join(STATE_DIR, "printer.json")
WRITE_CHAR = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000ff03-0000-1000-8000-00805f9b34fb"
LABEL_W, LABEL_H = 400, 640        # 50 x 80 mm at 203 dpi
HEAD_PX = 576                      # print head width in pixels (72 bytes)
HOST, PORT = "127.0.0.1", 8221
CLAUDE_MODEL = "sonnet"
