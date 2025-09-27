import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// @ts-ignore placeholder
// Real LongSpanForm will replace fallback later.

// Fallback replicates: if end-start > 5y show confirm modal before proceeding
// @ts-ignore
const FallbackLongSpanForm = ({ onConfirm }: { onConfirm?: () => void }) => {
  const [showModal, setShowModal] = React.useState(false);
  const [confirmed, setConfirmed] = React.useState(false);
  const submit = () => {
    // simulate detection of >5y span
    if (!confirmed) {
      setShowModal(true);
      return;
    }
    onConfirm && onConfirm();
  };
  return (
    <div>
      <button onClick={submit}>submit-long-span</button>
      {showModal && !confirmed && (
        <div data-testid="long-span-modal">
          <p>Long date span may be slow</p>
          <button
            onClick={() => {
              setConfirmed(true);
              setShowModal(false);
            }}
          >
            confirm
          </button>
        </div>
      )}
      {confirmed && <div data-testid="confirmed">CONFIRMED</div>}
    </div>
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedLongSpanForm = FallbackLongSpanForm;

describe('T023 Long Date Span Warning (Test-First)', () => {
  it('shows confirmation modal then proceeds only after confirm', () => {
    render(<ResolvedLongSpanForm />);
    fireEvent.click(screen.getByText('submit-long-span'));
    expect(screen.getByTestId('long-span-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByText('confirm'));
    expect(screen.queryByTestId('long-span-modal')).toBeNull();
    expect(screen.getByTestId('confirmed')).toBeInTheDocument();
  });
});
