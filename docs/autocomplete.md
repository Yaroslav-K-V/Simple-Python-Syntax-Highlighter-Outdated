# Autocomplete Setup

Autocomplete runs fully offline using a local model compatible with
`transformers` (causal language model).

## Required Files
Place the model files in a single folder (default: `model/`). The folder must
include:
- `config.json`
- `tokenizer.json` or `tokenizer.model`
- `tokenizer_config.json`
- `generation_config.json` (optional but recommended)
- `merges.txt` + `vocab.json` (if using a BPE tokenizer)
- Weights: `model.safetensors` or `pytorch_model.bin`

If your weights have a different name, rename them to `model.safetensors` for
the simplest setup.

## Install Dependencies

```bash
pip install torch transformers safetensors
```

## Enable in the App
Open **Settings → Autocomplete**:
- Enable autocomplete
- Set **Model folder**
- Choose **Device** (CPU/CUDA/Auto)
- Adjust **Max new tokens**, **Context tokens**, **Debounce**
- Toggle **Allow suggestions in strings/comments**

## How Suggestions Work
Autocomplete is hybrid:
- Fast symbol suggestions from the current file, keywords, and builtins
- LLM suggestions only when no symbol completion is available

Tab accepts the suggestion. Esc dismisses it.
