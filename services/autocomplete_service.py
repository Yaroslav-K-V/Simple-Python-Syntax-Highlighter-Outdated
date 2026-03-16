"""Local autocomplete engine using a local Qwen model."""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
)
from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer

from models.autocomplete_model import AutocompleteModel


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
    llm_enabled: bool
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
    slow_mode_ms: int


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

    slow_mode_changed = Signal(bool, int)
    # Emitted instead of calling editor methods directly
    suggestion_ready = Signal(str)      # text to show as ghost suggestion
    autocomplete_cleared = Signal()     # request to clear ghost text
    status_updated = Signal(str)        # status bar message

    def __init__(self, editor, config) -> None:
        super().__init__(editor)
        self._editor = editor
        self._config = config
        self._ac_model = AutocompleteModel()
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
        self._latest_request_started = 0.0
        self._latest_prefix = ""
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0
        self._slow_mode_active = False

        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.cursorPositionChanged.connect(self._on_cursor_changed)

    def _read_settings(self) -> AutocompleteSettings:
        model_dir = self._config.get("autocomplete", "model_dir")
        if not os.path.isabs(model_dir):
            model_dir = os.path.abspath(model_dir)
        return AutocompleteSettings(
            enabled=self._config.get("autocomplete", "enabled"),
            llm_enabled=self._config.get("autocomplete", "llm_enabled"),
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
            slow_mode_ms=self._config.get("autocomplete", "slow_mode_ms"),
        )

    def reload_settings(self) -> None:
        self._engine.shutdown()
        self._engine = AutocompleteEngine(self._read_settings())
        self._engine.suggestion_ready.connect(self._on_suggestion)
        self._engine.status.connect(self._on_status)
        self._engine.error.connect(self._on_error)
        self.autocomplete_cleared.emit()
        self._set_slow_mode(False, 0)

    def refresh_settings(self) -> None:
        """Update settings without recreating the engine."""
        settings = self._read_settings()
        self._engine.update_settings(settings)
        self.autocomplete_cleared.emit()
        self._set_slow_mode(False, 0)

    @Slot()
    def _on_text_changed(self) -> None:
        settings = self._read_settings()
        if not settings.enabled:
            self.autocomplete_cleared.emit()
            self._set_slow_mode(False, 0)
            return
        self._pending_text = self._editor.toPlainText()
        self._pending_cursor = self._editor.textCursor().position()
        self.autocomplete_cleared.emit()
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0
        if not settings.allow_in_strings:
            if self._ac_model.is_in_string_or_comment(
                self._pending_text, self._pending_cursor
            ):
                return
        symbol_suggestion = self._ac_model.symbol_suggestion(
            self._pending_text, self._pending_cursor
        )
        if symbol_suggestion:
            if settings.llm_first and settings.llm_enabled:
                self.suggestion_ready.emit(symbol_suggestion)
                self.status_updated.emit("Autocomplete: symbol (LLM pending)")
                self._fallback_symbol = symbol_suggestion
                self._fallback_prefix = self._pending_text[: self._pending_cursor]
                self._fallback_cursor = self._pending_cursor
            else:
                self.suggestion_ready.emit(symbol_suggestion)
                if settings.llm_enabled:
                    self.status_updated.emit("Autocomplete: symbol")
                else:
                    self.status_updated.emit("Autocomplete: symbol (LLM off)")
                return
        if not settings.llm_enabled:
            self._set_slow_mode(False, 0)
            return
        self._timer.start(max(0, settings.debounce_ms))

    @Slot()
    def _on_cursor_changed(self) -> None:
        self.autocomplete_cleared.emit()
        self._fallback_symbol = ""
        self._fallback_prefix = ""
        self._fallback_cursor = 0

    @Slot()
    def _send_request(self) -> None:
        settings = self._read_settings()
        if not settings.enabled:
            return
        if not settings.llm_enabled:
            self._set_slow_mode(False, 0)
            return
        if not settings.allow_in_strings:
            if self._ac_model.is_in_string_or_comment(
                self._pending_text, self._pending_cursor
            ):
                return
        prefix = self._pending_text[: self._pending_cursor]
        self._latest_prefix = prefix
        if not self._fallback_symbol:
            self.status_updated.emit("Autocomplete: model (pending)")
        self._latest_request_started = time.monotonic()
        self._latest_request_id = self._engine.request(prefix, self._pending_cursor)

    @Slot(int, str, int, str)
    def _on_suggestion(
        self, request_id: int, suggestion: str, cursor_pos: int, prefix: str
    ) -> None:
        if request_id != self._latest_request_id:
            return
        settings = self._read_settings()
        if not settings.enabled or not settings.llm_enabled:
            return
        elapsed_ms = self._record_latency_ms()
        current_cursor = self._editor.textCursor().position()
        if cursor_pos != current_cursor:
            return
        if self._editor.toPlainText()[:cursor_pos] != prefix:
            return
        suggestion = self._ac_model.sanitize_suggestion(suggestion, prefix, self._max_suggestion_chars)
        if not suggestion:
            if (
                settings.llm_first
                and self._fallback_symbol
                and cursor_pos == self._fallback_cursor
                and prefix == self._fallback_prefix
            ):
                self.suggestion_ready.emit(self._fallback_symbol)
                self.status_updated.emit("Autocomplete: symbol")
                if elapsed_ms is not None:
                    self._update_slow_mode(elapsed_ms)
                return
            self.autocomplete_cleared.emit()
            if elapsed_ms is not None:
                self._update_slow_mode(elapsed_ms)
            return
        self.suggestion_ready.emit(suggestion)
        if elapsed_ms is not None:
            self._update_slow_mode(elapsed_ms)
            self.status_updated.emit(self._format_model_status(elapsed_ms))
        else:
            self.status_updated.emit("Autocomplete: model")

    def _record_latency_ms(self) -> int | None:
        if self._latest_request_started <= 0:
            return None
        elapsed = time.monotonic() - self._latest_request_started
        return int(elapsed * 1000)

    def _update_slow_mode(self, elapsed_ms: int) -> None:
        settings = self._read_settings()
        self._set_slow_mode(elapsed_ms >= settings.slow_mode_ms, elapsed_ms)

    def _set_slow_mode(self, active: bool, elapsed_ms: int) -> None:
        if active != self._slow_mode_active or active:
            self._slow_mode_active = active
            self.slow_mode_changed.emit(active, elapsed_ms)

    def _format_model_status(self, elapsed_ms: int) -> str:
        if elapsed_ms >= self._read_settings().slow_mode_ms:
            if elapsed_ms >= 1000:
                return f"Autocomplete: model (slow {elapsed_ms / 1000:.1f}s)"
            return f"Autocomplete: model (slow {elapsed_ms}ms)"
        return "Autocomplete: model"

    @Slot(str)
    def _on_status(self, message: str) -> None:
        self.status_updated.emit(message)

    @Slot(int, str)
    def _on_error(self, request_id: int, message: str) -> None:
        if request_id == self._latest_request_id:
            self._set_slow_mode(False, 0)
            self.status_updated.emit(f"Autocomplete: model error: {message}")
