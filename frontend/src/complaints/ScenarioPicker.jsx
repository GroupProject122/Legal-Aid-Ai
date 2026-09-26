import React from 'react';
import {
  Banknote,
  Droplets,
  FileQuestion,
  FileWarning,
  Gavel,
  HeartHandshake,
  Megaphone
} from 'lucide-react';

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
  },
  {
    id: 'rti_application',
    icon: FileQuestion,
    title: 'Right to Information (RTI) application',
    act: 'Right to Information Act, 2005',
    description:
      'Draft a request to a government office for documents, records, or information it holds — you are not required to give a reason for asking.'
  },
  {
    id: 'rti_first_appeal',
    icon: FileQuestion,
    title: 'RTI first appeal',
    act: 'Right to Information Act, 2005',
    description:
      "Draft an appeal to the Appellate Authority when a public authority doesn't respond to your RTI request within 30 days, or rejects it, or gives incomplete information."
  },
  {
    id: 'senior_citizen_maintenance',
    icon: HeartHandshake,
    title: 'Senior citizen maintenance application',
    act: 'Maintenance and Welfare of Parents and Senior Citizens Act, 2007',
    description:
      'Draft an application to the Maintenance Tribunal for a monthly maintenance allowance from a child (or, if childless, a relative who holds/would inherit your property) who neglects or refuses to maintain you.'
  },
  {
    id: 'tenant_essential_supply',
    icon: Droplets,
    title: 'Landlord cut off water/electricity',
    act: 'Delhi Rent Control Act, 1958',
    description:
      'Draft a tenant application to the Rent Controller when a landlord cuts off or withholds water, electricity, passage/staircase lighting, or conservancy/sanitary services without just cause.'
  },
  {
    id: 'bank_fraud_complaint',
    icon: Banknote,
    title: 'Unauthorized bank transaction / fraud',
    act: 'RBI Limiting Liability Directions, 2017 + IT Act, 2000',
    description:
      "Draft a complaint to your bank about an unauthorized electronic transaction, computing your liability tier from the RBI's own reporting-window rules, plus a pointer to the National Cybercrime Reporting Portal."
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
