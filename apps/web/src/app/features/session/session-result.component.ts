import { Component } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { SessionResult } from '@estudo-quiz/contracts';
import { SessionService } from './session.service';

@Component({
  selector: 'app-session-result',
  imports: [RouterLink, DecimalPipe],
  templateUrl: './session-result.component.html',
})
export class SessionResultComponent {
  result: SessionResult | null;
  retrying = false;
  error = '';

  constructor(
    private router: Router,
    private sessionService: SessionService,
  ) {
    this.result = this.sessionService.lastResult;
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
