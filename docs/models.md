# Model Variants

This app works with local, transformers-compatible causal language models
(`AutoModelForCausalLM`) stored in a local folder.

## Size Tiers (Rules of Thumb)
- Small (<= 1B parameters): fast on CPU, lower quality.
- Medium (1B-3B): better code quality, slower on CPU.
- Large (7B+): best quality, usually too slow on CPU.

## Picking a Model
Choose based on your hardware and latency goals:
- CPU-only: prefer smaller models and reduce max tokens.
- GPU available: medium models become viable.
- If quality matters most: use a larger code-tuned model and expect higher
  latency.

## Compatibility Checklist
Before using a model, ensure:
- It is a causal LM (not encoder-only).
- The folder includes tokenizer + config files.
- The weights file is named `model.safetensors` or `pytorch_model.bin`.
- The tokenizer supports Python code reasonably well (code-tuned models are
  preferred).

## Notes
Small models can produce weak suggestions. Hybrid autocomplete mitigates this
by prioritizing deterministic symbol completions.
