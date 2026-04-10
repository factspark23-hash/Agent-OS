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
        nav_result = await self.browser.navigate(url)
        if nav_result.get("status") != "success":
            return nav_result

        # Detect all form fields
        fields = await self.browser.evaluate_js("""() => {
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
                    required: el.required,
                    options: el.tagName === 'SELECT'
                        ? Array.from(el.options).map(o => ({value: o.value, text: o.text}))
                        : []
                });
            });
            return fields;
        }""")

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
        result = await self.browser.fill_form(fill_map)

        return {
            "status": "success",
            "fields_detected": len(fields),
            "fields_filled": len(result.get("filled", [])),
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

        for selector in submit_selectors:
            result = await self.browser.click(selector)
            if result.get("status") == "success":
                return {"status": "success", "submitted_via": selector}

        return {"status": "error", "error": "Could not find submit button"}

    def _match_field(self, field: Dict, profile: Dict) -> Optional[str]:
        """Match a form field to profile data."""
        name = (field.get("name") or "").lower()
        id_ = (field.get("id") or "").lower()
        placeholder = (field.get("placeholder") or "").lower()
        label = (field.get("label") or "").lower()
        combined = f"{name} {id_} {placeholder} {label}"

        for field_type, patterns in self.FIELD_PATTERNS.items():
            if any(p in combined for p in patterns):
                value = profile.get(field_type)
                if value:
                    return value

        return None

    def _build_selector(self, field: Dict) -> str:
        """Build a CSS selector for a form field."""
        tag = field.get("tag", "input")
        if field.get("id"):
            return f'#{field["id"]}'
        if field.get("name"):
            return f'{tag}[name="{field["name"]}"]'
        if field.get("placeholder"):
            return f'{tag}[placeholder="{field["placeholder"]}"]'
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
