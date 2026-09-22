import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from '@angular/core';

@Component({
  selector: 'app-timer',
  template: `
    <div class="badge" [class.text-bg-danger]="secondsLeft <= 5" [class.text-bg-warning]="secondsLeft > 5">
      {{ secondsLeft }}s
    </div>
  `,
})
export class TimerComponent implements OnInit, OnChanges, OnDestroy {
  @Input() seconds = 30;
  @Input() resetKey = 0;
  @Output() expired = new EventEmitter<void>();

  secondsLeft = 30;
  private handle: ReturnType<typeof setInterval> | null = null;
  private emitted = false;

  ngOnInit(): void {
    this.start();
  }

  ngOnDestroy(): void {
    this.clear();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['resetKey'] && !changes['resetKey'].firstChange) {
      this.start();
    }
  }

  private start(): void {
    this.clear();
    this.emitted = false;
    this.secondsLeft = this.seconds;
    this.handle = setInterval(() => {
      this.secondsLeft -= 1;
      if (this.secondsLeft <= 0) {
        this.secondsLeft = 0;
        this.clear();
        if (!this.emitted) {
          this.emitted = true;
          this.expired.emit();
        }
      }
    }, 1000);
  }

  private clear(): void {
    if (this.handle) {
      clearInterval(this.handle);
      this.handle = null;
    }
  }
}
