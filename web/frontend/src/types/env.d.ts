interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AUTH_REDIRECT?: string;
  readonly VITE_SIGNOUT_URL?: string;
  readonly VITE_FLAG_REACT_LANDING_PAGE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
