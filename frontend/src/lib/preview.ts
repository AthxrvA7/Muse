/** Muse's preview address for a Deezer track: it redirects to a fresh 30-second clip. */
export function previewUrl(deezerId: number): string {
  return `/api/v1/previews/${deezerId}`;
}
