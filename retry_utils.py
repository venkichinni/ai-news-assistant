"""
retry_utils.py
Small retry-with-backoff helper so a single transient API hiccup (network
blip, rate limit, brief outage) doesn't kill the whole day's digest.
"""

import time


def retry_with_backoff(fn, attempts=3, base_delay_seconds=2, what=""):
    """
    Calls fn() up to `attempts` times, with exponential backoff between
    attempts (base_delay * 2^attempt_index). Returns fn()'s result on
    success, or raises the last exception if every attempt fails.
    """
    last_exception = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            label = f" ({what})" if what else ""
            if i < attempts - 1:
                delay = base_delay_seconds * (2 ** i)
                print(f"[warn] Attempt {i+1}/{attempts} failed{label}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"[error] All {attempts} attempts failed{label}: {e}")
    raise last_exception
