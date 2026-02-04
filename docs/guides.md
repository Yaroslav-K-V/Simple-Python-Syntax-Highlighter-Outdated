# Guides and Troubleshooting

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
**Weights not found**
- Ensure the weights file is named `model.safetensors` or `pytorch_model.bin`.
- Confirm the model folder has `config.json` and tokenizer files.

## Release Tag Script
The script `scripts/new_random_tag.bat`:
- Generates a random `vXXXXXX` tag
- Prompts for a title and description (stored in an annotated tag)
- Pushes the tag to `origin`
- Optionally pushes the current branch (`git push -u origin <branch>`)

**Slow or freezing UI**
- Increase debounce and lower max tokens.
- Ensure autocomplete is running on CPU only if no GPU is available.

**Autocomplete inside strings**
- Use the "Allow suggestions in strings/comments" toggle in settings.
