"""HTTP-based search backend using curl_cffi for TLS fingerprinting."""

import re
import base64
import logging
import asyncio
import atexit
import threading
from typing import Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from src.agent_swarm.search.base import SearchBackend

logger = logging.getLogger(__name__)


class HTTPSearchBackend(SearchBackend):
    """Fast HTTP-based search using curl_cffi with Chrome 146 TLS fingerprinting.
    
    Supports: Bing, DuckDuckGo, Google (in reliability order).
    """

    def __init__(
        self,
        impersonate: str = "chrome146",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        timeout: float = 15.0,
        max_retries: int = 2,
    ):
        self.impersonate = impersonate
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None
        self._session_lock = threading.Lock()
        self._closed = False
        atexit.register(self.close)

    def _get_session(self):
        """Get or create curl_cffi session (thread-safe)."""
        if self._closed:
            return None
        with self._session_lock:
            if self._session is None:
                try:
                    from curl_cffi.requests import Session
                    self._session = Session(impersonate=self.impersonate)
                    logger.debug(f"Created curl_cffi session with impersonate={self.impersonate}")
                except ImportError:
                    logger.error("curl_cffi not installed. Run: pip install curl_cffi")
                    return None
            return self._session

    def is_available(self) -> bool:
        """Check if curl_cffi is available."""
        try:
            from curl_cffi.requests import Session
            return True
        except ImportError:
            return False

    def close(self):
        """Clean up resources."""
        self._closed = True
        with self._session_lock:
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None
        logger.debug("HTTPSearchBackend closed")

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search using HTTP requests with TLS fingerprinting."""
        if self._closed:
            return []
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, self._search_sync, query, max_results)
        return results

    def _search_sync(self, query: str, max_results: int = 10) -> list[dict]:
        """Synchronous search: Bing → DuckDuckGo → Google."""
        session = self._get_session()
        if session is None:
            return self._search_with_httpx(query, max_results)

        results = self._search_bing(session, query, max_results)
        if results:
            return results[:max_results]

        logger.info("Bing returned no results, trying DuckDuckGo...")
        results = self._search_duckduckgo(session, query, max_results)
        if results:
            return results[:max_results]

        logger.info("DuckDuckGo returned no results, trying Google...")
        results = self._search_google(session, query, max_results)
        return results[:max_results]

    def _search_google(self, session, query: str, max_results: int) -> list[dict]:
        """Search Google via HTML scraping."""
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_results + 5}&hl=en&gl=us"
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "Cookie": "CONSENT=PENDING+987; SOCS=CAESHAgBEhJnd3NfMjAyMzEwMTAtMF9SQzEaAmVuIAEaBgiA-LaoBg",
            }
            response = session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"Google returned status {response.status_code}")
                return []

            results = self._parse_google_results(response.text, max_results)
            if not results:
                results = self._parse_google_results_alt(response.text, max_results)
            return results
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
            return []

    def _parse_google_results(self, html: str, max_results: int) -> list[dict]:
        """Parse Google search results from HTML - primary parser."""
        results = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            selectors = ["div.g", "div[data-attrid]", "div.Gx5Zad", "div.yuRUbf"]
            found_divs = []
            for selector in selectors:
                found_divs = soup.select(selector)
                if found_divs:
                    break

            for g_div in found_divs:
                if len(results) >= max_results:
                    break
                title_elem = g_div.select_one("h3") or g_div.select_one("h2")
                title = title_elem.get_text(strip=True) if title_elem else ""
                link_elem = g_div.select_one("a[href]")
                url = link_elem.get("href", "") if link_elem else ""
                if url.startswith("/url?q="):
                    url = url.split("/url?q=")[1].split("&")[0]
                elif url.startswith("/search?"):
                    continue
                elif not url.startswith("http"):
                    continue

                snippet_elem = (
                    g_div.select_one("div[data-sncf]") or
                    g_div.select_one("span.aCOpRe") or
                    g_div.select_one("div.VwiC3b") or
                    g_div.select_one("div.IsZvec") or
                    g_div.select_one("span.st")
                )
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if title and url:
                    results.append({
                        "title": title, "url": url, "snippet": snippet,
                        "content": "", "relevance_score": 0.7 - (len(results) * 0.05),
                        "source_type": "web", "provider": "google",
                    })
        except Exception as e:
            logger.warning(f"Failed to parse Google results: {e}")
        return results

    def _parse_google_results_alt(self, html: str, max_results: int) -> list[dict]:
        """Alternative Google parser - extracts links with h3 titles."""
        results = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for h3 in soup.find_all("h3"):
                if len(results) >= max_results:
                    break
                title = h3.get_text(strip=True)
                if not title:
                    continue
                parent_a = h3.find_parent("a") or h3.find_previous_sibling("a")
                if not parent_a:
                    continue
                url = parent_a.get("href", "")
                if url.startswith("/url?q="):
                    url = url.split("/url?q=")[1].split("&")[0]
                elif url.startswith("/search?") or not url.startswith("http"):
                    continue
                snippet = ""
                parent_div = h3.find_parent("div")
                if parent_div:
                    for span in parent_div.find_all("span"):
                        text = span.get_text(strip=True)
                        if len(text) > 30 and text != title:
                            snippet = text
                            break
                results.append({
                    "title": title, "url": url, "snippet": snippet,
                    "content": "", "relevance_score": 0.65 - (len(results) * 0.05),
                    "source_type": "web", "provider": "google",
                })
        except Exception as e:
            logger.debug(f"Alt Google parser failed: {e}")
        return results

    def _search_bing(self, session, query: str, max_results: int) -> list[dict]:
        """Search Bing via HTML scraping."""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results + 5}&setlang=en&cc=us"
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": self.user_agent,
            }
            response = session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"Bing returned status {response.status_code}")
                return []
            return self._parse_bing_results(response.text, max_results)
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
            return []

    @staticmethod
    def _decode_bing_url(url: str) -> str:
        """Decode Bing redirect URLs to get the actual target URL."""
        if not url or "bing.com/ck/a" not in url:
            return url
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                encoded = params['u'][0]
                if encoded.startswith('a1') or encoded.startswith('a3'):
                    encoded = encoded[2:]
                missing_padding = len(encoded) % 4
                if missing_padding:
                    encoded += '=' * (4 - missing_padding)
                decoded = base64.b64decode(encoded).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
        except Exception as e:
            logger.debug(f"Failed to decode Bing redirect URL: {e}")
        return url

    def _parse_bing_results(self, html: str, max_results: int) -> list[dict]:
        """Parse Bing search results from HTML."""
        results = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for li in soup.select("li.b_algo"):
                if len(results) >= max_results:
                    break
                title_elem = li.select_one("h2 a")
                title = title_elem.get_text(strip=True) if title_elem else ""
                url = title_elem.get("href", "") if title_elem else ""
                url = self._decode_bing_url(url)
                snippet_elem = li.select_one("p, .b_caption p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                if title and url and url.startswith('http'):
                    results.append({
                        "title": title, "url": url, "snippet": snippet,
                        "content": "", "relevance_score": 0.7 - (len(results) * 0.05),
                        "source_type": "web", "provider": "bing",
                    })
        except Exception as e:
            logger.warning(f"Failed to parse Bing results: {e}")
        return results

    def _search_duckduckgo(self, session, query: str, max_results: int) -> list[dict]:
        """Search DuckDuckGo via HTML scraping."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl=us-en"
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": self.user_agent,
                "Referer": "https://duckduckgo.com/",
            }
            import time
            max_retries = 3
            for attempt in range(max_retries):
                response = session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
                if response.status_code == 200:
                    break
                elif response.status_code == 202:
                    if attempt < max_retries - 1:
                        wait_time = 1.0 * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        return []
                else:
                    return []

            if response.status_code != 200:
                return []
            return self._parse_ddg_results(response.text, max_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def _parse_ddg_results(self, html: str, max_results: int) -> list[dict]:
        """Parse DuckDuckGo search results from HTML."""
        results = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            for result_div in soup.select(".result"):
                if len(results) >= max_results:
                    break
                title_elem = result_div.select_one(".result__a")
                title = title_elem.get_text(strip=True) if title_elem else ""
                url = title_elem.get("href", "") if title_elem else ""
                if url.startswith("//duckduckgo.com/l/?uddg="):
                    url = unquote(url.split("uddg=")[1].split("&")[0])
                elif url.startswith("/"):
                    continue
                snippet_elem = result_div.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                if title and url and url.startswith("http"):
                    results.append({
                        "title": title, "url": url, "snippet": snippet,
                        "content": "", "relevance_score": 0.6 - (len(results) * 0.05),
                        "source_type": "web", "provider": "duckduckgo",
                    })

            if not results:
                for link in soup.select("a.result__a"):
                    if len(results) >= max_results:
                        break
                    title = link.get_text(strip=True)
                    url = link.get("href", "")
                    if url.startswith("//duckduckgo.com/l/?uddg="):
                        url = unquote(url.split("uddg=")[1].split("&")[0])
                    if title and url.startswith("http"):
                        results.append({
                            "title": title, "url": url, "snippet": "",
                            "content": "", "relevance_score": 0.55 - (len(results) * 0.05),
                            "source_type": "web", "provider": "duckduckgo",
                        })
        except Exception as e:
            logger.warning(f"Failed to parse DuckDuckGo results: {e}")
        return results

    def _search_with_httpx(self, query: str, max_results: int) -> list[dict]:
        """Fallback search using httpx (no TLS fingerprinting)."""
        try:
            import httpx
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {"User-Agent": self.user_agent}
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    return self._parse_ddg_results(response.text, max_results)
        except Exception as e:
            logger.error(f"httpx fallback search failed: {e}")
        return []

    async def extract_content(self, url: str) -> Optional[str]:
        """Extract text content from a URL."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_content_sync, url)

    def _extract_content_sync(self, url: str) -> Optional[str]:
        """Synchronous content extraction."""
        try:
            session = self._get_session()
            if session is None:
                return None
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            response = session.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            if response.status_code != 200:
                return None
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = "\n".join(lines)
            if len(content) > 5000:
                content = content[:5000] + "..."
            return content
        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return None
