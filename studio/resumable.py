"""One resumable downloader for install.py and the studio's Download button. Standard library only, because install.py runs before any package is installed.
It survives what a home connection does: a stall hits the read timeout, a dropped or cut-short connection waits and carries on from the bytes on disk, and a run stopped for any reason leaves a .part file the next run continues. Only a checksum failure throws bytes away, and that is the caller's call."""
import errno
import http.client
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHUNK = 1 << 20
READ_TIMEOUT_S = 30         # a stall longer than this counts as a dropped connection
TRIES = 12                  # failures in a row with no new bytes; about ten minutes of waiting in all
WAITS_S = (5, 10, 20, 40, 60)
FATAL_ERRNOS = {errno.ENOSPC, errno.EACCES, errno.EROFS, errno.EDQUOT, errno.EPERM}      # waiting does not fix a full or read-only disk


class Cancelled(Exception):
    pass


class Refused(Exception):
    """The server said no (401, 403, 404...), which waiting does not change."""
    def __init__(self, status):
        super().__init__(f"the server refused the download ({status})")
        self.status = status


class GaveUp(Exception):
    """The connection kept failing. The bytes that arrived are still on disk."""


class DropTokenOnRedirect(urllib.request.HTTPRedirectHandler):
    """Hugging Face redirects large files to a CDN; the token stays on huggingface.co."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        host = (urllib.parse.urlparse(newurl).hostname or "").lower()
        if new is not None and host != "huggingface.co" and not host.endswith(".huggingface.co"):
            new.remove_header("Authorization")
        return new


def default_opener(timeout=READ_TIMEOUT_S):
    built = urllib.request.build_opener(DropTokenOnRedirect)
    return lambda req: built.open(req, timeout=timeout)


def expected_size(response, start):
    """The whole file's size from the response headers, or None if the server does not say."""
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    whole = (headers.get("Content-Range") or "").rpartition("/")[2]
    if whole.isdigit():
        return int(whole)
    length = headers.get("Content-Length") or ""
    return start + int(length) if length.isdigit() else None


def fetch_partial(url, partial, token=None, progress=None, cancelled=None, on_wait=None, opener=None, tries=TRIES, sleep=time.sleep):
    """Download url into the file `partial`, continuing from whatever it already holds. Returns its path once every byte has arrived. It does not check a hash or rename: that is the caller's job.
    progress(n) reports new bytes and progress(n, reset=True) the starting point. on_wait(fail, tries, seconds, why) runs before each wait. Raises Cancelled, Refused, GaveUp, or OSError for a disk problem."""
    partial = Path(partial)
    partial.parent.mkdir(parents=True, exist_ok=True)
    opener = opener or default_opener()
    fails = 0
    while True:
        if cancelled and cancelled():
            raise Cancelled()
        start = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "parametric-studio-downloader"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if start:
            headers["Range"] = f"bytes={start}-"
        try:
            try:
                response = opener(urllib.request.Request(url, headers=headers))
            except urllib.error.HTTPError as e:
                if e.code == 416:      # nothing left to send: the partial file is already whole
                    return partial
                if e.code < 500 and e.code not in (408, 429):
                    raise Refused(e.code) from None
                raise
            if start and getattr(response, "status", 200) != 206:
                start = 0              # the server ignored the Range header
            if progress:
                progress(start, reset=True)
            whole = expected_size(response, start)
            got = start
            with open(partial, "ab" if start else "wb") as out:
                while chunk := response.read(CHUNK):
                    if cancelled and cancelled():
                        raise Cancelled()
                    out.write(chunk)
                    got += len(chunk)
                    fails = 0
                    if progress:
                        progress(len(chunk))
            if whole is None or got >= whole:
                return partial
            raise ConnectionError(f"the connection closed early, at {got} of {whole} bytes")   # read() reports this as a normal end of file
        except (OSError, http.client.HTTPException) as e:
            if isinstance(e, OSError) and e.errno in FATAL_ERRNOS:
                raise
            fails += 1
            why = str(e) or type(e).__name__
            if fails >= tries:
                raise GaveUp(why) from e
            wait = WAITS_S[min(fails - 1, len(WAITS_S) - 1)]
            if on_wait:
                on_wait(fails, tries, wait, why)
            sleep(wait)
