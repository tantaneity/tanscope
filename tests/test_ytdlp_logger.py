import logging

from tanscope.services.download.ytdlp_source import _YtDlpLogger

DEAD_COOKIES_WARNING = "[Instagram] The provided Instagram account cookies are no longer valid"


class _Recorder(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _record() -> tuple[_Recorder, logging.Logger]:
    recorder = _Recorder()
    logger = logging.getLogger("tanscope.services.download.ytdlp_source")
    logger.addHandler(recorder)
    logger.setLevel(logging.DEBUG)
    return recorder, logger


def test_warning_reaches_the_log() -> None:
    recorder, logger = _record()
    try:
        _YtDlpLogger().warning(DEAD_COOKIES_WARNING)
    finally:
        logger.removeHandler(recorder)
    assert any(DEAD_COOKIES_WARNING in message for message in recorder.messages), recorder.messages


def test_chatter_stays_out_of_the_log() -> None:
    recorder, logger = _record()
    try:
        quiet = _YtDlpLogger()
        quiet.debug("[debug] formats sorted")
        quiet.info("[download] 100%")
        quiet.error("ERROR: unsupported url")
    finally:
        logger.removeHandler(recorder)
    assert recorder.messages == []


if __name__ == "__main__":
    test_warning_reaches_the_log()
    test_chatter_stays_out_of_the_log()
    print("ok")
