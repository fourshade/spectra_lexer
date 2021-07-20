import random
import time


class ExponentialBackoff:
    """ An implementation of the exponential backoff algorithm.

    Provides a convenient interface to implement an exponential backoff
    for reconnecting or retrying transmissions in a distributed network.

    Once instantiated, the delay method will return the next interval to
    wait for when retrying a connection or transmission.  The maximum
    delay increases exponentially with each retry up to a maximum of
    2^10 * base, and is reset if no more attempts are needed in a period
    of 2^11 * base seconds. """

    def __init__(self, base=1) -> None:
        self._base = base  # Base delay in seconds. The first retry-delay will be up to this many seconds.
        self._exp = 0
        self._max = 10
        self._reset_time = base << 11
        self._last_invocation = time.monotonic()
        self._rand = random.Random()

    def delay(self) -> float:
        """ Return the next delay to wait according to the exponential
            backoff algorithm.  This is a value between 0 and base * 2^exp
            where exponent starts off at 1 and is incremented at every
            invocation of this method up to a maximum of 10.
            If a period of more than base * 2^11 has passed
            since the last retry, the exponent is reset to 1. """
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation
        if interval > self._reset_time:
            self._exp = 0
        self._exp = min(self._exp + 1, self._max)
        return self._rand.uniform(0, self._base * 2 ** self._exp)
