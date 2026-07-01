type RuntimeApi = {
  onInstalled: {
    addListener: (listener: () => void) => void;
  };
};

declare const chrome:
  | {
      runtime?: RuntimeApi;
    }
  | undefined;

chrome?.runtime?.onInstalled.addListener(() => undefined);
