import { useEffect, useState } from 'react';
import styles from './Navbar.module.css';

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <nav className={`${styles.navbar} ${scrolled ? styles.scrolled : ''}`} aria-label="Main navigation">
      <div className={styles.inner}>
        <a href="#" className={styles.brand} aria-label="DocLens Home">
          <span className={styles.logo} aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect x="2" y="2" width="24" height="24" rx="8" fill="#172738" />
              <path
                d="M8.4 8.2v11.6h3.4c3.1 0 5.3-2.2 5.3-5.8 0-3.6-2.2-5.8-5.3-5.8H8.4Z"
                stroke="#ffffff"
                strokeWidth="1.7"
                strokeLinejoin="round"
              />
              <path
                d="M19.4 8.3v11.5h-3.7"
                stroke="#d9a86c"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className={styles.brandLockup}>
            <span className={styles.brandText}>DocLens</span>
            <span className={styles.brandMeta}>3D document intelligence</span>
          </span>
        </a>

        <ul className={styles.links} role="list">
          <li>
            <a href="#workspace" className={styles.link}>
              Workspace
            </a>
          </li>
          <li>
            <a href="#pipeline" className={styles.link}>
              Method
            </a>
          </li>
        </ul>

        <div className={styles.trailing}>
          <span className={styles.badgeNav}>Classical ML</span>
        </div>
      </div>
    </nav>
  );
}
