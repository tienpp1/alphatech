"""Run fixed synthetic demonstrations without business data or AI providers."""

import hashlib
import io
import json
from pathlib import Path

import pandas as pd

from . import adaptive, guarded
from .artifacts import _check_finite, _decode_artifact, _reject_constant, _unique_object


DEMO_CASES = {
    'forecast': 'Dự báo XGBoost và đối chiếu sai số',
    'retrieval': 'Truy xuất trích đoạn theo truy vấn mẫu',
    'mapping_pending': 'Ánh xạ chưa xác nhận',
    'mapping_confirmed': 'Ánh xạ đã xác nhận mô phỏng',
    'recommendation': 'Xếp hạng kỹ thuật viên và xem trước duyệt',
}
DEMO_ASSET_DIR = Path(__file__).with_name('demo_assets')
SCOPE = 'SYNTHETIC_DEMO'
CASE_ID = 'weekly_calendar__2026110121'
HISTORY_SHA256 = '656bf978afa8918f6a251ff5d8114cc6b3b6c2f4d9898140ef8bf7a11d4abe49'
EVALUATION_MODEL_SHA256 = '31f9d3b13e896f83b80e3307d5d882131d099d2379562026c9f36b9450159b2e'
HISTORY_ROWS = 730
TRAINING_ROWS = 584
HORIZON = 14
TRAINING_CUTOFF = '2025-08-06'
HOLDOUT = ('2025-08-07', '2025-12-30')
MODEL = 'XGBOOST_DIRECT'
CALENDAR_MODE = 'full'
MODEL_SCOPE = {
    'kind': 'fixed_synthetic_pre_holdout_demo', 'case_id': CASE_ID,
    'history_sha256': HISTORY_SHA256, 'training_rows': TRAINING_ROWS, 'training_cutoff': TRAINING_CUTOFF,
}
MANIFEST_FIELDS = {
    'format': 'online_guarded_demo_v1', 'scope': SCOPE, 'case_id': CASE_ID,
    'history_rows': HISTORY_ROWS, 'training_rows': TRAINING_ROWS, 'training_cutoff': TRAINING_CUTOFF,
    'holdout': list(HOLDOUT), 'horizon': HORIZON, 'model': MODEL, 'calendar_mode': CALENDAR_MODE,
}


def _asset_bytes(name, limit):
    with (DEMO_ASSET_DIR / name).open('rb') as stream:
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError('Invalid demo asset size')
    # Validate the LF form so Git's Windows checkout line endings do not change the identity.
    return raw.replace(b'\r\n', b'\n')


def _load_forecast_assets():
    manifest = json.loads(_asset_bytes('manifest.json', 8_192),
                          object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in MANIFEST_FIELDS.items()):
        raise ValueError('Invalid demo forecast manifest or training cutoff')
    _check_finite(manifest)

    expected_hashes = {'history.csv': HISTORY_SHA256, 'evaluation_model.json': EVALUATION_MODEL_SHA256}
    if manifest.get('files_sha256') != expected_hashes:
        raise ValueError('Demo forecast manifest does not match pinned assets')
    history_raw = _asset_bytes('history.csv', 32_768)
    model_raw = _asset_bytes('evaluation_model.json', 262_144)
    for name, raw in (('history.csv', history_raw), ('evaluation_model.json', model_raw)):
        if hashlib.sha256(raw).hexdigest() != expected_hashes[name]:
            raise ValueError('Demo forecast asset SHA-256 mismatch')

    frame = pd.read_csv(io.BytesIO(history_raw), index_col='date', parse_dates=True)
    if len(frame) != HISTORY_ROWS:
        raise ValueError('Invalid demo history row count')
    adaptive.validate_history(frame)
    if tuple(frame.index[i].date().isoformat() for i in (TRAINING_ROWS - 1, TRAINING_ROWS, -1)) != (
            TRAINING_CUTOFF, *HOLDOUT):
        raise ValueError('Invalid demo history or cutoff dates')

    artifact = _decode_artifact(model_raw, MODEL_SCOPE)
    if (artifact.get('effective_model') != MODEL or artifact.get('calendar_mode') != CALENDAR_MODE
            or artifact.get('columns') != adaptive.columns_for(CALENDAR_MODE)
            or artifact.get('params') != adaptive.model_params()
            or not isinstance(artifact.get('booster'), dict)):
        raise ValueError('Invalid demo model or feature schema')
    return frame, artifact


def _holdout_rows(frame, artifact):
    """Repeat ten fixed origins; each origin sees only the history available then."""
    values = frame.target.to_numpy(dtype=float)
    observed = set(frame.index.date)
    rows = []
    for end in range(TRAINING_ROWS, len(frame) - HORIZON + 1, HORIZON):
        prediction = guarded.predict_artifact(artifact, frame.iloc[:end], horizon=HORIZON)
        if len(prediction) != HORIZON:
            raise ValueError('Incomplete demo prediction block')
        rows.extend(guarded._rows(values, frame.index, end - 1, HORIZON, observed, prediction))
    return rows


def _forecast():
    frame, artifact = _load_forecast_assets()
    rows = _holdout_rows(frame, artifact)
    actual = [row['actual'] for row in rows]
    metrics = {}
    for name, field in (('xgboost', 'prediction'), ('ma7', 'ma7'), ('seasonal_naive_7', 'naive')):
        scored = guarded._metrics(actual, [row[field] for row in rows])
        metrics[name] = {'mae': scored['mae'], 'rmse': scored['rmse']}
    holdout_rows = len(frame) - TRAINING_ROWS
    return {
        'model': artifact['effective_model'], 'calendar_mode': artifact['calendar_mode'],
        'training_cutoff': TRAINING_CUTOFF, 'training_rows': TRAINING_ROWS, 'history_rows': len(frame),
        'holdout_rows': holdout_rows, 'scored_rows': len(rows), 'omitted_rows': holdout_rows - len(rows),
        'holdout_start': HOLDOUT[0], 'holdout_end': HOLDOUT[1], 'horizon': HORIZON,
        'blocks': len(rows) // HORIZON, 'metrics': metrics, 'sample_rows': rows[:HORIZON],
    }


def _retrieval():
    from apps.knowledge.embedding import _generate_deterministic_embedding
    from apps.knowledge.retrieval import calculate_cosine_similarity, calculate_lexical_score

    query = 'Xác nhận quy tắc ánh xạ trước khi nhập dữ liệu'
    dimension = 128
    snippets = (
        ('DEMO-MAPPING', 'Phiếu minh họa ánh xạ',
         'Xác nhận quy tắc ánh xạ trước khi nhập dữ liệu. Trong mẫu này, quy tắc đang chờ xác nhận không được áp dụng.'),
        ('DEMO-DISPATCH', 'Phiếu minh họa phân công',
         'Chấm điểm kỹ thuật viên theo khoảng cách và khối lượng công việc; loại ứng viên không sẵn sàng.'),
    )
    query_vector = _generate_deterministic_embedding(query, dimension)
    candidates = []
    for source, title, excerpt in snippets:
        vector = _generate_deterministic_embedding(f'{title}\n{excerpt}', dimension)
        cosine = calculate_cosine_similarity(query_vector, vector)
        lexical = calculate_lexical_score(query, excerpt, title)
        # Same lexical boost as canonical retrieval, without the production pipeline or dense gate.
        similarity = max(round(cosine, 4), round(cosine * (1 + .25 * lexical), 4))
        candidates.append({'source': source, 'title': title, 'excerpt': excerpt,
                           'dense_similarity': round(cosine, 4), 'lexical_score': round(lexical, 4),
                           'similarity': similarity})
    candidates.sort(key=lambda row: row['similarity'], reverse=True)
    return {'query': query, 'embedding_dimension': dimension, 'candidates': candidates,
            'answer': candidates[0]['excerpt'], 'source': candidates[0]['source']}


def _mapping(confirmed):
    from apps.mapping.ai_suggester import suggest_mappings_for_fields
    from apps.mapping.engine.transformer import transform_single_record
    from apps.mapping.models import AIConfirmationStatus, MappingRule

    entity = 'Customer'
    before = {'ma_kh': 'DEMO-KH-01', 'ho_ten': 'Khách mô phỏng A', 'phan_khuc': 'CHƯA_PHÂN_LOẠI'}
    suggestions = suggest_mappings_for_fields(list(before), entity, {key: [value] for key, value in before.items()})
    status = AIConfirmationStatus.ACCEPTED if confirmed else AIConfirmationStatus.PENDING
    rules = [MappingRule(
        source_field=row['source_field'], target_field=row['suggested_target_field'],
        rule_type=row['suggested_rule_type'], transformation_config=row['transformation_config'],
        confidence_score=row['confidence'], ai_status=status, order=order,
    ) for order, row in enumerate(suggestions)]
    after, errors = transform_single_record(before, rules, entity)
    fields = ('source_field', 'suggested_target_field', 'confidence', 'suggested_rule_type')
    shown = [{**{key: row[key] for key in fields}, 'ai_status': status} for row in suggestions]
    return {'entity': entity, 'before': before, 'after': after, 'errors': errors,
            'suggestions': shown, 'confirmation_status': status}


def _recommendation():
    from apps.approvals.registry import ToolRegistry, validate_action_contract
    from apps.recommendations.scoring import calculate_technician_score

    candidates = []
    for name, distance, workload, available in (('Kỹ thuật viên A', 1., 1, True),
                                               ('Kỹ thuật viên B', 5., 0, True),
                                               ('Kỹ thuật viên C', 0.5, 0, False)):
        scoring = calculate_technician_score(distance, workload, is_available=available,
                                             weight_dist=.5, weight_workload=.5, weight_skill=0.)
        candidates.append({'name': name, 'distance_km': distance, 'active_tasks': workload,
                           'is_available': available, 'score': scoring['score'],
                           'subscores': scoring['subscores'], 'weights': scoring['weights']})
    candidates.sort(key=lambda row: row['score'], reverse=True)

    definition = ToolRegistry.get('dispatch_technician')
    validate_action_contract(definition, None, {'ticket_id': 1, 'employee_id': 1}, check_domain=False)
    tool = {name: getattr(definition, name) for name in ('name', 'classification', 'risk_level', 'required_permission')}
    return {'candidates': candidates, 'selected_candidate': candidates[0]['name'],
            'tool': {**tool, 'schema_valid': True, 'check_domain': False},
            'approval_preview': ['Gợi ý phân công', 'Kiểm tra kiểu tham số',
                                 'Minh họa bước người có quyền duyệt', 'Không thực thi phân công']}


def run_demo_case(case: str) -> dict:
    """Run a single allowlisted case; no request, workspace or supplied data is accepted."""
    if not isinstance(case, str) or case not in DEMO_CASES:
        raise ValueError('Unsupported synthetic demo case')

    if case == 'forecast':
        mode = 'Suy luận tại chỗ từ mô hình huấn luyện ngoại tuyến'
        warnings = ['Không huấn luyện lại khi chạy; chỉ dùng mô hình đã chốt trước kỳ đánh giá.',
                    'Chỉ chấm các khối đủ 14 ngày. Sai số trên dữ liệu mô phỏng không bảo đảm độ chính xác thực tế.']
        data = _forecast()
    elif case == 'retrieval':
        mode = 'Truy xuất thành phần bằng vectơ băm tất định và khớp từ'
        warnings = ['Chỉ so hai trích đoạn mô phỏng; không gọi LLM, API embedding hay chạy toàn bộ RAG.']
        data = _retrieval()
    elif case in ('mapping_pending', 'mapping_confirmed'):
        mode = 'Gợi ý heuristic và chạy bộ chuyển đổi bản ghi trong bộ nhớ'
        warnings = ['Độ tin cậy chỉ là điểm khớp heuristic, không phải độ chính xác.',
                    'Trạng thái xác nhận được mô phỏng; không lưu quy tắc hoặc nhập dữ liệu.']
        data = _mapping(confirmed=case == 'mapping_confirmed')
    else:
        mode = 'Chấm điểm tất định và xem trước hợp đồng công cụ'
        warnings = ['Chỉ kiểm tra schema tham số, không tra cứu đối tượng hay xác thực quyền thực thi.',
                    'Không tạo yêu cầu duyệt, phân công hoặc lưu nhật ký nghiệp vụ.']
        data = _recommendation()
    return {'scope': SCOPE, 'case': case, 'execution_mode': mode, 'warnings': warnings, 'data': data}
