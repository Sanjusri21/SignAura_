/**
 * Utility functions for formatting durations, timestamps, and numbers across SignAura.
 */

/**
 * Formats a duration in seconds into clean, human-readable text.
 * Avoids raw floating point representation (e.g., 225.14000000000001s).
 * Examples:
 *   - 45.2 -> "45.2s"
 *   - 45 -> "45s"
 *   - 120 -> "2m"
 *   - 225.14000000000001 -> "3m 45s"
 */
export function formatDuration(seconds: number | undefined | null, format: 'human' | 'seconds' = 'human'): string {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) {
    return '0s';
  }

  const roundedSecs = Math.round(seconds * 10) / 10;

  if (format === 'seconds' || seconds < 60) {
    const isInt = roundedSecs % 1 === 0;
    return `${isInt ? roundedSecs.toFixed(0) : roundedSecs.toFixed(1)}s`;
  }

  const mins = Math.floor(seconds / 60);
  const remSecs = Math.round(seconds % 60);

  if (remSecs === 0) {
    return `${mins}m`;
  }
  return `${mins}m ${remSecs}s`;
}

/**
 * Formats a timestamp in seconds cleanly to 1 decimal place (e.g., 1.2s).
 */
export function formatSeconds(seconds: number | undefined | null): string {
  if (seconds === undefined || seconds === null || isNaN(seconds)) {
    return '0s';
  }
  const rounded = Math.round(seconds * 10) / 10;
  return `${rounded % 1 === 0 ? rounded.toFixed(0) : rounded.toFixed(1)}s`;
}
