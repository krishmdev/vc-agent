// Dashboard module and question types for the redesigned product dashboard

export type ModuleId = 'founder' | 'problem' | 'customer' | 'product' | 'market';

export type QuestionType = 'text' | 'textarea' | 'structured' | 'list' | 'readonly';

export interface Question {
  id: string;
  label: string;
  placeholder?: string;
  type: QuestionType;
  helpText?: string;
  structuredFormat?: string; // For structured inputs like "For [X], [Y] causes [Z]"
  listItems?: string[]; // For list-type questions (e.g., evidence sources)
  minItems?: number; // Minimum required items for lists
  value: string | string[];
  completed: boolean;
}

export interface Subsection {
  id: string;
  title: string;
  description?: string;
  questions: Question[];
}

export interface Module {
  id: ModuleId;
  title: string;
  description: string;
  subsections: Subsection[];
  icon: string; // Lucide icon name
  completionPercentage: number;
}

export interface SequoiaResource {
  id: string;
  title: string;
  type: 'article' | 'framework' | 'example' | 'guidance';
  description: string;
  url?: string;
  moduleId: ModuleId;
  questionIds?: string[]; // Optional: specific questions this resource relates to
}

export interface DashboardState {
  activeModuleId: ModuleId | null;
  modules: Record<ModuleId, Module>;
  expandedModule: ModuleId | null;
  globalProgress: number;
}
