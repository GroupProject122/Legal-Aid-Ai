import React from 'react';
import { FileWarning, Gavel, Megaphone } from 'lucide-react';

export const SCENARIOS = [
  {
    id: 'tenancy_eviction',
    icon: Gavel,
    title: 'Tenancy eviction petition',
    act: 'Delhi Rent Control Act, 1958',
    description:
      'Draft an eviction petition against a tenant on one or more grounds: non-payment of rent, unauthorized subletting, damage to the premises, and/or bona fide personal requirement.'
  },
  {
    id: 'consumer_defective_goods',
    icon: FileWarning,
    title: 'Defective goods or deficient service',
    act: 'Consumer Protection Act, 2019',
    description:
      'Draft a complaint for a refund, replacement, and/or compensation over defective goods, a deficient service, short delivery, spurious goods, or an unfair trade practice.'
  },
  {
    id: 'consumer_misleading_ads',
    icon: Megaphone,
    title: 'Misleading advertisement or dark pattern',
    act: 'Consumer Protection Act, 2019',
    description:
      'Draft a complaint over a false claim, a misleading price, a false guarantee, a surrogate advertisement, or a deceptive "dark pattern" design.'
  }
];

export function ScenarioPicker({ onSelect }) {
  return (
    <div className="complaint-scenario-grid">
      {SCENARIOS.map((scenario) => {
        const Icon = scenario.icon;
        return (
          <button
            type="button"
            className="complaint-scenario-card"
            key={scenario.id}
            onClick={() => onSelect(scenario.id)}
          >
            <div className="complaint-scenario-icon">
              <Icon size={26} strokeWidth={1.6} />
            </div>
            <h3>{scenario.title}</h3>
            <p className="complaint-scenario-act">{scenario.act}</p>
            <p className="complaint-scenario-description">{scenario.description}</p>
            <span className="complaint-scenario-cta">Start this complaint →</span>
          </button>
        );
      })}
    </div>
  );
}
