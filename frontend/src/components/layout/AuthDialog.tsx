import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Button } from '../common/Button';
import styles from './AuthDialog.module.css';

export type AuthMode = 'login' | 'signup';

export interface PreviewAccountPayload {
  displayName: string;
  email: string;
}

interface AuthDialogProps {
  isOpen: boolean;
  mode: AuthMode;
  onClose: () => void;
  onModeChange: (mode: AuthMode) => void;
  onAuthenticate: (payload: PreviewAccountPayload) => void;
}

function formatDisplayName(value: string): string {
  const cleaned = value.trim();
  if (!cleaned) return 'Preview User';

  return cleaned
    .split('@')[0]
    .split(/[._\-\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function AuthDialog({
  isOpen,
  mode,
  onClose,
  onModeChange,
  onAuthenticate,
}: AuthDialogProps) {
  const reducedMotion = usePrefersReducedMotion();
  const id = useId();
  const loginIdentityRef = useRef<HTMLInputElement | null>(null);
  const signupNameRef = useRef<HTMLInputElement | null>(null);

  const [loginIdentity, setLoginIdentity] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');

  useEffect(() => {
    if (!isOpen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;

    const focusTarget = mode === 'login' ? loginIdentityRef.current : signupNameRef.current;
    focusTarget?.focus();
  }, [isOpen, mode]);

  const resetFormFields = () => {
    setLoginIdentity('');
    setLoginPassword('');
    setSignupName('');
    setSignupEmail('');
    setSignupPassword('');
  };

  const handleLoginSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const normalizedIdentity = loginIdentity.trim();
    if (!normalizedIdentity) return;

    onAuthenticate({
      displayName: formatDisplayName(normalizedIdentity),
      email: normalizedIdentity.includes('@')
        ? normalizedIdentity
        : `${normalizedIdentity.toLowerCase()}@preview.local`,
    });
    resetFormFields();
  };

  const handleSignupSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const normalizedName = signupName.trim();
    const normalizedEmail = signupEmail.trim();
    if (!normalizedName || !normalizedEmail) return;

    onAuthenticate({
      displayName: normalizedName,
      email: normalizedEmail,
    });
    resetFormFields();
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
                  A cleaner account entry, ready for the real backend pass.
                </h2>
                <p className={styles.storyCopy}>
                  Save uploads, return to earlier analysis sessions, and keep a personal document
                  trail once the live backend connection lands.
                </p>

                <div className={styles.signalList} aria-hidden="true">
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Access</span>
                    <span className={styles.signalValue}>Account shell ready</span>
                  </div>
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Files</span>
                    <span className={styles.signalValue}>Per-user storage next</span>
                  </div>
                  <div className={styles.signalCard}>
                    <span className={styles.signalLabel}>Analysis</span>
                    <span className={styles.signalValue}>Frontend prepared for live sync</span>
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

                <div className={styles.previewNotice}>
                  <span className={styles.previewDot} aria-hidden="true" />
                  Backend connection lands in the next integration pass, so this account flow stays
                  in preview mode for now.
                </div>

                {mode === 'login' ? (
                  <div role="tabpanel" id={loginPanelId} aria-labelledby={tabGroupId}>
                    <h3 className={styles.panelTitle}>Welcome back</h3>
                    <p className={styles.panelCopy}>
                      Use the visual shell now, then swap in real backend auth once the API work
                      lands.
                    </p>

                    <form className={styles.form} noValidate onSubmit={handleLoginSubmit}>
                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Email or username</span>
                        <input
                          ref={loginIdentityRef}
                          className={styles.input}
                          type="text"
                          name="identity"
                          autoComplete="username"
                          value={loginIdentity}
                          onChange={(event) => setLoginIdentity(event.target.value)}
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
                          onChange={(event) => setLoginPassword(event.target.value)}
                        />
                      </label>

                      <div className={styles.actionRow}>
                        <Button type="submit" size="md" className={styles.submitButton}>
                          Continue in preview
                        </Button>
                        <p className={styles.supportCopy}>
                          Session state stays local until backend auth is wired.
                        </p>
                      </div>
                    </form>
                  </div>
                ) : (
                  <div role="tabpanel" id={signupPanelId} aria-labelledby={tabGroupId}>
                    <h3 className={styles.panelTitle}>Create your account shell</h3>
                    <p className={styles.panelCopy}>
                      We'll keep the interface polished and honest now, then hook it into real user
                      storage later.
                    </p>

                    <form className={styles.form} noValidate onSubmit={handleSignupSubmit}>
                      <label className={styles.field}>
                        <span className={styles.fieldLabel}>Full name</span>
                        <input
                          ref={signupNameRef}
                          className={styles.input}
                          type="text"
                          name="fullName"
                          autoComplete="name"
                          value={signupName}
                          onChange={(event) => setSignupName(event.target.value)}
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
                          onChange={(event) => setSignupPassword(event.target.value)}
                        />
                      </label>

                      <div className={styles.actionRow}>
                        <Button type="submit" size="md" className={styles.submitButton}>
                          Continue in preview
                        </Button>
                        <p className={styles.supportCopy}>
                          The visual account state is live now; API-backed auth comes next.
                        </p>
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
