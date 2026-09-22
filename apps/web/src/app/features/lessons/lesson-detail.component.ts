import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LatestBank, Lesson } from '@estudo-quiz/contracts';
import { LessonService } from './lesson.service';
import { SessionService } from '../session/session.service';

@Component({
  selector: 'app-lesson-detail',
  imports: [RouterLink, DatePipe],
  templateUrl: './lesson-detail.component.html',
})
export class LessonDetailComponent implements OnInit {
  lesson: Lesson | null = null;
  loading = true;
  generating = false;
  starting = false;
  error = '';
  generateError = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private lessonService: LessonService,
    private sessionService: SessionService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.lessonService.get(id).subscribe({
      next: (lesson) => {
        this.lesson = lesson;
        this.loading = false;
      },
      error: () => {
        this.error = 'Aula não encontrada.';
        this.loading = false;
      },
    });
  }

  generateBank(): void {
    if (!this.lesson) {
      return;
    }
    this.generating = true;
    this.generateError = '';
    this.lessonService.generateBank(this.lesson.id).subscribe({
      next: (bank: LatestBank) => {
        this.generating = false;
        if (bank.status !== 'ready') {
          this.generateError = bank.error_message || 'A IA não conseguiu gerar o banco.';
        }
        this.lessonService.get(this.lesson!.id).subscribe((lesson) => (this.lesson = lesson));
      },
      error: (err) => {
        this.generating = false;
        const bank = err?.error as LatestBank | undefined;
        this.generateError =
          bank?.error_message ||
          'Falha ao gerar o banco. Confira o HF_TOKEN e o modelo gratuito.';
        if (this.lesson) {
          this.lessonService.get(this.lesson.id).subscribe((lesson) => (this.lesson = lesson));
        }
      },
    });
  }

  startSession(): void {
    if (!this.lesson) {
      return;
    }
    this.starting = true;
    this.sessionService.start(this.lesson.id).subscribe({
      next: (session) => this.router.navigate(['/sessoes', session.id]),
      error: (err) => {
        this.starting = false;
        this.generateError = err?.error?.detail || 'Não foi possível iniciar a sessão.';
      },
    });
  }
}
