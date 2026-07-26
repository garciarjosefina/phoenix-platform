import time


class SystemMillisecondClock:
    def now_ms(self) -> int:
        return time.time_ns() // 1_000_000
