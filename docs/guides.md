# Guides and Troubleshooting

## Configuration

Settings are stored in `~/.pyglow/settings.json` and created
automatically on first run. You can edit them through **View > Settings** or
manually in the JSON file.

Key sections:

| Section | Settings |
|---|---|
| `editor` | `font_family`, `font_size`, `tab_size`, `use_spaces`, `show_line_numbers` |
| `appearance` | `theme` (`auto`, `dark`, `light`) |
| `files` | `trim_whitespace`, `last_opened` |
| `autocomplete` | `enabled`, `model_dir`, `device`, `max_new_tokens`, `context_tokens`, `debounce_ms`, `temperature` |

## Performance Tuning (CPU)

- Lower **Max new tokens** (16-24 is usually enough).
- Increase **Debounce** (150-300 ms).
- Reduce **Context tokens** to avoid slow generation.
- Disable **Allow suggestions in strings/comments** if suggestions feel noisy.

## Suggestion Quality

- Prefer symbol completions when available (default behavior).
- If suggestions are nonsensical, reduce max tokens and keep temperature at 0.
- Consider a larger model if latency allows.

## Common Errors

**Autocomplete unavailable**

- The editor works without `torch` and `transformers` installed.
  Autocomplete is simply disabled.
- If you have the dependencies but autocomplete still fails, check that
  the model directory exists and contains `config.json` + weight files.

**Weights not found**

- Ensure the weights file is named `model.safetensors` or `pytorch_model.bin`.
- Confirm the model folder has `config.json` and tokenizer files.

**Slow or freezing UI**

- Increase debounce and lower max tokens.
- Ensure autocomplete is running on CPU only if no GPU is available.

**Autocomplete inside strings**

- Use the "Allow suggestions in strings/comments" toggle in Settings.
