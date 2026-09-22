import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Lesson, LessonPayload, LatestBank } from '@estudo-quiz/contracts';
import { API_URL } from '../../core/api';

@Injectable({ providedIn: 'root' })
export class LessonService {
  constructor(private http: HttpClient) {}

  list(): Observable<Lesson[]> {
    return this.http.get<Lesson[]>(`${API_URL}/lessons/`);
  }

  get(id: number): Observable<Lesson> {
    return this.http.get<Lesson>(`${API_URL}/lessons/${id}/`);
  }

  create(payload: LessonPayload): Observable<Lesson> {
    return this.http.post<Lesson>(`${API_URL}/lessons/`, payload);
  }

  update(id: number, payload: LessonPayload): Observable<Lesson> {
    return this.http.put<Lesson>(`${API_URL}/lessons/${id}/`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${API_URL}/lessons/${id}/`);
  }

  generateBank(id: number): Observable<LatestBank> {
    return this.http.post<LatestBank>(`${API_URL}/lessons/${id}/generate-bank/`, {});
  }
}
