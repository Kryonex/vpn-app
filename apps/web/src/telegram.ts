export type TGWebApp = {
  initData: string;
  initDataUnsafe?: Record<string, unknown>;
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
  return webApp;
}
