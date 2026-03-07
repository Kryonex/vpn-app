import { AlertTriangle, Loader2 } from 'lucide-react';

export function LoadingState({ text = 'Загрузка...' }: { text?: string }) {
  return (
    <div className="state-card state-loading">
      <Loader2 size={18} className="spin" />
      <p>{text}</p>
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="state-card">
      <p className="state-title">{title}</p>
      <p className="state-text">{text}</p>
    </div>
  );
}

export function ErrorState({ text }: { text: string }) {
  return (
    <div className="state-card state-error">
      <AlertTriangle size={18} />
      <p>{text}</p>
    </div>
  );
}
