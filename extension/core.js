export const DEFAULTS = {mode: 'video', height: 1080, languages: 'en', accurate: true};

export function parseTime(text) {
  const value = String(text).trim();
  if (!/^(?:\d+:){0,2}\d+(?:\.\d{1,3})?$/.test(value)) return NaN;
  const parts = value.split(':').map(Number);
  if (parts.length > 1 && parts.slice(1).some(x => x >= 60)) return NaN;
  return parts.reduce((total, part) => total * 60 + part, 0);
}

export function formatTime(value, milliseconds = true) {
  if (!Number.isFinite(value)) return '—';
  let ticks = Math.round(Math.max(0, value) * 1000);
  const hours = Math.floor(ticks / 3600000); ticks %= 3600000;
  const minutes = Math.floor(ticks / 60000); ticks %= 60000;
  const seconds = Math.floor(ticks / 1000);
  const fraction = ticks % 1000;
  const body = hours ? `${hours}:${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}` : `${minutes}:${String(seconds).padStart(2,'0')}`;
  return milliseconds && fraction ? `${body}.${String(fraction).padStart(3,'0').replace(/0+$/,'')}` : body;
}

export function validRange(start, end, duration) {
  return Number.isFinite(start) && start >= 0 && (end === null || (Number.isFinite(end) && end > start)) &&
    (!Number.isFinite(duration) || (start < duration && (end === null || end <= duration + .001)));
}

export function isWebUrl(value) {
  try { return ['http:','https:'].includes(new URL(value).protocol); } catch { return false; }
}

export function canonicalVideoUrl(value) {
  const u = new URL(value);
  if (/(^|\.)youtube\.com$/.test(u.hostname) && u.searchParams.has('v')) return `https://www.youtube.com/watch?v=${encodeURIComponent(u.searchParams.get('v'))}`;
  if (u.hostname === 'youtu.be') return `https://www.youtube.com/watch?v=${encodeURIComponent(u.pathname.slice(1))}`;
  u.hash = ''; return u.href;
}

export function clipRequest(source, range, settings) {
  if (!isWebUrl(source?.url)) throw new Error('Choose a video or paste its link first.');
  if (!validRange(range.start, range.end, source.duration)) throw new Error('Enter a valid start and end within the video.');
  return {url: source.url, page_url: source.pageUrl || source.url, title: source.title, ...settings, start: range.start,
    end: range.end !== null && Number.isFinite(source.duration) && Math.abs(range.end-source.duration)<.001 ? null : range.end};
}
