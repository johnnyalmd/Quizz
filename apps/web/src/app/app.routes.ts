import { Routes } from '@angular/router';
import { LessonListComponent } from './features/lessons/lesson-list.component';
import { LessonFormComponent } from './features/lessons/lesson-form.component';
import { LessonDetailComponent } from './features/lessons/lesson-detail.component';
import { SessionRunnerComponent } from './features/session/session-runner.component';
import { SessionResultComponent } from './features/session/session-result.component';

export const routes: Routes = [
  { path: '', component: LessonListComponent },
  { path: 'aulas/nova', component: LessonFormComponent },
  { path: 'aulas/:id/editar', component: LessonFormComponent },
  { path: 'aulas/:id', component: LessonDetailComponent },
  { path: 'sessoes/:id', component: SessionRunnerComponent },
  { path: 'sessoes/:id/resultado', component: SessionResultComponent },
  { path: '**', redirectTo: '' },
];
