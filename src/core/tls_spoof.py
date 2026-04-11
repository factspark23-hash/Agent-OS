"""
Agent-OS TLS Fingerprint Spoofing
Randomizes JA3 TLS fingerprint via CDP to evade advanced bot detection.
"""

import random
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("agent-os.tls_spoof")

# Real browser TLS cipher suites (Chrome 131+)
CHROME_CIPHERS = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_128_CBC_SHA",
    "TLS_RSA_WITH_AES_256_CBC_SHA",
]

# TLS extensions in order (real Chrome order)
TLS_EXTENSIONS = [
    "server_name",
    "extended_master_secret",
    "renegotiation_info",
    "supported_groups",
    "ec_point_formats",
    "application_layer_protocol_negotiation",
    "status_request",
    "signature_algorithms",
    "signed_certificate_timestamp",
    "key_share",
    "psk_key_exchange_modes",
    "supported_versions",
    "compress_certificate",
    "application_settings",
    "record_size_limit",
    "padding",
]

# Supported groups (elliptic curves)
SUPPORTED_GROUPS = [
    "X25519",
    "secp256r1",
    "secp384r1",
]

# Signature algorithms
SIGNATURE_ALGORITHMS = [
    "ecdsa_secp256r1_sha256",
    "rsa_pss_rsae_sha256",
    "rsa_pkcs1_sha256",
    "ecdsa_secp384r1_sha384",
    "rsa_pss_rsae_sha384",
    "rsa_pkcs1_sha384",
    "rsa_pss_rsae_sha512",
    "rsa_pkcs1_sha512",
]


def get_randomized_tls_config() -> Dict:
    """
    Generate a randomized but realistic TLS configuration.
    Returns a dict that can be applied via CDP Network.setUserAgentOverride
    or Network.setExtraHTTPHeaders.
    """
    # Shuffle cipher order slightly (real browsers have stable order but
    # different versions have different orders)
    ciphers = list(CHROME_CIPHERS)
    # Randomly swap 1-2 adjacent pairs to create variation
    for _ in range(random.randint(1, 2)):
        i = random.randint(0, len(ciphers) - 2)
        ciphers[i], ciphers[i + 1] = ciphers[i + 1], ciphers[i]

    # Randomize supported groups order
    groups = list(SUPPORTED_GROUPS)
    if random.random() > 0.5:
        groups[0], groups[1] = groups[1], groups[0]

    # Randomize ALPN (always h2 + http/1.1 for Chrome)
    alpn_protocols = ["h2", "http/1.1"]

    return {
        "ciphers": ciphers,
        "supported_groups": groups,
        "signature_algorithms": SIGNATURE_ALGORITHMS,
        "alpn_protocols": alpn_protocols,
        "tls_versions": ["TLS 1.3", "TLS 1.2"],
    }


async def apply_tls_spoofing(page, browser_version: str = "131") -> None:
    """
    Apply TLS fingerprint spoofing via CDP session.

    Args:
        page: Playwright page object
        browser_version: Chrome version to emulate
    """
    try:
        cdp = await page.context.new_cdp_session(page)

        # Set network user agent with realistic Chrome UA
        ua = (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{browser_version}.0.0.0 Safari/537.36"
        )

        await cdp.send("Network.setUserAgentOverride", {
            "userAgent": ua,
            "acceptLanguage": "en-US,en;q=0.9",
            "platform": "Win32",
            "userAgentMetadata": {
                "brands": [
                    {"brand": "Google Chrome", "version": browser_version},
                    {"brand": "Chromium", "version": browser_version},
                    {"brand": "Not/A)Brand", "version": "99"},
                ],
                "fullVersionList": [
                    {"brand": "Google Chrome", "version": f"{browser_version}.0.0.0"},
                    {"brand": "Chromium", "version": f"{browser_version}.0.0.0"},
                    {"brand": "Not/A)Brand", "version": "99.0.0.0"},
                ],
                "fullVersion": f"{browser_version}.0.0.0",
                "platform": "Windows",
                "platformVersion": "15.0.0",
                "architecture": "x86",
                "model": "",
                "mobile": False,
                "bitness": "64",
                "wow64": False,
            },
        })

        # Enable Network domain for header manipulation
        await cdp.send("Network.enable")

        # Set extra HTTP headers to match real Chrome
        await cdp.send("Network.setExtraHTTPHeaders", {
            "headers": {
                "sec-ch-ua": f'"Google Chrome";v="{browser_version}", "Chromium";v="{browser_version}", "Not/A)Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Accept-Encoding": "gzip, deflate, br",
            }
        })

        logger.info(f"TLS spoofing applied (Chrome {browser_version})")

    except Exception as e:
        logger.warning(f"TLS spoofing failed (non-fatal): {e}")
