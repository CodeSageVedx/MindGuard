# Contributing to MindGuard AI

Thank you for helping improve MindGuard. This project touches **sensitive mental health use cases**; contributions should prioritize **user safety**, **privacy**, and **honest scope** (no implied clinical licensure).

---

## Ways to contribute

- **Code:** Bug fixes, tests, Express ↔ FastAPI integration (replacing chat placeholders), ingestion tooling for the knowledge base, graph hardening.  
- **Docs:** README, architecture diagrams, runbooks for deployment and crisis escalation.  
- **Safety:** Safer defaults, clearer disclaimers, improved logging without leaking PII.  
- **Issues:** Repro steps, expected behavior, and risk/safety notes for counseling-related bugs.

---

## Before you start

1. Read **[README.md](./README.md)** (problem scope, limitations) and **[ARCHITECTURE.md](./ARCHITECTURE.md)**.  
2. Do **not** commit real **API keys**, **JWT secrets**, **phone numbers**, or **user transcripts**. Use `.env` locally and example placeholders in docs.  
3. If your change affects **counseling behavior** or **risk routing**, describe the **safety impact** in the PR and prefer small, reviewable diffs.

---

## Development setup

- **Server:** `cd Server && npm install && npm run dev`  
- **Server-AI:** Python venv, `pip install -r requirements.txt`, `uvicorn src.main:app --reload`  
- **client:** `cd client && npm install && npm run dev`  
- **Qdrant (optional):** `cd Server-AI && docker compose up -d`

Configure environment variables to match `Server-AI/src/config.py` and your local MongoDB.

---

## Branching and pull requests

- Branch from `main` (or the repo’s default branch) using a short descriptive name, e.g. `fix/chat-ai-wire`, `docs/architecture-rag`.  
- One PR should ideally address **one concern** (feature *or* refactor *or* docs).  
- PR description should explain **what**, **why**, and any **manual test steps**.  
- Link related issues when applicable.

---

## Code style

### TypeScript (`Server/`, `client/`)

- Match existing patterns: ES modules, path aliases as already used in the repo.  
- Run the client linter when you touch UI: `npm run lint` in `client/`.  
- Prefer explicit types on new public APIs.

### Python (`Server-AI/`)

- Follow **PEP 8** spacing and naming; keep functions focused.  
- Use existing `settings` from `src.config` for configuration—avoid new bare `os.environ` reads unless consistent with the file.  
- Prefer **async** endpoints and graph calls consistent with `routes.py`.

---

## AI and safety review checklist

For changes under `Server-AI/src/agents/` or prompt-heavy modules:

- [ ] Crisis / high-risk path still reachable when signals warrant it.  
- [ ] No new prompts that claim **diagnosis** or **prescription** authority.  
- [ ] Logging does not print **raw user text** at INFO in production code paths.  
- [ ] Third-party calls fail **gracefully** with safe user-facing errors.

---

## Community standards

Be respectful and assume good intent. Harassment, hate, or abusive behavior in issues or PRs is not acceptable. Keep discussion focused on improving the product and documentation.

---

## License

By contributing, you agree your contributions are licensed under the same terms as the project (**[LICENSE](./LICENSE)**).
