import { ChevronRight } from 'lucide-react';

export function PageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      <div className="page-header-chip">
        <ChevronRight size={16} />
      </div>
    </header>
  );
}
