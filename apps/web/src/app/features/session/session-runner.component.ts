import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { PhasePreview, SessionAnswer, SessionPhase, SessionQuestion, StudySession } from '@estudo-quiz/contracts';
import { TimerComponent } from '../../shared/timer.component';
import { ClozePromptComponent } from '../../shared/cloze-prompt.component';
import { SessionService } from './session.service';

@Component({
  selector: 'app-session-runner',
  imports: [FormsModule, RouterLink, TimerComponent, ClozePromptComponent],
  templateUrl: './session-runner.component.html',
})
export class SessionRunnerComponent implements OnInit {
  session: StudySession | null = null;
  loading = true;
  submitting = false;
  scoringPhase = false;
  error = '';
  phaseIndex = 0;
  questionIndex = 0;
  selectedIndex: number | null = null;
  clozeValues: string[] = [];
  mcqSelections: Record<number, number | string | null> = {};
  answers = new Map<number, SessionAnswer>();
  timerKey = 0;
  checkpoint: PhasePreview | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private sessionService: SessionService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.sessionService.get(id).subscribe({
      next: (session) => {
        this.session = session;
        this.loading = false;
        this.prepareCurrent();
      },
      error: () => {
        this.error = 'Sessão não encontrada ou já concluída.';
        this.loading = false;
      },
    });
  }

  get phase(): SessionPhase | null {
    return this.session?.phases[this.phaseIndex] ?? null;
  }

  get question(): SessionQuestion | null {
    return this.phase?.questions[this.questionIndex] ?? null;
  }

  get isMcqPhase(): boolean {
    return this.phase?.kind === 'mcq';
  }

  get isLastPhase(): boolean {
    return !!this.session && this.phaseIndex + 1 >= this.session.phases.length;
  }

  get progressLabel(): string {
    if (!this.phase) {
      return '';
    }
    if (this.checkpoint) {
      return `Fase ${this.phase.phase}/3 concluída`;
    }
    if (this.phase.kind === 'mcq') {
      return `Fase ${this.phase.phase}/3 · ${this.phase.questions.length} questões`;
    }
    return `Fase ${this.phase.phase}/3 · questão ${this.questionIndex + 1}/${this.phase.questions.length}`;
  }

  onClozeChange(values: string[]): void {
    this.clozeValues = values;
  }

  onExpired(): void {
    this.advance(true);
  }

  next(): void {
    this.advance(false);
  }

  keepPhaseScore(): void {
    if (!this.session) {
      return;
    }
    this.checkpoint = null;
    if (this.phaseIndex + 1 < this.session.phases.length) {
      this.phaseIndex += 1;
      this.questionIndex = 0;
      this.prepareCurrent();
      return;
    }
    this.submit();
  }

  restartPhase(): void {
    if (!this.phase) {
      return;
    }
    for (const question of this.phase.questions) {
      this.answers.delete(question.id);
    }
    this.checkpoint = null;
    this.error = '';
    this.questionIndex = 0;
    this.prepareCurrent();
  }

  private prepareCurrent(): void {
    this.selectedIndex = null;
    this.clozeValues = [];
    this.timerKey += 1;
    if (this.phase?.kind === 'mcq') {
      this.mcqSelections = {};
      for (const question of this.phase.questions) {
        this.mcqSelections[question.id] = null;
      }
    }
  }

  private storeMcqPhase(): boolean {
    if (!this.phase) {
      return false;
    }
    const missing = this.phase.questions.some(
      (question) => this.mcqSelections[question.id] === null || this.mcqSelections[question.id] === undefined,
    );
    if (missing) {
      this.error = 'Responda todas as questões da fase 1 antes de continuar.';
      return false;
    }
    this.error = '';
    for (const question of this.phase.questions) {
      this.answers.set(question.id, {
        question_id: question.id,
        selected_index: Number(this.mcqSelections[question.id]),
        selected_values: [],
        timed_out: false,
      });
    }
    return true;
  }

  private store(timedOut: boolean): void {
    const question = this.question;
    if (!question || !this.phase) {
      return;
    }
    this.answers.set(question.id, {
      question_id: question.id,
      selected_index: this.phase.kind === 'cloze' ? null : this.selectedIndex === null ? null : Number(this.selectedIndex),
      selected_values: this.phase.kind === 'cloze' ? this.clozeValues : [],
      timed_out: timedOut,
    });
  }

  private advance(timedOut: boolean): void {
    if (!this.session || !this.phase || this.checkpoint || this.scoringPhase) {
      return;
    }
    if (this.phase.kind === 'mcq') {
      if (!this.storeMcqPhase()) {
        return;
      }
      this.scoreCurrentPhase();
      return;
    }
    this.store(timedOut);
    if (this.questionIndex + 1 < this.phase.questions.length) {
      this.questionIndex += 1;
      this.prepareCurrent();
      return;
    }
    this.scoreCurrentPhase();
  }

  private scoreCurrentPhase(): void {
    if (!this.session || !this.phase) {
      return;
    }
    const answers = this.phase.questions
      .map((question) => this.answers.get(question.id))
      .filter((item): item is SessionAnswer => Boolean(item));
    if (answers.length !== this.phase.questions.length) {
      this.error = 'Não foi possível pontuar esta fase.';
      return;
    }
    this.scoringPhase = true;
    this.sessionService.preview(this.session.id, answers).subscribe({
      next: (preview) => {
        this.checkpoint = preview;
        this.scoringPhase = false;
      },
      error: () => {
        this.error = 'Não foi possível pontuar esta fase.';
        this.scoringPhase = false;
      },
    });
  }

  private submit(): void {
    if (!this.session || this.submitting) {
      return;
    }
    this.submitting = true;
    const payload = [...this.answers.values()];
    this.sessionService.submit(this.session.id, payload).subscribe({
      next: (result) => {
        this.sessionService.lastResult = result;
        this.router.navigate(['/sessoes', this.session!.id, 'resultado']);
      },
      error: () => {
        this.error = 'Não foi possível enviar as respostas.';
        this.submitting = false;
      },
    });
  }
}
