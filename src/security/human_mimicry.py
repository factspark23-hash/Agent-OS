"""
Agent-OS Human Mimicry Engine
Generates realistic human behavior patterns:
- Mouse movement curves (Bezier-based)
- Typing rhythm simulation
- Scroll behavior
- Page interaction timing
"""
import random
import math
import time
from typing import List, Tuple, Optional


class HumanMimicry:
    """Simulates human interaction patterns."""

    # Real human typing delays (ms) based on research
    TYPING_DELAYS = {
        "fast": (40, 90),
        "normal": (80, 180),
        "slow": (150, 300),
        "thinking": (300, 800),  # Pauses between words
    }

    # Mouse movement profiles
    SPEED_PROFILES = {
        "fast": 0.8,
        "normal": 0.5,
        "careful": 0.25,
    }

    def __init__(self, speed: str = "normal"):
        self.speed = speed
        self._last_move = (0, 0)

    def typing_delay(self, style: str = "normal") -> int:
        """Generate human-like delay between keystrokes (ms)."""
        lo, hi = self.TYPING_DELAYS.get(style, self.TYPING_DELAYS["normal"])
        return random.randint(lo, hi)

    def word_pause(self) -> int:
        """Generate pause between words (ms)."""
        # Humans pause 200-600ms between words, occasionally longer
        if random.random() < 0.1:  # 10% chance of "thinking" pause
            return random.randint(500, 1500)
        return random.randint(150, 450)

    def mouse_path(self, target_x: int, target_y: int, steps: Optional[int] = None) -> List[Tuple[float, float]]:
        """
        Generate human-like mouse movement path using Bezier curves.
        Humans don't move in straight lines — they curve slightly.
        """
        start_x, start_y = self._last_move
        self._last_move = (target_x, target_y)

        if steps is None:
            dist = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
            steps = max(5, min(50, int(dist / 20)))

        # Generate control points for Bezier curve
        # Add slight randomness to simulate human imperfection
        mid_x = (start_x + target_x) / 2 + random.gauss(0, 30)
        mid_y = (start_y + target_y) / 2 + random.gauss(0, 30)

        path = []
        for i in range(steps + 1):
            t = i / steps
            # Quadratic Bezier: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * target_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * target_y

            # Add micro-tremor (human hand jitter)
            x += random.gauss(0, 1.5)
            y += random.gauss(0, 1.5)

            path.append((round(x, 1), round(y, 1)))

        return path

    def mouse_delay(self) -> float:
        """Generate delay between mouse movements (seconds)."""
        base = self.SPEED_PROFILES.get(self.speed, 0.5)
        return random.gauss(base * 0.02, base * 0.008)

    def scroll_delay(self) -> float:
        """Generate delay between scroll events (seconds)."""
        return random.uniform(0.05, 0.15)

    def click_delay(self) -> float:
        """Generate delay before clicking (seconds)."""
        # Humans hesitate slightly before clicking
        return random.uniform(0.05, 0.2)

    def page_read_time(self, text_length: int = 1000) -> float:
        """
        Estimate time a human would take to "read" a page.
        Average reading speed: ~250 words/min = ~4.2 words/sec.
        """
        words = text_length / 5  # Approximate words
        base_time = words / 4.2
        # Add variance and minimum
        return max(1.0, base_time + random.gauss(0, base_time * 0.2))

    def form_fill_sequence(self, fields: list) -> List[Tuple[str, float]]:
        """
        Generate a realistic form fill sequence with delays.
        Returns (field_name, delay_before_filling_seconds).
        """
        sequence = []
        for i, field in enumerate(fields):
            # First field: longer delay (reading the form)
            if i == 0:
                delay = random.uniform(1.0, 3.0)
            # Between fields: short delay
            else:
                delay = random.uniform(0.3, 1.0)
            # Occasionally pause longer (thinking about what to enter)
            if random.random() < 0.15:
                delay += random.uniform(1.0, 3.0)
            sequence.append((field, delay))
        return sequence

    def mistake_and_correct(self, text: str) -> List[Tuple[str, str]]:
        """
        Simulate human typos and corrections.
        Returns list of (char_to_type, action) where action is 'type' or 'backspace'.
        """
        actions = []
        i = 0
        while i < len(text):
            # 3% chance of making a typo
            if random.random() < 0.03 and text[i].isalpha():
                # Type wrong char
                wrong_char = random.choice("qwertyuiop")
                actions.append((wrong_char, "type"))
                # Wait a bit
                actions.append(("", "think"))
                # Backspace
                actions.append(("", "backspace"))
                # Type correct char
                actions.append((text[i], "type"))
            else:
                actions.append((text[i], "type"))
            i += 1
        return actions

    def hesitation_before_action(self, action_type: str = "click") -> float:
        """
        Generate hesitation time before an action.
        Humans naturally pause before important actions.
        """
        hesitations = {
            "click": random.uniform(0.1, 0.4),
            "submit": random.uniform(0.5, 2.0),  # Longer pause before submitting
            "navigate": random.uniform(0.2, 0.8),
            "type": random.uniform(0.05, 0.2),
        }
        return hesitations.get(action_type, 0.2)


class InteractionRecorder:
    """Records interaction patterns for analysis (optional)."""

    def __init__(self):
        self.events = []
        self.start_time = time.time()

    def record(self, event_type: str, data: dict):
        self.events.append({
            "time": time.time() - self.start_time,
            "type": event_type,
            "data": data
        })

    def get_summary(self) -> dict:
        total_time = time.time() - self.start_time
        return {
            "total_duration": round(total_time, 2),
            "total_events": len(self.events),
            "events_by_type": {
                etype: len([e for e in self.events if e["type"] == etype])
                for etype in set(e["type"] for e in self.events)
            }
        }
