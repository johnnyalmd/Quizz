import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PhasePreview, SessionAnswer, SessionResult, StudySession } from '@estudo-quiz/contracts';
import { API_URL } from '../../core/api';

@Injectable({ providedIn: 'root' })
export class SessionService {
  lastResult: SessionResult | null = null;

  constructor(private http: HttpClient) {}

  start(lessonId: number): Observable<StudySession> {
    return this.http.post<StudySession>(`${API_URL}/lessons/${lessonId}/sessions/`, {});
  }

  get(id: number): Observable<StudySession> {
    return this.http.get<StudySession>(`${API_URL}/sessions/${id}/`);
  }

  preview(id: number, answers: SessionAnswer[]): Observable<PhasePreview> {
    return this.http.post<PhasePreview>(`${API_URL}/sessions/${id}/preview/`, { answers });
  }

  submit(id: number, answers: SessionAnswer[]): Observable<SessionResult> {
    return this.http.post<SessionResult>(`${API_URL}/sessions/${id}/answers/`, { answers });
  }

  getResult(id: number): Observable<SessionResult> {
    return this.http.get<SessionResult>(`${API_URL}/sessions/${id}/result/`);
  }
}
