# Frontend Architecture

This directory now contains the React + TypeScript client that will gradually
replace the legacy Flask templates while we continue to ship the existing UI
from `legacy/`.

## Structure

- `src/` – Vite + React application source (see `src/pages/LandingPage.tsx` for
  the initial authenticated landing page).
- `public/` – Static assets copied verbatim into the final Vite build.
- `legacy/` – Existing Flask templates/static assets that continue to ship
  until the React client replaces them.
- `api/` – Generated API clients or request definitions that should always be
  derived from `../shared/contracts/openapi.yaml`.

## Commands

```bash
# Install node dependencies the first time
npm install

# Vite dev server
npm run dev

# Or run both backend + frontend together
uv run devserver

# Storybook (component-level docs)
npm run storybook

# Type checking + linting
npm run lint

# Production bundle
npm run build
```

All commands above should be executed from `web/frontend/`.

> Tip: running `uv run devserver` from the repo root automatically launches
> both the Flask backend and the Vite dev server, so you don’t need to keep
> two terminals open while iterating on the React UI.

## Env configuration

Frontend-specific runtime values live beside the backend `.env` entries. The
most important ones are:

- `VITE_API_BASE_URL` – base URL for authenticated API calls (defaults to
  `/api`).
- `VITE_AUTH_REDIRECT` – where `PrimaryButton` actions send unauthenticated
  users.
- `VITE_SIGNOUT_URL` – optional URL to hit after sign-out.
- `VITE_FLAG_REACT_LANDING_PAGE` – feature-flag hook so the backend can toggle
  traffic to the new landing page.

## Design system + Storybook

- `@trussworks/react-uswds` powers the component primitives and USWDS Sass
  tokens (`src/theme/uswds-theme.scss`). Wrapper components such as
  `PrimaryButton` and `FormLayout` keep shared styling in one place.
- Storybook is configured with the Vite builder (`.storybook/`) and includes
  addons for essentials, a11y, viewport testing, and interactions. See
  `src/stories/` for the initial docs covering the landing page and button.

## Working with the legacy UI

The Flask backend still serves templates from `legacy/templates` and static
files from `legacy/static`. Keep any Jinja-specific changes isolated to this
folder so they can be removed cleanly once the React client ships. React
components can talk to existing routes so long as they honor the shared
authentication provider (`src/providers/AuthProvider.tsx`).
