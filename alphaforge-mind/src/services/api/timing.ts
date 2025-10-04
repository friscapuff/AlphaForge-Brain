/**
 * Lightweight timing utility (clean implementation, duplicates removed).
 */
export interface TimingSpan {
	name: string;
	start: number;
	end?: number;
	duration?: number;
	meta?: Record<string, unknown>;
}

class TimingCollector {
	private enabled = true;
	private spans: TimingSpan[] = [];

	setEnabled(v: boolean) {
		this.enabled = v;
	}

	start(name: string, meta?: Record<string, unknown>): () => void {
		if (!this.enabled) return () => undefined;
		const span: TimingSpan = { name, start: performance.now(), meta };
		this.spans.push(span);
		return () => {
			if (span.end != null) return;
			span.end = performance.now();
			span.duration = span.end - span.start;
		};
	}

	withTiming<T>(name: string, fn: () => T, meta?: Record<string, unknown>): T {
		const stop = this.start(name, meta);
		try {
			return fn();
		} finally {
			stop();
		}
	}

	flush(): TimingSpan[] {
		const out = this.spans.slice();
		this.spans = [];
		return out;
	}

	peek(): TimingSpan[] {
		return this.spans.slice();
	}
}

export const timingCollector = new TimingCollector();

export function startTiming(name: string, meta?: Record<string, unknown>) {
	return timingCollector.start(name, meta);
}

export function withTiming<T>(name: string, fn: () => T, meta?: Record<string, unknown>): T {
	return timingCollector.withTiming(name, fn, meta);
}

export function getPendingSpans() {
	return timingCollector.peek();
}

export function flushSpans() {
	return timingCollector.flush();
}

export function enableTiming(v: boolean) {
	timingCollector.setEnabled(v);
}
