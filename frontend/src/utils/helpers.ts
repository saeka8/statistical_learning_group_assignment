export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function generateId(): string {
  return `doc_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    invoice: 'var(--color-accent-indigo)',
    email: 'var(--color-accent-sky)',
    resume: 'var(--color-accent-emerald)',
    scientific_publication: 'var(--color-accent-violet)',
  };
  return colors[category] || 'var(--color-text-tertiary)';
}

export function getCategoryBg(category: string): string {
  const colors: Record<string, string> = {
    invoice: 'var(--color-accent-indigo-bg)',
    email: 'rgba(14, 165, 233, 0.08)',
    resume: 'var(--color-accent-emerald-bg)',
    scientific_publication: 'rgba(139, 92, 246, 0.08)',
  };
  return colors[category] || 'rgba(148, 163, 184, 0.08)';
}
