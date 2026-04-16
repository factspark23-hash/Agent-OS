"""
Agent-OS AI Content Extractor
Transforms raw browser data into structured, symmetrical JSON that
AI agents can instantly parse — no fluff, no HTML noise, no guessing.

This is the key differentiator: when the browser/swarm fetches data,
it returns it in a format AI understands natively, not human-readable
fluff that requires another parsing step.

Design Principles:
1. Symmetrical: Same structure regardless of source (HTTP vs browser)
2. Type-tagged: Every piece of data has a type label AI can route on
3. Deduplicated: Nav, footer, sidebar, ads stripped automatically
4. Compact: Only the data AI needs, nothing extra
5. Schema-aware: Extract JSON-LD, Microdata, Open Graph when present

No external AI API needed — pure DOM analysis + heuristics.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("agent-os.ai_content")


# ─── Structured Output Types ────────────────────────────────────

@dataclass
class AIContent:
    """
    The universal structured output that AI agents receive.

    Every field is optional so the structure is always valid even
    for pages that lack certain content types. AI can check
    `content_type` to know what kind of page it's dealing with
    and which fields to expect data in.
    """
    # ── Identity ──────────────────────────────────────────
    content_type: str = "unknown"       # article, product, listing, forum, api_doc, search_results, profile, table, form, error, other
    url: str = ""
    title: str = ""
    domain: str = ""
    language: str = ""

    # ── Core Content ──────────────────────────────────────
    summary: str = ""                   # 2-3 sentence extractive summary
    main_text: str = ""                 # Clean, deduplicated body text
    headings: List[Dict[str, Any]] = field(default_factory=list)   # [{level, text, id}]
    paragraphs: List[str] = field(default_factory=list)            # Core paragraph texts

    # ── Structured Data ───────────────────────────────────
    tables: List[Dict[str, Any]] = field(default_factory=list)     # [{headers, rows}]
    lists: List[Dict[str, Any]] = field(default_factory=list)      # [{type: ol|ul, items: []}]
    code_blocks: List[Dict[str, Any]] = field(default_factory=list) # [{language, code}]
    forms: List[Dict[str, Any]] = field(default_factory=list)      # [{action, method, fields}]

    # ── Extracted Entities ────────────────────────────────
    links: List[Dict[str, str]] = field(default_factory=list)      # [{text, url, type}]
    images: List[Dict[str, str]] = field(default_factory=list)     # [{alt, src}]
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    prices: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)

    # ── Schema.org / Structured Data ──────────────────────
    schema_org: List[Dict[str, Any]] = field(default_factory=list)  # JSON-LD data
    open_graph: Dict[str, str] = field(default_factory=dict)
    meta: Dict[str, str] = field(default_factory=dict)

    # ── Metrics ───────────────────────────────────────────
    word_count: int = 0
    confidence: float = 0.0             # How confident we are in content_type
    extraction_method: str = ""         # "dom" or "http"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, omitting empty fields for compactness."""
        result = {}
        for key, value in asdict(self).items():
            if value or key in ("content_type", "url", "title"):
                result[key] = value
        return result


# ─── Content Type Detection ─────────────────────────────────────

class ContentTypeDetector:
    """
    Detects what type of content a page contains.
    Uses URL patterns, DOM structure, and meta tags.
    No external API needed — pure heuristics.
    """

    # URL patterns → content types
    URL_PATTERNS = {
        "product": [
            r"/product/", r"/products/", r"/item/", r"/p/", r"/dp/",
            r"amazon\.(com|in|co\.uk)/.*/dp/",
            r"ebay\.(com|co\.uk)/.*/itm/",
            r"etsy\.com/listing/",
            r"shopify\.(com|dev)/products/",
        ],
        "listing": [
            r"/search", r"/listings?", r"/catalog", r"/browse",
            r"/category/", r"/categories/", r"/collection/",
            r"/filter", r"/results",
        ],
        "forum": [
            r"/forum/", r"/thread/", r"/topic/", r"/discussion/",
            r"/post/", r"reddit\.com/r/", r"stackoverflow\.com/questions",
            r"discourse\.", r"/t/",
        ],
        "api_doc": [
            r"/api/", r"/docs/", r"/reference/", r"/endpoint/",
            r"swagger", r"openapi", r"/graphql",
            r"developer\.", r"api\.",
        ],
        "article": [
            r"/blog/", r"/article/", r"/news/", r"/story/",
            r"/post/", r"/\d{4}/\d{2}/",  # date-based URLs
            r"medium\.com/@", r"substack\.com",
        ],
        "profile": [
            r"/profile/", r"/user/", r"/u/", r"/@",
            r"linkedin\.com/in/", r"twitter\.com/",
            r"github\.com/[^/]+$",
        ],
    }

    @classmethod
    def detect(cls, url: str, dom_signals: Dict[str, Any] = None) -> tuple:
        """
        Detect content type and confidence score.

        Returns:
            (content_type, confidence) tuple
        """
        scores: Dict[str, float] = {}

        # 1. URL pattern matching (weight: 0.4)
        for content_type, patterns in cls.URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    scores[content_type] = scores.get(content_type, 0.0) + 0.4

        # 2. DOM signal matching (weight: 0.4)
        if dom_signals:
            # Schema.org types are strongest signals
            schema_types = dom_signals.get("schema_types", [])
            for st in schema_types:
                st_lower = st.lower()
                if "product" in st_lower:
                    scores["product"] = scores.get("product", 0.0) + 0.5
                elif "article" in st_lower or "newsarticle" in st_lower:
                    scores["article"] = scores.get("article", 0.0) + 0.5
                elif "person" in st_lower:
                    scores["profile"] = scores.get("profile", 0.0) + 0.5
                elif "searchresultspage" in st_lower or "itemlist" in st_lower:
                    scores["listing"] = scores.get("listing", 0.0) + 0.5
                elif "discussionforum" in st_lower or "comment" in st_lower:
                    scores["forum"] = scores.get("forum", 0.0) + 0.5

            # Open Graph type signals
            og_type = dom_signals.get("og_type", "").lower()
            if og_type == "product":
                scores["product"] = scores.get("product", 0.0) + 0.4
            elif og_type in ("article", "news"):
                scores["article"] = scores.get("article", 0.0) + 0.4
            elif og_type == "profile":
                scores["profile"] = scores.get("profile", 0.0) + 0.4

            # DOM structure signals
            has_article = dom_signals.get("has_article_tag", False)
            has_product = dom_signals.get("has_product_markup", False)
            has_forum = dom_signals.get("has_forum_markup", False)
            table_count = dom_signals.get("table_count", 0)
            form_count = dom_signals.get("form_count", 0)
            code_count = dom_signals.get("code_block_count", 0)

            if has_article:
                scores["article"] = scores.get("article", 0.0) + 0.3
            if has_product:
                scores["product"] = scores.get("product", 0.0) + 0.3
            if has_forum:
                scores["forum"] = scores.get("forum", 0.0) + 0.3
            if table_count > 3:
                scores["table"] = scores.get("table", 0.0) + 0.2
            if code_count > 2:
                scores["api_doc"] = scores.get("api_doc", 0.0) + 0.3
            if form_count > 0 and table_count == 0:
                scores["form"] = scores.get("form", 0.0) + 0.2

        # Pick the highest scoring type
        if not scores:
            return ("other", 0.3)

        best_type = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_type])
        return (best_type, round(confidence, 2))


# ─── Main Extractor ─────────────────────────────────────────────

class AIContentExtractor:
    """
    Extracts structured, AI-ready content from web pages.

    Usage with browser:
        extractor = AIContentExtractor()
        result = await extractor.extract_from_browser(browser, page_id="main")

    Usage with HTTP response:
        result = await extractor.extract_from_html(html, url)

    The result is always an AIContent object with a predictable
    structure — same fields regardless of how the page was fetched.
    """

    # JavaScript to run in the browser to extract all data in one pass
    _BROWSER_EXTRACT_JS = """() => {
        const result = {};

        // ── Basic Identity ─────────────────────────────────
        result.url = window.location.href;
        result.title = document.title;
        result.domain = window.location.hostname;
        result.language = document.documentElement.lang || '';

        // ── DOM Signals for Content Type Detection ─────────
        result.dom_signals = {
            schema_types: [],
            og_type: '',
            has_article_tag: !!document.querySelector('article'),
            has_product_markup: !!document.querySelector('[itemtype*="Product"], [data-product-id], .product-price'),
            has_forum_markup: !!document.querySelector('.post-body, .forum-post, [itemtype*="Comment"]'),
            table_count: document.querySelectorAll('table').length,
            form_count: document.querySelectorAll('form').length,
            code_block_count: document.querySelectorAll('pre, code').length,
        };

        // JSON-LD schema types
        document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
            try {
                const data = JSON.parse(s.textContent);
                if (data['@type']) result.dom_signals.schema_types.push(data['@type']);
                if (Array.isArray(data)) {
                    data.forEach(item => { if (item['@type']) result.dom_signals.schema_types.push(item['@type']); });
                }
            } catch(e) {}
        });

        // OG type
        const ogType = document.querySelector('meta[property="og:type"]');
        if (ogType) result.dom_signals.og_type = ogType.getAttribute('content') || '';

        // ── Main Content Extraction ────────────────────────
        // Try semantic containers first, fall back to body
        const mainSelectors = ['main', 'article', '[role="main"]', '.post-content', '.article-body', '.entry-content', '#content', '#main'];
        let mainEl = null;
        for (const sel of mainSelectors) {
            mainEl = document.querySelector(sel);
            if (mainEl) break;
        }
        if (!mainEl) mainEl = document.body;

        // ── Headings ──────────────────────────────────────
        result.headings = [];
        mainEl.querySelectorAll('h1, h2, h3, h4').forEach(h => {
            const text = h.textContent.trim();
            if (text && text.length < 200) {
                result.headings.push({
                    level: parseInt(h.tagName[1]),
                    text: text,
                    id: h.id || ''
                });
            }
        });

        // ── Paragraphs (deduplicated) ─────────────────────
        result.paragraphs = [];
        const seenTexts = new Set();
        mainEl.querySelectorAll('p').forEach(p => {
            const text = p.textContent.trim();
            // Skip short, duplicate, or boilerplate paragraphs
            if (text.length < 20) return;
            if (text.length > 3000) return;
            // Deduplicate by first 50 chars
            const key = text.substring(0, 50).toLowerCase();
            if (seenTexts.has(key)) return;
            seenTexts.add(key);
            // Skip nav/footer noise
            const parent = p.closest('nav, footer, header, .sidebar, .menu, .navigation');
            if (parent) return;
            result.paragraphs.push(text);
        });

        // ── Main Text (concatenated paragraphs) ───────────
        result.main_text = result.paragraphs.join('\\n\\n');

        // ── Tables ────────────────────────────────────────
        result.tables = [];
        document.querySelectorAll('table').forEach((table, idx) => {
            const headers = [];
            table.querySelectorAll('thead th, tr:first-child th').forEach(th => {
                headers.push(th.textContent.trim());
            });
            const rows = [];
            table.querySelectorAll('tbody tr, tr:not(:first-child)').forEach(tr => {
                const cells = [];
                tr.querySelectorAll('td').forEach(td => {
                    cells.push(td.textContent.trim().substring(0, 500));
                });
                if (cells.length > 0) rows.push(cells);
            });
            if (headers.length > 0 || rows.length > 0) {
                result.tables.push({
                    index: idx,
                    headers: headers,
                    rows: rows.slice(0, 50),  // Cap at 50 rows
                    row_count: rows.length,
                });
            }
        });

        // ── Lists ─────────────────────────────────────────
        result.lists = [];
        mainEl.querySelectorAll('ol, ul').forEach(list => {
            // Skip nav lists
            if (list.closest('nav, footer, header, .menu')) return;
            const items = [];
            list.querySelectorAll(':scope > li').forEach(li => {
                const text = li.textContent.trim().substring(0, 500);
                if (text) items.push(text);
            });
            if (items.length > 0 && items.length < 100) {
                result.lists.push({
                    type: list.tagName.toLowerCase(),
                    items: items,
                });
            }
        });

        // ── Code Blocks ──────────────────────────────────
        result.code_blocks = [];
        document.querySelectorAll('pre, pre > code').forEach(block => {
            const code = block.textContent.trim();
            if (code.length > 10 && code.length < 50000) {
                // Try to detect language from class
                let language = '';
                const codeEl = block.querySelector('code') || block;
                const classes = codeEl.className || '';
                const langMatch = classes.match(/language-(\\w+)|lang-(\\w+)|(\\w+)-code/);
                if (langMatch) language = langMatch[1] || langMatch[2] || langMatch[3] || '';
                result.code_blocks.push({
                    language: language,
                    code: code.substring(0, 10000),  // Cap at 10k chars
                });
            }
        });

        // ── Forms ────────────────────────────────────────
        result.forms = [];
        document.querySelectorAll('form').forEach(form => {
            const fields = [];
            form.querySelectorAll('input, textarea, select').forEach(inp => {
                const type = inp.type || inp.tagName.toLowerCase();
                if (type === 'hidden' || type === 'submit' || type === 'button') return;
                fields.push({
                    name: inp.name || inp.id || '',
                    type: type,
                    label: '',  // Will be filled below
                    required: inp.required,
                    placeholder: inp.placeholder || '',
                });
            });
            // Try to find labels
            form.querySelectorAll('label').forEach(label => {
                const forId = label.htmlFor;
                if (forId) {
                    const field = fields.find(f => f.name === forId);
                    if (field) field.label = label.textContent.trim();
                }
            });
            result.forms.push({
                action: form.action || '',
                method: (form.method || 'GET').toUpperCase(),
                fields: fields,
            });
        });

        // ── Links (deduplicated, categorized) ────────────
        result.links = [];
        const seenLinks = new Set();
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href;
            const text = (a.textContent || a.title || '').trim().substring(0, 200);
            if (!text || !href || text.length < 2) return;
            if (href.startsWith('javascript:') || href === '#') return;
            // Deduplicate
            const linkKey = href + '|' + text;
            if (seenLinks.has(linkKey)) return;
            seenLinks.add(linkKey);
            // Categorize
            let linkType = 'external';
            if (href.includes(window.location.hostname)) linkType = 'internal';
            else if (href.startsWith('mailto:')) linkType = 'email';
            else if (href.includes('download') || href.endsWith('.pdf') || href.endsWith('.zip')) linkType = 'download';

            result.links.push({text: text, url: href, type: linkType});
        });
        // Cap at 50 links
        result.links = result.links.slice(0, 50);

        // ── Images ───────────────────────────────────────
        result.images = [];
        document.querySelectorAll('img').forEach(img => {
            if (!img.src) return;
            // Skip tiny/hidden images (likely icons/tracking)
            if (img.naturalWidth > 0 && img.naturalWidth < 20) return;
            if (img.width > 0 && img.width < 20) return;
            result.images.push({
                alt: img.alt || '',
                src: img.src,
            });
        });
        result.images = result.images.slice(0, 30);

        // ── Emails ───────────────────────────────────────
        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
        const bodyText = document.body.innerText || '';
        result.emails = [...new Set(bodyText.match(emailRegex) || [])];

        // ── Phone Numbers ────────────────────────────────
        const phonePatterns = [
            /\\+?\\d{1,3}[-.\\s]?\\(?\\d{1,4}\\)?[-.\\s]?\\d{1,4}[-.\\s]?\\d{1,9}/g,
            /\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}/g,
        ];
        const phones = new Set();
        const cleanedText = bodyText.replace(/\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/g, ' ');
        phonePatterns.forEach(p => {
            (cleanedText.match(p) || []).forEach(m => {
                if (m.replace(/\\D/g, '').length >= 7) phones.add(m.trim());
            });
        });
        result.phones = [...phones];

        // ── Prices ───────────────────────────────────────
        const priceRegex = /[$€£¥₹]\\s?[\\d,]+\\.?\\d{0,2}|\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?\\s?(?:USD|EUR|GBP|JPY|INR)/g;
        result.prices = [...new Set((bodyText.match(priceRegex) || []))].slice(0, 20);

        // ── Schema.org (JSON-LD) ────────────────────────
        result.schema_org = [];
        document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
            try {
                const data = JSON.parse(script.textContent);
                result.schema_org.push(data);
            } catch(e) {}
        });

        // ── Open Graph ──────────────────────────────────
        result.open_graph = {};
        document.querySelectorAll('meta[property^="og:"]').forEach(m => {
            const key = m.getAttribute('property').replace('og:', '');
            const val = m.getAttribute('content');
            if (val) result.open_graph[key] = val;
        });

        // ── Meta Tags ───────────────────────────────────
        result.meta = {};
        document.querySelectorAll('meta[name], meta[property]').forEach(m => {
            const key = m.getAttribute('name') || m.getAttribute('property') || '';
            const val = m.getAttribute('content') || '';
            if (key && val && !key.startsWith('og:') && !key.startsWith('twitter:')) {
                result.meta[key] = val.substring(0, 500);
            }
        });

        // ── Word Count ──────────────────────────────────
        result.word_count = result.main_text.split(/\\s+/).filter(w => w.length > 0).length;

        return result;
    }"""

    async def extract_from_browser(self, browser, page_id: str = "main") -> Dict[str, Any]:
        """
        Extract AI-structured content from a browser page.

        Args:
            browser: AgentBrowser instance
            page_id: Browser page/tab identifier

        Returns:
            Dict with AIContent structure — same format regardless of page type
        """
        try:
            page = browser._pages.get(page_id, browser.page)
            raw = await page.evaluate(self._BROWSER_EXTRACT_JS)

            content = AIContent(
                url=raw.get("url", ""),
                title=raw.get("title", ""),
                domain=raw.get("domain", ""),
                language=raw.get("language", ""),
                headings=raw.get("headings", []),
                paragraphs=raw.get("paragraphs", []),
                main_text=raw.get("main_text", ""),
                tables=raw.get("tables", []),
                lists=raw.get("lists", []),
                code_blocks=raw.get("code_blocks", []),
                forms=raw.get("forms", []),
                links=raw.get("links", []),
                images=raw.get("images", []),
                emails=raw.get("emails", []),
                phones=raw.get("phones", []),
                prices=raw.get("prices", []),
                schema_org=raw.get("schema_org", []),
                open_graph=raw.get("open_graph", {}),
                meta=raw.get("meta", {}),
                word_count=raw.get("word_count", 0),
                extraction_method="dom",
            )

            # Generate summary from first few paragraphs
            content.summary = self._generate_summary(content.paragraphs)

            # Detect content type
            dom_signals = raw.get("dom_signals", {})
            content.content_type, content.confidence = ContentTypeDetector.detect(
                content.url, dom_signals
            )

            return {
                "status": "success",
                "data": content.to_dict(),
            }

        except Exception as exc:
            logger.error(f"Browser extraction failed: {exc}", exc_info=True)
            return {"status": "error", "error": str(exc)}

    async def extract_from_html(self, html: str, url: str = "") -> Dict[str, Any]:
        """
        Extract AI-structured content from raw HTML (HTTP fetch path).

        Uses BeautifulSoup for parsing — same output structure as
        extract_from_browser but without JavaScript execution.

        Args:
            html: Raw HTML string
            url: Source URL for context

        Returns:
            Dict with AIContent structure
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {"status": "error", "error": "BeautifulSoup not available for HTML parsing"}

        try:
            soup = BeautifulSoup(html, "html.parser")

            # ── Basic Identity ──────────────────────────────
            title_tag = soup.find("title")
            title = title_tag.string.strip() if title_tag and title_tag.string else ""
            lang = soup.find("html", lang=True)
            language = lang.get("lang", "") if lang else ""

            # ── Remove boilerplate ──────────────────────────
            for tag_name in ("script", "style", "noscript", "svg", "iframe"):
                for element in soup.find_all(tag_name):
                    element.decompose()
            for tag_name in ("nav", "footer", "header"):
                for element in soup.find_all(tag_name):
                    element.decompose()

            # ── Headings ────────────────────────────────────
            headings = []
            for h in soup.find_all(["h1", "h2", "h3", "h4"]):
                text = h.get_text(strip=True)
                if text and len(text) < 200:
                    headings.append({"level": int(h.name[1]), "text": text, "id": h.get("id", "")})

            # ── Paragraphs ─────────────────────────────────
            paragraphs = []
            seen = set()
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) < 20 or len(text) > 3000:
                    continue
                key = text[:50].lower()
                if key in seen:
                    continue
                seen.add(key)
                paragraphs.append(text)

            main_text = "\n\n".join(paragraphs)
            summary = self._generate_summary(paragraphs)

            # ── Tables ──────────────────────────────────────
            tables = []
            for idx, table in enumerate(soup.find_all("table")):
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                rows = []
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True)[:500] for td in tr.find_all("td")]
                    if cells:
                        rows.append(cells)
                if headers or rows:
                    tables.append({"index": idx, "headers": headers, "rows": rows[:50], "row_count": len(rows)})

            # ── Lists ───────────────────────────────────────
            lists = []
            for list_tag in soup.find_all(["ol", "ul"]):
                items = [li.get_text(strip=True)[:500] for li in list_tag.find_all("li", recursive=False)]
                if 0 < len(items) < 100:
                    lists.append({"type": list_tag.name, "items": items})

            # ── Code Blocks ────────────────────────────────
            code_blocks = []
            for pre in soup.find_all("pre"):
                code = pre.get_text(strip=True)
                if 10 < len(code) < 50000:
                    language = ""
                    code_el = pre.find("code")
                    if code_el:
                        classes = " ".join(code_el.get("class", []))
                        match = re.search(r"language-(\w+)", classes)
                        if match:
                            language = match.group(1)
                    code_blocks.append({"language": language, "code": code[:10000]})

            # ── Links ───────────────────────────────────────
            links = []
            seen_links = set()
            from urllib.parse import urlparse
            domain = urlparse(url).hostname or ""
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = (a.get_text(strip=True) or a.get("title", ""))[:200]
                if not text or not href or href.startswith("javascript:") or href == "#":
                    continue
                link_key = f"{href}|{text}"
                if link_key in seen_links:
                    continue
                seen_links.add(link_key)
                link_type = "internal" if domain in href else "external"
                links.append({"text": text, "url": href, "type": link_type})

            # ── Images ──────────────────────────────────────
            images = []
            for img in soup.find_all("img", src=True):
                images.append({"alt": img.get("alt", ""), "src": img["src"]})

            # ── Emails & Phones ─────────────────────────────
            body_text = soup.get_text()
            emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body_text)))
            cleaned_text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", " ", body_text)
            phones_raw = re.findall(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}", cleaned_text)
            phones = list(set(p.strip() for p in phones_raw if len(re.sub(r"\D", "", p)) >= 7))

            # ── Prices ──────────────────────────────────────
            prices = list(set(re.findall(
                r"[$€£¥₹]\s?[\d,]+\.?\d{0,2}|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s?(?:USD|EUR|GBP|JPY|INR)",
                body_text
            )))[:20]

            # ── Schema.org ──────────────────────────────────
            schema_org = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    schema_org.append(json.loads(script.string))
                except Exception:
                    pass

            # ── Open Graph ──────────────────────────────────
            open_graph = {}
            for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
                key = meta.get("property", "").replace("og:", "")
                val = meta.get("content", "")
                if key and val:
                    open_graph[key] = val

            # ── Meta ────────────────────────────────────────
            meta = {}
            for m in soup.find_all("meta", attrs={"name": True, "content": True}):
                key = m.get("name", "")
                val = m.get("content", "")
                if key and val and not key.startswith("og:") and not key.startswith("twitter:"):
                    meta[key] = val[:500]

            # ── Build Content Object ────────────────────────
            content = AIContent(
                url=url,
                title=title,
                domain=domain,
                language=language,
                summary=summary,
                main_text=main_text,
                headings=headings,
                paragraphs=paragraphs,
                tables=tables,
                lists=lists,
                code_blocks=code_blocks,
                links=links[:50],
                images=images[:30],
                emails=emails,
                phones=phones,
                prices=prices,
                schema_org=schema_org,
                open_graph=open_graph,
                meta=meta,
                word_count=len(main_text.split()) if main_text else 0,
                extraction_method="http",
            )

            # Detect content type
            schema_types = []
            for s in schema_org:
                if isinstance(s, dict) and s.get("@type"):
                    schema_types.append(s["@type"])
            og_type = open_graph.get("type", "")

            dom_signals = {
                "schema_types": schema_types,
                "og_type": og_type,
                "has_article_tag": bool(soup.find("article")),
                "has_product_markup": bool(soup.find(attrs={"itemtype": re.compile(r"Product")})),
                "table_count": len(tables),
                "form_count": len(soup.find_all("form")),
                "code_block_count": len(code_blocks),
            }
            content.content_type, content.confidence = ContentTypeDetector.detect(url, dom_signals)

            return {"status": "success", "data": content.to_dict()}

        except Exception as exc:
            logger.error(f"HTML extraction failed: {exc}", exc_info=True)
            return {"status": "error", "error": str(exc)}

    def _generate_summary(self, paragraphs: List[str]) -> str:
        """
        Generate a 2-3 sentence extractive summary from paragraphs.
        No LLM needed — uses position-weighted sentence extraction.
        """
        if not paragraphs:
            return ""

        # Collect sentences from first few paragraphs
        sentences = []
        for p in paragraphs[:5]:
            for sent in re.split(r'(?<=[.!?])\s+', p):
                sent = sent.strip()
                if 20 < len(sent) < 300:
                    sentences.append(sent)

        if not sentences:
            # Fallback: truncate first paragraph
            return paragraphs[0][:300] + "..." if len(paragraphs[0]) > 300 else paragraphs[0]

        # Take first 2-3 sentences (position-weighted: first sentences are most important)
        summary_sentences = sentences[:3]
        return " ".join(summary_sentences)
