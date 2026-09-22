import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { SessionAnswer, SessionPhase, SessionQuestion, StudySession } from '@estudo-quiz/contracts';
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
  error = '';
  phaseIndex = 0;
  questionIndex = 0;
  selectedIndex: number | null = null;
  clozeValues: string[] = [];
  answers = new Map<number, SessionAnswer>();
  timerKey = 0;

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

  get progressLabel(): string {
    if (!this.phase) {
      return '';
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

  private prepareCurrent(): void {
    this.selectedIndex = null;
    this.clozeValues = [];
    this.timerKey += 1;
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
    if (!this.session || !this.phase) {
      return;
    }
    this.store(timedOut);
    if (this.questionIndex + 1 < this.phase.questions.length) {
      this.questionIndex += 1;
      this.prepareCurrent();
      return;
    }
    if (this.phaseIndex + 1 < this.session.phases.length) {
      this.phaseIndex += 1;
      this.questionIndex = 0;
      this.prepareCurrent();
      return;
    }
    this.submit();
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
