"""Repository source inventory, NOT a commercial policy approval registry.

Scope classifications guide academic presentation only. They do not change
workspace permissions, existing documents or runtime retrieval filters.
"""
PRIMARY_SOPS = (
    'SOP_RETAIL_SUPPLY_CHAIN_2026.md',
    'SOP_RETAIL_FINANCIAL_MARGIN_2026.md',
    'SOP_INTER_BRANCH_TRANSFER_2026.md',
    'SOP_RETAIL_RMA_WARRANTY_2026.md',
    'SOP_OMNICHANNEL_FULFILLMENT_2026.md',
    'SOP_RETAIL_INVENTORY_AUDIT_2026.md',
    'SOP_SERVICE_OPS_INCIDENT_SLA_2026.md',
)
SUPPLEMENTARY_SOPS = (
    'SOP_CUSTOMER_RETENTION_LOYALTY_2026.md',
    'SOP_SUPPLIER_CONTRACT_PENALTIES_2026.md',
    'SOP_RETAIL_PROMO_FRAUD_2026.md',
    'SOP_RETAIL_TRADE_IN_2026.md',
    'SOP_FIELD_ENGINEERING_SAFETY_2026.md',
    'SOP_CYBERSECURITY_INCIDENT_DRP_2026.md',
    'SOP_SLA_ESCALATION_DISPUTE_2026.md',
    'SOP_DATACENTER_THERMAL_ENERGY_2026.md',
    'SOP_SVC_CHANGE_MANAGEMENT_2026.md',
    'SOP_SVC_ASSET_DECOMMISSION_2026.md',
    'SOP_SVC_BACKUP_RETENTION_2026.md',
    'SOP_CORE_WORKING_HOURS_LEAVE_2026.md',
    'SOP_CORE_EXPENSE_TRAVEL_REIMBURSEMENT_2026.md',
    'SOP_CORE_IT_SECURITY_DEVICE_USAGE_2026.md',
    'SOP_CORE_ONBOARDING_PROBATION_2026.md',
    'SOP_CORE_CODE_OF_CONDUCT_CULTURE_2026.md',
    'SOP_CORE_PERFORMANCE_BENEFITS_BONUS_2026.md',
)


def inventory():
    return tuple({'filename': filename, 'academic_scope': scope,
                  'approval_status': 'UNVERIFIED', 'public_publication_approved': False}
                 for scope, filenames in (('PRIMARY', PRIMARY_SOPS), ('SUPPLEMENTARY', SUPPLEMENTARY_SOPS))
                 for filename in filenames)
