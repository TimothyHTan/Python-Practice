// Ignore Windows line endings, trailing spaces on each line, and trailing blank lines.
export const normalize = (s) =>
  s.replace(/\r\n?/g, '\n').split('\n').map((l) => l.trimEnd()).join('\n').replace(/\n+$/, '');

export const sameOutput = (expected, actual) => normalize(expected) === normalize(actual);
