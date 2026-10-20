// A design token's value as the page has it (design/tokens/colours.css, linked by the page): the 3D views take their
// colours from here, never from a literal. A token the page lacks is an error, not a silent black.
export function token(name) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!value) throw new Error(`design token ${name} is not on this page: link design/tokens/colours.css`);
  return value;
}
