/**
 * Centralized deterministic random utilities (supports T026 + future Monte Carlo tasks T043/T044).
 */
export interface LCG {
  next(): number; // [0,1)
  seed(): number; // current internal seed (uint32)
}

export function createLCG(initialSeed: number): LCG {
  let s = initialSeed >>> 0;
  return {
    next() {
      s = (s * 1664525 + 1013904223) % 4294967296;
      return s / 4294967296;
    },
    seed() {
      return s;
    },
  };
}

export function randomFloat(lcg: LCG, min: number, max: number) {
  return min + (max - min) * lcg.next();
}

export function randomWalkPath(length: number, seed: number, step = 40, start = 10000): number[] {
  const lcg = createLCG(seed);
  let v = start;
  const arr = [v];
  for (let i = 1; i < length; i++) {
    v += (lcg.next() - 0.5) * step;
    arr.push(v);
  }
  return arr;
}

export function randomWalkPaths(count: number, length: number, seed: number, step = 40, start = 10000): number[][] {
  const paths: number[][] = [];
  // Derive per-path seeds deterministically from base seed
  let perSeed = seed >>> 0;
  for (let i = 0; i < count; i++) {
    // simple derivation
    perSeed = (perSeed * 1664525 + 1013904223) >>> 0;
    paths.push(randomWalkPath(length, perSeed, step, start));
  }
  return paths;
}
