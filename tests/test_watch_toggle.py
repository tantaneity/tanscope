import asyncio

from tanscope.services.watch.scheduler import WatchScheduler


class _ExplodingService:
    async def enabled(self):
        raise AssertionError("disabled watcher must not poll anything")


def test_disabled_scheduler_returns_without_polling() -> None:
    scheduler = WatchScheduler(_ExplodingService(), delivery=None, interval_seconds=1, is_enabled=False)
    asyncio.run(asyncio.wait_for(scheduler.run(), timeout=1))


def test_enabled_scheduler_polls() -> None:
    polled = asyncio.Event()

    class _Service:
        async def enabled(self):
            polled.set()
            return []

    async def main() -> None:
        scheduler = WatchScheduler(_Service(), delivery=None, interval_seconds=60, is_enabled=True)
        task = asyncio.create_task(scheduler.run())
        await asyncio.wait_for(polled.wait(), timeout=1)
        task.cancel()

    asyncio.run(main())


if __name__ == "__main__":
    test_disabled_scheduler_returns_without_polling()
    test_enabled_scheduler_polls()
    print("ok")
