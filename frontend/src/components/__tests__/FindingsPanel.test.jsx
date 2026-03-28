import { describe, expect, it } from 'vitest';
import FindingsPanel from '../FindingsPanel';
import { renderWithProviders, screen } from '../../test/utils';

const resultWithFindings = {
  parallel_review: {
    findings: [
      {
        finding_id: 'finding-high',
        title: 'Critical gap',
        detail: 'A major acceptance criterion is missing.',
        severity: 'high',
      },
      {
        finding_id: 'finding-low',
        title: 'Minor copy tweak',
        detail: 'Some wording can be tightened.',
        severity: 'low',
      },
    ],
  },
};

describe('FindingsPanel', () => {
  it('shows an empty state when no findings are available', () => {
    renderWithProviders(<FindingsPanel result={null} status="idle" resultState="idle" />);

    expect(screen.getByText('No findings are available for this run yet.')).toBeInTheDocument();
  });

  it('renders the findings list when findings exist', () => {
    renderWithProviders(<FindingsPanel result={resultWithFindings} status="completed" resultState="ready" />);

    expect(screen.getByText('Critical gap')).toBeInTheDocument();
    expect(screen.getByText('Minor copy tweak')).toBeInTheDocument();
    expect(screen.getByText('A major acceptance criterion is missing.')).toBeInTheDocument();
  });

  it('maps severity values to the expected severity classes', () => {
    renderWithProviders(<FindingsPanel result={resultWithFindings} status="completed" resultState="ready" />);

    expect(screen.getByText('high')).toHaveClass('severity-high');
    expect(screen.getByText('low')).toHaveClass('severity-low');
  });
});
