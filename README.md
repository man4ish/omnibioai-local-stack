# OmniBioAI Local Development Workspace

This repository defines a **local development workspace and orchestration layer** for the **OmniBioAI ecosystem**, including workflow execution, tool services, LIMS integration, and AI-driven bioinformatics applications.

All services are designed to run **locally**, **without mandatory cloud dependencies**, using a shared workspace layout and reproducible startup scripts.

> **Important**
>
> This repository does **not** vendor or embed application source code.
> Each major component lives in its **own GitHub repository** and is referenced here explicitly.

---

## Workspace Layout

```
Desktop/machine/
├── omnibioai/                 # OmniBioAI Workbench (Django)
├── omnibioai-tool-exec/       # TES – Tool Execution Service
├── omnibioai-toolserver/      # FastAPI ToolServer (Enrichr, BLAST, etc.)
├── lims-x/                    # LIMS-X (Laboratory Information Management)
├── ragbio/                    # RAG-based Bioinformatics Assistant
├── utils/
│   └── kill_port.sh           # Utility to free busy ports
├── smoke_test_stack.sh        # Health checks for the full stack
├── start_stack_tmux.sh        # One-command stack launcher (tmux)
├── backup/                    # Archived / experimental work
└── ai-dev-docker/             # Docker experiments (optional)
```

---

## Canonical Repositories

Each service must be cloned independently. This workspace assumes the following repositories:

| Component                        | Repository                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------------------- |
| **OmniBioAI Workbench**          | [https://github.com/man4ish/omnibioai](https://github.com/man4ish/omnibioai)                       |
| **Tool Execution Service (TES)** | [https://github.com/man4ish/omnibioai-tool-exec](https://github.com/man4ish/omnibioai-tool-exec)   |
| **ToolServer**                   | [https://github.com/man4ish/omnibioai-toolserver](https://github.com/man4ish/omnibioai-toolserver) |
| **LIMS-X**                       | [https://github.com/man4ish/lims-x](https://github.com/man4ish/lims-x)                             |
| **RAGBio**                       | [https://github.com/man4ish/ragbio](https://github.com/man4ish/ragbio)                             |

This repository **only orchestrates** these projects; it does not replace them.

---

## Design Principles

* **Single workspace root**
* **Relative paths only** in registries and metadata
* **No hardcoded absolute paths**
* **Service isolation via ports**
* **tmux-managed lifecycle**
* **Restart-safe startup (ports auto-freed)**

This makes the workspace:

* Portable across machines
* Safe to rename or relocate
* Suitable for Docker, HPC, or VM environments
* Stable across long-running research work

---

## Services & Ports

| Service                      | Repo                   | Default Port | Description                    |
| ---------------------------- | ---------------------- | ------------ | ------------------------------ |
| OmniBioAI Workbench          | `omnibioai`            | `8000`       | Django UI, plugins, registries |
| TES (Tool Execution Service) | `omnibioai-tool-exec`  | `8080`       | Workflow & tool execution      |
| ToolServer                   | `omnibioai-toolserver` | `9090`       | FastAPI tool APIs              |
| LIMS-X                       | `lims-x`               | `7000`       | LIMS integration (placeholder) |

All ports are configurable via environment variables.

---

## One-Command Startup (Recommended)

Start the entire stack with:

```bash
bash start_stack_tmux.sh
```

This script:

1. Frees required ports
2. Creates a fresh `tmux` session
3. Starts:

   * TES
   * ToolServer (via `uvicorn`)
   * OmniBioAI Workbench
   * LIMS-X (stub / placeholder)
4. Runs smoke tests automatically

Attach to the session:

```bash
tmux attach -t omnibioai
```

---

## tmux Window Layout

| Window       | Purpose                |
| ------------ | ---------------------- |
| `tes`        | Tool Execution Service |
| `toolserver` | FastAPI ToolServer     |
| `limsx`      | LIMS-X (stub / future) |
| `workbench`  | OmniBioAI Django app   |
| `smoke`      | Health checks          |

Each service runs independently and can be restarted without impacting others.

---

## Startup Script Behavior

`start_stack_tmux.sh`:

* Uses `utils/kill_port.sh` to avoid port conflicts
* Is fully restartable
* Supports environment overrides:

```bash
TES_PORT=8081 WORKBENCH_PORT=9000 bash start_stack_tmux.sh
```

---

## Health & Smoke Tests

After startup, `smoke_test_stack.sh` validates:

* TES `/health`
* ToolServer `/health`
* OmniBioAI root page
* Core APIs reachable

Manual run:

```bash
bash smoke_test_stack.sh
```

---

## Path Handling Policy (Important)

All persisted paths in **OmniBioAI**, **LIMS-X**, and related services must be:

✅ Relative to workspace root
❌ Absolute paths like `/home/manish/...`

Example (correct):

```json
{
  "path": "omnibioai/work/results/run_001"
}
```

Resolution happens at runtime via the workspace root.

This guarantees:

* Portability
* Safe repo renames
* Docker/HPC compatibility
* Stable object registries

---

## Repository Renaming Notes (Historical)

The following renames were performed cleanly (local + remote):

| Old Name                       | New Name    |
| ------------------------------ | ----------- |
| `omnibioai_workbench`          | `omnibioai` |
| `LIMS-X`                       | `lims-x`    |
| `rag-gene-discovery-assistant` | `ragbio`    |

All internal references were updated to avoid legacy paths.

---

## Intended Usage

This workspace is designed for:

* **Local development**
* **Cross-service integration testing**
* **Workflow execution via TES**
* **AI-assisted analysis (RAGBio + agentic workflows)**

Future directions include:

* Docker Compose
* Kubernetes
* HPC deployments

---

## Quick Debug Commands

```bash
# Check ports
lsof -i :8000
lsof -i :8080
lsof -i :9090

# Restart everything
bash start_stack_tmux.sh

# Attach to logs
tmux attach -t omnibioai
```

---

## Status

✅ Clean workspace
✅ No hardcoded absolute paths
✅ Independent services
✅ Fully reproducible local stack

This repository now acts as a **stable control plane** for the OmniBioAI local ecosystem.

