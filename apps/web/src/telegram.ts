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
  openTelegramLink?: (url: string) => void;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TGWebApp;
    };
  }
}

let themeListenersBound = false;

function debugTelegramState(stage: string, webApp: TGWebApp | null) {
  console.info('[telegram]', stage, {
    hasTelegram: Boolean(window.Telegram),
    hasWebApp: Boolean(webApp),
    hasInitData: Boolean(webApp?.initData),
  });
}

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
  debugTelegramState('init', webApp);
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

export async function waitForTelegramWebApp(timeoutMs = 2000, stepMs = 100): Promise<TGWebApp | null> {
  const startedAt = Date.now();
  let webApp = window.Telegram?.WebApp ?? null;
  debugTelegramState('wait:start', webApp);

  while (Date.now() - startedAt < timeoutMs) {
    webApp = window.Telegram?.WebApp ?? null;
    if (webApp?.initData) {
      debugTelegramState('wait:resolved', webApp);
      return webApp;
    }
    await new Promise((resolve) => window.setTimeout(resolve, stepMs));
  }

  webApp = window.Telegram?.WebApp ?? null;
  debugTelegramState('wait:timeout', webApp);
  return webApp;
}

export function normalizeTelegramProxyUrl(rawUrl: string): string {
  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (trimmed.startsWith('tg://proxy?')) {
    return `https://t.me/proxy?${trimmed.slice('tg://proxy?'.length)}`;
  }
  return trimmed;
}

export function openTelegramProxy(rawUrl: string): void {
  const normalizedUrl = normalizeTelegramProxyUrl(rawUrl);
  const webApp = window.Telegram?.WebApp;

  console.info('[telegram] open proxy', {
    hasWebApp: Boolean(webApp),
    usedTelegramLink: Boolean(webApp?.openTelegramLink),
    usedOpenLink: Boolean(!webApp?.openTelegramLink && webApp?.openLink),
    normalizedScheme: normalizedUrl.startsWith('https://') ? 'https' : normalizedUrl.split(':', 1)[0],
  });

  if (webApp?.openTelegramLink && normalizedUrl.startsWith('https://t.me/')) {
    webApp.openTelegramLink(normalizedUrl);
    return;
  }

  if (webApp?.openLink) {
    webApp.openLink(normalizedUrl);
    return;
  }

  if (normalizedUrl) {
    window.location.href = normalizedUrl;
  }
}

export function openProxyThenBot(rawProxyUrl: string, botUrl: string): void {
  const normalizedProxyUrl = normalizeTelegramProxyUrl(rawProxyUrl);
  const normalizedBotUrl = botUrl.trim();

  if (!normalizedProxyUrl || !normalizedBotUrl) {
    return;
  }

  try {
    const popup = window.open(normalizedProxyUrl, '_blank', 'noopener,noreferrer');
    if (!popup) {
      window.location.href = normalizedProxyUrl;
    }
  } catch {
    window.location.href = normalizedProxyUrl;
  }

  window.setTimeout(() => {
    window.location.href = normalizedBotUrl;
  }, 1200);
}

export function openTelegramPage(rawUrl: string): void {
  const normalizedUrl = rawUrl.trim();
  const webApp = window.Telegram?.WebApp;

  console.info('[telegram] open page', {
    hasWebApp: Boolean(webApp),
    hasOpenLink: Boolean(webApp?.openLink),
    url: normalizedUrl,
  });

  if (!normalizedUrl) {
    return;
  }

  if (webApp?.openLink) {
    webApp.openLink(normalizedUrl);
    return;
  }

  window.open(normalizedUrl, '_blank', 'noopener,noreferrer');
}
