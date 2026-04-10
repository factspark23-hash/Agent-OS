"""
Agent-OS Input Validation
Pydantic schemas for all command inputs with sanitization.
Prevents injection attacks, path traversal, and malformed data.
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger("agent-os.validation")

# Dangerous patterns in JavaScript
JS_DANGEROUS_PATTERNS = [
    r"document\.cookie\s*=",
    r"window\.location\s*=",
    r"location\.href\s*=",
    r"location\.replace",
    r"\.innerHTML\s*=",
    r"eval\s*\(",
    r"Function\s*\(",
    r"setTimeout\s*\(\s*['\"]",
    r"setInterval\s*\(\s*['\"]",
    r"new\s+Function",
    r"__proto__",
    r"constructor\s*\[",
    r"import\s*\(",
    r"require\s*\(",
    r"process\.env",
    r"fs\.",
    r"child_process",
    r"\.exec\s*\(",
]

COMPILED_JS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JS_DANGEROUS_PATTERNS]

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Max lengths for various fields
MAX_URL_LENGTH = 2048
MAX_SELECTOR_LENGTH = 500
MAX_TEXT_LENGTH = 100000
MAX_JS_LENGTH = 50000
MAX_FIELDS_COUNT = 50
MAX_STEPS_COUNT = 100
MAX_FIELD_VALUE_LENGTH = 10000


class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


def _shallow_validate(obj, depth: int = 0, max_depth: int = 3):
    """Recursively validate nested structures with depth limit."""
    if depth > max_depth:
        raise ValidationError(f"Object nesting exceeds max depth of {max_depth}")
    if isinstance(obj, dict):
        return {
            str(k)[:200]: _shallow_validate(v, depth + 1, max_depth)
            for k, v in list(obj.items())[:100]
        }
    elif isinstance(obj, list):
        return [
            _shallow_validate(item, depth + 1, max_depth)
            for item in obj[:200]
        ]
    elif isinstance(obj, str):
        # Strip null bytes and limit length
        return obj.replace("\x00", "")[:10000]
    elif isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)[:10000]


def sanitize_string(value: str, max_length: int = 10000, field_name: str = "value") -> str:
    """Sanitize a string input."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name)

    # Strip null bytes
    value = value.replace("\x00", "")

    # Truncate
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters",
            field_name
        )

    return value


def validate_url(url: str, field_name: str = "url") -> str:
    """Validate and sanitize a URL."""
    url = sanitize_string(url, MAX_URL_LENGTH, field_name)

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError(f"Invalid URL format: {field_name}", field_name)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValidationError(
            f"URL scheme must be http or https, got: {parsed.scheme}",
            field_name
        )

    if not parsed.hostname:
        raise ValidationError(f"URL must have a hostname: {field_name}", field_name)

    # Block internal networks (basic SSRF protection)
    hostname = parsed.hostname.lower()
    blocked_hosts = {
        "localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254",
        "metadata.google.internal",
    }
    if hostname in blocked_hosts:
        raise ValidationError(f"URL targets blocked host: {hostname}", field_name)

    # Block private IP ranges (basic check)
    if hostname.startswith("10.") or hostname.startswith("172.16.") or hostname.startswith("192.168."):
        logger.warning(f"URL targets private IP: {hostname}")

    return url


def validate_selector(selector: str, field_name: str = "selector") -> str:
    """Validate a CSS selector."""
    selector = sanitize_string(selector, MAX_SELECTOR_LENGTH, field_name)

    if not selector.strip():
        raise ValidationError(f"{field_name} cannot be empty", field_name)

    # Block JavaScript injection via selector
    if "javascript:" in selector.lower():
        raise ValidationError(f"JavaScript protocol not allowed in {field_name}", field_name)

    return selector


def validate_javascript(script: str, field_name: str = "script") -> str:
    """Validate JavaScript code with security checks. Rejects dangerous patterns."""
    script = sanitize_string(script, MAX_JS_LENGTH, field_name)

    if not script.strip():
        raise ValidationError(f"{field_name} cannot be empty", field_name)

    # Check for dangerous patterns — reject, don't just log
    for pattern in COMPILED_JS_PATTERNS:
        if pattern.search(script):
            raise ValidationError(
                f"Dangerous pattern detected in {field_name}: {pattern.pattern}",
                field_name
            )

    return script


def validate_fields_dict(fields: dict, field_name: str = "fields") -> dict:
    """Validate a selector->value dictionary for form filling."""
    if not isinstance(fields, dict):
        raise ValidationError(f"{field_name} must be a dictionary", field_name)

    if len(fields) > MAX_FIELDS_COUNT:
        raise ValidationError(
            f"{field_name} has {len(fields)} entries, max is {MAX_FIELDS_COUNT}",
            field_name
        )

    validated = {}
    for key, value in fields.items():
        validated_key = validate_selector(str(key), f"{field_name} key")
        validated_value = sanitize_string(str(value), MAX_FIELD_VALUE_LENGTH, f"{field_name} value")
        validated[validated_key] = validated_value

    return validated


def validate_command_payload(data: dict) -> dict:
    """
    Validate and sanitize a full command payload.
    Returns cleaned data dict.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    command = data.get("command", "").lower().strip()
    if not command:
        raise ValidationError("Missing 'command' field")

    if len(command) > 100:
        raise ValidationError("Command name too long")

    # Whitelist allowed command characters
    if not re.match(r'^[a-z][a-z0-9\-]*$', command):
        raise ValidationError(f"Invalid command format: {command}")

    validated = {"command": command}

    # Validate common fields
    if "token" in data:
        validated["token"] = sanitize_string(str(data["token"]), 500, "token")

    if "url" in data:
        validated["url"] = validate_url(str(data["url"]))

    if "selector" in data:
        validated["selector"] = validate_selector(str(data["selector"]))

    if "source" in data:
        validated["source"] = validate_selector(str(data["source"]))

    if "target" in data:
        validated["target"] = validate_selector(str(data["target"]))

    if "text" in data:
        validated["text"] = sanitize_string(str(data["text"]), MAX_TEXT_LENGTH, "text")

    if "key" in data:
        sanitized_key = sanitize_string(str(data["key"]), 50, "key")
        # Whitelist keyboard keys
        allowed_keys = {
            "Enter", "Tab", "Escape", "Backspace", "Delete", "Space",
            "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
            "Home", "End", "PageUp", "PageDown",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Control+a", "Control+c", "Control+v", "Control+x", "Control+z",
            "Control+s", "Control+f", "Control+g",
            "Shift+Tab",
        }
        if sanitized_key not in allowed_keys and not re.match(r'^[a-zA-Z0-9]$', sanitized_key):
            if "+" in sanitized_key:
                parts = sanitized_key.split("+")
                valid_modifiers = {"Control", "Shift", "Alt", "Meta"}
                if not all(p in valid_modifiers or re.match(r'^[a-zA-Z0-9]$', p) for p in parts):
                    raise ValidationError(f"Invalid key combination: {sanitized_key}")
        validated["key"] = sanitized_key

    if "script" in data:
        validated["script"] = validate_javascript(str(data["script"]))

    if "fields" in data:
        validated["fields"] = validate_fields_dict(data["fields"])

    if "value" in data:
        validated["value"] = sanitize_string(str(data["value"]), MAX_FIELD_VALUE_LENGTH, "value")

    if "description" in data:
        validated["description"] = sanitize_string(str(data["description"]), 500, "description")

    if "label" in data:
        validated["label"] = sanitize_string(str(data["label"]), 500, "label")

    if "name" in data:
        validated["name"] = sanitize_string(str(data["name"]), 200, "name")

    # Numeric fields
    for int_field in ["width", "height", "amount", "timeout", "full_page",
                      "page_id", "idle_ms", "dom_stable_ms", "timeout_ms",
                      "stability_ms", "speed", "from_event", "to_event",
                      "retry_count", "step_delay_ms", "priority"]:
        if int_field in data:
            try:
                val = int(data[int_field]) if not isinstance(data[int_field], bool) else data[int_field]
                validated[int_field] = max(0, min(val, 999999))
            except (ValueError, TypeError):
                raise ValidationError(f"{int_field} must be a number", int_field)

    # Boolean fields
    for bool_field in ["checked", "full_page", "clear", "http_only", "secure",
                       "capture_body", "deduplicate"]:
        if bool_field in data:
            validated[bool_field] = bool(data[bool_field])

    # Pass through steps, variables, conditions with recursive validation
    if "steps" in data and isinstance(data["steps"], list):
        validated["steps"] = [
            validate_command_payload(step) if isinstance(step, dict) else step
            for step in data["steps"][:MAX_STEPS_COUNT]
        ]

    if "conditions" in data and isinstance(data["conditions"], list):
        validated["conditions"] = [
            validate_command_payload(cond) if isinstance(cond, dict) else cond
            for cond in data["conditions"][:20]
        ]

    if "command_payload" in data and isinstance(data["command_payload"], dict):
        validated["command_payload"] = validate_command_payload(data["command_payload"])

    # Simple pass-through for non-nested data structures
    for passthrough in ["variables", "headers", "tags", "capabilities",
                        "metadata", "dependencies", "profile", "result",
                        "context", "resource_types", "methods"]:
        if passthrough in data:
            val = data[passthrough]
            if isinstance(val, (dict, list)):
                # Limit depth to prevent deeply nested abuse
                validated[passthrough] = _shallow_validate(val, depth=0, max_depth=3)
            else:
                validated[passthrough] = val

    # String fields that don't need special validation
    for str_field in ["page_id", "action", "tab_id", "direction", "device",
                      "domain", "file_path", "extension_path", "action_text",
                      "attribute", "path", "same_site", "value",
                      "template_name", "json", "expression", "format",
                      "filename", "proxy_url", "language", "agent_id",
                      "lock_type", "topic", "sender_id", "key",
                      "to_agent_id", "from_agent_id", "resource",
                      "session_id", "strategy", "filepath", "api_url",
                      "api_key", "proxy_type", "recording_id",
                      "workflow_id", "inner_command", "operation",
                      "error", "message", "category", "assigned_to",
                      "assigned_by", "url_pattern", "query",
                      "event_type", "status", "country", "region",
                      "proxy_id", "name", "prefix", "strategy",
                      "recording_id", "username", "password",
                      "region", "proxy_id", "email", "display_name",
                      "organization", "plan", "role"]:
        if str_field in data and data[str_field] is not None:
            validated[str_field] = sanitize_string(str(data[str_field]), 2000, str_field)

    # Pass through remaining fields with basic sanitization
    for key, value in data.items():
        if key not in validated:
            if isinstance(value, str):
                validated[key] = sanitize_string(value, 5000, key)
            elif isinstance(value, (int, float, bool)):
                validated[key] = value
            elif isinstance(value, (list, dict)):
                validated[key] = value
            elif value is None:
                validated[key] = None

    return validated
