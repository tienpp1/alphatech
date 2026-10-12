// Exercise the actual inline handler; timer/provider behavior stays simulated.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const template = fs.readFileSync(path.join(__dirname, '../templates/public/service_request.html'), 'utf8');
const handler = template.match(/function selectPriority\([\s\S]*?(?=\r?\nfunction startSlaSimulation)/)[0];

function ui() {
  const input = {value: 'MEDIUM'};
  const display = {textContent: ''};
  const cards = new Map(['P1', 'P2', 'P3'].map(level => [level, {classList: {
    selected: level === 'P2',
    add(name) { if (name === 'selected') this.selected = true; },
    remove(name) { if (name === 'selected') this.selected = false; },
  }}]));
  let simulations = 0;
  const context = {selectedSlaMinutes: 30,
    startSlaSimulation() { simulations++; },
    document: {
      querySelectorAll(selector) { assert.equal(selector, '.priority-card'); return [...cards.values()]; },
      getElementById(id) {
        if (id === 'service-priority') return input;
        if (id === 'sla-display-text') return display;
        return cards.get(id.replace('pcard-', '').toUpperCase());
      },
    },
  };
  vm.runInNewContext(handler, context);
  return {context, input, display, cards, get simulations() { return simulations; }};
}

test('actual P1/P2/P3 handler sends HIGH/MEDIUM/LOW without a real SLA promise', () => {
  for (const [level, priority, minutes, label] of [
    ['P1', 'HIGH', 15, 'Khẩn cấp'], ['P2', 'MEDIUM', 30, 'Tiêu chuẩn'], ['P3', 'LOW', 120, 'Kế hoạch'],
  ]) {
    const app = ui();
    app.context.selectPriority(level, minutes, label);
    assert.equal(app.input.value, priority);
    assert.equal(app.context.selectedSlaMinutes, minutes);
    for (const [id, card] of app.cards) assert.equal(card.classList.selected, id === level);
    assert.match(app.display.textContent, /Ví dụ mô phỏng/);
    assert.match(app.display.textContent, /cần xác nhận thời gian thực tế/);
    assert.equal(app.simulations, 1);
  }
  assert.match(template, /id="pcard-p3" onclick="selectPriority\('P3', 120, 'Kế hoạch'\)"/);
});

test('unknown or inherited priority keys cannot change submitted priority', () => {
  for (const level of ['P4', '', '__proto__', 'constructor']) {
    const app = ui();
    app.context.selectPriority(level, 0, 'Invalid');
    assert.equal(app.input.value, 'MEDIUM');
    assert.equal(app.cards.get('P2').classList.selected, true);
    assert.equal(app.simulations, 0);
  }
});
