/**
 * Building follow-up messages (F19). The editor shows bold and italics as
 * they will arrive. WhatsApp's own marks, *bold* and _italic_, are added
 * here, out of sight, only when sending.
 */
import type { Template } from '../api/journeys';

export function greeting(d = new Date()) {
  const h = d.getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function fill(text: string, v: { nextService: string; sender: string }) {
  return text.replace('[Next service]', v.nextService).replace('[Shepherd]', v.sender)
    .replace('[Programme]', 'our special programme').replace('[Answer to their question] ', '').replace('[Answer to their question]', '');
}

/** A message as it will arrive: bold greeting, verse in italics with the reference in bold, body, signature in italics. */
export function messageHTML(t: Pick<Template, 'verse' | 'reference' | 'body'>, first: string, v: { nextService: string; sender: string }) {
  const verse = t.verse ? `<p><i>"${esc(t.verse)}"</i> <b>${esc(t.reference)}</b></p>` : '';
  return `<p><b>${greeting()}, ${esc(first)}</b></p>${verse}<p>${esc(fill(t.body, v))}</p><p><i>${esc(v.sender)}, DCLM Bahrain</i></p>`;
}

export function blankHTML(first: string, sender: string) {
  return `<p><b>${greeting()}, ${esc(first)}</b></p><p><br></p><p><i>${esc(sender)}, DCLM Bahrain</i></p>`;
}

export function toWhatsApp(html: string) {
  const div = document.createElement('div');
  div.innerHTML = html;
  const walk = (n: Node): string => {
    if (n.nodeType === 3) return n.textContent ?? '';
    const inner = [...n.childNodes].map(walk).join('');
    const tag = n.nodeName;
    if (tag === 'B' || tag === 'STRONG') return inner.trim() ? `*${inner.trim()}*` : inner;
    if (tag === 'I' || tag === 'EM') return inner.trim() ? `_${inner.trim()}_` : inner;
    if (tag === 'BR') return '\n';
    if (tag === 'P' || tag === 'DIV') return inner + '\n\n';
    return inner;
  };
  return walk(div).replace(/\u00a0/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
}

/** The WhatsApp link: to their number when we have one, otherwise the sender picks the chat. */
export function waLink(phone: string, text: string) {
  const digits = (phone || '').replace(/[^0-9]/g, '');
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}

/** Keeps only paragraphs, line breaks, bold and italics, with no attributes. */
export function cleanHTML(html: string) {
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  const allowed = new Set(['P', 'BR', 'B', 'STRONG', 'I', 'EM', 'DIV']);
  const walk = (n: Node): string => {
    if (n.nodeType === 3) return (n.textContent ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (n.nodeType !== 1) return '';
    const inner = [...n.childNodes].map(walk).join('');
    const tag = (n as Element).tagName;
    if (!allowed.has(tag)) return inner;
    const t = tag === 'DIV' ? 'p' : tag.toLowerCase();
    return t === 'br' ? '<br>' : `<${t}>${inner}</${t}>`;
  };
  return [...tpl.content.childNodes].map(walk).join('');
}
export const escapeHTML = esc;
