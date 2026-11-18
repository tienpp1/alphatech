(() => {
    'use strict';
    const form = document.getElementById('revenue-research-form');
    if (!form) return;
    const button = document.getElementById('revenue-research-run');
    const status = document.getElementById('revenue-research-status');
    const result = document.getElementById('revenue-research-result');
    const number = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2});
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
            summary.textContent = `Dữ liệu ${data.start} – ${data.end}: ${data.observed}/${data.periods} ngày có quan sát, ${data.imputed} ngày điền 0 chưa xác nhận. Kiểm thử: ${data.holdout_observed}/${data.holdout_periods} ngày có quan sát. MAE XGBoost: ${number.format(data.metrics.xgboost.mae)} đ; MAE MA7: ${number.format(data.metrics.ma7.mae)} đ. ${data.warning}`;
            result.append(summary);
            const heading = document.createElement('h3');
            heading.textContent = '14 ngày dự báo thử nghiệm (đồng)';
            result.append(heading);
            const list = document.createElement('ul');
            for (const row of data.forecast) {
                const item = document.createElement('li');
                item.textContent = `${row.date}: ${number.format(row.value)} đ`;
                list.append(item);
            }
            result.append(list);
            status.textContent = 'Đã chạy thử nghiệm; không lưu hay thay đổi đơn hàng.';
        } catch (error) {
            status.textContent = error.message || 'Không thể kết nối; hãy thử lại sau.';
        } finally { button.disabled = false; }
    });
})();
