"""Local autocomplete engine using a local Qwen model."""
from __future__ import annotations

from dataclasses import dataclass
import builtins
import keyword
import os
import re
import threading

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
)
from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer


class _SharedState:
    """Thread-safe state for cancellation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest_request_id = 0

    def set_latest(self, request_id: int) -> None:
        with self._lock:
            self._latest_request_id = request_id

    def get_latest(self) -> int:
        with self._lock:
            return self._latest_request_id


class _CancelOnNewRequest(StoppingCriteria):
    """Stop generation when a newer request arrives."""

    def __init__(self, shared_state: _SharedState, request_id: int) -> None:
        super().__init__()
        self._shared_state = shared_state
        self._request_id = request_id

    def __call__(self, *args, **kwargs) -> bool:
        return self._shared_state.get_latest() != self._request_id


@dataclass
class AutocompleteSettings:
    enabled: bool
    model_dir: str
    device: str  # "auto", "cpu", "cuda"
    max_new_tokens: int
    context_tokens: int
    context_chars: int
    temperature: float
    top_p: float
    debounce_ms: int
    allow_in_strings: bool
    llm_first: bool


class AutocompleteWorker(QObject):
    suggestion_ready = Signal(int, str, int, str)
    status = Signal(str)
    error = Signal(int, str)

    def __init__(self, settings: AutocompleteSettings, shared_state: _SharedState) -> None:
        super().__init__()
        self._settings = settings
        self._shared_state = shared_state
        self._model = None
        self._tokenizer = None
        self._device = "cpu"

    def update_settings(self, settings: AutocompleteSettings) -> None:
        self._settings = settings

    def _resolve_device(self) -> str:
        if self._settings.device == "cpu":
            return "cpu"
        if self._settings.device == "cuda" and torch.cuda.is_available():
            return "cuda"
        if self._settings.device == "cuda":
            self.status.emit("CUDA not available. Falling back to CPU.")
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        self.status.emit("Loading autocomplete model...")
        self._device = self._resolve_device()
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._settings.model_dir,
            local_files_only=True,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self._settings.model_dir,
            local_files_only=True,
            dtype=torch.float32,
        )
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token_id = self._tokenizer.eos_token_id
        self._model.to(self._device)
        self._model.eval()
        self.status.emit(f"Autocomplete model ready ({self._device}).")

    @Slot(int, str, int)
    def handle_request(self, request_id: int, prefix: str, cursor_pos: int) -> None:
        try:
            self._load_model()
            if not prefix:
                self.suggestion_ready.emit(request_id, "", cursor_pos, prefix)
                return

            prompt = prefix
            if self._settings.context_chars > 0:
                prompt = prefix[-self._settings.context_chars :]

            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self._settings.context_tokens,
            )
            input_ids = inputs["input_ids"].to(self._device)
            attention_mask = inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self._device)

            do_sample = self._settings.temperature > 0.0
            stopping = StoppingCriteriaList(
                [_CancelOnNewRequest(self._shared_state, request_id)]
            )

            gen_kwargs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "max_new_tokens": self._settings.max_new_tokens,
                "do_sample": do_sample,
                "num_beams": 1,
                "pad_token_id": self._tokenizer.pad_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
                "stopping_criteria": stopping,
            }
            if do_sample:
                gen_kwargs["temperature"] = max(self._settings.temperature, 1e-5)
                gen_kwargs["top_p"] = self._settings.top_p

            with torch.inference_mode():
                output = self._model.generate(**gen_kwargs)

            if output.shape[-1] <= input_ids.shape[-1]:
                suggestion = ""
            else:
                new_tokens = output[0, input_ids.shape[-1] :]
                suggestion = self._tokenizer.decode(
                    new_tokens, skip_special_tokens=True
                )

            suggestion = suggestion.splitlines()[0]
            self.suggestion_ready.emit(request_id, suggestion, cursor_pos, prefix)
        except Exception as exc:
            self.error.emit(request_id, str(exc))


class AutocompleteEngine(QObject):
    suggestion_ready = Signal(int, str, int, str)
    status = Signal(str)
    error = Signal(int, str)

    _request_signal = Signal(int, str, int)

    def __init__(self, settings: AutocompleteSettings) -> None:
        super().__init__()
        self._settings = settings
        self._shared_state = _SharedState()
        self._thread = QThread()
        self._worker = AutocompleteWorker(settings, self._shared_state)
        self._worker.moveToThread(self._thread)

        self._request_signal.connect(self._worker.handle_request)
        self._worker.suggestion_ready.connect(self.suggestion_ready)
        self._worker.status.connect(self.status)
        self._worker.error.connect(self.error)
        self._thread.start()
        self._request_id = 0

    def update_settings(self, settings: AutocompleteSettings) -> None:
        self._settings = settings
        self._worker.update_settings(settings)

    def request(self, prefix: str, cursor_pos: int) -> int:
        self._request_id += 1
        self._shared_state.set_latest(self._request_id)
        self._request_signal.emit(self._request_id, prefix, cursor_pos)
        return self._request_id

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait(2000)


class AutocompleteController(QObject):
    """Connects editor events to the autocomplete engine."""

    _COMMON_DOT_IDENTIFIERS = [
        "Console.WriteLine",
        "Console.Write",
        "System.out.println",
        "System.out.print",
        "System.out.printf",
        "String.format",
        "Math.Max",
        "Math.Min",
        "Math.Abs",
        "Math.Round",
        "Math.Floor",
        "Math.Ceiling",
    ]

    def __init__(self, editor, config) -> None:
        super().__init__(editor)
        self._editor = editor
        self._config = config
        self._max_suggestion_chars = 80
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._send_request)
        self._engine = AutocompleteEngine(self._read_settings())
        self._engine.suggestion_ready.connect(self._on_suggestion)
        self._engine.status.connect(self._on_status)
        self._engine.error.connect(self._on_error)
        self._pending_text = ""
        self._pending_cursor = 0
        self._latest_request_id = 0
        self._latest_prefix = ""
        self._last_symbol_text = ""
        self._symbol_cache: list[str] = []
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0

        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.cursorPositionChanged.connect(self._on_cursor_changed)

    def _extract_symbols(self, text: str) -> list[str]:
        if text == self._last_symbol_text:
            return self._symbol_cache
        tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))
        tokens.update(keyword.kwlist)
        tokens.update(dir(builtins))
        tokens.update(self._COMMON_DOT_IDENTIFIERS)
        self._last_symbol_text = text
        self._symbol_cache = list(tokens)
        return self._symbol_cache

    def _word_prefix(self, text: str, cursor_pos: int) -> tuple[str, int]:
        if cursor_pos <= 0:
            return "", cursor_pos
        start = cursor_pos
        while start > 0 and re.match(r"[A-Za-z0-9_]", text[start - 1]):
            start -= 1
        prefix = text[start:cursor_pos]
        return prefix, start

    def _can_complete_here(self, text: str, cursor_pos: int) -> bool:
        if cursor_pos < len(text):
            next_char = text[cursor_pos]
            if re.match(r"[A-Za-z0-9_]", next_char):
                return False
        return True

    def _in_string_or_comment(self, text: str, cursor_pos: int) -> bool:
        line_start = text.rfind("\n", 0, cursor_pos) + 1
        line = text[line_start:cursor_pos]
        in_single = False
        in_double = False
        escape = False
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif not in_double and ch == "'" and line[i:i + 3] != "'''":
                in_single = not in_single
            elif not in_single and ch == '"' and line[i:i + 3] != '"""':
                in_double = not in_double
            elif not in_single and not in_double and ch == "#":
                return True
            i += 1
        return in_single or in_double

    def _symbol_suggestion(self, text: str, cursor_pos: int) -> str:
        if not self._can_complete_here(text, cursor_pos):
            return ""
        prefix, _ = self._word_prefix(text, cursor_pos)
        if not prefix:
            return self._assignment_symbol_suggestion(text, cursor_pos)
        symbols = self._extract_symbols(text)
        matches = [s for s in symbols if s.startswith(prefix) and s != prefix]
        if not matches:
            return ""
        matches.sort(
            key=lambda s: (-text.rfind(s), len(s), s)
        )
        best = matches[0]
        return best[len(prefix):]

    def _assignment_symbol_suggestion(self, text: str, cursor_pos: int) -> str:
        pos = cursor_pos - 1
        while pos >= 0 and text[pos].isspace():
            pos -= 1
        if pos < 0:
            return ""
        if text[pos] not in "=+-*/%&|^~,:()[]{}":
            return ""
        line_start = text.rfind("\n", 0, cursor_pos) + 1
        prior_text = text[:line_start]
        if not prior_text:
            return ""
        last_symbol = ""
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", prior_text):
            eq_pos = match.end() - 1
            if eq_pos + 1 < len(prior_text) and prior_text[eq_pos + 1] == "=":
                continue
            last_symbol = match.group(1)
        return last_symbol

    def _read_settings(self) -> AutocompleteSettings:
        model_dir = self._config.get("autocomplete", "model_dir")
        if not os.path.isabs(model_dir):
            model_dir = os.path.abspath(model_dir)
        return AutocompleteSettings(
            enabled=self._config.get("autocomplete", "enabled"),
            model_dir=model_dir,
            device=self._config.get("autocomplete", "device"),
            max_new_tokens=self._config.get("autocomplete", "max_new_tokens"),
            context_tokens=self._config.get("autocomplete", "context_tokens"),
            context_chars=self._config.get("autocomplete", "context_chars"),
            temperature=self._config.get("autocomplete", "temperature"),
            top_p=self._config.get("autocomplete", "top_p"),
            debounce_ms=self._config.get("autocomplete", "debounce_ms"),
            allow_in_strings=self._config.get("autocomplete", "allow_in_strings"),
            llm_first=self._config.get("autocomplete", "llm_first"),
        )

    def reload_settings(self) -> None:
        self._engine.shutdown()
        self._engine = AutocompleteEngine(self._read_settings())
        self._engine.suggestion_ready.connect(self._on_suggestion)
        self._engine.status.connect(self._on_status)
        self._engine.error.connect(self._on_error)
        self._editor.clear_autocomplete()

    @Slot()
    def _on_text_changed(self) -> None:
        settings = self._read_settings()
        if not settings.enabled:
            self._editor.clear_autocomplete()
            return
        self._pending_text = self._editor.toPlainText()
        self._pending_cursor = self._editor.textCursor().position()
        self._editor.clear_autocomplete()
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0
        if not settings.allow_in_strings:
            if self._in_string_or_comment(
                self._pending_text, self._pending_cursor
            ):
                return
        symbol_suggestion = self._symbol_suggestion(
            self._pending_text, self._pending_cursor
        )
        if symbol_suggestion:
            if settings.llm_first:
                self._editor.set_autocomplete_suggestion(symbol_suggestion)
                self._editor.set_status_message("Autocomplete: symbol (pending model)")
                self._fallback_symbol = symbol_suggestion
                self._fallback_prefix = self._pending_text[: self._pending_cursor]
                self._fallback_cursor = self._pending_cursor
            else:
                self._editor.set_autocomplete_suggestion(symbol_suggestion)
                self._editor.set_status_message("Autocomplete: symbol")
                return
        self._timer.start(max(0, settings.debounce_ms))

    @Slot()
    def _on_cursor_changed(self) -> None:
        self._editor.clear_autocomplete()
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0

    @Slot()
    def _send_request(self) -> None:
        settings = self._read_settings()
        if not settings.enabled:
            return
        if not settings.allow_in_strings:
            if self._in_string_or_comment(
                self._pending_text, self._pending_cursor
            ):
                return
        prefix = self._pending_text[: self._pending_cursor]
        self._latest_prefix = prefix
        self._latest_request_id = self._engine.request(prefix, self._pending_cursor)

    @Slot(int, str, int, str)
    def _on_suggestion(
        self, request_id: int, suggestion: str, cursor_pos: int, prefix: str
    ) -> None:
        if request_id != self._latest_request_id:
            return
        current_cursor = self._editor.textCursor().position()
        if cursor_pos != current_cursor:
            return
        if self._editor.toPlainText()[:cursor_pos] != prefix:
            return
        suggestion = self._sanitize_suggestion(suggestion, prefix)
        if not suggestion:
            if (
                self._config.get("autocomplete", "llm_first")
                and
                self._fallback_symbol
                and cursor_pos == self._fallback_cursor
                and prefix == self._fallback_prefix
            ):
                self._editor.set_autocomplete_suggestion(self._fallback_symbol)
                self._editor.set_status_message("Autocomplete: symbol")
                return
            self._editor.clear_autocomplete()
            return
        self._editor.set_autocomplete_suggestion(suggestion)
        self._editor.set_status_message("Autocomplete: model")

    def _sanitize_suggestion(self, suggestion: str, prefix: str) -> str:
        suggestion = suggestion.lstrip("\r\n")
        if not suggestion:
            return ""
        word_prefix, _ = self._word_prefix(prefix, len(prefix))
        if word_prefix:
            suggestion = suggestion.lstrip()
            if not suggestion:
                return ""
            if suggestion.startswith(word_prefix):
                suggestion = suggestion[len(word_prefix):]
                if not suggestion:
                    return ""
            if not re.match(r"[A-Za-z0-9_]", suggestion[0]):
                return ""
        if len(suggestion) > self._max_suggestion_chars:
            suggestion = suggestion[: self._max_suggestion_chars]
        if len(suggestion) > 8:
            unique = set(suggestion)
            if len(unique) == 1:
                return ""
            if all(ch.isdigit() for ch in suggestion):
                return ""
        return suggestion

    @Slot(str)
    def _on_status(self, message: str) -> None:
        self._editor.set_status_message(message)

    @Slot(int, str)
    def _on_error(self, request_id: int, message: str) -> None:
        if request_id == self._latest_request_id:
            self._editor.set_status_message(f"Autocomplete error: {message}")
