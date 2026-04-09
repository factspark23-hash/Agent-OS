"""
Agent-OS Structured Data Extractor
Extracts tables, lists, articles, JSON-LD, metadata, and categorized links from web pages.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("agent-os.extractor")


class DataExtractor:
    """Extract structured data from web pages."""

    def __init__(self, browser: Any) -> None:
        """Initialize with an AgentBrowser instance."""
        self.browser = browser

    async def extract_tables(self, page_id: str = "main") -> Dict[str, Any]:
        """Find and parse ALL HTML tables on the page.

        For each table: headers (from th or first row), rows (list of dicts),
        caption, row_count, col_count. Handles colspan/rowspan gracefully.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status, tables list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "tables": [], "count": 0}

        try:
            tables = await page.evaluate("""() => {
                const results = [];

                document.querySelectorAll('table').forEach((table, idx) => {
                    // Get caption
                    const captionEl = table.querySelector('caption');
                    const caption = captionEl ? captionEl.textContent.trim() : null;

                    // Collect all rows
                    const trs = table.querySelectorAll('tr');
                    if (trs.length === 0) return;

                    // Check for thead/tbody structure
                    const thead = table.querySelector('thead');
                    let headers = [];
                    let dataStartRow = 0;

                    if (thead) {
                        const headerRow = thead.querySelector('tr');
                        if (headerRow) {
                            headerRow.querySelectorAll('th, td').forEach(cell => {
                                headers.push(cell.textContent.trim());
                            });
                            dataStartRow = -1; // signal to skip thead rows
                        }
                    } else {
                        // Check if first row has th elements
                        const firstRow = trs[0];
                        const thCells = firstRow.querySelectorAll('th');
                        if (thCells.length > 0) {
                            thCells.forEach(th => {
                                headers.push(th.textContent.trim());
                            });
                            dataStartRow = 1;
                        }
                    }

                    // Parse data rows
                    const rows = [];
                    for (let i = 0; i < trs.length; i++) {
                        // Skip header rows
                        if (dataStartRow === -1 && trs[i].closest('thead')) continue;
                        if (dataStartRow > 0 && i < dataStartRow) continue;

                        const cells = [];
                        trs[i].querySelectorAll('td, th').forEach(cell => {
                            const colspan = parseInt(cell.getAttribute('colspan') || '1');
                            const text = cell.textContent.trim();
                            // Handle colspan by repeating the value
                            for (let c = 0; c < colspan; c++) {
                                cells.push(text);
                            }
                        });

                        if (cells.length > 0) {
                            if (headers.length > 0 && cells.length === headers.length) {
                                // Build dict from headers
                                const row = {};
                                headers.forEach((h, j) => {
                                    row[h || `col_${j}`] = cells[j] || '';
                                });
                                rows.push(row);
                            } else {
                                rows.push(cells);
                            }
                        }
                    }

                    if (rows.length > 0) {
                        results.push({
                            index: idx,
                            id: table.id || null,
                            caption: caption,
                            headers: headers,
                            rows: rows,
                            row_count: rows.length,
                            col_count: headers.length || (Array.isArray(rows[0]) ? rows[0].length : Object.keys(rows[0]).length),
                        });
                    }
                });

                return results;
            }""")

            logger.info(f"extract_tables: {len(tables)} tables found")
            return {"status": "success", "tables": tables, "count": len(tables)}

        except Exception as e:
            logger.error(f"extract_tables error: {e}")
            return {"status": "error", "error": str(e), "tables": [], "count": 0}

    async def extract_lists(self, page_id: str = "main") -> Dict[str, Any]:
        """Parse ALL UL/OL lists into structured data.

        For each: type (ordered/unordered), items (list of strings),
        nested lists preserved as sub-lists.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status, lists list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "lists": [], "count": 0}

        try:
            lists_data = await page.evaluate("""() => {
                const results = [];

                function parseList(listEl, depth) {
                    const items = [];
                    const children = listEl.querySelectorAll(':scope > li');

                    children.forEach((li, idx) => {
                        const item = {
                            index: idx,
                            text: '',
                            sub_lists: [],
                        };

                        // Get direct text (not from nested lists)
                        const clone = li.cloneNode(true);
                        clone.querySelectorAll('ul, ol').forEach(sub => sub.remove());
                        item.text = clone.textContent.trim().replace(/\\s+/g, ' ');

                        // Check for nested lists
                        li.querySelectorAll(':scope > ul, :scope > ol').forEach(subList => {
                            const parsed = parseList(subList, depth + 1);
                            if (parsed.items.length > 0) {
                                item.sub_lists.push({
                                    type: subList.tagName.toLowerCase() === 'ol' ? 'ordered' : 'unordered',
                                    items: parsed.items,
                                });
                            }
                        });

                        // Extract any links
                        const links = [];
                        li.querySelectorAll('a[href]').forEach(a => {
                            links.push({ text: a.textContent.trim(), href: a.href });
                        });
                        if (links.length > 0) {
                            item.links = links;
                        }

                        if (item.text || item.sub_lists.length > 0) {
                            items.push(item);
                        }
                    });

                    return { items };
                }

                // Only top-level lists (not nested inside another list)
                document.querySelectorAll(':root > ul, :root > ol, body > ul, body > ol, main > ul, main > ol, article > ul, article > ol, section > ul, section > ol, div > ul, div > ol').forEach((list, idx) => {
                    // Skip small lists that are likely navigation
                    const liCount = list.querySelectorAll(':scope > li').length;
                    const isNav = list.closest('nav') !== null;
                    const isFooter = list.closest('footer') !== null;
                    if (isNav || isFooter) return;

                    const parsed = parseList(list, 0);
                    if (parsed.items.length > 0) {
                        results.push({
                            index: idx,
                            type: list.tagName.toLowerCase() === 'ol' ? 'ordered' : 'unordered',
                            items: parsed.items,
                            item_count: parsed.items.length,
                            is_navigation: isNav,
                        });
                    }
                });

                return results;
            }""")

            logger.info(f"extract_lists: {len(lists_data)} lists found")
            return {"status": "success", "lists": lists_data, "count": len(lists_data)}

        except Exception as e:
            logger.error(f"extract_lists error: {e}")
            return {"status": "error", "error": str(e), "lists": [], "count": 0}

    async def extract_articles(self, page_id: str = "main") -> Dict[str, Any]:
        """Extract main article content using multiple heuristics.

        Heuristics (in order):
        1. Look for <article> tag
        2. Look for schema.org Article markup
        3. Look for common content containers (.post, .article, #content, main, .entry-content)
        4. Largest text block heuristic

        Extracts: title, body_text, author, publish_date, description, images.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status and article data.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}"}

        try:
            article = await page.evaluate("""() => {
                const result = {
                    title: document.title || null,
                    body_text: null,
                    author: null,
                    publish_date: null,
                    description: null,
                    images: [],
                    source: null,
                };

                // Helper: clean text from a container
                function extractCleanText(container) {
                    if (!container) return null;
                    const clone = container.cloneNode(true);
                    // Remove non-content elements
                    const removeSelectors = [
                        'script', 'style', 'noscript', 'nav', 'footer', 'aside',
                        '.ad', '.ads', '.advertisement', '.sidebar', '.comments',
                        '.comment', '.related', '.recommended', '.share', '.social',
                        '[role=banner]', '[role=contentinfo]', '[role=navigation]',
                        'iframe', 'embed', 'object',
                    ];
                    clone.querySelectorAll(removeSelectors.join(', ')).forEach(el => el.remove());
                    const text = clone.textContent.trim().replace(/\\s+/g, ' ');
                    return text.length > 50 ? text : null;
                }

                // Helper: extract images from container
                function extractImages(container) {
                    const images = [];
                    if (!container) return images;
                    container.querySelectorAll('img').forEach(img => {
                        if (img.src && img.src.startsWith('http')) {
                            images.push({
                                src: img.src,
                                alt: img.alt || '',
                                width: img.naturalWidth || img.width || 0,
                                height: img.naturalHeight || img.height || 0,
                            });
                        }
                    });
                    return images.slice(0, 20);
                }

                // Helper: find author
                function findAuthor(root) {
                    const selectors = [
                        '[rel="author"]', '.author', '.byline', '[class*="author"]',
                        '[itemprop="author"]', 'meta[name="author"]',
                        '.post-author', '.article-author', '[data-author]',
                    ];
                    for (const sel of selectors) {
                        const el = root.querySelector(sel) || document.querySelector(sel);
                        if (el) {
                            return el.getAttribute('content') ||
                                el.getAttribute('data-author') ||
                                el.textContent.trim().substring(0, 100);
                        }
                    }
                    return null;
                }

                // Helper: find publish date
                function findDate(root) {
                    const selectors = [
                        'time[datetime]', '[itemprop="datePublished"]', '.date', '.published',
                        'meta[property="article:published_time"]',
                        'meta[name="date"]', '.post-date', '.article-date',
                        '[data-date]', '[data-time]',
                    ];
                    for (const sel of selectors) {
                        const el = root.querySelector(sel) || document.querySelector(sel);
                        if (el) {
                            return el.getAttribute('datetime') ||
                                el.getAttribute('content') ||
                                el.getAttribute('data-date') ||
                                el.textContent.trim().substring(0, 50);
                        }
                    }
                    return null;
                }

                // Strategy 1: <article> tag
                const articleEl = document.querySelector('article');
                if (articleEl) {
                    result.source = 'article_tag';
                    const h1 = articleEl.querySelector('h1') || articleEl.querySelector('h2');
                    result.title = h1 ? h1.textContent.trim() : document.title;
                    result.body_text = extractCleanText(articleEl);
                    result.author = findAuthor(articleEl);
                    result.publish_date = findDate(articleEl);
                    result.images = extractImages(articleEl);

                    const desc = document.querySelector('meta[name="description"]') ||
                                document.querySelector('meta[property="og:description"]');
                    result.description = desc ? desc.getAttribute('content') : null;

                    return result;
                }

                // Strategy 2: Schema.org Article
                const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const script of jsonLdScripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        const items = Array.isArray(data) ? data : [data];
                        for (const item of items) {
                            const type = item['@type'] || '';
                            if (type.includes('Article') || type.includes('BlogPosting') || type.includes('NewsArticle')) {
                                result.source = 'schema_org';
                                result.title = item.headline || result.title;
                                result.body_text = item.articleBody || null;
                                result.author = item.author ? (item.author.name || JSON.stringify(item.author)) : null;
                                result.publish_date = item.datePublished || null;
                                result.description = item.description || null;
                                if (item.image) {
                                    const img = Array.isArray(item.image) ? item.image[0] : item.image;
                                    result.images.push({
                                        src: typeof img === 'string' ? img : img.url || '',
                                        alt: '',
                                        width: 0,
                                        height: 0,
                                    });
                                }
                                // Also get body text from page if schema didn't provide
                                if (!result.body_text) {
                                    const mainEl = document.querySelector('main') || document.querySelector('[role="main"]');
                                    result.body_text = extractCleanText(mainEl);
                                }
                                return result;
                            }
                        }
                    } catch(e) { /* skip invalid JSON-LD */ }
                }

                // Strategy 3: Common content containers
                const contentSelectors = [
                    '.post-content', '.article-content', '.entry-content',
                    '.post-body', '.article-body', '#content', '.content',
                    'main', '[role="main"]', '.post', '.article',
                ];
                for (const sel of contentSelectors) {
                    const container = document.querySelector(sel);
                    if (container) {
                        const text = extractCleanText(container);
                        if (text && text.length > 200) {
                            result.source = 'content_container';
                            result.body_text = text;
                            result.author = findAuthor(container);
                            result.publish_date = findDate(container);
                            result.images = extractImages(container);
                            const desc = document.querySelector('meta[name="description"]');
                            result.description = desc ? desc.getAttribute('content') : null;
                            return result;
                        }
                    }
                }

                // Strategy 4: Largest text block
                let bestBlock = null;
                let bestLen = 0;
                document.querySelectorAll('div, section').forEach(el => {
                    const text = extractCleanText(el);
                    if (text && text.length > bestLen && text.length < 100000) {
                        bestLen = text.length;
                        bestBlock = el;
                    }
                });
                if (bestBlock) {
                    result.source = 'largest_block';
                    result.body_text = extractCleanText(bestBlock);
                    result.author = findAuthor(bestBlock);
                    result.publish_date = findDate(bestBlock);
                    result.images = extractImages(bestBlock);
                }

                const desc = document.querySelector('meta[name="description"]') ||
                            document.querySelector('meta[property="og:description"]');
                result.description = desc ? desc.getAttribute('content') : null;

                return result;
            }""")

            logger.info(f"extract_articles: source={article.get('source')}, body_len={len(article.get('body_text') or '')}")
            return {"status": "success", "article": article}

        except Exception as e:
            logger.error(f"extract_articles error: {e}")
            return {"status": "error", "error": str(e)}

    async def extract_jsonld(self, page_id: str = "main") -> Dict[str, Any]:
        """Parse ALL JSON-LD structured data from <script type='application/ld+json'> tags.

        Returns parsed objects with @type identification.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status, jsonld list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "jsonld": [], "count": 0}

        try:
            jsonld_data = await page.evaluate("""() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                const data = [];
                scripts.forEach((script, idx) => {
                    try {
                        const parsed = JSON.parse(script.textContent);
                        const items = Array.isArray(parsed) ? parsed : [parsed];
                        items.forEach(item => {
                            data.push({
                                index: idx,
                                type: item['@type'] || 'Unknown',
                                context: item['@context'] || null,
                                data: item,
                            });
                        });
                    } catch (e) {
                        data.push({
                            index: idx,
                            type: 'PARSE_ERROR',
                            error: e.message,
                            raw: script.textContent.substring(0, 500),
                        });
                    }
                });
                return data;
            }""")

            logger.info(f"extract_jsonld: {len(jsonld_data)} objects found")
            return {"status": "success", "jsonld": jsonld_data, "count": len(jsonld_data)}

        except Exception as e:
            logger.error(f"extract_jsonld error: {e}")
            return {"status": "error", "error": str(e), "jsonld": [], "count": 0}

    async def extract_metadata(self, page_id: str = "main") -> Dict[str, Any]:
        """Extract ALL metadata from the page.

        Includes: OpenGraph, Twitter Cards, standard meta tags, title, canonical.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status and metadata.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}"}

        try:
            metadata = await page.evaluate("""() => {
                const result = {
                    title: document.title || null,
                    standard: {},
                    open_graph: {},
                    twitter: {},
                    links: {},
                };

                // Standard meta tags (name-based)
                document.querySelectorAll('meta[name]').forEach(meta => {
                    const name = meta.getAttribute('name').toLowerCase();
                    const content = meta.getAttribute('content');
                    if (content) {
                        result.standard[name] = content;
                    }
                });

                // OpenGraph tags (property-based)
                document.querySelectorAll('meta[property^="og:"]').forEach(meta => {
                    const prop = meta.getAttribute('property').replace('og:', '').toLowerCase();
                    const content = meta.getAttribute('content');
                    if (content) {
                        result.open_graph[prop] = content;
                    }
                });

                // Twitter Card tags
                document.querySelectorAll('meta[name^="twitter:"]').forEach(meta => {
                    const name = meta.getAttribute('name').replace('twitter:', '').toLowerCase();
                    const content = meta.getAttribute('content');
                    if (content) {
                        result.twitter[name] = content;
                    }
                });

                // Link tags
                document.querySelectorAll('link[rel][href]').forEach(link => {
                    const rel = link.getAttribute('rel');
                    const href = link.getAttribute('href');
                    const hreflang = link.getAttribute('hreflang');
                    const media = link.getAttribute('media');
                    if (rel && href) {
                        const key = hreflang ? `${rel} (${hreflang})` : rel;
                        result.links[key] = href;
                    }
                });

                return result;
            }""")

            logger.info(f"extract_metadata: og={len(metadata.get('open_graph', {}))}, twitter={len(metadata.get('twitter', {}))}")
            return {"status": "success", "metadata": metadata}

        except Exception as e:
            logger.error(f"extract_metadata error: {e}")
            return {"status": "error", "error": str(e)}

    async def extract_links_structured(self, page_id: str = "main") -> Dict[str, Any]:
        """Extract links categorized: navigation, footer, content, external, internal, social, download.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with status, categorized links, and counts.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}"}

        try:
            categorized = await page.evaluate("""() => {
                const origin = window.location.origin;
                const results = {
                    navigation: [],
                    footer: [],
                    content: [],
                    external: [],
                    internal: [],
                    social: [],
                    download: [],
                };

                const socialDomains = [
                    'twitter.com', 'x.com', 'facebook.com', 'linkedin.com',
                    'instagram.com', 'youtube.com', 'github.com', 'tiktok.com',
                    'reddit.com', 'pinterest.com', 'medium.com', 'discord.gg',
                    't.me', 'wa.me',
                ];

                const downloadExtensions = [
                    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
                    '.zip', '.rar', '.tar', '.gz', '.7z',
                    '.mp3', '.mp4', '.avi', '.mov',
                    '.exe', '.dmg', '.apk',
                ];

                const seen = new Set();

                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    if (!href || !href.startsWith('http') || seen.has(href)) return;
                    seen.add(href);

                    const text = (a.innerText || a.textContent || '').trim().substring(0, 100);
                    const isExternal = !href.startsWith(origin);
                    const isSocial = socialDomains.some(d => href.includes(d));
                    const isDownload = downloadExtensions.some(ext => href.toLowerCase().includes(ext));

                    const link = {
                        text: text,
                        href: href,
                        title: a.title || '',
                        target: a.target || '',
                        rel: a.rel || '',
                    };

                    // Categorize
                    if (isSocial) {
                        results.social.push(link);
                    } else if (isDownload) {
                        results.download.push(link);
                    } else if (a.closest('nav') || a.closest('[role="navigation"]')) {
                        results.navigation.push(link);
                    } else if (a.closest('footer') || a.closest('[role="contentinfo"]')) {
                        results.footer.push(link);
                    } else {
                        results.content.push(link);
                    }

                    if (isExternal) {
                        results.external.push(link);
                    } else {
                        results.internal.push(link);
                    }
                });

                return results;
            }""")

            counts = {k: len(v) for k, v in categorized.items()}
            total = sum(counts.values())
            logger.info(f"extract_links_structured: {total} links in {len(categorized)} categories")

            return {
                "status": "success",
                "links": categorized,
                "counts": counts,
                "total": total,
            }

        except Exception as e:
            logger.error(f"extract_links_structured error: {e}")
            return {"status": "error", "error": str(e)}

    async def extract_all(self, page_id: str = "main") -> Dict[str, Any]:
        """Run ALL extractors and combine results.

        Args:
            page_id: Which browser tab to extract from.

        Returns:
            Dict with all extracted data combined.
        """
        try:
            tables = await self.extract_tables(page_id)
            lists = await self.extract_lists(page_id)
            articles = await self.extract_articles(page_id)
            jsonld = await self.extract_jsonld(page_id)
            metadata = await self.extract_metadata(page_id)
            links = await self.extract_links_structured(page_id)

            return {
                "status": "success",
                "tables": tables.get("tables", []),
                "table_count": tables.get("count", 0),
                "lists": lists.get("lists", []),
                "list_count": lists.get("count", 0),
                "article": articles.get("article", {}),
                "jsonld": jsonld.get("jsonld", []),
                "jsonld_count": jsonld.get("count", 0),
                "metadata": metadata.get("metadata", {}),
                "links": links.get("links", {}),
                "link_counts": links.get("counts", {}),
                "total_links": links.get("total", 0),
            }

        except Exception as e:
            logger.error(f"extract_all error: {e}")
            return {"status": "error", "error": str(e)}
