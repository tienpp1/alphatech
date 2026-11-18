(() => {
    'use strict';
    const form = document.getElementById('revenue-research-form');
    if (!form) return;
    const button = document.getElementById('revenue-research-run');
    const status = document.getElementById('revenue-research-status');
    const result = document.getElementById('revenue-research-result');
    const number = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2});
    function addTable(title, columns, rows) {
        const wrapper = document.createElement('div');
        wrapper.className = 'demo-scroll';
        wrapper.tabIndex = 0;
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', title + ' (có thể cuộn ngang)');
        const table = document.createElement('table');
        const caption = document.createElement('caption'); caption.textContent = title;
        const head = document.createElement('thead'); const header = document.createElement('tr');
        for (const column of columns) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = column; header.append(th); }
        head.append(header); const body = document.createElement('tbody');
        for (const values of rows) {
            const tr = document.createElement('tr');
            for (const value of values) { const td = document.createElement('td'); td.textContent = value; tr.append(td); }
            body.append(tr);
        }
        table.append(caption, head, body); wrapper.append(table); result.append(wrapper);
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (button.disabled) return;
        button.disabled = true;
        result.replaceChildren();
        status.textContent = 'Đang chạy thử nghiệm, vui lòng chờ…';
        try {
            const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin',
                headers: {'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value},
                body: new URLSearchParams({run: '1'})});
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Không thể chạy thử nghiệm.');
            const summary = document.createElement('p');
            summary.textContent = data.warning;
            result.append(summary);
            const facts = document.createElement('dl'); facts.className = 'demo-facts';
            for (const [label, value] of [
                ['Mô hình thực thi', 'XGBoost thử nghiệm'], ['Lịch sử đơn hoàn tất', `${data.periods} ngày`],
                ['Ngày có quan sát', `${data.observed}/${data.periods}`], ['Ngày điền 0 chưa xác nhận', data.imputed],
                ['Dữ liệu huấn luyện kiểm thử', `${data.training_periods} ngày đến ${data.training_end}`],
                ['Kỳ kiểm thử', `${data.holdout_start} → ${data.holdout_end}`],
                ['Ngày được chấm / kỳ kiểm thử', `${data.holdout_observed}/${data.holdout_periods}`],
                ['Giao thức đánh giá', '2 khối × 14 ngày'],
            ]) {
                const box = document.createElement('div'); const dt = document.createElement('dt'); const dd = document.createElement('dd');
                dt.textContent = label; dd.textContent = String(value); box.append(dt, dd); facts.append(box);
            }
            result.append(facts);
            addTable('Sai số trên cùng các ngày có quan sát (đồng)', ['Phương pháp', 'MAE', 'RMSE'],
                [['XGBoost', data.metrics.xgboost], ['MA7', data.metrics.ma7], ['Lặp theo tuần (lag-7)', data.metrics.lag7]]
                    .map(([name, metric]) => [name, number.format(metric.mae), number.format(metric.rmse)]));
            const note = document.createElement('p'); note.textContent = 'MAE và RMSE càng thấp càng tốt; các ngày thiếu quan sát không được chấm điểm.'; result.append(note);
            addTable('Đối chiếu ngày kiểm thử có quan sát (đồng)', ['Ngày', 'Mốc dự báo', 'Bước', 'Doanh thu ghi nhận', 'XGBoost', 'MA7', 'Lag-7'],
                data.holdout_rows.map(row => [row.date, row.origin, row.step, number.format(row.actual), number.format(row.prediction), number.format(row.ma7), number.format(row.naive)]));
            addTable('14 ngày dự báo thử nghiệm XGBoost (đồng)', ['Ngày', 'Dự báo'],
                data.forecast.map(row => [row.date, number.format(row.value)]));
            status.textContent = 'Đã chạy thử nghiệm; không lưu hay thay đổi đơn hàng.';
        } catch (error) {
            status.textContent = error.message || 'Không thể kết nối; hãy thử lại sau.';
        } finally { button.disabled = false; }
    });
})();
