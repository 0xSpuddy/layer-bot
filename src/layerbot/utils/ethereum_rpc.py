"""Ethereum RPC connection helpers with primary/fallback failover."""

import os
import threading
import time
from typing import List, Optional

from web3 import Web3
from web3.providers import BaseProvider, HTTPProvider


_RETRYABLE_ERROR_CODES = {-32005, -32016, -32603}
_RETRYABLE_ERROR_TEXT = (
    "rate limit",
    "too many request",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "service unavailable",
    "gateway",
)


def _is_retryable_response(response) -> bool:
    error = response.get("error") if isinstance(response, dict) else None
    if not error:
        return False

    code = error.get("code") if isinstance(error, dict) else None
    message = str(error.get("message", error) if isinstance(error, dict) else error).lower()
    return code in _RETRYABLE_ERROR_CODES or any(text in message for text in _RETRYABLE_ERROR_TEXT)


class FallbackHTTPProvider(BaseProvider):
    """Use another HTTP endpoint when the active endpoint has a transient failure."""

    def __init__(
        self,
        endpoint_urls: List[str],
        timeout: float,
        request_interval: float = 1.0,
        spacer=None,
    ):
        super().__init__()
        self._providers = [
            HTTPProvider(url, request_kwargs={"timeout": timeout}) for url in endpoint_urls
        ]
        self._active_index = 0
        self._spacer = spacer or RequestSpacer(request_interval)

    def make_request(self, method, params):
        last_exception = None
        last_response = None

        for offset in range(len(self._providers)):
            index = (self._active_index + offset) % len(self._providers)
            try:
                self._spacer.wait()
                response = self._providers[index].make_request(method, params)
            except Exception as exc:
                last_exception = exc
                continue

            if _is_retryable_response(response):
                last_response = response
                continue

            if index != self._active_index:
                print("Ethereum RPC failover activated")
                self._active_index = index
            return response

        if last_response is not None:
            return last_response
        if last_exception is not None:
            raise last_exception
        raise ConnectionError("No Ethereum RPC endpoints are configured")


class RequestSpacer:
    """Keep a minimum interval between Ethereum RPC request attempts."""

    def __init__(self, interval_seconds: float):
        self._interval = max(0.0, interval_seconds)
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            delay = self._interval - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            self._last_request = time.monotonic()


def _configured_urls() -> List[str]:
    urls = [
        os.getenv("ETHEREUM_RPC_URL", "").strip(),
        os.getenv("ETHEREUM_FALLBACK_RPC_URL", "").strip(),
    ]
    # Avoid sending every request twice when both variables contain the same URL.
    return list(dict.fromkeys(url for url in urls if url))


def get_ethereum_web3() -> Optional[Web3]:
    """Return a checked Web3 client that fails over on transient RPC errors."""
    urls = _configured_urls()
    if not urls:
        print(
            "Error: ETHEREUM_RPC_URL or ETHEREUM_FALLBACK_RPC_URL "
            "must be set in .env"
        )
        return None

    try:
        timeout = max(1.0, float(os.getenv("ETHEREUM_RPC_TIMEOUT_SECONDS", "10")))
    except ValueError:
        print("Warning: Invalid ETHEREUM_RPC_TIMEOUT_SECONDS; using 10 seconds")
        timeout = 10.0

    try:
        request_interval = max(
            0.0, float(os.getenv("ETHEREUM_RPC_REQUEST_INTERVAL_SECONDS", "1"))
        )
    except ValueError:
        print(
            "Warning: Invalid ETHEREUM_RPC_REQUEST_INTERVAL_SECONDS; "
            "using 1 second"
        )
        request_interval = 1.0

    spacer = RequestSpacer(request_interval)
    healthy_urls = []
    chain_id = None
    for index, url in enumerate(urls):
        label = "primary" if index == 0 else "fallback"
        try:
            candidate = Web3(
                FallbackHTTPProvider(
                    [url],
                    timeout,
                    request_interval=request_interval,
                    spacer=spacer,
                )
            )
            if not candidate.is_connected():
                print(f"Warning: Ethereum {label} RPC is not reachable")
                continue
            candidate_chain_id = candidate.eth.chain_id
            if chain_id is None:
                chain_id = candidate_chain_id
            elif candidate_chain_id != chain_id:
                print(
                    f"Warning: Ethereum {label} RPC is on chain ID "
                    f"{candidate_chain_id}, expected {chain_id}; ignoring it"
                )
                continue
            healthy_urls.append(url)
        except Exception as exc:
            # Do not print an exception containing an authenticated endpoint URL.
            print(
                f"Warning: Ethereum {label} RPC check failed "
                f"({type(exc).__name__})"
            )

    if not healthy_urls:
        print("Error: Could not connect to any configured Ethereum RPC endpoint")
        return None

    if healthy_urls[0] != urls[0]:
        print("Using fallback Ethereum RPC endpoint")
    print(f"Connected to Ethereum chain ID {chain_id}")
    print(f"Ethereum RPC request spacing: {request_interval:g} second(s)")
    return Web3(
        FallbackHTTPProvider(
            healthy_urls,
            timeout,
            request_interval=request_interval,
            spacer=spacer,
        )
    )
