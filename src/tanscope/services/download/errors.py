class DownloadError(Exception):
    pass


class UnsupportedUrlError(DownloadError):
    pass


class NoMediaError(DownloadError):
    pass
