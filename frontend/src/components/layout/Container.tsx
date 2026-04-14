import { type HTMLAttributes, type ReactNode } from 'react';
import styles from './Container.module.css';

interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'default' | 'wide' | 'narrow';
  children: ReactNode;
}

export function Container({ size = 'default', children, className = '', ...props }: ContainerProps) {
  return (
    <div className={`${styles.container} ${styles[size]} ${className}`} {...props}>
      {children}
    </div>
  );
}
