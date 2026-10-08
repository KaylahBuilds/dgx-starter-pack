# DGX Spark Configuration

This folder is reserved for versioned, non-sensitive DGX Spark configuration.
There is no active configuration or automatic installer yet.

Before adding a template, record:

- Operating system release and CPU architecture.
- GPU driver and model-serving runtime versions.
- Model format, local model location, and storage requirements.
- Local service settings and the intended network boundaries.

Use clearly labeled example files and placeholders for machine-specific values.
Keep credentials in ignored local `.env` files; do not commit tokens, private
addresses, model weights, or raw machine logs.

Validate templates on the DGX Spark before documenting them as supported.
