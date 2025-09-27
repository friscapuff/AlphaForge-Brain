export function estimateMatrixBytes(paths: number, points: number, bytesPer = 8): number {
  return paths * points * bytesPer; // float64 assumption
}

export function formatMB(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(2) + 'MB';
}

export function generateMonteCarloMatrix(paths: number, points: number): number[][] {
  const out: number[][] = new Array(paths);
  for (let i = 0; i < paths; i++) {
    const row = new Array(points);
    let base = 10000;
    for (let j = 0; j < points; j++) {
      // simple random walk
      base += (Math.random() - 0.5) * 5;
      row[j] = +(base.toFixed(2));
    }
    out[i] = row;
  }
  return out;
}
