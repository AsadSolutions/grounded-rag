const CITATION_PATTERN = /\[([^[\]]+)\]/g;

function parseBracketIds(inner: string): string[] {
  return inner
    .split(",")
    .map((id) => id.trim())
    .filter((id) => id.length > 0);
}

export type CitationSegment =
  | { type: "text"; value: string }
  | { type: "citation"; chunkIds: string[]; docNames: string[] };

export type CitationSource = { chunkId: string; docName: string };

export function splitCitations(
  content: string,
  sources: CitationSource[],
): CitationSegment[] {
  const byId = new Map(sources.map((s) => [s.chunkId, s]));

  const segments: CitationSegment[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(CITATION_PATTERN)) {
    const ids = parseBracketIds(match[1]);
    if (ids.length === 0 || !ids.every((id) => byId.has(id))) continue;

    const index = match.index ?? 0;
    if (index > lastIndex) {
      segments.push({ type: "text", value: content.slice(lastIndex, index) });
    }
    const docNames = [...new Set(ids.map((id) => byId.get(id)!.docName))];
    segments.push({ type: "citation", chunkIds: ids, docNames });
    lastIndex = index + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({ type: "text", value: content.slice(lastIndex) });
  }

  return segments;
}
