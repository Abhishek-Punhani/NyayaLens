const map = new Map();

export const audioContext = (() => {
  let didInteract = Promise.resolve();
  if (typeof window !== "undefined") {
    didInteract = new Promise((res) => {
      window.addEventListener("pointerdown", res, { once: true });
      window.addEventListener("keydown", res, { once: true });
    });
  }

  return async (options) => {
    try {
      const a = new Audio();
      a.src = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
      await a.play().catch(() => {});
      if (options?.id && map.has(options.id)) {
        const ctx = map.get(options.id);
        if (ctx) return ctx;
      }
      const ctx = new AudioContext(options);
      if (options?.id) map.set(options.id, ctx);
      return ctx;
    } catch (e) {
      await didInteract;
      if (options?.id && map.has(options.id)) {
        const ctx = map.get(options.id);
        if (ctx) return ctx;
      }
      const ctx = new AudioContext(options);
      if (options?.id) map.set(options.id, ctx);
      return ctx;
    }
  };
})();

export function base64ToArrayBuffer(base64) {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

export function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
