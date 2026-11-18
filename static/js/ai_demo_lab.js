(() => {
    'use strict';

    const $ = id => document.getElementById('demo-' + id);
    const form = $('form');
    if (!form) return;
    const select = $('case'), run = $('run'), panel = $('panel'), status = $('status');
    const output = $('result'), error = $('error'), previous = $('previous'), empty = $('empty');
    const caveat = $('caveat').textContent;
    const formatter = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 4});
    const number = value => Number.isFinite(value) ? formatter.format(value) : '—';
    const yesNo = value => value ? 'Có' : 'Không';

    function node(tag, text) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text ?? '—';
        return element;
    }

    function facts(items) {
        const list = node('dl');
        list.className = 'demo-facts';
        for (const [label, value] of items) {
            const item = node('div');
            item.append(node('dt', label), node('dd', value));
            list.append(item);
        }
        return list;
    }

    function table(title, columns, rows) {
        const wrapper = node('div');
        wrapper.className = 'demo-scroll';
        wrapper.setAttribute('tabindex', '0');
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', title + ' (có thể cuộn ngang)');
        const grid = node('table');
        const head = node('thead'), headings = node('tr'), body = node('tbody');
        for (const label of columns) {
            const th = node('th', label);
            th.setAttribute('scope', 'col');
            headings.append(th);
        }
        head.append(headings);
        for (const cells of rows) {
            const row = node('tr');
            row.append(...cells.map(value => node('td', value)));
            body.append(row);
        }
        grid.append(node('caption', title), head, body);
        wrapper.append(grid);
        return wrapper;
    }

    function timestamp(value) {
        const time = node('time', value);
        time.setAttribute('datetime', value);
        return time;
    }

    function showForecast(parent, data) {
        const comparisons = [
            ['XGBoost', data.metrics.xgboost], ['MA7', data.metrics.ma7],
            ['Lặp theo tuần (lag-7)', data.metrics.seasonal_naive_7],
        ];
        parent.append(
            node('p', 'Máy chủ suy luận từ mô hình huấn luyện ngoại tuyến đã chốt trước kỳ đánh giá; không huấn luyện lại.'),
            facts([
                ['Mô hình thực thi', data.model],
                ['Đặc trưng lịch', data.calendar_mode === 'full' ? 'Đầy đủ' : data.calendar_mode],
                ['Ngày cuối dùng để huấn luyện', data.training_cutoff],
                ['Lịch sử mô phỏng', number(data.history_rows) + ' ngày'],
                ['Dữ liệu huấn luyện', number(data.training_rows) + ' ngày'],
                ['Kỳ đánh giá', data.holdout_start + ' → ' + data.holdout_end],
                ['Số ngày chấm / kỳ đánh giá', number(data.scored_rows) + ' / ' + number(data.holdout_rows)],
                ['Ngày không đủ khối để chấm', number(data.omitted_rows)],
                ['Giao thức đánh giá', number(data.blocks) + ' khối × ' + number(data.horizon) + ' bước'],
            ]),
            table('Sai số trên cùng tập ngày được chấm (đồng mô phỏng)', ['Phương pháp', 'MAE', 'RMSE'],
                comparisons.map(([name, metrics]) => [name, number(metrics.mae), number(metrics.rmse)])),
            node('p', 'MAE là sai số tuyệt đối trung bình; RMSE nhạy hơn với sai số lớn. Cùng một tập ngày, giá trị nhỏ hơn là tốt hơn.'),
            table('Mẫu đối chiếu từ khối đầu (đồng mô phỏng)', ['Ngày', 'Mốc dự báo', 'Bước', 'Thực tế mô phỏng', 'XGBoost', 'MA7', 'Lag-7'],
                data.sample_rows.map(row => [row.date, row.origin, number(row.step), number(row.actual),
                    number(row.prediction), number(row.ma7), number(row.naive)])),
        );
    }

    function showRetrieval(parent, data) {
        parent.append(
            node('p', 'Chỉ trình diễn thành phần truy xuất; không gọi LLM hoặc API embedding, không kiểm chứng toàn bộ RAG.'),
            facts([['Truy vấn mẫu', data.query], ['Số chiều vectơ băm', number(data.embedding_dimension)],
                ['Nguồn trích đoạn được chọn', data.source]]),
            node('h3', 'Trả lời bằng trích đoạn được chọn'),
            node('p', data.answer),
            table('Xếp hạng hai nguồn mô phỏng', ['Nguồn', 'Tiêu đề', 'Trích đoạn', 'Cosine', 'Khớp từ', 'Điểm tổng hợp'],
                data.candidates.map(row => [row.source, row.title, row.excerpt, number(row.dense_similarity),
                    number(row.lexical_score), number(row.similarity)])),
        );
    }

    function showMapping(parent, data) {
        const mappingState = data.confirmation_status === 'ACCEPTED' ? 'Đã xác nhận mô phỏng' : 'Chưa xác nhận';
        const mapped = Object.entries(data.after);
        parent.append(
            facts([['Đối tượng mô phỏng', data.entity], ['Trạng thái quy tắc', mappingState]]),
            table('Trường trước khi chuyển đổi', ['Cột nguồn', 'Giá trị mẫu'], Object.entries(data.before)),
            mapped.length
                ? table('Trường sau khi chuyển đổi trong bộ nhớ', ['Trường đích', 'Giá trị mẫu'], mapped)
                : node('p', 'Sau khi chuyển đổi: không có trường nào được ánh xạ.'),
            table('Gợi ý ánh xạ (điểm khớp heuristic)', ['Cột nguồn', 'Trường đích', 'Loại quy tắc', 'Điểm khớp (0–1)'],
                data.suggestions.map(row => [row.source_field, row.suggested_target_field,
                    row.suggested_rule_type, number(row.confidence)])),
            data.errors.length
                ? table('Lỗi giá trị khi chuyển đổi', ['Cột nguồn', 'Trường đích', 'Loại quy tắc', 'Lỗi'],
                    data.errors.map(row => [row.source_field, row.target_field, row.rule_type, row.error]))
                : node('p', 'Không có lỗi được trả về cho lần chuyển đổi này.'),
        );
    }

    function showRecommendation(parent, data) {
        const tool = data.tool, weights = data.candidates[0].weights;
        const stages = node('ol');
        stages.append(...data.approval_preview.map(stage => node('li', stage)));
        parent.append(
            facts([['Kỹ thuật viên xếp đầu', data.selected_candidate],
                ['Trọng số khoảng cách / tải / kỹ năng',
                    [weights.distance, weights.workload, weights.skill].map(number).join(' / ')]]),
            node('p', 'Ứng viên không sẵn sàng không được chọn, dù ở gần hoặc ít việc.'),
            table('Ứng viên mô phỏng và điểm thành phần', ['Kỹ thuật viên', 'Khoảng cách (km)', 'Việc đang làm',
                'Sẵn sàng?', 'Điểm khoảng cách', 'Điểm tải', 'Điểm kỹ năng', 'Điểm sẵn sàng', 'Điểm tổng'],
            data.candidates.map(row => [
                row.name, number(row.distance_km), number(row.active_tasks), yesNo(row.is_available),
                number(row.subscores.distance_score), number(row.subscores.workload_score),
                number(row.subscores.skill_score), number(row.subscores.availability_score), number(row.score),
            ])),
            node('h3', 'Xem trước phê duyệt — chỉ kiểm tra cấu trúc tham số'),
            node('p', 'Không kiểm tra dữ liệu nghiệp vụ, không cấp quyền và không thực thi phân công.'),
            facts([['Công cụ nghiệp vụ', tool.name], ['Loại công cụ', tool.classification],
                ['Mức rủi ro', tool.risk_level], ['Quyền yêu cầu khi dùng thật', tool.required_permission],
                ['Cấu trúc hợp lệ?', yesNo(tool.schema_valid)], ['Kiểm tra đối tượng nghiệp vụ?', yesNo(tool.check_domain)]]),
            stages,
        );
    }

    const renderers = new Map([
        ['forecast', showForecast], ['retrieval', showRetrieval], ['mapping_pending', showMapping],
        ['mapping_confirmed', showMapping], ['recommendation', showRecommendation],
    ]);

    function renderResult(result, caseKey, label) {
        if (result.scope !== 'SYNTHETIC_DEMO' || result.case !== caseKey || !renderers.has(caseKey) ||
                typeof result.executed_at !== 'string' || !Number.isFinite(Date.parse(result.executed_at)) ||
                !Number.isFinite(result.elapsed_seconds) || result.elapsed_seconds < 0) {
            throw new Error('Invalid demo result');
        }
        const content = node('div');
        const generated = node('p', 'Thời điểm tạo kết quả: ');
        generated.append(timestamp(result.executed_at));
        const warnings = node('ul');
        warnings.append(...result.warnings.map(warning => node('li', warning)));
        content.append(node('h3', label), node('p', 'Chế độ: ' + result.execution_mode), generated,
            node('p', 'Thời gian xử lý máy chủ: ' + number(result.elapsed_seconds) + ' giây.'), node('p', caveat), warnings);
        renderers.get(caseKey)(content, result.data);
        // Commit the UI update only after all fields render successfully.
        output.replaceChildren(content);
        output.hidden = false;
        if (empty) empty.hidden = true;
    }

    function failure(message) {
        status.textContent = '';
        error.textContent = message;
        error.hidden = false;
    }

    const messages = {
        400: 'Biểu mẫu không hợp lệ. Tải lại trang rồi thử lại.',
        403: 'Không có quyền chạy, phiên đã hết hạn hoặc không gian làm việc đã đổi. Hãy tải lại trang.',
        409: 'Phòng mô phỏng đang bận. Bấm chạy lại khi sẵn sàng.',
        503: 'Chưa thể chạy kịch bản mô phỏng. Vui lòng thử lại sau.',
    };
    let lastSuccess = null;

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (run.disabled) return;
        const caseKey = select.value;
        const label = select.selectedOptions[0].textContent;
        run.disabled = true;
        select.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        error.hidden = true;
        status.textContent = 'Đang chạy kịch bản mô phỏng…';
        if (lastSuccess) {
            previous.textContent = 'Kết quả thành công trước — ';
            previous.append(timestamp(lastSuccess));
            previous.hidden = false;
        }
        try {
            const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
            const response = await fetch(form.action, {
                method: 'POST',
                credentials: 'same-origin',
                redirect: 'error',
                headers: {'Accept': 'application/json', 'X-CSRFToken': csrf},
                body: new URLSearchParams({case: caseKey}),
            });
            if (response.redirected || !response.ok) {
                failure(messages[response.status] || 'Chưa thể nhận kết quả mô phỏng.');
                return;
            }
            const result = await response.json();
            renderResult(result, caseKey, label);
            lastSuccess = result.executed_at;
            previous.hidden = true;
            status.textContent = 'Hoàn tất: ' + label + '.';
        } catch {
            failure('Không thể kết nối hoặc nhận kết quả hợp lệ. Vui lòng thử lại sau.');
        } finally {
            run.disabled = false;
            select.disabled = false;
            panel.setAttribute('aria-busy', 'false');
        }
    });
})();
