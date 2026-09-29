import { Component, OnInit } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ResultItem, SessionResult } from '@estudo-quiz/contracts';
import { SessionService } from './session.service';

@Component({
  selector: 'app-session-result',
  imports: [RouterLink, DecimalPipe],
  templateUrl: './session-result.component.html',
})
export class SessionResultComponent implements OnInit {
  result: SessionResult | null = null;
  loading = true;
  retrying = false;
  error = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private sessionService: SessionService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    const cached = this.sessionService.lastResult;
    if (cached?.id === id) {
      this.result = cached;
      this.loading = false;
      return;
    }
    this.sessionService.getResult(id).subscribe({
      next: (result) => {
        this.result = result;
        this.sessionService.lastResult = result;
        this.loading = false;
      },
      error: () => {
        this.error = 'Não foi possível carregar essa tentativa.';
        this.loading = false;
      },
    });
  }

  userAnswer(item: ResultItem): string {
    if (item.timed_out) {
      return 'Tempo esgotado';
    }
    if (item.kind === 'cloze') {
      return item.selected_values.join(', ') || '—';
    }
    if (item.selected_index === null || item.selected_index === undefined) {
      return '—';
    }
    return item.options[item.selected_index] ?? '—';
  }

  correctAnswer(item: ResultItem): string {
    if (item.kind === 'cloze') {
      return item.correct_values.join(', ') || '—';
    }
    if (item.correct_index === null || item.correct_index === undefined) {
      return '—';
    }
    return item.options[item.correct_index] ?? '—';
  }

  retry(): void {
    if (!this.result) {
      return;
    }
    this.retrying = true;
    this.sessionService.start(this.result.lesson).subscribe({
      next: (session) => this.router.navigate(['/sessoes', session.id]),
      error: (err) => {
        this.retrying = false;
        this.error = err?.error?.detail || 'Não foi possível criar outra sessão.';
      },
    });
  }
}
