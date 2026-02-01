// Initial data for dashboard modules
import { Module, ModuleId, SequoiaResource } from "./dashboard-types"

// Sequoia resources for each module
export const sequoiaResources: SequoiaResource[] = [
    // Founder resources
    {
        id: 'founder-1',
        title: 'Founder-Market Fit',
        type: 'framework',
        description: 'Why the best founders have deep personal connection to the problem they solve.',
        moduleId: 'founder',
    },
    {
        id: 'founder-2',
        title: 'The Idea Maze',
        type: 'article',
        description: 'Understanding the history and evolution of your space gives you an edge.',
        url: 'https://sequoiacap.com',
        moduleId: 'founder',
    },
    // Problem resources
    {
        id: 'problem-1',
        title: 'Hair on Fire Problem',
        type: 'framework',
        description: 'The best problems are so urgent that customers will use an imperfect solution.',
        moduleId: 'problem',
        questionIds: ['hair-on-fire'],
    },
    {
        id: 'problem-2',
        title: 'Problem Definition Template',
        type: 'guidance',
        description: 'For [target customer], [problem] causes [negative outcome].',
        moduleId: 'problem',
        questionIds: ['problem-statement'],
    },
    // Customer resources
    {
        id: 'customer-1',
        title: 'Early Adopter Profile',
        type: 'framework',
        description: 'Your first 100 customers define your trajectory. Choose wisely.',
        moduleId: 'customer',
    },
    {
        id: 'customer-2',
        title: 'Customer Evidence Hierarchy',
        type: 'guidance',
        description: 'Revenue > Waitlist > Interviews > Surveys > Assumptions',
        moduleId: 'customer',
        questionIds: ['customer-evidence'],
    },
    // Product resources
    {
        id: 'product-1',
        title: 'Minimum Viable Product',
        type: 'framework',
        description: 'The smallest thing you can build to test your riskiest assumption.',
        moduleId: 'product',
        questionIds: ['mvp-scope'],
    },
    {
        id: 'product-2',
        title: 'Unique Insight',
        type: 'example',
        description: 'Airbnb knew strangers would trust each other. Stripe knew developers wanted simple APIs.',
        moduleId: 'product',
        questionIds: ['unique-insight'],
    },
    // Market resources
    {
        id: 'market-1',
        title: 'Why Now?',
        type: 'framework',
        description: 'The best companies are built on secular trends and technology shifts.',
        moduleId: 'market',
        questionIds: ['why-now'],
    },
    {
        id: 'market-2',
        title: 'TAM/SAM/SOM Framework',
        type: 'guidance',
        description: 'Bottom-up market sizing is more credible than top-down estimates.',
        moduleId: 'market',
        questionIds: ['tam'],
    },
]

export const initialModules: Record<ModuleId, Module> = {
    founder: {
        id: 'founder',
        title: 'Founder',
        description: 'Your background and motivation',
        icon: 'User',
        completionPercentage: 0,
        subsections: [
            {
                id: 'background',
                title: 'Background',
                description: 'Tell us about yourself',
                questions: [
                    {
                        id: 'founder-name',
                        label: 'Your Name',
                        placeholder: 'Enter your full name',
                        type: 'text',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'founder-background',
                        label: 'Background',
                        placeholder: 'What is your professional background?',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'founder-motivation',
                        label: 'Why This Problem?',
                        placeholder: 'What drives you to solve this problem?',
                        type: 'textarea',
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
        description: 'The pain point you are solving',
        icon: 'AlertTriangle',
        completionPercentage: 0,
        subsections: [
            {
                id: 'problem-definition',
                title: 'Problem Definition',
                description: 'Define the core problem',
                questions: [
                    {
                        id: 'problem-statement',
                        label: 'Problem Statement',
                        placeholder: 'Describe the problem in one sentence',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'who-has-problem',
                        label: 'Who Has This Problem?',
                        placeholder: 'Be specific about who experiences this pain',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'hair-on-fire',
                        label: 'Is This a "Hair on Fire" Problem?',
                        helpText: 'A hair-on-fire problem is urgent and painful enough that people will pay immediately',
                        placeholder: 'Why is this problem urgent and painful?',
                        type: 'textarea',
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
        description: 'Your target user and buyer',
        icon: 'Users',
        completionPercentage: 0,
        subsections: [
            {
                id: 'customer-profile',
                title: 'Customer Profile',
                description: 'Define your ideal customer',
                questions: [
                    {
                        id: 'ideal-customer',
                        label: 'Ideal Customer',
                        placeholder: 'Describe your ideal customer persona',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'customer-evidence',
                        label: 'Customer Evidence',
                        helpText: 'What evidence do you have that customers want this?',
                        placeholder: 'Interviews, surveys, waitlist signups, etc.',
                        type: 'list',
                        listItems: [''],
                        minItems: 1,
                        value: [''],
                        completed: false,
                    },
                ],
            },
        ],
    },
    product: {
        id: 'product',
        title: 'Product',
        description: 'Your solution and MVP',
        icon: 'Package',
        completionPercentage: 0,
        subsections: [
            {
                id: 'solution',
                title: 'Solution',
                description: 'How you solve the problem',
                questions: [
                    {
                        id: 'solution-description',
                        label: 'Solution Description',
                        placeholder: 'How does your product solve the problem?',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'unique-insight',
                        label: 'Unique Insight',
                        helpText: 'What do you know that others don\'t?',
                        placeholder: 'Your unfair advantage or secret',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'mvp-scope',
                        label: 'MVP Scope',
                        placeholder: 'What is the smallest thing you can build to test this?',
                        type: 'textarea',
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
        description: 'Market size and competition',
        icon: 'TrendingUp',
        completionPercentage: 0,
        subsections: [
            {
                id: 'market-size',
                title: 'Market Size',
                description: 'How big is the opportunity?',
                questions: [
                    {
                        id: 'tam',
                        label: 'Total Addressable Market',
                        placeholder: 'What is the total market size?',
                        type: 'text',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'why-now',
                        label: 'Why Now?',
                        helpText: 'Why is this the right time for this solution?',
                        placeholder: 'What has changed to make this possible now?',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                    {
                        id: 'competition',
                        label: 'Competition',
                        placeholder: 'Who else is solving this problem?',
                        type: 'textarea',
                        value: '',
                        completed: false,
                    },
                ],
            },
        ],
    },
}
