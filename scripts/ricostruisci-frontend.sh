#!/usr/bin/env bash
# Ricostruisce il frontend servito dal servizio systemd. `vite preview` legge
# dist/ a ogni richiesta: non serve riavviare niente, basta Ctrl+F5.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend"
npx vite build
