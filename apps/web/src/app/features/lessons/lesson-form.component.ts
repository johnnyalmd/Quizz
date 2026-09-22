import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LessonService } from './lesson.service';

@Component({
  selector: 'app-lesson-form',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './lesson-form.component.html',
})
export class LessonFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private lessonService = inject(LessonService);

  lessonId: number | null = null;
  saving = false;
  loading = false;
  error = '';

  form = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(255)]],
    class_content: ['', Validators.required],
    learned_notes: ['', Validators.required],
  });

  get isEdit(): boolean {
    return this.lessonId !== null;
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      return;
    }
    this.lessonId = Number(id);
    this.loading = true;
    this.lessonService.get(this.lessonId).subscribe({
      next: (lesson) => {
        this.form.patchValue({
          title: lesson.title,
          class_content: lesson.class_content,
          learned_notes: lesson.learned_notes,
        });
        this.loading = false;
      },
      error: () => {
        this.error = 'Não foi possível carregar a aula.';
        this.loading = false;
      },
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.error = '';
    const payload = this.form.getRawValue();
    const request = this.lessonId
      ? this.lessonService.update(this.lessonId, payload)
      : this.lessonService.create(payload);

    request.subscribe({
      next: (lesson) => this.router.navigate(['/aulas', lesson.id]),
      error: () => {
        this.error = 'Não foi possível salvar a aula.';
        this.saving = false;
      },
    });
  }
}
