# Architecture and offline execution

## Process model

Avalonia/.NET 10 UI → bundled Python worker → Marker 2 / Surya → CPU layout/error models and llama.cpp OCR. The GUI sends a request JSON file and receives JSON Lines on stdout. Technical library messages go to a per-run stderr log. UI progress reports completed files, with an indeterminate state during startup.

The original Streamlit application is independent and unchanged except for its earlier missing-Gemini-key guidance. Existing UdpSim code is not involved.

## Offline controls

- All model paths are absolute paths relative to the installed engine directory. No dependence on the build user's Hugging Face or Datalab caches.
- HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE enabled. Included Python sitecustomize refuses external socket connections and non-local DNS lookups in the worker and its Python subprocesses. Loopback communication between local OCR services remains allowed.
- Native llama.cpp is given local GGUF/MMProj files directly. No URL/model-download arguments.
- External LLM settings are not exposed; use_llm is forced false. User API keys and inference-server URL overrides are cleared.
- Each run has an isolated server-sentinel/log directory to avoid attaching to unrelated Marker instances. Servers bind to loopback.
- The policy is an application-level guard, not an OS security boundary. Network isolation and organization controls remain the deployment environment's responsibility. Python/native dependencies are included as third-party software.

## Reliability

Source files remain unchanged. Results use UUID-suffixed directories to avoid accidental replacement. A failed file generates an error event and the next file continues. Cancellation uses .NET process-tree termination; ordinary exit also cleans model servers up through psutil. User preferences and logs are writable outside the installation directory.

## Local changes

- Marker chunks page indices: use the page segment in `/page/0/Page/6`, not the final internal block number.
- Surya server lifecycle: psutil process-tree cleanup, avoiding Windows `os.kill(pid, 0)` behavior.
- Surya sentinels and logs: per-run MARKER_RUNTIME_DIR instead of global home-cache server state.
- UTF-8 protocol and child-process I/O so Korean paths survive Windows code pages.
- Offline Python sitecustomize and environment configuration.

No model weights were modified. Runtime patch source is kept in scripts/prepare_engine.py. Upgrades require rerunning the offline integration suite.
