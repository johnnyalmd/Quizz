import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Lesson } from '@estudo-quiz/contracts';
import { LessonService } from './lesson.service';

@Component({
  selector: 'app-lesson-list',
  imports: [RouterLink, DatePipe],
  templateUrl: './lesson-list.component.html',
})
export class LessonListComponent implements OnInit {
  lessons: Lesson[] = [];
  loading = true;
  error = '';

  constructor(private lessonService: LessonService) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.error = '';
    this.lessonService.list().subscribe({
      next: (lessons) => {
        this.lessons = lessons;
        this.loading = false;
      },
      error: () => {
        this.error = 'Não foi possível carregar as aulas. Suba a API em http://localhost:8000.';
        this.loading = false;
      },
    });
  }

  bankLabel(lesson: Lesson): string {
    const bank = lesson.latest_bank;
    if (!bank) {
      return '';
    }
    if (bank.status === 'ready') {
      return ' · Banco pronto';
    }
    if (bank.status === 'failed') {
      return ' · Banco falhou';
    }
    return ' · Gerando banco';
  }

  remove(lesson: Lesson, event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    if (!confirm(`Excluir a aula "${lesson.title}"?`)) {
      return;
    }
    this.lessonService.delete(lesson.id).subscribe({
      next: () => {
        this.lessons = this.lessons.filter((item) => item.id !== lesson.id);
      },
      error: () => {
        this.error = 'Não foi possível excluir a aula.';
      },
    });
  }
}
