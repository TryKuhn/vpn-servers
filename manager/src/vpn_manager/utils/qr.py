"""QR code rendering utilities."""

from __future__ import annotations

import io

import qrcode
from qrcode.constants import ERROR_CORRECT_L


def render_qr_to_terminal(text: str) -> str:
    """Render a QR code as a terminal-friendly Unicode string.

    Uses Unicode block characters (▀ and ▄) so the QR is rendered at
    twice the row density compared to ASCII. Each output character
    represents two QR pixels stacked vertically.

    Returns:
        The QR as a multi-line string, ready to be printed.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)

    # qrcode supports built-in terminal rendering via print_ascii(), which
    # we capture into a string buffer.
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=False, tty=False)
    return buf.getvalue()
