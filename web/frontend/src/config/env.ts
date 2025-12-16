const { VITE_API_BASE_URL, VITE_AUTH_REDIRECT, VITE_SIGNOUT_URL, VITE_FLAG_REACT_LANDING_PAGE } =
  import.meta.env;

export const appEnv = {
  apiBaseUrl: VITE_API_BASE_URL ?? '/api',
  authRedirect: VITE_AUTH_REDIRECT ?? '/login',
  signOutUrl: VITE_SIGNOUT_URL,
  featureFlags: {
    reactLandingPage: VITE_FLAG_REACT_LANDING_PAGE === 'true',
  },
} as const;
