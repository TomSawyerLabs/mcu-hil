export function delay(ms: number, unref = false): Promise<void> {
  return new Promise((resolve) => {
    const t = setTimeout(resolve, ms);
    if (unref) t.unref();
  });
}
