import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../common/Button';
import { AuthDialog, type AuthMode } from './AuthDialog';
import { useAuth } from '../../hooks/useAuth';
import styles from './Navbar.module.css';

export function Navbar() {
  const { user, login, register, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [scrolled, setScrolled] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [menuOpen, setMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);
  const pendingReturnPathRef = useRef<string | null>(null);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  // Close account menu on outside click or Escape
  useEffect(() => {
    if (!menuOpen) return undefined;

    const onPointerDown = (event: MouseEvent) => {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };

    window.addEventListener('mousedown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('mousedown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);

  // Close menu when user changes (login / logout)
  useEffect(() => {
    setMenuOpen(false);
    setDialogOpen(false);
  }, [user]);

  useEffect(() => {
    if (user) return;

    const state = location.state as { authIntent?: string; from?: string } | null;
    if (state?.authIntent !== 'login') return;

    pendingReturnPathRef.current = state.from ?? '/workspace';
    setAuthMode('login');
    setDialogOpen(true);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate, user]);

  useEffect(() => {
    if (!user || !pendingReturnPathRef.current) return;

    const returnTo = pendingReturnPathRef.current;
    pendingReturnPathRef.current = null;
    navigate(returnTo, { replace: true });
  }, [navigate, user]);

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode);
    setDialogOpen(true);
    setMenuOpen(false);
  };

  const handleSignOut = () => {
    logout();
    setMenuOpen(false);
  };

  // Listen for login requests from other parts of the app (e.g. UploadWorkspace CTA)
  useEffect(() => {
    const handler = () => openAuth('login');
    window.addEventListener('doclens:open-login', handler);
    return () => window.removeEventListener('doclens:open-login', handler);
  }, []);

  // Route-aware nav button: shows "Workspace" on the landing page and
  // "Home page" on the workspace page — placed to the left of the profile.
  const isOnWorkspace = location.pathname === '/workspace';
  const contextButtonLabel = isOnWorkspace ? 'Home page' : 'Workspace';
  const contextButtonPath = isOnWorkspace ? '/' : '/workspace';

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
          {user && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className={styles.navButton}
              onClick={() => navigate(contextButtonPath)}
            >
              {contextButtonLabel}
            </Button>
          )}
          {user ? (
            <div className={styles.accountWrap} ref={accountMenuRef}>
              <button
                type="button"
                className={styles.accountButton}
                aria-expanded={menuOpen}
                aria-label={`Open account menu for ${user.displayName}`}
                onClick={() => setMenuOpen((current) => !current)}
              >
                <span className={styles.accountAvatar} aria-hidden="true">
                  {user.initials}
                </span>
                <span className={styles.accountCopy}>
                  <span className={styles.accountName}>{user.displayName}</span>
                  <span className={styles.accountMeta}>{user.email}</span>
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
                    <div className={styles.menuHeader}>
                      <p className={styles.menuName}>{user.displayName}</p>
                      <p className={styles.menuEmail}>{user.email}</p>
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
        onClose={() => setDialogOpen(false)}
        onModeChange={setAuthMode}
        onLogin={login}
        onRegister={register}
      />
    </nav>
  );
}
