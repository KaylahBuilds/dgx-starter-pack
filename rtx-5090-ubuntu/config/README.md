# RTX 5090 Ubuntu Configuration

This folder is reserved for versioned, non-sensitive configuration for the
RTX 5090 Ubuntu host. There is no active configuration or automatic installer yet.

Before adding a template, record:

- Ubuntu release, kernel, and CPU architecture.
- GPU driver and model-serving runtime versions.
- Any CUDA dependencies required by the selected runtime.
- Model format, local model location, and storage requirements.
- Local service settings and the intended network boundaries.

Use clearly labeled example files and placeholders for machine-specific values.
Keep credentials in ignored local `.env` files; do not commit tokens, private
addresses, model weights, or raw machine logs.

Validate templates on this Ubuntu host before documenting them as supported.
