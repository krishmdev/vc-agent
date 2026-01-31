// Initial module structure and Sequoia resources

import { Module, ModuleId, SequoiaResource } from './dashboard-types';

export const initialModules: Record<ModuleId, Module> = {
  founder: {
    id: 'founder',
    title: 'Founder',
    description: 'Establish credibility, motivation, and founder–problem fit',
    icon: 'User',
    completionPercentage: 0,
    subsections: [
      {
        id: 'founder-main',
        title: 'Founder Background',
        questions: [
          {
            id: 'founder-motivation',
            label: 'Why do you care about this problem personally?',
            type: 'textarea',
            placeholder: 'Describe your personal connection to this problem...',
            value: '',
            completed: false,
          },
          {
            id: 'founder-uniqueness',
            label: 'What makes you uniquely suited to solve this?',
            type: 'textarea',
            placeholder: 'What experience, insight, or unfair advantage do you have?',
            helpText: 'Experience, insight, unfair advantage',
            value: '',
            completed: false,
          },
        ],
      },
    ],
  },

  problem: {
    id: 'problem',
    title: 'Problem',
    description: 'Prove the problem is real, painful, and worth solving',
    icon: 'AlertCircle',
    completionPercentage: 0,
    subsections: [
      {
        id: 'problem-statement',
        title: 'Problem Statement',
        questions: [
          {
            id: 'problem-formula',
            label: 'Problem statement',
            type: 'structured',
            structuredFormat: 'For [customer], [problem] causes [impact] because [root cause].',
            placeholder: 'For [customer], [problem] causes [impact] because [root cause]',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'problem-analysis',
        title: 'Problem Analysis',
        questions: [
          {
            id: 'problem-breaks',
            label: 'What breaks today?',
            type: 'textarea',
            placeholder: 'Describe what fails or breaks in the current situation...',
            value: '',
            completed: false,
          },
          {
            id: 'problem-persists',
            label: 'Why does this persist?',
            type: 'textarea',
            placeholder: 'Why hasn\'t this been solved already?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'problem-evidence',
        title: 'Evidence the Problem Exists',
        description: 'Provide 3 sources of evidence',
        questions: [
          {
            id: 'evidence-market',
            label: 'Market data',
            type: 'textarea',
            placeholder: 'Market research, studies, statistics...',
            value: '',
            completed: false,
          },
          {
            id: 'evidence-user',
            label: 'User quotes',
            type: 'textarea',
            placeholder: 'Direct quotes from potential users...',
            value: '',
            completed: false,
          },
          {
            id: 'evidence-behavioral',
            label: 'Behavioral evidence',
            type: 'textarea',
            placeholder: 'Observable behaviors that demonstrate the pain...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'problem-online',
        title: 'Evidence of Customer Pain Online',
        questions: [
          {
            id: 'pain-online',
            label: 'Forums, Reddit, Twitter, reviews',
            type: 'textarea',
            placeholder: 'Links and quotes from online discussions...',
            helpText: 'Provide links or screenshots from forums, Reddit, Twitter, reviews, etc.',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'problem-specialist',
        title: 'Specialist Review',
        questions: [
          {
            id: 'specialist-review',
            label: 'Problem Space Specialist Review (AI-powered)',
            type: 'readonly',
            placeholder: 'This will be generated after you complete the problem analysis',
            value: '',
            completed: false,
          },
        ],
      },
    ],
  },

  customer: {
    id: 'customer',
    title: 'Customer',
    description: 'Define exactly who feels the pain most',
    icon: 'Users',
    completionPercentage: 0,
    subsections: [
      {
        id: 'customer-who',
        title: 'Who Are You Building For?',
        questions: [
          {
            id: 'customer-description',
            label: 'Plain-language description',
            type: 'textarea',
            placeholder: 'Describe your target customer...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'customer-target',
        title: 'Target Audience & Early Adopters',
        questions: [
          {
            id: 'early-adopters',
            label: 'Who feels this pain first and strongest?',
            type: 'textarea',
            placeholder: 'Identify your early adopters...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'customer-cares',
        title: 'What Does Your Customer Care About?',
        questions: [
          {
            id: 'customer-metrics',
            label: 'Success metrics, anxieties, tradeoffs',
            type: 'textarea',
            placeholder: 'What keeps them up at night? What do they optimize for?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'customer-persona',
        title: 'Customer Persona / ICP',
        questions: [
          {
            id: 'persona-demographics',
            label: 'Demographics',
            type: 'textarea',
            placeholder: 'Age, location, role, company size, etc.',
            value: '',
            completed: false,
          },
          {
            id: 'persona-behaviors',
            label: 'Behaviors',
            type: 'textarea',
            placeholder: 'How do they currently solve this problem?',
            value: '',
            completed: false,
          },
          {
            id: 'persona-goals',
            label: 'Goals',
            type: 'textarea',
            placeholder: 'What are they trying to achieve?',
            value: '',
            completed: false,
          },
          {
            id: 'persona-frustrations',
            label: 'Frustrations',
            type: 'textarea',
            placeholder: 'What frustrates them about current solutions?',
            value: '',
            completed: false,
          },
          {
            id: 'persona-alternatives',
            label: 'Current alternatives',
            type: 'textarea',
            placeholder: 'What do they use today?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'customer-validation',
        title: 'Customer Validation',
        questions: [
          {
            id: 'validation-forum',
            label: 'Link to a forum or community',
            type: 'text',
            placeholder: 'https://...',
            value: '',
            completed: false,
          },
          {
            id: 'validation-conversations',
            label: 'Log user conversations',
            type: 'textarea',
            placeholder: 'Summarize conversations with potential customers...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'customer-review',
        title: 'Mentor + Specialist Review',
        questions: [
          {
            id: 'customer-specialist-review',
            label: 'Customer analysis (AI-powered synthesis)',
            type: 'readonly',
            placeholder: 'This will be generated after you complete the customer section',
            value: '',
            completed: false,
          },
        ],
      },
    ],
  },

  product: {
    id: 'product',
    title: 'Product',
    description: 'Define what you are building and why it matters',
    icon: 'Package',
    completionPercentage: 0,
    subsections: [
      {
        id: 'product-what',
        title: 'What Are You Building?',
        questions: [
          {
            id: 'product-description',
            label: 'High-level description',
            type: 'textarea',
            placeholder: 'Describe what you are building...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-purpose',
        title: 'Company Purpose',
        questions: [
          {
            id: 'company-purpose',
            label: 'Single declarative sentence',
            type: 'text',
            placeholder: 'We exist to...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-capabilities',
        title: 'What Does Your Product Need to Do?',
        questions: [
          {
            id: 'core-capabilities',
            label: 'Core capabilities only',
            type: 'textarea',
            placeholder: 'List the essential capabilities (not features)...',
            helpText: 'Focus on core capabilities, not feature bloat',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-differentiation',
        title: 'Differentiation & Moat',
        questions: [
          {
            id: 'differentiation',
            label: 'How are you different, not merely better?',
            type: 'textarea',
            placeholder: 'What makes you fundamentally different?',
            value: '',
            completed: false,
          },
          {
            id: 'moat',
            label: 'Why does this advantage compound over time?',
            type: 'textarea',
            placeholder: 'What is your sustainable competitive advantage?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-value',
        title: 'Value Creation',
        questions: [
          {
            id: 'value-customer',
            label: 'How is value created for the customer?',
            type: 'textarea',
            placeholder: 'Describe the value proposition...',
            value: '',
            completed: false,
          },
          {
            id: 'value-current',
            label: 'How do customers currently address the pain?',
            type: 'textarea',
            placeholder: 'What is the current alternative or workaround?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-timing',
        title: 'Why Now?',
        questions: [
          {
            id: 'why-now',
            label: 'Timing, inflection points, enabling forces',
            type: 'textarea',
            placeholder: 'What has changed to make this possible now?',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'product-risks',
        title: 'Product–Market Fit Risks',
        questions: [
          {
            id: 'pmf-risks',
            label: 'Terrifying questions checklist',
            type: 'textarea',
            placeholder: 'What could go wrong? What are you most afraid of?',
            value: '',
            completed: false,
          },
        ],
      },
    ],
  },

  market: {
    id: 'market',
    title: 'Market',
    description: 'Show this can be a venture-scale company',
    icon: 'TrendingUp',
    completionPercentage: 0,
    subsections: [
      {
        id: 'market-sizing',
        title: 'Market Sizing',
        questions: [
          {
            id: 'tam',
            label: 'TAM (Total Addressable Market)',
            type: 'text',
            placeholder: '$X billion',
            value: '',
            completed: false,
          },
          {
            id: 'sam',
            label: 'SAM (Serviceable Addressable Market)',
            type: 'text',
            placeholder: '$X million',
            value: '',
            completed: false,
          },
          {
            id: 'som',
            label: 'SOM (Serviceable Obtainable Market)',
            type: 'text',
            placeholder: '$X million in first 3 years',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'market-dynamics',
        title: 'Market Dynamics',
        questions: [
          {
            id: 'market-state',
            label: 'Growing, stagnant, or saturated?',
            type: 'textarea',
            placeholder: 'Describe the current market dynamics...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'market-competition',
        title: 'Competitive Landscape',
        questions: [
          {
            id: 'competitors',
            label: 'Direct + indirect competitors',
            type: 'textarea',
            placeholder: 'List competitors and how you differ...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'market-signals',
        title: 'Investment Signals',
        questions: [
          {
            id: 'capital-flow',
            label: 'Is capital flowing into the space?',
            type: 'textarea',
            placeholder: 'Recent investments, acquisitions, or funding rounds...',
            value: '',
            completed: false,
          },
        ],
      },
      {
        id: 'market-risks',
        title: 'Risks & Roadblocks',
        questions: [
          {
            id: 'risk-regulatory',
            label: 'Regulatory risks',
            type: 'textarea',
            placeholder: 'Legal or regulatory challenges...',
            value: '',
            completed: false,
          },
          {
            id: 'risk-platform',
            label: 'Platform dependencies',
            type: 'textarea',
            placeholder: 'Dependencies on other platforms or ecosystems...',
            value: '',
            completed: false,
          },
          {
            id: 'risk-structural',
            label: 'Structural constraints',
            type: 'textarea',
            placeholder: 'Fundamental constraints or limitations...',
            value: '',
            completed: false,
          },
        ],
      },
    ],
  },
};

export const sequoiaResources: SequoiaResource[] = [
  // Founder module resources
  {
    id: 'founder-market-fit',
    title: 'Founder–Market Fit',
    type: 'guidance',
    description: 'Why the founder\'s unique background matters for this problem',
    moduleId: 'founder',
    questionIds: ['founder-motivation', 'founder-uniqueness'],
  },
  {
    id: 'founder-narrative',
    title: 'Pitch Examples: Founder Narrative',
    type: 'example',
    description: 'How successful founders frame their personal journey',
    moduleId: 'founder',
  },

  // Problem module resources
  {
    id: 'problem-real',
    title: 'Great Companies Start with a Real Problem',
    type: 'article',
    description: 'Sequoia\'s framework for validating problem-solution fit',
    moduleId: 'problem',
    questionIds: ['problem-formula', 'problem-breaks'],
  },
  {
    id: 'problem-framing',
    title: 'Market Problem Framing',
    type: 'framework',
    description: 'How to articulate the problem in investor-grade language',
    moduleId: 'problem',
    questionIds: ['problem-formula'],
  },
  {
    id: 'problem-rigor',
    title: 'ARC-style Problem Rigor',
    type: 'guidance',
    description: 'Applying rigorous analysis to validate the problem',
    moduleId: 'problem',
  },

  // Customer module resources
  {
    id: 'customer-obsession',
    title: 'Customer Obsession',
    type: 'guidance',
    description: 'Sequoia\'s principles for understanding your customer deeply',
    moduleId: 'customer',
  },
  {
    id: 'icp-examples',
    title: 'ICP Examples from Strong Pitch Decks',
    type: 'example',
    description: 'How top companies define their ideal customer profile',
    moduleId: 'customer',
    questionIds: ['persona-demographics', 'persona-behaviors'],
  },

  // Product module resources
  {
    id: 'moat-differentiation',
    title: 'Moat and Differentiation',
    type: 'framework',
    description: 'Building sustainable competitive advantages',
    moduleId: 'product',
    questionIds: ['differentiation', 'moat'],
  },
  {
    id: 'pmf-heuristics',
    title: 'Product-Market Fit Heuristics',
    type: 'guidance',
    description: 'Sequoia\'s signals for validating PMF',
    moduleId: 'product',
    questionIds: ['pmf-risks'],
  },
  {
    id: 'why-now',
    title: 'The "Why Now?" Framework',
    type: 'framework',
    description: 'Identifying market inflection points and timing',
    moduleId: 'product',
    questionIds: ['why-now'],
  },

  // Market module resources
  {
    id: 'market-sizing',
    title: 'Market Sizing Guidance',
    type: 'guidance',
    description: 'How to calculate and present TAM/SAM/SOM',
    moduleId: 'market',
    questionIds: ['tam', 'sam', 'som'],
  },
  {
    id: 'competitive-analysis',
    title: 'Competitive Analysis Examples',
    type: 'example',
    description: 'How to position against direct and indirect competitors',
    moduleId: 'market',
    questionIds: ['competitors'],
  },
];
