"""Read-only presentation of stored evidence; never certifies unmeasured quality."""
import math
import json
from numbers import Real


def measured(value, nonnegative=True):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    if not math.isfinite(value) or (nonnegative and value < 0):
        return None
    return float(value)


def improvement(model, baseline):
    model, baseline = measured(model), measured(baseline)
    if model is None or baseline is None or baseline == 0:
        return None
    return (baseline - model) / baseline * 100


def fmt(value):
    return 'Chưa đo' if value is None else f'{value:,.4f}'


def comparison_text(model, baseline):
    gain = improvement(model, baseline)
    if gain is None:
        return 'Chưa đủ dữ liệu so sánh phần trăm MAE'
    if gain < 0:
        return 'Kém baseline theo MAE'
    if gain > 0:
        return 'Tốt hơn baseline theo MAE'
    return 'Bằng baseline theo MAE'


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def provenance_notes(parameters):
    """Render stored, allowlisted evidence; never infer missing historic metadata."""
    parameters = parameters if isinstance(parameters, dict) else {}
    provenance = parameters.get('provenance')
    if not isinstance(provenance, dict):
        return ['Hồ sơ run: Chưa ghi nhận provenance; không suy diễn từ settings hiện tại.']
    lines = ['| Thành phần hồ sơ | Giá trị đã lưu |', '|---|---|']
    fields = {
        'dataset': ('period_start', 'period_end', 'row_count', 'source_observation_count',
                    'missing_period_count', 'missing_period_policy', 'source_frequency', 'unit', 'fingerprint_sha256'),
        'split': ('method', 'train_start', 'train_end', 'train_rows', 'test_start', 'test_end',
                  'test_rows', 'validation', 'evaluation', 'test_size'),
        'runtime': ('python', 'django', 'pandas', 'numpy', 'xgboost', 'code_revision'),
    }
    for group, keys in fields.items():
        values = provenance.get(group)
        values = values if isinstance(values, dict) else {}
        for key in keys:
            value = values.get(key)
            lines.append(f'| {group}.{key} | {cell(value if value is not None else "Chưa ghi nhận")} |')
    for key in ('workspace_code', 'target_type', 'model_config_id', 'model_version', 'granularity',
                'dimensions', 'horizon_days', 'feature_config', 'feature_columns', 'training_config',
                'artifact_sha256', 'source_sha256'):
        value = provenance.get(key)
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) if value is not None else 'Chưa ghi nhận'
        lines.append(f'| {key} | {cell(rendered)} |')
    lines.append('validation=no_separate_validation_partition nghĩa là không có tập validation riêng; không phải đã tối ưu trên validation. Hash nhận diện dữ liệu/model, không thay thế bản lưu dữ liệu gốc.')
    return lines


def render_report(rows, counts, timestamp):
    lines = [
        '# Báo cáo bằng chứng thực nghiệm hiện có', '',
        '**Đề tài:** Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI',
        f'Thời điểm xuất: {timestamp}', '',
        'Đây là bản đọc các run đã lưu, không huấn luyện lại, không gọi API AI và không chứng nhận nghiệm thu.',
        'Mỗi run được liệt kê riêng, kể cả run thất bại; không chọn kết quả tốt nhất hoặc gộp khác workspace/cấu hình.', '',
        '## Dự báo', '',
        '| Run | Workspace | Config | Target | Status | Train/Test | MAE | RMSE | MAPE % | R² | Baseline MAE | Cải thiện MAE % | Nhận xét |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|',
    ]
    if not rows:
        lines.append('Chưa có run trong phạm vi đã chọn; không suy ra sai số bằng 0.')
    notes = []
    for row in rows:
        has_test = measured(row['test']) is not None and row['test'] > 0
        eligible = row['status'] == 'COMPLETED' and has_test
        metrics = row['metrics'] if eligible and isinstance(row['metrics'], dict) else {}
        baseline = row['baseline'] if eligible and isinstance(row['baseline'], dict) else {}
        mae = measured(metrics.get('mae'))
        base = measured(baseline.get('naive_mae', baseline.get('mae')))
        r2 = measured(metrics.get('r2'), nonnegative=False)
        values = [row['id'], row['workspace'], row['config'], row['target'], row['status'],
                  f"{row['train']}/{row['test']}", fmt(mae), fmt(measured(metrics.get('rmse'))),
                  fmt(measured(metrics.get('mape'))), fmt(r2), fmt(base), fmt(improvement(mae, base)),
                  comparison_text(mae, base)]
        lines.append('| ' + ' | '.join(cell(v) for v in values) + ' |')
        notes.append(f"\nRun {row['id']}: khoảng dữ liệu {cell(row['start'])} đến {cell(row['end'])}.\n")
        notes.extend(provenance_notes(row['parameters']))
        if r2 is not None and r2 < 0:
            notes.append('R² âm: không kết luận mô hình giải thích phần lớn phương sai.\n')
    lines += notes
    lines += ['', 'Backtest hiện tại là one-step observed-history; không thay thế đánh giá đệ quy nhiều ngày.',
              'Số liệu thiếu/không hợp lệ ghi Chưa đo. Baseline bằng 0 không có phần trăm cải thiện xác định.',
              'Cần snapshot dữ liệu, cấu hình và đánh giá độc lập trước khi suy rộng hiệu quả kinh doanh.', '',
              '## RAG', '',
              'CHƯA ĐÁNH GIÁ trong lệnh này. Bộ chấm keyword hiện tại chưa chứng minh độ đúng ngữ nghĩa.',
              'Cần benchmark có đáp án/nguồn chuẩn, mode API hoặc fallback và log từng ca; không dùng tỷ lệ lịch sử như kết quả mới.', '',
              '## GIS', '',
              'CHƯA ĐÁNH GIÁ trong lệnh này. Hai cặp Haversine không chứng nhận truy vấn PostGIS hoặc độ chính xác thực địa.', '',
              '## Phê duyệt và audit', '',
              'Chỉ đếm trạng thái hiện có; không phải phép đo tuân thủ hoặc tính toàn vẹn audit.',
              f"Số khuyến nghị: {counts['recommendations']}; số approval: {counts['approvals']}.",
              'Trạng thái approval: ' + cell(counts['statuses']),
              'Tuân thủ phê duyệt: CHƯA ĐO. Audit đầy đủ/bất biến: CHƯA ĐO.',
              'Cần ca thực thi, từ chối, tự duyệt, sai quyền, lặp, đồng thời và rollback trên database kiểm thử.', '',
              '## Giới hạn', '', 'Không có kết luận hoàn thành toàn bộ đồ án hoặc production trong báo cáo này.']
    return '\n'.join(lines) + '\n'
