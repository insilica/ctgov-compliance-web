# Frontend Architecture

This directory contains everything required to migrate the UI to a modern React +
TypeScript stack while still serving the existing Flask templates from
`legacy/`.

## Structure

- `src/` – Source for the future React SPA (scaffolded but not yet implemented).
- `public/` – Static assets injected by Vite/Next.js during builds.
- `legacy/` – Existing Flask templates and static assets that continue to ship
  until the React client replaces them.
- `api/` – Generated API clients or request definitions that should always be
  derived from `../shared/contracts/openapi.yaml`.

## Tech stack goals

1. React 18+ with TypeScript for type-safe UI development.
2. Vite as the default dev server/bundler (swap to Next.js if routing/SSR is
   required).
3. OpenAPI-driven clients so data contracts stay in sync with the backend.

## Working with the legacy UI

The Flask backend now serves templates from `legacy/templates` and static files
from `legacy/static`. Keep any Jinja-specific changes isolated to this folder
so they can be deleted cleanly once the React client ships.

## Consuming backend APIs

Backend routes are documented in `../shared/contracts/openapi.yaml`. Use that
file to generate typed clients (e.g., with `openapi-typescript-codegen`) and
commit the outputs inside `api/`.
