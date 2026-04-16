"""
Agent-OS Form Filler
Automates job applications and complex multi-step forms.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger("agent-os.form-filler")


class FormFiller:
    """Automated form filling with human-like behavior."""

    # Common field name patterns and their semantic meaning
    FIELD_PATTERNS = {
        "email": ["email", "e-mail", "mail", "user_email"],
        "username": ["username", "user_name", "user", "userid", "user_id", "login", "login_id"],
        "password": ["password", "passwd", "pass", "pwd", "user_password", "user_pass"],
        "first_name": ["first_name", "firstname", "fname", "first-name", "given_name"],
        "last_name": ["last_name", "lastname", "lname", "last-name", "family_name"],
        "full_name": ["full_name", "fullname", "name", "your_name", "candidate_name"],
        "phone": ["phone", "telephone", "mobile", "cell", "phone_number"],
        "address": ["address", "street", "street_address", "address1"],
        "city": ["city", "town"],
        "state": ["state", "province", "region"],
        "zip": ["zip", "zipcode", "zip_code", "postal", "postcode"],
        "country": ["country", "nation"],
        "linkedin": ["linkedin", "linkedin_url", "linkedin_profile"],
        "website": ["website", "portfolio", "url", "personal_website"],
        "cover_letter": ["cover_letter", "coverletter", "cover-letter", "message"],
        "salary": ["salary", "compensation", "expected_salary", "salary_expectation"],
        "experience": ["experience", "years_experience", "years_of_experience"],
        "resume": ["resume", "cv", "file", "upload"],
    }

    # Cross-field mappings: when looking for 'username', also check 'email' fields
    # This handles sites like Instagram that use name="email" for username input
    CROSS_FIELD_MAP = {
        "username": ["email"],
        "email": ["username"],
    }

    def __init__(self, browser):
        self.browser = browser

    async def fill_job_application(self, url: str, profile: Dict[str, str]) -> Dict:
        """
        Fill a job application form automatically.

        profile should contain:
        - email, first_name, last_name, phone, address, city, state, zip
        - cover_letter (optional), salary (optional), linkedin (optional)
        """
        logger.info(f"Filling job application at {url}")

        # Navigate to the job page
        try:
            nav_result = await self.browser.navigate(url)
            # browser.navigate() may return a dict or a string (URL)
            if isinstance(nav_result, dict):
                if nav_result.get("status") != "success":
                    return nav_result
            elif isinstance(nav_result, str):
                # navigate() returned a URL string — navigation succeeded
                pass
            # If nav_result is None or unexpected, continue anyway
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return {"status": "error", "error": f"Navigation failed: {e}"}

        # Detect all form fields
        try:
            result = await self.browser.evaluate_js("""() => {
                const fields = [];
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    if (el.type === 'hidden' || el.type === 'submit') return;
                    fields.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || 'text',
                        name: el.name || '',
                        id: el.id || '',
                        placeholder: el.placeholder || '',
                        label: el.labels?.[0]?.textContent?.trim() || '',
                        aria_label: el.getAttribute('aria-label') || '',
                        title: el.title || '',
                        data_testid: el.getAttribute('data-testid') || '',
                        required: el.required,
                        options: el.tagName === 'SELECT'
                            ? Array.from(el.options).map(o => ({value: o.value, text: o.text}))
                            : []
                    });
                });
                return fields;
            }""")
            # evaluate_js now returns {"status": ..., "result": ...} — unwrap
            if isinstance(result, dict) and result.get("status") == "success":
                fields = result.get("result", [])
            elif isinstance(result, list):
                fields = result  # backward compat
            else:
                fields = []
                
        except Exception as e:
            logger.error(f"Field detection failed: {e}")
            return {"status": "error", "error": f"Field detection failed: {e}"}

        if not fields:
            return {"status": "error", "error": "No form fields found on page"}

        # Map detected fields to profile data
        fill_map = {}
        for field in fields:
            matched_value = self._match_field(field, profile)
            if matched_value:
                selector = self._build_selector(field)
                fill_map[selector] = matched_value

        if not fill_map:
            return {"status": "error", "error": "No matching fields found for profile data"}

        # Fill the form with human-like timing
        try:
            result = await self.browser.fill_form(fill_map)
        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            return {"status": "error", "error": f"Form filling failed: {e}"}

        # Handle both dict and string results from fill_form
        if isinstance(result, dict):
            filled_count = len(result.get("filled", []))
        elif isinstance(result, str):
            filled_count = len(fill_map)  # Assume all fields were attempted
        else:
            filled_count = 0

        return {
            "status": "success",
            "fields_detected": len(fields),
            "fields_filled": filled_count,
            "fill_map": fill_map,
            "note": "Review before submitting — form filled but NOT submitted automatically"
        }

    async def auto_submit(self) -> Dict:
        """Click submit button (use with caution)."""
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            'button:has-text("Continue")',
            '[data-testid="submit-button"]',
            '.submit-btn',
            '#submit',
        ]

        submitted = False
        submitted_via = None

        for selector in submit_selectors:
            try:
                result = await self.browser.click(selector)
                if result.get("status") == "success":
                    submitted = True
                    submitted_via = selector
                    break  # Stop after first successful submit to prevent double submission
            except Exception as e:
                logger.warning(f"Failed to click submit selector '{selector}': {e}")
                continue

        if submitted:
            return {"status": "success", "submitted_via": submitted_via}

        # Final fallback: submit form via JavaScript
        try:
            js_result = await self.browser.evaluate_js("""
                const form = document.querySelector('form');
                if (form) { form.submit(); return true; }
                return false;
            """)
            if isinstance(js_result, dict) and js_result.get("result"):
                return {"status": "success", "submitted_via": "js_form_submit"}
        except Exception:
            pass

        return {"status": "error", "error": "Could not find submit button"}

    # Common misspellings mapped to correct field type names
    MISSPELLING_MAP = {
        "emial": "email",
        "e-mail": "email",
        "fisrtname": "first_name",
        "firtsname": "first_name",
        "frist_name": "first_name",
        "fisrt_name": "first_name",
        "lastnme": "last_name",
        "lasname": "last_name",
        "passowrd": "password",
        "passwrod": "password",
        "phonenumber": "phone",
        "phon": "phone",
        "adddress": "address",
        "adress": "address",
        "zipocde": "zip",
        "zipcoce": "zip",
        "contry": "country",
        "conutry": "country",
    }

    def _match_field(self, field: Dict, profile: Dict) -> Optional[str]:
        """Match a form field to profile data.

        Multi-strategy matching:
        1. Check name, id, placeholder, label attributes
        2. Also check aria-label, title, data-testid attributes
        3. Fuzzy matching for common misspellings (e.g., "emial" → "email")
        4. Cross-field mappings (e.g., username field can match email profile data)
        """
        name = (field.get("name") or "").lower()
        id_ = (field.get("id") or "").lower()
        placeholder = (field.get("placeholder") or "").lower()
        label = (field.get("label") or "").lower()
        aria_label = (field.get("aria_label") or "").lower()
        title = (field.get("title") or "").lower()
        data_testid = (field.get("data_testid") or "").lower()
        combined = f"{name} {id_} {placeholder} {label} {aria_label} {title} {data_testid}"

        # Apply misspelling corrections to combined text
        corrected = combined
        for misspelling, correction in self.MISSPELLING_MAP.items():
            if misspelling in corrected:
                corrected = corrected.replace(misspelling, correction)

        # Try matching with both original and corrected text
        for text in (combined, corrected):
            for field_type, patterns in self.FIELD_PATTERNS.items():
                if any(p in text for p in patterns):
                    value = profile.get(field_type)
                    if value:
                        return value
                    # Try cross-field mapping (e.g., username field → email profile data)
                    cross_fields = self.CROSS_FIELD_MAP.get(field_type, [])
                    for cross_field in cross_fields:
                        cross_value = profile.get(cross_field)
                        if cross_value:
                            logger.debug(f"Cross-field match: {field_type} → {cross_field} for field '{name}'")
                            return cross_value

        return None

    def _build_selector(self, field: Dict) -> str:
        """Build a CSS selector for a form field with multi-strategy fallbacks."""
        tag = field.get("tag", "input")
        if field.get("id"):
            return f'#{field["id"]}'
        if field.get("name"):
            return f'{tag}[name="{field["name"]}"]'
        if field.get("placeholder"):
            return f'{tag}[placeholder="{field["placeholder"]}"]'
        # Try aria-label selector
        if field.get("aria_label"):
            return f'{tag}[aria-label="{field["aria_label"]}"]'
        # Try data-testid selector
        if field.get("data_testid"):
            return f'{tag}[data-testid="{field["data_testid"]}"]'
        # Try CSS :has-text pseudo-selector as fallback (for label text)
        label = field.get("label", "").strip()
        if label:
            return f'{tag}:has-text("{label}")'
        return tag


class ProfileBuilder:
    """Builds a user profile for form filling."""

    @staticmethod
    def from_dict(data: Dict[str, str]) -> Dict[str, str]:
        """Create profile from dictionary."""
        return {
            "email": data.get("email", ""),
            "first_name": data.get("first_name", data.get("firstName", "")),
            "last_name": data.get("last_name", data.get("lastName", "")),
            "full_name": data.get("full_name", data.get("fullName", "")),
            "phone": data.get("phone", data.get("phoneNumber", "")),
            "address": data.get("address", data.get("streetAddress", "")),
            "city": data.get("city", ""),
            "state": data.get("state", data.get("province", "")),
            "zip": data.get("zip", data.get("zipCode", data.get("postalCode", ""))),
            "country": data.get("country", ""),
            "linkedin": data.get("linkedin", data.get("linkedinUrl", "")),
            "website": data.get("website", data.get("portfolio", "")),
            "cover_letter": data.get("cover_letter", data.get("coverLetter", "")),
            "salary": data.get("salary", data.get("expectedSalary", "")),
            "experience": data.get("experience", data.get("yearsExperience", "")),
        }
