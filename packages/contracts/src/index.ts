export type QuestionKind = 'mcq' | 'cloze' | 'scenario';
export type BankStatus = 'pending' | 'ready' | 'failed';
export type SessionStatus = 'in_progress' | 'completed';

export interface LessonPayload {
  title: string;
  class_content: string;
  learned_notes: string;
}

export interface LatestBank {
  id: number;
  status: BankStatus;
  error_message: string;
  created_at: string;
  counts: {
    mcq: number;
    cloze: number;
    scenario: number;
  };
}

export interface Lesson {
  id: number;
  title: string;
  class_content: string;
  learned_notes: string;
  created_at: string;
  updated_at: string;
  latest_bank: LatestBank | null;
}

export interface SessionQuestion {
  id: number;
  kind: QuestionKind;
  prompt: string;
  options: string[];
  blank_count: number;
}

export interface SessionPhase {
  phase: 1 | 2 | 3;
  kind: QuestionKind;
  time_limit_seconds: number | null;
  questions: SessionQuestion[];
}

export interface StudySession {
  id: number;
  lesson: number;
  lesson_title: string;
  status: SessionStatus;
  phases: SessionPhase[];
}

export interface SessionAnswer {
  question_id: number;
  selected_index?: number | null;
  selected_values?: string[];
  timed_out: boolean;
}

export interface ResultItem {
  question_id: number;
  kind: QuestionKind;
  phase: number;
  topic: string;
  prompt: string;
  options: string[];
  selected_index: number | null;
  selected_values: string[];
  correct_index: number | null;
  correct_values: string[];
  timed_out: boolean;
  is_correct: boolean;
  explanation: string;
}

export interface StudyAdvice {
  topic: string;
  missed: number;
  advice: string;
}

export interface PhaseScore {
  phase: number;
  kind: QuestionKind;
  score: number;
  total: number;
}

export interface SessionResult {
  id: number;
  lesson: number;
  status: SessionStatus;
  score: number;
  total: number;
  phase_scores: PhaseScore[];
  study_plan: StudyAdvice[];
  results: ResultItem[];
  created_at: string;
}
