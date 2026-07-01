import { extractAcademicPage } from "./extractors.js";
import type { BrowserExtensionExtraction } from "../shared/types.js";

type ExtensionMessage = {
  type?: string;
};

type ExtractionResponse = {
  ok: true;
  extraction: BrowserExtensionExtraction;
};

type RuntimeMessageSender = unknown;

type RuntimeApi = {
  onMessage: {
    addListener: (
      listener: (
        message: ExtensionMessage,
        sender: RuntimeMessageSender,
        sendResponse: (response: ExtractionResponse) => void,
      ) => boolean | undefined,
    ) => void;
  };
};

declare const chrome:
  | {
      runtime?: RuntimeApi;
    }
  | undefined;

chrome?.runtime?.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "SAPSOS_EXTRACT_PAGE") {
    return false;
  }
  sendResponse({
    ok: true,
    extraction: extractAcademicPage(document, location.href, document.title),
  });
  return false;
});
