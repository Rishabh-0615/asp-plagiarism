"""Code-aware heuristic scoring to complement model-based AI detection."""
import math
import re
from collections import Counter


class CodeSignalService:
    """Compute heuristic AI-likelihood signals for source code submissions."""

    _BOILERPLATE_PATTERNS = [
        r"\bthis\s+function\b",
        r"\bthis\s+method\b",
        r"\bhere\s+we\b",
        r"\bas\s+an\s+ai\b",
        r"\blet'?s\s+implement\b",
        r"\bsolution\s+approach\b",
        r"\btime\s+complexity\b",
        r"\bspace\s+complexity\b",
        r"\bexample\s+usage\b",
        r"\boptimal\s+solution\b",
        r"\bexplanation\b",
        r"\bedge\s+case\b",
        r"\bclean\s+and\s+maintainable\b",
        r"\bhelper\s+function\b",
        r"\bstep\s*\d+\b",
    ]

    _EXPLANATION_COMMENT_PATTERNS = [
        r"\bthis\b.*\breturns?\b",
        r"\bwe\s+first\b",
        r"\bnow\s+we\b",
        r"\bto\s+handle\b",
        r"\bin\s+order\s+to\b",
        r"\bfinally\b",
    ]

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _safe_div(num: float, den: float) -> float:
        return num / den if den else 0.0

    def _line_stats(self, text: str) -> dict:
        lines = [line.rstrip() for line in text.splitlines()]
        non_empty = [line for line in lines if line.strip()]

        comment_like = 0
        for line in non_empty:
            stripped = line.strip()
            if (
                stripped.startswith("//")
                or stripped.startswith("#")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                or stripped.startswith("--")
            ):
                comment_like += 1

        counts = Counter(non_empty)
        duplicate_lines = sum(c for c in counts.values() if c > 1)

        lengths = [len(line) for line in non_empty]
        if lengths:
            mean_len = sum(lengths) / len(lengths)
            variance = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
            std_len = math.sqrt(variance)
        else:
            std_len = 0.0

        return {
            "line_count": len(lines),
            "non_empty_line_count": len(non_empty),
            "comment_ratio": self._safe_div(comment_like, len(non_empty)),
            "duplicate_line_ratio": self._safe_div(duplicate_lines, len(non_empty)),
            "line_length_std": std_len,
        }

    def _explanatory_comment_ratio(self, text: str) -> float:
        comment_lines = []
        for raw in text.splitlines():
            line = raw.strip().lower()
            if (
                line.startswith("//")
                or line.startswith("#")
                or line.startswith("/*")
                or line.startswith("*")
                or line.startswith("--")
            ):
                comment_lines.append(line)

        if not comment_lines:
            return 0.0

        explanatory = 0
        for line in comment_lines:
            if any(re.search(pat, line) for pat in self._EXPLANATION_COMMENT_PATTERNS):
                explanatory += 1

        return self._safe_div(explanatory, len(comment_lines))

    def score_code_ai_likelihood(self, text: str) -> dict:
        """Return heuristic AI probability (0-100) and signal metadata for code."""
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
        token_count = len(tokens)
        unique_ratio = self._safe_div(len(set(t.lower() for t in tokens)), token_count)

        stats = self._line_stats(text)
        lowered = text.lower()
        boilerplate_hits = sum(
            1 for pattern in self._BOILERPLATE_PATTERNS if re.search(pattern, lowered)
        )
        explanatory_comment_ratio = self._explanatory_comment_ratio(text)
        markdown_artifact = 1.0 if "```" in text else 0.0

        # Bias correction for common under-detection on generated source code.
        comment_signal = self._clamp((stats["comment_ratio"] - 0.08) / 0.35)
        repetition_signal = self._clamp((stats["duplicate_line_ratio"] - 0.02) / 0.22)
        diversity_signal = self._clamp((0.55 - unique_ratio) / 0.28)
        uniformity_signal = self._clamp((28.0 - stats["line_length_std"]) / 28.0)
        boilerplate_signal = self._clamp(boilerplate_hits / 3.0)
        explanatory_signal = self._clamp(explanatory_comment_ratio / 0.55)

        weighted_signal = (
            0.14 * comment_signal
            + 0.18 * repetition_signal
            + 0.24 * diversity_signal
            + 0.17 * uniformity_signal
            + 0.13 * boilerplate_signal
            + 0.09 * explanatory_signal
            + 0.05 * markdown_artifact
        )
        base_ai_score = 100.0 * weighted_signal

        # Calibration curve: boost moderate signals while clamping hard upper bound.
        calibrated = (base_ai_score * 1.32) + 7.0
        heuristic_ai_score = round(self._clamp(calibrated / 100.0) * 100.0, 2)

        # Confidence increases with sample size and signal density.
        length_conf = self._clamp(token_count / 220.0)
        signal_conf = self._clamp((
            comment_signal + repetition_signal + diversity_signal + boilerplate_signal + explanatory_signal
        ) / 2.5)
        confidence = round(self._clamp(0.55 * length_conf + 0.45 * signal_conf), 2)

        return {
            "heuristic_ai_score": heuristic_ai_score,
            "heuristic_human_score": round(100.0 - heuristic_ai_score, 2),
            "heuristic_confidence": confidence,
            "signals": {
                "token_count": token_count,
                "unique_identifier_ratio": round(unique_ratio, 3),
                "comment_ratio": round(stats["comment_ratio"], 3),
                "duplicate_line_ratio": round(stats["duplicate_line_ratio"], 3),
                "line_length_std": round(stats["line_length_std"], 2),
                "boilerplate_hits": boilerplate_hits,
                "explanatory_comment_ratio": round(explanatory_comment_ratio, 3),
                "markdown_artifact": int(markdown_artifact),
            },
        }
