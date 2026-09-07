export const registeredWorklets = new Map();

export const createWorkletFromSrc = (workletName, workletSrc) => {
  const script = new Blob(
    [`registerProcessor("${workletName}", ${workletSrc})`],
    { type: "application/javascript" }
  );
  return URL.createObjectURL(script);
};
