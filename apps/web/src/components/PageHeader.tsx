import { ChevronDown } from 'lucide-react';
import { useRef, type ReactNode } from 'react';

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  const headerRef = useRef<HTMLElement | null>(null);

  const handleDefaultAction = () => {
    const header = headerRef.current;
    if (!header) return;

    const parent = header.parentElement;
    if (!parent) return;

    const contentTarget = Array.from(parent.children).find((node) => node !== header) as HTMLElement | undefined;
    if (!contentTarget) return;

    const targetTop = contentTarget.getBoundingClientRect().top + window.scrollY - 12;
    if (window.scrollY > 120) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    window.scrollTo({ top: Math.max(targetTop, 0), behavior: 'smooth' });
  };

  return (
    <header className="page-header" ref={headerRef}>
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action ?? (
        <button className="page-header-chip page-header-auto-action" onClick={handleDefaultAction} aria-label="Прокрутить к содержимому">
          <ChevronDown size={16} />
        </button>
      )}
    </header>
  );
}
