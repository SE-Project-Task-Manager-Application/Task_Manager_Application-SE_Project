import re


MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".csv", ".doc", ".docx", ".gif", ".jpg", ".jpeg", ".pdf", ".png", ".txt", ".zip"
}
EICAR_MARKER = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def scan_attachment(upload):
    """Perform the configured lightweight scanner check before storage."""
    if upload.size > MAX_ATTACHMENT_BYTES:
        return False, "The attachment must be 10 MB or smaller."
    name = upload.name or ""
    if not re.fullmatch(r"[^\\/:*?\"<>|\\r\\n]+", name) or "." not in name:
        return False, "The attachment filename is invalid."
    if "." + name.rsplit(".", 1)[-1].lower() not in ALLOWED_EXTENSIONS:
        return False, "This attachment type is not allowed."
    upload.seek(0)
    content = upload.read()
    upload.seek(0)
    if EICAR_MARKER in content:
        return False, "The attachment failed the malware scan."
    return True, ""
