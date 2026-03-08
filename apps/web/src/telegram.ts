export type TGUser = {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  photo_url?: string;
};

export type TGWebApp = {
  initData: string;
  colorScheme?: 'light' | 'dark';
  initDataUnsafe?: {
    user?: TGUser;
    [key: string]: unknown;
  };
  onEvent?: (event: 'themeChanged', handler: () => void) => void;
  offEvent?: (event: 'themeChanged', handler: () => void) => void;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openLink?: (url: string) => void;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TGWebApp;
    };
  }
}

let themeListenersBound = false;

export function initTelegramSDK(): TGWebApp | null {
  // The SDK package is intentionally kept to align with official Mini Apps tooling.
  // Runtime compatibility varies between SDK versions, so we call it defensively.
  import('@telegram-apps/sdk')
    .then((sdkModule: unknown) => {
      const sdk = sdkModule as Record<string, unknown>;
      const maybeInit = sdk.init;
      if (typeof maybeInit === 'function') {
        (maybeInit as () => void)();
      }
    })
    .catch(() => {
      // Ignore SDK init errors in local/dev environments.
    });

  const webApp = window.Telegram?.WebApp ?? null;
  if (webApp) {
    webApp.ready();
    webApp.expand();
  }

  const applyTheme = () => {
    const mediaQuery = typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;
    const prefersDark = Boolean(mediaQuery?.matches);
    const scheme = webApp?.colorScheme === 'dark' || webApp?.colorScheme === 'light'
      ? webApp.colorScheme
      : prefersDark
        ? 'dark'
        : 'light';
    const root = document.documentElement;
    root.dataset.theme = scheme;
    root.style.colorScheme = scheme;
  };

  applyTheme();
  if (!themeListenersBound) {
    webApp?.onEvent?.('themeChanged', applyTheme);
    const mediaQuery = typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;
    if (mediaQuery?.addEventListener) {
      mediaQuery.addEventListener('change', applyTheme);
    } else {
      mediaQuery?.addListener?.(applyTheme);
    }
    themeListenersBound = true;
  }

  return webApp;
}
