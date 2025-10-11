import React from 'react';
import { TrustGatePanel } from './Dashboard/TrustGatePanel.js';

export function DashboardPage(): React.ReactElement {
  return (
    <main className="space-y-4 bg-neutral-950 p-4 text-neutral-100" aria-labelledby="dashboard-title">
      <h1 id="dashboard-title" className="text-2xl font-semibold">Operational Dashboard</h1>
      <p className="text-sm text-neutral-400 max-w-2xl">
        Monitor cross-system health at a glance. Trust gate metrics stream directly from Prometheus to surface
        failures before they impact Masters validation.
      </p>
      <TrustGatePanel />
    </main>
  );
}

export default DashboardPage;
