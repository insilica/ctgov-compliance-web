import { Alert, Label, TextInput } from '@trussworks/react-uswds';
import type { FormEvent } from 'react';
import { useState } from 'react';
import { appEnv } from '../config/env';
import { useAuth } from '../providers/AuthProvider';
import { PrimaryButton } from './PrimaryButton';

type Status = 'idle' | 'success' | 'error';

export function SignInPanel() {
  const { refresh } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState<string>();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus('idle');
    setMessage(undefined);

    try {
      const response = await fetch(`${appEnv.apiBaseUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const body = (await response.json().catch(() => undefined)) as { message?: string } | undefined;

      if (!response.ok) {
        setStatus('error');
        setMessage(body?.message ?? 'Invalid credentials.');
        return;
      }

      await refresh();
      setEmail('');
      setPassword('');
      setStatus('success');
      setMessage('Signed in successfully.');
    } catch (error) {
      console.error('Sign in failed', error);
      setStatus('error');
      setMessage('Unable to sign in right now. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="sign-in-panel usa-card">
      <div className="usa-card__body">
        <h3 className="margin-top-0">Sign in</h3>
        {status !== 'idle' && message && (
          <Alert type={status === 'success' ? 'success' : 'error'} slim headingLevel="h4">
            {message}
          </Alert>
        )}
        <form className="margin-top-2" onSubmit={handleSubmit}>
          <div className="usa-form-group">
            <Label htmlFor="sign-in-email">Email</Label>
            <TextInput
              id="sign-in-email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="usa-form-group">
            <Label htmlFor="sign-in-password">Password</Label>
            <TextInput
              id="sign-in-password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="display-flex flex-justify-between flex-wrap margin-bottom-2">
            <a className="usa-link" href="/register">
              Create an account
            </a>
            <a className="usa-link" href="/reset">
              Forgot password?
            </a>
          </div>
          <PrimaryButton
            type="submit"
            isLoading={isSubmitting}
            disabled={isSubmitting || !email || !password}
          >
            Sign in
          </PrimaryButton>
        </form>
      </div>
    </div>
  );
}
