"""Central constants."""
PRINTER_NAME = "YOUR-PRINTER-BLE-NAME"   # BLE name (serial) of the Phomemo M221
PRINTER_SERVICE_UUID = "0000af30-0000-1000-8000-00805f9b34fb"  # also accepted when advertised
WRITE_CHAR = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000ff03-0000-1000-8000-00805f9b34fb"
LABEL_W, LABEL_H = 400, 640        # 50 x 80 mm at 203 dpi
HEAD_PX = 576                      # print head width in pixels (72 bytes)
HOST, PORT = "127.0.0.1", 8221
CLAUDE_MODEL = "sonnet"
