import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Button } from '../common/Button';
import styles from './AuthDialog.module.css';

export type AuthMode = 'login' | 'signup';

interface AuthDialogProps {
  isOpen: boolean;
  mode: AuthMode;
  onClose: () => void;
  onModeChange: (mode: AuthMode) => void;
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (
    username: string,
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>;
}

export function AuthDialog({
  isOpen,
  mode,
  onClose,
  onModeChange,
  onLogin,
  onRegister,
}: AuthDialogProps) {
  const reducedMotion = usePrefersReducedMotion();
  const id = useId();
  const loginUsernameRef = useRef<HTMLInputElement | null>(null);
  const signupNameRef = useRef<HTMLInputElement | null>(null);

  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupUsername, setSignupUsername] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lock scroll and handle Escape key
  useEffect(() => {
    if (!isOpen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen, onClose]);

  // Auto-focus the first field when the dialog opens
  useEffect(() => {
    if (!isOpen) return;
    const target = mode === 'login' ? loginUsernameRef.current : signupNameRef.current;
    target?.focus();
  }, [isOpen, mode]);

  // Clear error when switching modes
  useEffect(() => {
    setError(null);
  }, [mode]);

  const resetFormFields = () => {
    setLoginUsername('');
    setLoginPassword('');
    setSignupName('');
    setSignupUsername('');
    setSignupEmail('');
    setSignupPassword('');
    setError(null);
  };

  const handleLoginSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const username = loginUsername.trim();
    const password = loginPassword;
    if (!username || !password) return;

    setSubmitting(true);
    setError(null);
    try {
      await onLogin(username, password);
      resetFormFields();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignupSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const displayName = signupName.trim();
    const username = signupUsername.trim();
    const email = signupEmail.trim();
    const password = signupPassword;
    if (!username || !email || !password) return;

    setSubmitting(true);
    setError(null);
    try {
      await onRegister(username, email, password, displayName || undefined);
      resetFormFields();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const tabGroupId = `${id}-tabs`;
  const loginPanelId = `${id}-login-panel`;
  const signupPanelId = `${id}-signup-panel`;

  return (
    <AnimatePresence>
      {isOpen ? (
        <motion.div
          className={styles.backdrop}
          onClick={onClose}
          initial={reducedMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reducedMotion ? undefined : { opacity: 0 }}
          transition={{ duration: reducedMotion ? 0 : 0.24, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={mode === 'signup' ? 'Create your DocLens account' : 'Log in to DocLens'}
            className={styles.dialog}
            onClick={(event) => event.stopPropagation()}
            initial={reducedMotion ? false : { opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reducedMotion ? undefined : { opacity: 0, y: 18, scale: 0.99 }}
            transition={{ duration: reducedMotion ? 0 : 0.32, ease: [0.16, 1, 0.3, 1] }}
          >
            <button
              type="button"
              className={styles.closeButton}
              onClick={onClose}
              aria-label="Close authentication dialog"
            >
              <span aria-hidden="true">x</span>
            </button>

            <div className={styles.dialogGrid}>
              <aside className={styles.storyPanel}>
                <span className={styles.storyEyebrow}>Private workspace</span>
                <h2 className={styles.storyTitle}>
                  Your documents, your account.
                </h2>
                <p className={styles.storyCopy}>
                  Save uploads, return to earlier analysis sessions, and keep a personal document
                  history across every visit.
                </p>

                <div className={styles.signalList} aria-hidden="true">
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Access</span>
                    <span className={styles.signalValue}>JWT-secured account</span>
                  </div>
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Files</span>
                    <span className={styles.signalValue}>Per-user MinIO storage</span>
                  </div>
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Analysis</span>
                    <span className={styles.signalValue}>Results linked to your account</span>
                  </div>
                </div>
              </aside>

              <section className={styles.formPanel}>
                <div
                  className={styles.tabList}
                  role="tablist"
                  aria-label="Authentication modes"
                  id={tabGroupId}
                >
                  <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'login'}
                    aria-controls={loginPanelId}
                    className={`${styles.tab} ${mode === 'login' ? styles.tabActive : ''}`}
                    onClick={() => onModeChange('login')}
                  >
                    Log in
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'signup'}
                    aria-controls={signupPanelId}
                    className={`${styles.tab} ${mode === 'signup' ? styles.tabActive : ''}`}
                    onClick={() => onModeChange('signup')}
                  >
                    Create account
                  </button>
                </div>

                {error ? (
                  <div className={styles.previewNotice} role="alert">
                    <span className={styles.previewDot} aria-hidden="true" />
                    {error}
                  </div>
                ) : null}

                {mode === 'login' ? (
                  <div role="tabpanel" id={loginPanelId} aria-labelledby={tabGroupId}>
                    <h3 className={styles.panelTitle}>Welcome back</h3>
                    <p className={styles.panelCopy}>
                      Sign in to access your documents and analysis history.
                    </p>

                    <form className={styles.form} noValidate onSubmit={handleLoginSubmit}>
                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Username</span>
                        <input
                          ref={loginUsernameRef}
                          className={styles.input}
                          type="text"
                          name="username"
                          autoComplete="username"
                          value={loginUsername}
                          disabled={submitting}
                          onChange={(event) => setLoginUsername(event.target.value)}
                        />
                      </label>

                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Password</span>
                        <input
                          className={styles.input}
                          type="password"
                          name="password"
                          autoComplete="current-password"
                          value={loginPassword}
                          disabled={submitting}
                          onChange={(event) => setLoginPassword(event.target.value)}
                        />
                      </label>

                      <div className={styles.actionRow}>
                        <Button
                          type="submit"
                          size="md"
                          className={styles.submitButton}
                          disabled={submitting}
                        >
                          {submitting ? 'Signing in…' : 'Sign in'}
                        </Button>
                      </div>
                    </form>
                  </div>
                ) : (
                  <div role="tabpanel" id={signupPanelId} aria-labelledby={tabGroupId}>
                    <h3 className={styles.panelTitle}>Create your account</h3>
                    <p className={styles.panelCopy}>
                      Pick a username and start analysing documents right away.
                    </p>

                    <form className={styles.form} noValidate onSubmit={handleSignupSubmit}>
                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Display name</span>
                        <input
                          ref={signupNameRef}
                          className={styles.input}
                          type="text"
                          name="displayName"
                          autoComplete="name"
                          value={signupName}
                          disabled={submitting}
                          onChange={(event) => setSignupName(event.target.value)}
                        />
                      </label>

                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Username</span>
                        <input
                          className={styles.input}
                          type="text"
                          name="username"
                          autoComplete="username"
                          value={signupUsername}
                          disabled={submitting}
                          onChange={(event) => setSignupUsername(event.target.value)}
                        />
                      </label>

                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Email address</span>
                        <input
                          className={styles.input}
                          type="email"
                          name="email"
                          autoComplete="email"
                          value={signupEmail}
                          disabled={submitting}
                          onChange={(event) => setSignupEmail(event.target.value)}
                        />
                      </label>

                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Password</span>
                        <input
                          className={styles.input}
                          type="password"
                          name="signupPassword"
                          autoComplete="new-password"
                          value={signupPassword}
                          disabled={submitting}
                          onChange={(event) => setSignupPassword(event.target.value)}
                        />
                      </label>

                      <div className={styles.actionRow}>
                        <Button
                          type="submit"
                          size="md"
                          className={styles.submitButton}
                          disabled={submitting}
                        >
                          {submitting ? 'Creating account…' : 'Create account'}
                        </Button>
                      </div>
                    </form>
                  </div>
                )}
              </section>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
