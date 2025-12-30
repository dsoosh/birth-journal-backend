from __future__ import annotations

import base64
from io import BytesIO

try:
    import qrcode
except ImportError:
    qrcode = None


def generate_qr_code(data: str) -> str | None:
    """Generate a QR code and return it as a base64-encoded PNG data URI.
    
    Args:
        data: The data to encode (URL, join code, etc.)
    
    Returns:
        A data URI string (data:image/png;base64,...) or None if qrcode not installed
    """
    if qrcode is None:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    png_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{png_data}"
