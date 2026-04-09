"""
Agent-OS Smart Element Finder
Find elements by text, ARIA role, aria-label, placeholder, or natural language description.
Returns structured results with selectors, confidence scores, and metadata.
"""
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("agent-os.element-finder")


class ElementFinder:
    """Find elements on a page using various strategies beyond CSS selectors."""

    # Map ARIA roles to native HTML element selectors
    ROLE_TO_NATIVE: Dict[str, str] = {
        "button": "button, input[type=button], input[type=submit], input[type=reset]",
        "link": "a[href]",
        "textbox": "input[type=text], input:not([type]), textarea, input[type=email], input[type=password], input[type=search], input[type=url], input[type=tel], input[type=number]",
        "checkbox": "input[type=checkbox]",
        "radio": "input[type=radio]",
        "combobox": "select, input[list]",
        "tab": "[role=tab], [data-tab]",
        "menuitem": "[role=menuitem], li[role=menuitem]",
        "dialog": "dialog, [role=dialog], [aria-modal=true]",
        "alert": "[role=alert], .alert",
        "navigation": "nav, [role=navigation]",
        "search": "[role=search], form[action*=search], input[type=search]",
        "main": "main, [role=main]",
        "banner": "header, [role=banner]",
        "contentinfo": "footer, [role=contentinfo]",
        "form": "form, [role=form]",
        "heading": "h1, h2, h3, h4, h5, h6, [role=heading]",
        "list": "ul, ol, [role=list]",
        "listitem": "li, [role=listitem]",
        "table": "table, [role=table]",
        "row": "tr, [role=row]",
        "cell": "td, th, [role=cell], [role=gridcell]",
        "img": "img, [role=img]",
    }

    def __init__(self, browser: Any) -> None:
        """Initialize with an AgentBrowser instance."""
        self.browser = browser

    async def find_by_text(
        self,
        text: str,
        exact: bool = False,
        tag: Optional[str] = None,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Find elements by visible text content.

        Args:
            text: Text to search for.
            exact: If True, match exact text only; otherwise substring match (case-insensitive).
            tag: Optional HTML tag filter (e.g. 'button', 'a', 'span').
            page_id: Which browser tab to search.

        Returns:
            Dict with status, matches list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "matches": [], "count": 0}

        try:
            matches = await page.evaluate(
                """([text, exact, tagFilter]) => {
                    const results = [];
                    const allElements = document.querySelectorAll(tagFilter || '*');
                    const lowerText = text.toLowerCase();

                    for (const el of allElements) {
                        // Skip invisible elements and script/style
                        if (el.offsetParent === null && el.tagName !== 'BODY') continue;
                        if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'META', 'LINK'].includes(el.tagName)) continue;

                        const elText = (el.innerText || el.textContent || '').trim();
                        if (!elText) continue;

                        let matched = false;
                        if (exact) {
                            matched = elText === text;
                        } else {
                            matched = elText.toLowerCase().includes(lowerText);
                        }

                        if (matched) {
                            // Build a unique CSS selector
                            let selector = el.tagName.toLowerCase();
                            if (el.id) {
                                selector = '#' + CSS.escape(el.id);
                            } else if (el.name) {
                                selector += '[name="' + el.name + '"]';
                            } else if (el.className && typeof el.className === 'string') {
                                const firstClass = el.className.trim().split(/\\s+/)[0];
                                if (firstClass) selector += '.' + CSS.escape(firstClass);
                            }

                            const role = el.getAttribute('role') ||
                                (el.tagName === 'BUTTON' ? 'button' :
                                 el.tagName === 'A' ? 'link' :
                                 el.tagName === 'INPUT' ? 'textbox' : '');

                            results.push({
                                selector: selector,
                                text: elText.substring(0, 200),
                                tag: el.tagName.toLowerCase(),
                                role: role,
                                id: el.id || null,
                                name: el.name || null,
                                href: el.href || null,
                                visible: true,
                            });

                            // Limit results
                            if (results.length >= 20) break;
                        }
                    }
                    return results;
                }""",
                [text, exact, tag],
            )

            # Add confidence scores
            for m in matches:
                if exact and m["text"] == text:
                    m["confidence"] = 1.0
                elif exact:
                    m["confidence"] = 0.9
                elif m["text"].lower() == text.lower():
                    m["confidence"] = 0.95
                else:
                    m["confidence"] = 0.7

            logger.info(f"find_by_text('{text}', exact={exact}): {len(matches)} matches")
            return {"status": "success", "matches": matches, "count": len(matches)}

        except Exception as e:
            logger.error(f"find_by_text error: {e}")
            return {"status": "error", "error": str(e), "matches": [], "count": 0}

    async def find_by_role(
        self,
        role: str,
        name: Optional[str] = None,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Find elements by ARIA role.

        Args:
            role: ARIA role (button, link, textbox, checkbox, radio, combobox, tab,
                  menuitem, dialog, alert, navigation, search, main, banner,
                  contentinfo, form, heading, list, listitem, table, row, cell, img, etc.).
            name: Optional accessible name to filter by.
            page_id: Which browser tab to search.

        Returns:
            Dict with status, matches list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "matches": [], "count": 0}

        try:
            native_selector = self.ROLE_TO_NATIVE.get(role, "")
            matches = await page.evaluate(
                """([role, nameFilter, nativeSelector]) => {
                    const results = [];
                    // Try ARIA role attribute first
                    const selectors = ['[role="' + role + '"]'];
                    if (nativeSelector) selectors.push(nativeSelector);

                    const seen = new Set();
                    for (const sel of selectors) {
                        let elements;
                        try { elements = document.querySelectorAll(sel); } catch(e) { continue; }
                        for (const el of elements) {
                            if (seen.has(el)) continue;
                            seen.add(el);

                            if (el.offsetParent === null && el.tagName !== 'BODY') continue;

                            const elText = (el.innerText || el.textContent || '').trim().substring(0, 200);
                            const ariaLabel = el.getAttribute('aria-label') || '';
                            const accessibleName = ariaLabel || elText;

                            // Filter by name if provided
                            if (nameFilter) {
                                const lowerName = nameFilter.toLowerCase();
                                if (!accessibleName.toLowerCase().includes(lowerName) &&
                                    !elText.toLowerCase().includes(lowerName)) continue;
                            }

                            let selector = el.tagName.toLowerCase();
                            if (el.id) {
                                selector = '#' + CSS.escape(el.id);
                            } else if (el.name) {
                                selector += '[name="' + el.name + '"]';
                            }

                            results.push({
                                selector: selector,
                                text: elText,
                                tag: el.tagName.toLowerCase(),
                                role: el.getAttribute('role') || role,
                                aria_label: ariaLabel,
                                name: el.name || null,
                                id: el.id || null,
                                href: el.href || null,
                                visible: true,
                            });

                            if (results.length >= 20) break;
                        }
                        if (results.length >= 20) break;
                    }
                    return results;
                }""",
                [role, name, native_selector],
            )

            for m in matches:
                m["confidence"] = 0.95 if name else 0.9

            logger.info(f"find_by_role('{role}', name={name}): {len(matches)} matches")
            return {"status": "success", "matches": matches, "count": len(matches)}

        except Exception as e:
            logger.error(f"find_by_role error: {e}")
            return {"status": "error", "error": str(e), "matches": [], "count": 0}

    async def find_by_aria_label(
        self,
        label: str,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Find elements by aria-label or aria-labelledby text.

        Args:
            label: Label text to search for (case-insensitive substring match).
            page_id: Which browser tab to search.

        Returns:
            Dict with status, matches list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "matches": [], "count": 0}

        try:
            matches = await page.evaluate(
                """([label]) => {
                    const results = [];
                    const lowerLabel = label.toLowerCase();

                    // Check aria-label
                    document.querySelectorAll('[aria-label]').forEach(el => {
                        const elLabel = el.getAttribute('aria-label');
                        if (elLabel.toLowerCase().includes(lowerLabel)) {
                            let selector = el.tagName.toLowerCase();
                            if (el.id) selector = '#' + CSS.escape(el.id);
                            else if (el.name) selector += '[name="' + el.name + '"]';

                            results.push({
                                selector: selector,
                                text: (el.innerText || '').trim().substring(0, 200),
                                tag: el.tagName.toLowerCase(),
                                role: el.getAttribute('role') || '',
                                aria_label: elLabel,
                                match_type: 'aria-label',
                                visible: el.offsetParent !== null || el.tagName === 'BODY',
                            });
                        }
                    });

                    // Check aria-labelledby
                    document.querySelectorAll('[aria-labelledby]').forEach(el => {
                        const ids = el.getAttribute('aria-labelledby').split(/\\s+/);
                        for (const id of ids) {
                            const refEl = document.getElementById(id);
                            if (refEl && refEl.textContent.trim().toLowerCase().includes(lowerLabel)) {
                                let selector = el.tagName.toLowerCase();
                                if (el.id) selector = '#' + CSS.escape(el.id);
                                else if (el.name) selector += '[name="' + el.name + '"]';

                                results.push({
                                    selector: selector,
                                    text: (el.innerText || '').trim().substring(0, 200),
                                    tag: el.tagName.toLowerCase(),
                                    role: el.getAttribute('role') || '',
                                    aria_label: refEl.textContent.trim(),
                                    match_type: 'aria-labelledby',
                                    visible: el.offsetParent !== null || el.tagName === 'BODY',
                                });
                                break;
                            }
                        }
                    });

                    return results.slice(0, 20);
                }""",
                [label],
            )

            for m in matches:
                m["confidence"] = 0.95 if m.get("match_type") == "aria-label" else 0.85

            logger.info(f"find_by_aria_label('{label}'): {len(matches)} matches")
            return {"status": "success", "matches": matches, "count": len(matches)}

        except Exception as e:
            logger.error(f"find_by_aria_label error: {e}")
            return {"status": "error", "error": str(e), "matches": [], "count": 0}

    async def find_by_placeholder(
        self,
        text: str,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Find input elements by placeholder text.

        Args:
            text: Placeholder text to search for (case-insensitive substring match).
            page_id: Which browser tab to search.

        Returns:
            Dict with status, matches list, and count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}", "matches": [], "count": 0}

        try:
            matches = await page.evaluate(
                """([text]) => {
                    const results = [];
                    const lowerText = text.toLowerCase();

                    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(el => {
                        const placeholder = el.getAttribute('placeholder') || '';
                        if (!placeholder.toLowerCase().includes(lowerText)) return;
                        if (el.offsetParent === null && el.type !== 'hidden') return;

                        let selector = el.tagName.toLowerCase();
                        if (el.id) selector = '#' + CSS.escape(el.id);
                        else if (el.name) selector += '[name="' + el.name + '"]';

                        const labelText = el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '';

                        results.push({
                            selector: selector,
                            text: '',
                            tag: el.tagName.toLowerCase(),
                            type: el.type || 'text',
                            role: el.getAttribute('role') || 'textbox',
                            placeholder: placeholder,
                            label: labelText,
                            name: el.name || null,
                            id: el.id || null,
                            visible: true,
                        });

                        if (results.length >= 20) return;
                    });

                    return results;
                }""",
                [text],
            )

            for m in matches:
                m["confidence"] = 0.9

            logger.info(f"find_by_placeholder('{text}'): {len(matches)} matches")
            return {"status": "success", "matches": matches, "count": len(matches)}

        except Exception as e:
            logger.error(f"find_by_placeholder error: {e}")
            return {"status": "error", "error": str(e), "matches": [], "count": 0}

    async def find_smart(
        self,
        description: str,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Natural language element finding.

        Examples:
            "login button" -> finds button with "login" text or "Login" aria-label
            "search input" -> finds textbox/search input
            "username field" -> finds input with username-related name/placeholder/label
            "submit" -> finds submit button
            "the pricing link" -> finds link containing "pricing"

        Strategy: Parse description for action keywords (click=button/link, type=input/textarea),
        identify target word, search by text then role then placeholder then aria-label.
        Return best match with confidence score and selector to use.

        Args:
            description: Natural language description of the element.
            page_id: Which browser tab to search.

        Returns:
            Dict with status, matches list, count, and best_match.
        """
        desc = description.lower().strip()
        if not desc:
            return {"status": "error", "error": "Empty description", "matches": [], "count": 0}

        # Strip filler words
        desc = re.sub(r'\b(the|a|an|that|this|my|the)\b\s*', '', desc).strip()

        # Detect element type from description
        element_type = self._classify_element_type(desc)
        keyword = self._extract_keyword(desc, element_type)

        logger.info(f"find_smart('{description}'): type={element_type}, keyword='{keyword}'")

        # Try strategies in order of specificity
        all_matches: List[Dict[str, Any]] = []

        strategy_chain = self._build_strategy_chain(element_type, keyword, desc)
        for strategy_name, strategy_fn in strategy_chain:
            try:
                result = await strategy_fn(page_id)
                if result.get("status") == "success" and result.get("count", 0) > 0:
                    for m in result.get("matches", []):
                        m["strategy"] = strategy_name
                        if "confidence" not in m:
                            m["confidence"] = 0.7
                        all_matches.append(m)
                    # If we found high-confidence matches, stop early
                    high_conf = [m for m in all_matches if m.get("confidence", 0) >= 0.85]
                    if high_conf:
                        break
            except Exception as e:
                logger.debug(f"Strategy '{strategy_name}' failed: {e}")
                continue

        # Sort by confidence descending
        all_matches.sort(key=lambda m: m.get("confidence", 0), reverse=True)

        # Deduplicate by selector
        seen_selectors: set = set()
        unique_matches: List[Dict[str, Any]] = []
        for m in all_matches:
            sel = m.get("selector", "")
            if sel and sel not in seen_selectors:
                seen_selectors.add(sel)
                unique_matches.append(m)

        best_match = unique_matches[0] if unique_matches else None

        return {
            "status": "success" if unique_matches else "error",
            "matches": unique_matches[:10],
            "count": len(unique_matches),
            "best_match": best_match,
            "element_type": element_type,
            "keyword": keyword,
            "error": None if unique_matches else f"No element found for: {description}",
        }

    def _classify_element_type(self, desc: str) -> str:
        """Classify the expected element type from a description."""
        button_words = {"button", "btn", "click", "submit", "ok", "cancel", "save", "delete", "confirm", "close", "accept", "decline", "next", "previous", "back", "continue", "login", "logout", "sign in", "sign up", "register", "search"}
        input_words = {"input", "field", "textbox", "text box", "type", "enter", "fill"}
        link_words = {"link", "href", "url", "navigate"}
        checkbox_words = {"checkbox", "check", "tick", "toggle"}
        select_words = {"dropdown", "select", "menu", "combo", "combobox"}
        radio_words = {"radio"}

        words = set(desc.split())
        # Check multi-word patterns
        for phrase in ["sign in", "sign up", "text box"]:
            if phrase in desc:
                words.add(phrase)

        if words & button_words:
            return "button"
        if words & input_words:
            return "input"
        if words & link_words:
            return "link"
        if words & checkbox_words:
            return "checkbox"
        if words & select_words:
            return "select"
        if words & radio_words:
            return "radio"
        return "any"

    def _extract_keyword(self, desc: str, element_type: str) -> str:
        """Extract the target keyword from the description."""
        # Remove type words
        type_words = {
            "button", "btn", "input", "field", "textbox", "text box", "link",
            "checkbox", "check", "dropdown", "select", "menu", "radio",
            "click", "type", "enter", "fill", "the", "for", "of", "with",
        }
        tokens = desc.split()
        keyword_tokens = [t for t in tokens if t not in type_words]
        return " ".join(keyword_tokens).strip() or desc

    def _build_strategy_chain(self, element_type: str, keyword: str, desc: str):
        """Build an ordered list of search strategies to try."""
        strategies = []

        if element_type == "button":
            strategies.append(("text_search", lambda pid: self.find_by_text(keyword, tag="button", page_id=pid)))
            strategies.append(("role_button", lambda pid: self.find_by_role("button", name=keyword, page_id=pid)))
            strategies.append(("aria_label", lambda pid: self.find_by_aria_label(keyword, page_id=pid)))
            strategies.append(("text_any", lambda pid: self.find_by_text(keyword, page_id=pid)))
        elif element_type == "input":
            strategies.append(("placeholder", lambda pid: self.find_by_placeholder(keyword, page_id=pid)))
            strategies.append(("role_textbox", lambda pid: self.find_by_role("textbox", name=keyword, page_id=pid)))
            strategies.append(("aria_label", lambda pid: self.find_by_aria_label(keyword, page_id=pid)))
            strategies.append(("text_nearby", lambda pid: self.find_by_text(keyword, tag="label", page_id=pid)))
        elif element_type == "link":
            strategies.append(("text_link", lambda pid: self.find_by_text(keyword, tag="a", page_id=pid)))
            strategies.append(("role_link", lambda pid: self.find_by_role("link", name=keyword, page_id=pid)))
            strategies.append(("aria_label", lambda pid: self.find_by_aria_label(keyword, page_id=pid)))
        elif element_type == "checkbox":
            strategies.append(("role_checkbox", lambda pid: self.find_by_role("checkbox", name=keyword, page_id=pid)))
            strategies.append(("text_nearby", lambda pid: self.find_by_text(keyword, page_id=pid)))
        elif element_type == "select":
            strategies.append(("role_combobox", lambda pid: self.find_by_role("combobox", name=keyword, page_id=pid)))
            strategies.append(("aria_label", lambda pid: self.find_by_aria_label(keyword, page_id=pid)))
        else:
            # Generic: try everything
            strategies.append(("text_search", lambda pid: self.find_by_text(keyword, page_id=pid)))
            strategies.append(("aria_label", lambda pid: self.find_by_aria_label(keyword, page_id=pid)))
            strategies.append(("placeholder", lambda pid: self.find_by_placeholder(keyword, page_id=pid)))
            strategies.append(("role_any", lambda pid: self.find_by_role("button", name=keyword, page_id=pid)))

        return strategies

    async def find_all_interactive(self, page_id: str = "main") -> Dict[str, Any]:
        """Find ALL interactive elements on the page.

        Returns a structured list of buttons, links, inputs, selects, textareas,
        checkboxes, radios, etc. Each entry has: tag, type, text, selector,
        aria_role, visible, enabled.

        Args:
            page_id: Which browser tab to search.

        Returns:
            Dict with status, categorized elements, and total count.
        """
        page = self.browser._pages.get(page_id, self.browser.page)
        if not page:
            return {"status": "error", "error": f"Page not found: {page_id}"}

        try:
            elements = await page.evaluate("""() => {
                const results = {
                    buttons: [],
                    links: [],
                    inputs: [],
                    selects: [],
                    textareas: [],
                    checkboxes: [],
                    radios: [],
                    other_interactive: [],
                };

                const makeSelector = (el) => {
                    if (el.id) return '#' + CSS.escape(el.id);
                    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
                    if (el.className && typeof el.className === 'string') {
                        const cls = el.className.trim().split(/\\s+/)[0];
                        if (cls) return el.tagName.toLowerCase() + '.' + CSS.escape(cls);
                    }
                    return el.tagName.toLowerCase();
                };

                // Buttons
                document.querySelectorAll('button, input[type=button], input[type=submit], input[type=reset], [role=button]').forEach(el => {
                    if (el.offsetParent === null && el.type !== 'hidden') return;
                    results.buttons.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || 'button',
                        text: (el.innerText || el.value || '').trim().substring(0, 100),
                        selector: makeSelector(el),
                        aria_role: el.getAttribute('role') || 'button',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: el.offsetParent !== null,
                        enabled: !el.disabled,
                    });
                });

                // Links
                document.querySelectorAll('a[href], [role=link]').forEach(el => {
                    if (el.offsetParent === null) return;
                    results.links.push({
                        tag: el.tagName.toLowerCase(),
                        type: 'link',
                        text: (el.innerText || '').trim().substring(0, 100),
                        selector: makeSelector(el),
                        href: el.href || '',
                        aria_role: el.getAttribute('role') || 'link',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: true,
                        enabled: true,
                    });
                });

                // Inputs (text-like)
                document.querySelectorAll('input[type=text], input[type=email], input[type=password], input[type=search], input[type=url], input[type=tel], input[type=number], input[type=date], input[type=time], input:not([type])').forEach(el => {
                    if (el.offsetParent === null && el.type !== 'hidden') return;
                    results.inputs.push({
                        tag: 'input',
                        type: el.type || 'text',
                        text: '',
                        selector: makeSelector(el),
                        placeholder: el.placeholder || '',
                        name: el.name || '',
                        aria_role: el.getAttribute('role') || 'textbox',
                        aria_label: el.getAttribute('aria-label') || '',
                        label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '',
                        visible: el.offsetParent !== null,
                        enabled: !el.disabled,
                    });
                });

                // Textareas
                document.querySelectorAll('textarea').forEach(el => {
                    if (el.offsetParent === null) return;
                    results.textareas.push({
                        tag: 'textarea',
                        type: 'textarea',
                        text: '',
                        selector: makeSelector(el),
                        placeholder: el.placeholder || '',
                        name: el.name || '',
                        aria_role: el.getAttribute('role') || 'textbox',
                        aria_label: el.getAttribute('aria-label') || '',
                        label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '',
                        visible: true,
                        enabled: !el.disabled,
                    });
                });

                // Selects
                document.querySelectorAll('select, [role=combobox], [role=listbox]').forEach(el => {
                    if (el.offsetParent === null) return;
                    const options = el.tagName === 'SELECT'
                        ? Array.from(el.options || []).map(o => o.text).slice(0, 20)
                        : [];
                    results.selects.push({
                        tag: el.tagName.toLowerCase(),
                        type: 'select',
                        text: options.join(', '),
                        selector: makeSelector(el),
                        name: el.name || '',
                        aria_role: el.getAttribute('role') || 'combobox',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: true,
                        enabled: !el.disabled,
                    });
                });

                // Checkboxes
                document.querySelectorAll('input[type=checkbox], [role=checkbox]').forEach(el => {
                    if (el.offsetParent === null) return;
                    results.checkboxes.push({
                        tag: el.tagName.toLowerCase(),
                        type: 'checkbox',
                        text: (el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '').substring(0, 100),
                        selector: makeSelector(el),
                        name: el.name || '',
                        checked: el.checked || el.getAttribute('aria-checked') === 'true',
                        aria_role: 'checkbox',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: true,
                        enabled: !el.disabled,
                    });
                });

                // Radios
                document.querySelectorAll('input[type=radio], [role=radio]').forEach(el => {
                    if (el.offsetParent === null) return;
                    results.radios.push({
                        tag: el.tagName.toLowerCase(),
                        type: 'radio',
                        text: (el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '').substring(0, 100),
                        selector: makeSelector(el),
                        name: el.name || '',
                        checked: el.checked || el.getAttribute('aria-checked') === 'true',
                        aria_role: 'radio',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: true,
                        enabled: !el.disabled,
                    });
                });

                // Other interactive (tabindex, contenteditable, role-based)
                document.querySelectorAll('[tabindex], [contenteditable=true], [role=tab], [role=menuitem], [role=slider], [role=switch]').forEach(el => {
                    if (el.offsetParent === null) return;
                    // Skip if already captured
                    const tag = el.tagName.toLowerCase();
                    if (['button', 'a', 'input', 'select', 'textarea'].includes(tag)) return;
                    results.other_interactive.push({
                        tag: tag,
                        type: el.getAttribute('role') || 'interactive',
                        text: (el.innerText || '').trim().substring(0, 100),
                        selector: makeSelector(el),
                        aria_role: el.getAttribute('role') || '',
                        aria_label: el.getAttribute('aria-label') || '',
                        visible: true,
                        enabled: true,
                    });
                });

                return results;
            }""")

            total = sum(len(v) for v in elements.values())
            logger.info(f"find_all_interactive: {total} elements found")

            return {
                "status": "success",
                "elements": elements,
                "total": total,
                "counts": {k: len(v) for k, v in elements.items()},
            }

        except Exception as e:
            logger.error(f"find_all_interactive error: {e}")
            return {"status": "error", "error": str(e)}
