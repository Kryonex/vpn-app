import { useState } from 'react';

export function useApiCall<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (...args: TArgs): Promise<TResult | null> => {
    try {
      setIsLoading(true);
      setError(null);
      return await fn(...args);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { run, isLoading, error };
}
