"""
Agent-OS Page-to-Markdown Converter
Production-grade HTML to Markdown conversion tuned for AI agent consumption.
Converts live page DOM via Playwright JS evaluation — no raw HTML parsing needed.
"""
import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("agent-os.markdown-converter")


class MarkdownConverter:
    """Convert live web pages to clean Markdown for AI agent consumption."""

    # JS that walks the DOM and converts to Markdown
    _CONVERSION_JS = r"""
    (function(options) {
        const opts = Object.assign({
            include_images: true,
            include_links: true,
            include_tables: true,
            strip_nav: true,
            strip_footer: true,
            strip_ads: true,
            max_depth: 6,
            code_blocks: true,
        }, options || {});

        // ── Helpers ──
        function isVisible(el) {
            if (!el) return false;
            if (el.nodeType === Node.TEXT_NODE) return true;
            if (el.nodeType !== Node.ELEMENT_NODE) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
            // Keep elements that are off-screen but exist (like sr-only)
            return true;
        }

        function isInline(el) {
            if (!el || el.nodeType !== Node.ELEMENT_NODE) return false;
            const tag = el.tagName.toLowerCase();
            return ['a', 'span', 'strong', 'b', 'em', 'i', 'code', 'mark', 'small',
                    'sub', 'sup', 'del', 'ins', 'abbr', 'time', 'cite', 'q'].includes(tag);
        }

        function isBlock(el) {
            if (!el || el.nodeType !== Node.ELEMENT_NODE) return false;
            const tag = el.tagName.toLowerCase();
            return ['p', 'div', 'section', 'article', 'header', 'footer', 'blockquote',
                    'pre', 'table', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'hr', 'figure', 'figcaption', 'details', 'main'].includes(tag);
        }

        function cleanText(text) {
            if (!text) return '';
            return text.replace(/\s+/g, ' ').trim();
        }

        function escapeMarkdown(text) {
            // Escape markdown special characters in text content
            return text.replace(/([*_`\[\]\\])/g, '\\$1');
        }

        // ── Node conversion ──
        function convertNode(node, depth, listDepth) {
            if (!node) return '';
            depth = depth || 0;
            listDepth = listDepth || 0;

            if (node.nodeType === Node.TEXT_NODE) {
                return cleanText(node.textContent);
            }

            if (node.nodeType !== Node.ELEMENT_NODE) return '';

            const tag = node.tagName.toLowerCase();

            // Skip these tags entirely
            const skipTags = ['script', 'style', 'noscript', 'svg', 'math',
                              'link', 'meta', 'head', 'title'];
            if (skipTags.includes(tag)) return '';

            // Skip ad containers
            if (opts.strip_ads) {
                const classList = (node.className || '').toString().toLowerCase();
                if (/\b(ad|ads|advertisement|sponsored|banner-ad|ad-slot|ad-container)\b/.test(classList)) return '';
                if (node.id && /ad[s]?[-_]/.test(node.id.toLowerCase())) return '';
            }

            // Skip nav/footer if configured
            if (opts.strip_nav && (tag === 'nav' || node.getAttribute('role') === 'navigation')) return '';
            if (opts.strip_footer && (tag === 'footer' || node.getAttribute('role') === 'contentinfo')) return '';
            if (opts.strip_nav && node.getAttribute('role') === 'banner') return '';

            // Skip sidebar
            const cls = (node.className || '').toString().toLowerCase();
            if (/\b(sidebar|side-bar|widget-area)\b/.test(cls)) return '';

            // Skip hidden elements
            if (!isVisible(node)) return '';

            // ── Block elements ──
            // Headings
            if (/^h[1-6]$/.test(tag)) {
                const level = parseInt(tag[1]);
                if (level > opts.max_depth) return '';
                const inner = convertChildren(node, depth + 1, listDepth);
                if (!inner.trim()) return '';
                return '\n\n' + '#'.repeat(level) + ' ' + inner.trim() + '\n\n';
            }

            // Paragraphs
            if (tag === 'p') {
                const inner = convertChildren(node, depth + 1, listDepth);
                if (!inner.trim()) return '';
                return '\n\n' + inner.trim() + '\n\n';
            }

            // Line break
            if (tag === 'br') return '  \n';

            // Horizontal rule
            if (tag === 'hr') return '\n\n---\n\n';

            // Blockquote
            if (tag === 'blockquote') {
                const inner = convertChildren(node, depth + 1, listDepth).trim();
                if (!inner) return '';
                const lines = inner.split('\n');
                return '\n\n' + lines.map(l => '> ' + l).join('\n') + '\n\n';
            }

            // Pre / Code blocks
            if (tag === 'pre' && opts.code_blocks) {
                const codeEl = node.querySelector('code');
                const lang = codeEl && codeEl.className
                    ? (codeEl.className.match(/language-(\w+)/) || [])[1] || ''
                    : '';
                const code = (codeEl || node).textContent;
                return '\n\n```' + lang + '\n' + code + '\n```\n\n';
            }

            if (tag === 'code' && node.parentElement && node.parentElement.tagName.toLowerCase() !== 'pre') {
                const inner = node.textContent;
                if (!inner.trim()) return '';
                // Check if it contains backticks
                if (inner.includes('`')) {
                    return '`` ' + inner + ' ``';
                }
                return '`' + inner + '`';
            }

            // Table
            if (tag === 'table' && opts.include_tables) {
                return convertTable(node);
            }

            // Lists
            if (tag === 'ul' || tag === 'ol') {
                return convertList(node, tag, depth, listDepth);
            }

            // List item (handled by convertList, but fallback)
            if (tag === 'li') {
                const inner = convertChildren(node, depth + 1, listDepth);
                return inner.trim() ? '- ' + inner.trim() + '\n' : '';
            }

            // Figure / Figcaption
            if (tag === 'figure') {
                const img = node.querySelector('img');
                const caption = node.querySelector('figcaption');
                let result = '';
                if (img && opts.include_images) {
                    result += convertImg(img);
                }
                if (caption) {
                    result += '\n*' + cleanText(caption.textContent) + '*\n';
                }
                return result;
            }
            if (tag === 'figcaption') return '';

            // Details / Summary
            if (tag === 'details') {
                const summary = node.querySelector('summary');
                const summaryText = summary ? cleanText(summary.textContent) : 'Details';
                const inner = convertChildren(node, depth + 1, listDepth);
                return '\n\n**' + summaryText + '**\n' + inner + '\n\n';
            }
            if (tag === 'summary') return '';

            // ── Inline elements ──
            // Bold
            if (tag === 'strong' || tag === 'b') {
                const inner = convertChildren(node, depth + 1, listDepth);
                if (!inner.trim()) return '';
                return '**' + inner.trim() + '**';
            }

            // Italic
            if (tag === 'em' || tag === 'i') {
                const inner = convertChildren(node, depth + 1, listDepth);
                if (!inner.trim()) return '';
                return '*' + inner.trim() + '*';
            }

            // Strikethrough
            if (tag === 'del' || tag === 's') {
                const inner = convertChildren(node, depth + 1, listDepth);
                if (!inner.trim()) return '';
                return '~~' + inner.trim() + '~~';
            }

            // Image
            if (tag === 'img' && opts.include_images) {
                return convertImg(node);
            }
            if (tag === 'img') return '';

            // Link
            if (tag === 'a' && opts.include_links) {
                const href = node.getAttribute('href') || '';
                const inner = convertChildren(node, depth + 1, listDepth).trim();
                if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
                    return inner;
                }
                if (!inner) return '';
                return '[' + inner + '](' + href + ')';
            }
            if (tag === 'a') {
                return convertChildren(node, depth + 1, listDepth);
            }

            // Inline code (already handled above)

            // Skip div/section/span wrappers, just process children
            if (['div', 'section', 'article', 'span', 'main', 'header',
                 'aside', 'label', 'fieldset', 'legend', 'address',
                 'time', 'mark', 'small', 'abbr', 'cite', 'dfn', 'kbd', 'samp', 'var',
                 'bdi', 'bdo', 'ruby', 'rt', 'rp'].includes(tag)) {
                return convertChildren(node, depth + 1, listDepth);
            }

            // Input/button elements — skip
            if (['input', 'button', 'select', 'textarea', 'form', 'option',
                 'optgroup', 'datalist', 'output', 'progress', 'meter'].includes(tag)) {
                return '';
            }

            // Iframe — skip unless youtube embed
            if (tag === 'iframe') {
                const src = node.getAttribute('src') || '';
                if (src.includes('youtube') || src.includes('vimeo') || src.includes('player')) {
                    return '\n\n[Embedded video: ' + src + ']\n\n';
                }
                return '';
            }

            // Audio/Video
            if (tag === 'video' || tag === 'audio') {
                const src = node.getAttribute('src') || '';
                const sourceEl = node.querySelector('source');
                const sourceSrc = sourceEl ? sourceEl.getAttribute('src') || '' : '';
                const mediaSrc = src || sourceSrc;
                if (mediaSrc) {
                    return '\n\n[' + tag + ': ' + mediaSrc + ']\n\n';
                }
                return '';
            }

            // Default: process children
            return convertChildren(node, depth + 1, listDepth);
        }

        function convertChildren(node, depth, listDepth) {
            let result = '';
            for (const child of node.childNodes) {
                result += convertNode(child, depth, listDepth);
            }
            return result;
        }

        function convertImg(img) {
            const src = img.getAttribute('src') || img.getAttribute('data-src') || '';
            const alt = img.getAttribute('alt') || '';
            if (!src) return '';
            // Resolve relative URLs
            let fullSrc = src;
            try { fullSrc = new URL(src, window.location.href).href; } catch(e) {}
            return '\n\n![' + alt + '](' + fullSrc + ')\n\n';
        }

        function convertTable(table) {
            const rows = [];
            table.querySelectorAll('tr').forEach(tr => {
                const cells = [];
                tr.querySelectorAll('th, td').forEach(cell => {
                    cells.push(cleanText(cell.textContent).replace(/\|/g, '\\|'));
                });
                if (cells.length > 0) rows.push(cells);
            });

            if (rows.length === 0) return '';

            let md = '\n\n';

            // Header row
            const maxCols = Math.max(...rows.map(r => r.length));
            const header = rows[0];

            // Pad rows to maxCols
            while (header.length < maxCols) header.push('');
            md += '| ' + header.join(' | ') + ' |\n';

            // Separator
            md += '| ' + header.map(() => '---').join(' | ') + ' |\n';

            // Data rows
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                while (row.length < maxCols) row.push('');
                md += '| ' + row.join(' | ') + ' |\n';
            }

            md += '\n';
            return md;
        }

        function convertList(listEl, listTag, depth, listDepth) {
            if (listDepth > 5) return ''; // Prevent infinite nesting
            let result = '\n';
            const items = listEl.querySelectorAll(':scope > li');
            items.forEach((li, idx) => {
                const prefix = listTag === 'ol' ? (idx + 1) + '. ' : '- ';
                // Get text content excluding nested lists
                const clone = li.cloneNode(true);
                clone.querySelectorAll('ul, ol').forEach(sub => sub.remove());
                const directText = convertChildren(li, depth + 1, listDepth + 1).trim();
                if (directText) {
                    // Indent for nesting
                    const indent = '  '.repeat(listDepth);
                    result += indent + prefix + directText + '\n';
                }
                // Process nested lists
                li.querySelectorAll(':scope > ul, :scope > ol').forEach(subList => {
                    result += convertList(subList, subList.tagName.toLowerCase(), depth + 1, listDepth + 1);
                });
            });
            return result + '\n';
        }

        // ── Main conversion ──
        const body = document.body.cloneNode(true);

        // Remove elements we always skip
        body.querySelectorAll('script, style, noscript').forEach(el => el.remove());

        if (opts.strip_ads) {
            body.querySelectorAll('.ad, .ads, .advertisement, .ad-container, [class*="ad-slot"]').forEach(el => el.remove());
        }

        const markdown = convertNode(body, 0, 0);

        // Clean up
        let cleaned = markdown
            .replace(/\n{3,}/g, '\n\n')    // Collapse multiple blank lines
            .replace(/^\s+|\s+$/g, '')      // Trim
            .replace(/\n\n\n/g, '\n\n');    // Extra cleanup

        // Get metadata
        const title = document.title || '';
        const url = window.location.href;
        const wordCount = cleaned.split(/\s+/).filter(w => w.length > 0).length;

        return {
            markdown: cleaned,
            title: title,
            url: url,
            word_count: wordCount,
        };
    })
    """

    def __init__(self, browser: Any) -> None:
        """Initialize with an AgentBrowser instance."""
        self.browser = browser

    async def page_to_markdown(
        self,
        page_id: str = "main",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert the current page to clean Markdown.

        Args:
            page_id: Which browser tab to convert.
            options: Conversion options dict:
                include_images: Include images as ![alt](url). Default True.
                include_links: Include links as [text](url). Default True.
                include_tables: Convert tables to markdown tables. Default True.
                strip_nav: Remove navigation elements. Default True.
                strip_footer: Remove footer elements. Default True.
                strip_ads: Remove ad containers. Default True.
                max_depth: Max heading depth (1-6). Default 6.
                code_blocks: Preserve code blocks. Default True.

        Returns:
            Dict with status, markdown string, title, url, word_count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {
                "status": "error",
                "error": f"Page not found: {page_id}",
                "markdown": "",
                "title": "",
                "url": "",
                "word_count": 0,
            }

        # Build options with defaults
        opts = {
            "include_images": True,
            "include_links": True,
            "include_tables": True,
            "strip_nav": True,
            "strip_footer": True,
            "strip_ads": True,
            "max_depth": 6,
            "code_blocks": True,
        }
        if options:
            opts.update(options)

        # Clamp max_depth
        opts["max_depth"] = max(1, min(6, opts.get("max_depth", 6)))

        try:
            logger.info(f"page_to_markdown: converting page '{page_id}' with options {opts}")

            # The JS function is an IIFE that takes options and returns the result directly
            js_code = f"""
            (() => {{
                const opts = {json.dumps(opts)};

                function isVisible(el) {{
                    if (!el) return false;
                    if (el.nodeType === Node.TEXT_NODE) return true;
                    if (el.nodeType !== Node.ELEMENT_NODE) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    return true;
                }}

                function cleanText(text) {{
                    if (!text) return '';
                    return text.replace(/\\s+/g, ' ').trim();
                }}

                function convertNode(node, depth, listDepth) {{
                    if (!node) return '';
                    depth = depth || 0;
                    listDepth = listDepth || 0;

                    if (node.nodeType === Node.TEXT_NODE) {{
                        return cleanText(node.textContent);
                    }}
                    if (node.nodeType !== Node.ELEMENT_NODE) return '';

                    const tag = node.tagName.toLowerCase();
                    const skipTags = ['script', 'style', 'noscript', 'svg', 'math', 'link', 'meta', 'head', 'title'];
                    if (skipTags.includes(tag)) return '';

                    if (opts.strip_ads) {{
                        const cl = (node.className || '').toString().toLowerCase();
                        if (/\\b(ad|ads|advertisement|sponsored|banner-ad|ad-slot|ad-container)\\b/.test(cl)) return '';
                        if (node.id && /ad[s]?[-_]/.test(node.id.toLowerCase())) return '';
                    }}
                    if (opts.strip_nav && (tag === 'nav' || node.getAttribute('role') === 'navigation')) return '';
                    if (opts.strip_footer && (tag === 'footer' || node.getAttribute('role') === 'contentinfo')) return '';
                    if (opts.strip_nav && node.getAttribute('role') === 'banner') return '';
                    const cls = (node.className || '').toString().toLowerCase();
                    if (/\\b(sidebar|side-bar|widget-area)\\b/.test(cls)) return '';
                    if (!isVisible(node)) return '';

                    if (/^h[1-6]$/.test(tag)) {{
                        const level = parseInt(tag[1]);
                        if (level > opts.max_depth) return '';
                        const inner = convertChildren(node, depth + 1, listDepth);
                        if (!inner.trim()) return '';
                        return '\\n\\n' + '#'.repeat(level) + ' ' + inner.trim() + '\\n\\n';
                    }}
                    if (tag === 'p') {{
                        const inner = convertChildren(node, depth + 1, listDepth);
                        if (!inner.trim()) return '';
                        return '\\n\\n' + inner.trim() + '\\n\\n';
                    }}
                    if (tag === 'br') return '  \\n';
                    if (tag === 'hr') return '\\n\\n---\\n\\n';
                    if (tag === 'blockquote') {{
                        const inner = convertChildren(node, depth + 1, listDepth).trim();
                        if (!inner) return '';
                        return '\\n\\n' + inner.split('\\n').map(l => '> ' + l).join('\\n') + '\\n\\n';
                    }}
                    if (tag === 'pre' && opts.code_blocks) {{
                        const codeEl = node.querySelector('code');
                        const lang = codeEl && codeEl.className ? (codeEl.className.match(/language-(\\w+)/) || [])[1] || '' : '';
                        const code = (codeEl || node).textContent;
                        return '\\n\\n```' + lang + '\\n' + code + '\\n```\\n\\n';
                    }}
                    if (tag === 'code' && node.parentElement && node.parentElement.tagName.toLowerCase() !== 'pre') {{
                        const inner = node.textContent;
                        if (!inner.trim()) return '';
                        return inner.includes('`') ? '`` ' + inner + ' ``' : '`' + inner + '`';
                    }}
                    if (tag === 'table' && opts.include_tables) {{
                        const rows = [];
                        node.querySelectorAll('tr').forEach(tr => {{
                            const cells = [];
                            tr.querySelectorAll('th, td').forEach(cell => {{
                                cells.push(cleanText(cell.textContent).replace(/\\|/g, '\\\\|'));
                            }});
                            if (cells.length > 0) rows.push(cells);
                        }});
                        if (rows.length === 0) return '';
                        let md = '\\n\\n';
                        const maxCols = Math.max(...rows.map(r => r.length));
                        const header = rows[0];
                        while (header.length < maxCols) header.push('');
                        md += '| ' + header.join(' | ') + ' |\\n';
                        md += '| ' + header.map(() => '---').join(' | ') + ' |\\n';
                        for (let i = 1; i < rows.length; i++) {{
                            const row = rows[i];
                            while (row.length < maxCols) row.push('');
                            md += '| ' + row.join(' | ') + ' |\\n';
                        }}
                        return md + '\\n';
                    }}
                    if (tag === 'ul' || tag === 'ol') {{
                        return convertList(node, tag, depth, listDepth);
                    }}
                    if (tag === 'figure') {{
                        const img = node.querySelector('img');
                        const caption = node.querySelector('figcaption');
                        let result = '';
                        if (img && opts.include_images) result += convertImg(img);
                        if (caption) result += '\\n*' + cleanText(caption.textContent) + '*\\n';
                        return result;
                    }}
                    if (tag === 'figcaption' || tag === 'summary') return '';
                    if (tag === 'details') {{
                        const summary = node.querySelector('summary');
                        const st = summary ? cleanText(summary.textContent) : 'Details';
                        return '\\n\\n**' + st + '**\\n' + convertChildren(node, depth + 1, listDepth) + '\\n\\n';
                    }}
                    if (tag === 'strong' || tag === 'b') {{
                        const inner = convertChildren(node, depth + 1, listDepth);
                        return inner.trim() ? '**' + inner.trim() + '**' : '';
                    }}
                    if (tag === 'em' || tag === 'i') {{
                        const inner = convertChildren(node, depth + 1, listDepth);
                        return inner.trim() ? '*' + inner.trim() + '*' : '';
                    }}
                    if (tag === 'del' || tag === 's') {{
                        const inner = convertChildren(node, depth + 1, listDepth);
                        return inner.trim() ? '~~' + inner.trim() + '~~' : '';
                    }}
                    if (tag === 'img' && opts.include_images) return convertImg(node);
                    if (tag === 'img') return '';
                    if (tag === 'a' && opts.include_links) {{
                        const href = node.getAttribute('href') || '';
                        const inner = convertChildren(node, depth + 1, listDepth).trim();
                        if (!href || href.startsWith('#') || href.startsWith('javascript:')) return inner;
                        return inner ? '[' + inner + '](' + href + ')' : '';
                    }}
                    if (tag === 'a') return convertChildren(node, depth + 1, listDepth);
                    if (['div', 'section', 'article', 'span', 'main', 'header', 'aside', 'label', 'fieldset', 'legend', 'address', 'time', 'mark', 'small', 'abbr', 'cite', 'dfn', 'kbd', 'samp', 'var', 'bdi', 'bdo', 'ruby', 'rt', 'rp', 'li'].includes(tag)) {{
                        return convertChildren(node, depth + 1, listDepth);
                    }}
                    if (['input', 'button', 'select', 'textarea', 'form', 'option', 'optgroup', 'datalist', 'output', 'progress', 'meter'].includes(tag)) return '';
                    if (tag === 'iframe') {{
                        const src = node.getAttribute('src') || '';
                        if (src.includes('youtube') || src.includes('vimeo') || src.includes('player'))
                            return '\\n\\n[Embedded video: ' + src + ']\\n\\n';
                        return '';
                    }}
                    if (tag === 'video' || tag === 'audio') {{
                        const src = node.getAttribute('src') || '';
                        const se = node.querySelector('source');
                        const ss = se ? se.getAttribute('src') || '' : '';
                        const ms = src || ss;
                        return ms ? '\\n\\n[' + tag + ': ' + ms + ']\\n\\n' : '';
                    }}
                    return convertChildren(node, depth + 1, listDepth);
                }}

                function convertChildren(node, depth, listDepth) {{
                    let r = '';
                    for (const child of node.childNodes) r += convertNode(child, depth, listDepth);
                    return r;
                }}

                function convertImg(img) {{
                    const src = img.getAttribute('src') || img.getAttribute('data-src') || '';
                    const alt = img.getAttribute('alt') || '';
                    if (!src) return '';
                    let fullSrc = src;
                    try {{ fullSrc = new URL(src, window.location.href).href; }} catch(e) {{}}
                    return '\\n\\n![' + alt + '](' + fullSrc + ')\\n\\n';
                }}

                function convertList(listEl, listTag, depth, listDepth) {{
                    if (listDepth > 5) return '';
                    let result = '\\n';
                    const items = listEl.querySelectorAll(':scope > li');
                    items.forEach((li, idx) => {{
                        const prefix = listTag === 'ol' ? (idx + 1) + '. ' : '- ';
                        const indent = '  '.repeat(listDepth);
                        const directText = convertChildren(li, depth + 1, listDepth + 1).trim();
                        if (directText) result += indent + prefix + directText + '\\n';
                        li.querySelectorAll(':scope > ul, :scope > ol').forEach(subList => {{
                            result += convertList(subList, subList.tagName.toLowerCase(), depth + 1, listDepth + 1);
                        }});
                    }});
                    return result + '\\n';
                }}

                // Main
                const body = document.body.cloneNode(true);
                body.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                if (opts.strip_ads) {{
                    body.querySelectorAll('.ad, .ads, .advertisement, .ad-container, [class*="ad-slot"]').forEach(el => el.remove());
                }}
                let markdown = convertNode(body, 0, 0);
                markdown = markdown.replace(/\\n{{3,}}/g, '\\n\\n').replace(/^\\s+|\\s+$/g, '');
                const wordCount = markdown.split(/\\s+/).filter(w => w.length > 0).length;
                return {{
                    markdown: markdown,
                    title: document.title || '',
                    url: window.location.href,
                    word_count: wordCount,
                }};
            }})()
            """

            result = await page.evaluate(js_code)

            logger.info(
                f"page_to_markdown: converted '{result.get('title', '')}' — "
                f"{result.get('word_count', 0)} words, "
                f"{len(result.get('markdown', ''))} chars"
            )

            return {
                "status": "success",
                "markdown": result.get("markdown", ""),
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "word_count": result.get("word_count", 0),
            }

        except Exception as e:
            logger.error(f"page_to_markdown error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "markdown": "",
                "title": "",
                "url": "",
                "word_count": 0,
            }
