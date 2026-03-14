import type { ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action ?? (
        <div className="page-header-chip">
          <ChevronRight size={16} />
        </div>
      )}
    </header>
  );
}
