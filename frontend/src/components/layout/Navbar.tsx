import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { Button } from '../common/Button';
import { AuthDialog, type AuthMode, type PreviewAccountPayload } from './AuthDialog';
import styles from './Navbar.module.css';

interface PreviewAccount {
  displayName: string;
  email: string;
  initials: string;
}

function getInitials(value: string): string {
  const tokens = value
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (tokens.length === 0) return 'DU';
  if (tokens.length === 1) return tokens[0].slice(0, 2).toUpperCase();
  return `${tokens[0][0]}${tokens[1][0]}`.toUpperCase();
}

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [account, setAccount] = useState<PreviewAccount | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  useEffect(() => {
    if (!menuOpen) return undefined;

    const onPointerDown = (event: MouseEvent) => {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
      }
    };

    window.addEventListener('mousedown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('mousedown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode);
    setDialogOpen(true);
    setMenuOpen(false);
  };

  const closeAuth = () => {
    setDialogOpen(false);
  };

  const handleAuthenticate = ({ displayName, email }: PreviewAccountPayload) => {
    setAccount({
      displayName,
      email,
      initials: getInitials(displayName),
    });
    setDialogOpen(false);
    setMenuOpen(false);
  };

  const handleSignOut = () => {
    setAccount(null);
    setMenuOpen(false);
  };

  return (
    <nav
      className={`${styles.navbar} ${scrolled ? styles.scrolled : ''}`}
      aria-label="Main navigation"
    >
      <div className={styles.inner}>
        <a href="#" className={styles.brand} aria-label="DocLens Home">
          <span className={styles.logo}>
            <img
              src="/brand/doclens-mark.svg"
              alt="DocLens brand mark"
              className={styles.logoImage}
            />
          </span>
          <span className={styles.brandLockup}>
            <span className={styles.brandText}>DocLens</span>
            <span className={styles.brandMeta}>3D document intelligence</span>
          </span>
        </a>

        <div className={styles.trailing}>
          {account ? (
            <div className={styles.accountWrap} ref={accountMenuRef}>
              <button
                type="button"
                className={styles.accountButton}
                aria-expanded={menuOpen}
                aria-label={`Open account menu for ${account.displayName}`}
                onClick={() => setMenuOpen((current) => !current)}
              >
                <span className={styles.accountAvatar} aria-hidden="true">
                  {account.initials}
                </span>
                <span className={styles.accountCopy}>
                  <span className={styles.accountName}>{account.displayName}</span>
                  <span className={styles.accountMeta}>Preview account</span>
                </span>
                <span className={styles.accountChevron} aria-hidden="true">
                  v
                </span>
              </button>

              <AnimatePresence>
                {menuOpen ? (
                  <motion.div
                    className={styles.accountMenu}
                    initial={{ opacity: 0, y: -10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.99 }}
                    transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <span className={styles.menuEyebrow}>Preview session</span>
                    <div className={styles.menuHeader}>
                      <p className={styles.menuName}>{account.displayName}</p>
                      <p className={styles.menuEmail}>{account.email}</p>
                    </div>
                    <p className={styles.menuNote}>
                      Saved files sync will appear here once backend is connected.
                    </p>
                    <div className={styles.menuSignals} aria-hidden="true">
                      <span className={styles.menuSignal}>Auth shell ready</span>
                      <span className={styles.menuSignal}>Workspace persistence next</span>
                    </div>
                    <button
                      type="button"
                      className={styles.signOutButton}
                      onClick={handleSignOut}
                    >
                      Sign out
                    </button>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          ) : (
            <div className={styles.authActions}>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={styles.navButton}
                onClick={() => openAuth('login')}
              >
                Log in
              </Button>
              <Button
                type="button"
                size="sm"
                className={styles.navButton}
                onClick={() => openAuth('signup')}
              >
                Sign up
              </Button>
            </div>
          )}
        </div>
      </div>

      <AuthDialog
        isOpen={dialogOpen}
        mode={authMode}
        onClose={closeAuth}
        onModeChange={setAuthMode}
        onAuthenticate={handleAuthenticate}
      />
    </nav>
  );
}
