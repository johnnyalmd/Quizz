import { Component, EventEmitter, Input, Output } from '@angular/core';
import { SessionQuestion } from '@estudo-quiz/contracts';

@Component({
  selector: 'app-cloze-prompt',
  templateUrl: './cloze-prompt.component.html',
})
export class ClozePromptComponent {
  @Input({ required: true }) question!: SessionQuestion;
  @Input() values: string[] = [];
  @Output() valuesChange = new EventEmitter<string[]>();

  get parts(): string[] {
    return this.question.prompt.split('___');
  }

  get remainingChips(): string[] {
    const used = [...this.values];
    return this.question.options.filter((option) => {
      const index = used.indexOf(option);
      if (index === -1) {
        return true;
      }
      used.splice(index, 1);
      return false;
    });
  }

  fill(option: string): void {
    if (this.values.length >= this.question.blank_count) {
      return;
    }
    this.valuesChange.emit([...this.values, option]);
  }

  clearBlank(index: number): void {
    const next = this.values.filter((_, current) => current !== index);
    this.valuesChange.emit(next);
  }
}
