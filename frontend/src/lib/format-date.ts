/** Format an ISO date string or Date as dd/mm/yyyy */
export function formatDate(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

/** Format an ISO datetime string as dd/mm/yyyy HH:mm */
export function formatDateTime(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
}

/** Format an ISO date string as dd/mm (short, for charts) */
export function formatDateShort(value: string): string {
  const parts = value.split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
  return value;
}
