# ContentExtractor

ContentExtractor turns a URL, a saved social post, or a research topic into small, reviewable improvement proposals. Each proposal is classified, given a recommendation, and routed to the repository that owns the work; the application keeps a queue and never changes another repository directly.

## Features

- Ingest links, saved-content exports, and research topics through the Life learning pipeline.
- Review, adopt, or reject proposals in a FastAPI API and React dashboard.
- Keep proposals, content, and decisions separated by Life instance.
- Import queued links from another device without losing their instance attribution.

## Requirements

- Python 3.13
- Node.js 20 and npm
- A checkout of the Life framework next to this repository (`../Life`), including its `learn-core`, `shared`, and `backend-core` packages

## Quickstart

Clone this repository and the Life framework side by side, then create local configuration from the example:

```sh
git clone <this-repository-url> ContentExtractor
git clone "${LIFE_FRAMEWORK_REPO:-https://github.com/example/suite-life.git}" Life
cd ContentExtractor
cp .env.example .env

python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt \
  -e ../Life/packages/shared \
  -e ../Life/packages/backend-core \
  -e ../Life/packages/learn-core
(cd backend && .venv/bin/python -m content_extractor_backend)
```

In another terminal, start the dashboard:

```sh
cd frontend
npm ci
npm run dev
```

For a prebuilt container image, copy `.env.example` to `.env` and run `docker compose -f deploy/docker-compose.example.yml up`.

## Tests

The backend needs the adjacent Life checkout:

```sh
(cd backend && PYTHONPATH=. ../backend/.venv/bin/python -m pytest)
(cd frontend && npm ci && npm test -- --pool=forks --poolOptions.forks.maxForks=2 --poolOptions.forks.minForks=1 && npm run build)
```

The GitHub workflow checks out the framework as `Life` beside this repository and runs both suites.

## Configuration

| Variable | Purpose |
| --- | --- |
| `AI_BACKEND` | Selects the AI backend. |
| `LEARN_LLM_LETTURA` | Selects the image-reading backend. |
| `LIFE_FRAMEWORK_ROOT` | Overrides the adjacent Life framework path. |
| `LIFE_HOME` | Location of the Life instance registry. |
| `LIFE_INSTANCE` | Default instance for new queue records. |
| `LEARN_QUEUE_ROOT` | Location of the local proposal queue. |
| `LEARN_REPOS_DIR` | Repositories available as proposal targets. |
| `DATABASE_URL` | Optional database URL for framework services. |
| `VITE_BACKEND_PROXY_TARGET` | Dashboard API proxy URL during development. |
| `INGEST_REMOTE_BOXES` | Semicolon-separated remote ingest mailbox definitions. |
| `INSTAGRAM_COOKIES_FILE` | Optional cookie file for permitted Instagram reads. |
| `VIDEO_UNDERSTAND_SCRIPT` | Optional local video-processing helper. |

## License

MIT. See [LICENSE](LICENSE).
