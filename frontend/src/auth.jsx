import React from 'react';
import { CircleUserRound, Eye, EyeOff, LogOut, Mail, Phone, BriefcaseBusiness, FileText } from 'lucide-react';

import './auth.css';

// Accounts: the backend keeps the session in an HttpOnly cookie (JavaScript never sees the
// token), so every existing fetch('/api/...') call is sent as the signed-in user automatically.
// This module only tracks WHO is signed in, for the UI.

const AuthContext = React.createContext({ user: null, status: 'loading', setUser: () => {}, signOut: async () => {} });

export function AuthProvider({ children }) {
  const [user, setUser] = React.useState(null);
  const [status, setStatus] = React.useState('loading');

  React.useEffect(() => {
    let ignore = false;
    fetch('/api/auth/me')
      .then((response) => (response.ok ? response.json() : { user: null }))
      .catch(() => ({ user: null }))
      .then((payload) => {
        if (ignore) return;
        setUser(payload?.user || null);
        setStatus('ready');
      });
    return () => {
      ignore = true;
    };
  }, []);

  const signOut = React.useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
      // Full reload, not just setUser(null): conversations, attached document facts and other
      // in-memory state from this account must not stay on screen for whoever uses the browser next.
      try {
        window.sessionStorage.clear();
      } catch {
        // Storage can be unavailable; the reload still clears in-memory state.
      }
      window.location.hash = '#/';
      window.location.reload();
    }
  }, []);

  const value = React.useMemo(() => ({ user, status, setUser, signOut }), [user, status, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return React.useContext(AuthContext);
}

export function accountLabel(user) {
  return user?.email || user?.phone || 'Account';
}

/** Hash link to the sign-in page that returns to `next` (default: the current page) afterwards. */
export function signInHref(mode = 'signin', next = window.location.hash || '#/') {
  const path = mode === 'signup' ? '#/signup' : '#/signin';
  return `${path}?next=${encodeURIComponent(next)}`;
}

function safeNext(value) {
  // Only same-app hash routes -- never an arbitrary URL -- and never back to the sign-in pages.
  if (!value || !value.startsWith('#/') || value.startsWith('#/signin') || value.startsWith('#/signup')) {
    return '#/cases';
  }
  return value;
}

export function AuthForm({ mode, next }) {
  const { user: currentUser, setUser } = useAuth();
  const isSignup = mode === 'signup';
  const [method, setMethod] = React.useState('email');
  const [identifier, setIdentifier] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [status, setStatus] = React.useState('idle');
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    setError('');
    setPassword('');
    setConfirmPassword('');
  }, [mode]);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (!identifier.trim()) {
      setError(isSignup ? `Enter your ${method === 'email' ? 'email address' : 'phone number'}.` : 'Enter your email address or phone number.');
      return;
    }
    if (isSignup && password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (isSignup && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setStatus('submitting');
    try {
      const body = isSignup
        ? { [method]: identifier.trim(), password }
        : { identifier: identifier.trim(), password };
      const response = await fetch(isSignup ? '/api/auth/signup' : '/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.user) {
        throw new Error(payload?.detail || (isSignup ? 'Could not create your account.' : 'Could not sign you in.'));
      }
      window.location.hash = safeNext(next);
      if (currentUser && currentUser.id !== payload.user.id) {
        // Switched accounts without signing out first: reload so nothing from the previous
        // account stays in memory (same reason signOut() reloads).
        window.location.reload();
        return;
      }
      setUser(payload.user);
    } catch (submitError) {
      setError(submitError.message || 'Something went wrong. Please try again.');
      setStatus('idle');
    }
  };

  const nextParam = next ? `?next=${encodeURIComponent(next)}` : '';

  return (
    <form className="auth-card" onSubmit={submit} noValidate>
      <h3>{isSignup ? 'Create your account' : 'Sign in'}</h3>
      <p className="auth-card-lead">
        {isSignup
          ? 'Save your conversations and documents privately, and pick them up again from any device.'
          : 'Welcome back. Your saved cases and documents are waiting.'}
      </p>

      {isSignup && (
        <div className="auth-method-toggle" role="radiogroup" aria-label="Sign up with">
          <button
            type="button"
            role="radio"
            aria-checked={method === 'email'}
            className={method === 'email' ? 'is-active' : ''}
            onClick={() => { setMethod('email'); setIdentifier(''); }}
          >
            <Mail size={16} strokeWidth={1.8} /> Email
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={method === 'phone'}
            className={method === 'phone' ? 'is-active' : ''}
            onClick={() => { setMethod('phone'); setIdentifier(''); }}
          >
            <Phone size={16} strokeWidth={1.8} /> Phone number
          </button>
        </div>
      )}

      <label className="auth-field">
        <span>{isSignup ? (method === 'email' ? 'Email address' : 'Phone number') : 'Email or phone number'}</span>
        <input
          value={identifier}
          onChange={(event) => setIdentifier(event.target.value)}
          type={isSignup && method === 'email' ? 'email' : isSignup ? 'tel' : 'text'}
          inputMode={isSignup && method === 'phone' ? 'tel' : undefined}
          autoComplete={isSignup ? (method === 'email' ? 'email' : 'tel') : 'username'}
          placeholder={isSignup ? (method === 'email' ? 'you@example.com' : '98765 43210') : 'you@example.com or 98765 43210'}
          autoFocus
        />
        {isSignup && method === 'phone' && (
          <small>Indian mobile numbers can be entered without +91. For other countries, include the country code.</small>
        )}
      </label>

      <label className="auth-field">
        <span>Password</span>
        <div className="auth-password-input">
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type={showPassword ? 'text' : 'password'}
            autoComplete={isSignup ? 'new-password' : 'current-password'}
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            title={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        </div>
        {isSignup && <small>At least 8 characters.</small>}
      </label>

      {isSignup && (
        <label className="auth-field">
          <span>Confirm password</span>
          <input
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
          />
        </label>
      )}

      {error && <p className="auth-error" role="alert">{error}</p>}

      <button type="submit" className="case-open-button auth-submit" disabled={status === 'submitting'}>
        {status === 'submitting' ? (isSignup ? 'Creating account...' : 'Signing in...') : (isSignup ? 'Create account' : 'Sign in')}
      </button>

      <p className="auth-switch">
        {isSignup ? 'Already have an account? ' : 'New here? '}
        <a href={`${isSignup ? '#/signin' : '#/signup'}${nextParam}`}>{isSignup ? 'Sign in' : 'Create an account'}</a>
      </p>
    </form>
  );
}

/** Header control: "Sign in" for guests; an account menu (with sign out) when signed in. */
export function AccountMenu() {
  const { user, status, signOut } = useAuth();
  const [open, setOpen] = React.useState(false);
  const menuRef = React.useRef(null);

  React.useEffect(() => {
    if (!open) return undefined;
    const handlePointer = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false);
    };
    const handleKey = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  if (status === 'loading') {
    return (
      <div className="avatar" aria-hidden="true">
        <CircleUserRound size={20} strokeWidth={1.6} />
      </div>
    );
  }

  if (!user) {
    return (
      <a className="account-signin-link" href={signInHref()}>
        Sign in
      </a>
    );
  }

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        type="button"
        className="avatar account-avatar-button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account: ${accountLabel(user)}`}
        title={accountLabel(user)}
        onClick={() => setOpen((current) => !current)}
      >
        <CircleUserRound size={20} strokeWidth={1.6} />
      </button>
      {open && (
        <div className="account-dropdown" role="menu">
          <p className="account-dropdown-label">Signed in as</p>
          <p className="account-dropdown-identity">{accountLabel(user)}</p>
          <a role="menuitem" href="#/cases" onClick={() => setOpen(false)}>
            <BriefcaseBusiness size={16} strokeWidth={1.8} /> My Cases
          </a>
          <a role="menuitem" href="#/documents" onClick={() => setOpen(false)}>
            <FileText size={16} strokeWidth={1.8} /> Documents
          </a>
          <button type="button" role="menuitem" onClick={signOut}>
            <LogOut size={16} strokeWidth={1.8} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
