import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { appEnv } from '../config/env';

type OrganizationMembership = {
  id: number;
  name: string;
  role?: string;
};

type UserProfile = {
  id?: number;
  email: string;
  name: string;
  roles: string[];
  organizations?: OrganizationMembership[];
};

type AuthContextValue = {
  currentUser?: UserProfile;
  isAuthenticated: boolean;
  loading: boolean;
  refresh: () => Promise<void>;
  signIn: (profile: UserProfile) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = 'ctgov-compliance::auth';

function readFromStorage(): UserProfile | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }

  const value = sessionStorage.getItem(STORAGE_KEY);
  return value ? (JSON.parse(value) as UserProfile) : undefined;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<UserProfile | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setCurrentUser(readFromStorage());
    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${appEnv.apiBaseUrl}/auth/session`, {
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status !== 401) {
          console.warn('Auth refresh failed', response.status);
        }
        setCurrentUser(undefined);
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem(STORAGE_KEY);
        }
        return;
      }

      const body = (await response.json()) as { user: UserProfile };
      setCurrentUser(body.user);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(body.user));
      }
    } catch (error) {
      console.error('Failed to refresh auth state', error);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback((profile: UserProfile) => {
    setCurrentUser(profile);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await fetch(`${appEnv.apiBaseUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.warn('Failed to call logout endpoint', error);
    }
    setCurrentUser(undefined);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    if (appEnv.signOutUrl && typeof window !== 'undefined') {
      window.location.assign(appEnv.signOutUrl);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      currentUser,
      isAuthenticated: Boolean(currentUser),
      loading,
      refresh,
      signIn,
      signOut,
    }),
    [currentUser, loading, refresh, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error('useAuth must be used inside of an AuthProvider');
  }

  return ctx;
}
