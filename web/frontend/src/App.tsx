import { LandingPage } from './pages/LandingPage';
import { useAuth } from './providers/AuthProvider';

export default function App() {
  const { isAuthenticated, signOut, loading } = useAuth();

  if (loading) {
    return (
      <div className="usa-section text-center">
        <p className="usa-intro">Loading your workspace…</p>
      </div>
    );
  }

  return <LandingPage isAuthenticated={isAuthenticated} onSignOut={signOut} />;
}
