// Round vendor initials in a pale tint from the teal family plus neutral, picked stably from the
// name so the same vendor always looks the same (as in the phone app).
const TINTS = ["tint-a", "tint-b", "tint-c", "tint-d"];

function initials(name) {
  const words = (name || "?").replace(/[^A-Za-z0-9 ]/g, " ").trim().split(/\s+/);
  return ((words[0]?.[0] || "?") + (words[1]?.[0] || "")).toUpperCase();
}

function tintFor(name) {
  let h = 0;
  for (const ch of name || "") h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return TINTS[h % TINTS.length];
}

export default function VendorAvatar({ name }) {
  return (
    <span className={`avatar ${tintFor(name)}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}
