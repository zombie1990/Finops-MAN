from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    accounts = relationship("CloudAccount", back_populates="tenant")
    cost_items = relationship("CostItem", back_populates="tenant")
    recommendations = relationship("Recommendation", back_populates="tenant")
    anomalies = relationship("Anomaly", back_populates="tenant")

class CloudAccount(Base):
    __tablename__ = "cloud_accounts"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    provider = Column(String, nullable=False)  # AWS, Azure, GCP, K8s, OpenAI
    name = Column(String, nullable=False)
    status = Column(String, default="Active")  # Active, Error, Syncing
    credentials = Column(JSON, nullable=True)  # Clés stockées de manière chiffrée
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="accounts")

class CostItem(Base):
    __tablename__ = "cost_items"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    account_id = Column(String, ForeignKey("cloud_accounts.id"), nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    provider = Column(String, nullable=False)
    service = Column(String, index=True, nullable=False)
    resource_id = Column(String, index=True)
    resource_name = Column(String)
    region = Column(String)
    cost = Column(Float, nullable=False)
    usage_quantity = Column(Float, default=0.0)
    usage_unit = Column(String)
    tags = Column(JSON)  # {env: prod, owner: data-team}
    carbon_emissions = Column(Float, default=0.0)  # en kg CO2
    
    tenant = relationship("Tenant", back_populates="cost_items")

class KubernetesCost(Base):
    __tablename__ = "kubernetes_costs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(String, nullable=False, index=True)
    cluster_id = Column(String, nullable=False, index=True)
    namespace = Column(String, nullable=False, index=True)
    pod_name = Column(String)
    date = Column(DateTime, nullable=False)
    cpu_cores_requested = Column(Float, default=0.0)
    cpu_cores_used = Column(Float, default=0.0)
    memory_gb_requested = Column(Float, default=0.0)
    memory_gb_used = Column(Float, default=0.0)
    cost = Column(Float, nullable=False)
    efficiency_score = Column(Float, default=100.0) # 0-100%

class Anomaly(Base):
    __tablename__ = "anomalies"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    provider = Column(String, nullable=False)
    service = Column(String, nullable=False)
    resource_id = Column(String)
    expected_cost = Column(Float, nullable=False)
    actual_cost = Column(Float, nullable=False)
    deviation_percentage = Column(Float, nullable=False)
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    status = Column(String, default="Unresolved")  # Unresolved, Investigating, Resolved, FalsePositive
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="anomalies")

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    resource_id = Column(String, index=True, nullable=False)
    resource_name = Column(String)
    provider = Column(String, nullable=False)
    service = Column(String, nullable=False)
    recommendation_type = Column(String, nullable=False)  # Rightsizing, Idle, SavingsPlan, Carbon, GPU
    description = Column(Text, nullable=False)
    current_cost = Column(Float, nullable=False)
    estimated_saving = Column(Float, nullable=False)
    roi_days = Column(Integer, default=30)
    operational_risk = Column(String, default="Low")  # Low, Medium, High
    remediation_effort = Column(String, default="Low") # Low, Medium, High
    status = Column(String, default="Pending")  # Pending, Applied, Dismissed, InProgress
    remediation_script_type = Column(String)  # terraform, bash, kubectl, azure_cli, aws_cli
    remediation_script = Column(Text)
    rollback_script = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="recommendations")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    title = Column(String, default="Nouvelle discussion")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)  # Graphiques, widgets à afficher
    
    conversation = relationship("Conversation", back_populates="messages")

# ==========================================
# PHASE 1 — NOUVEAUX MODÈLES ENTERPRISE
# ==========================================

class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Montant total du budget
    period = Column(String, default="monthly")  # monthly, quarterly, yearly
    provider_filter = Column(String, nullable=True)  # AWS, Azure, GCP, All
    service_filter = Column(String, nullable=True)  # Filtre par service spécifique
    alert_threshold_warning = Column(Float, default=75.0)  # % seuil avertissement
    alert_threshold_critical = Column(Float, default=90.0)  # % seuil critique
    spent = Column(Float, default=0.0)  # Montant dépensé calculé
    forecast = Column(Float, default=0.0)  # Prévision fin de période
    status = Column(String, default="On Track")  # On Track, Warning, Critical, Exceeded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)  # cost_threshold, anomaly, budget_overrun, idle_resource, carbon
    condition = Column(String, nullable=False)  # gt, lt, eq, spike
    threshold_value = Column(Float, nullable=False)
    provider_filter = Column(String, nullable=True)
    service_filter = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=True)
    notify_slack = Column(Boolean, default=False)
    notify_webhook = Column(Boolean, default=False)
    cooldown_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertEvent(Base):
    __tablename__ = "alert_events"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, ForeignKey("alert_rules.id"), nullable=False)
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    title = Column(String, nullable=False)
    description = Column(Text)
    current_value = Column(Float)
    threshold_value = Column(Float)
    status = Column(String, default="Active")  # Active, Acknowledged, Resolved
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    report_type = Column(String, nullable=False)  # executive, technical, savings, carbon
    title = Column(String, nullable=False)
    status = Column(String, default="Generating")  # Generating, Ready, Failed
    period_days = Column(Integer, default=30)
    summary = Column(Text)
    content_json = Column(JSON)  # Contenu structuré du rapport
    generated_at = Column(DateTime, default=datetime.utcnow)
    download_count = Column(Integer, default=0)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # login, remediation_applied, budget_created, alert_acknowledged...
    user = Column(String, default="admin")
    resource_type = Column(String)  # recommendation, budget, alert, connector
    resource_id = Column(String)
    details = Column(Text)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class ScanResult(Base):
    __tablename__ = "scan_results"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # csv, xlsx, pdf
    status = Column(String, default="Processing")  # Processing, Completed, Failed
    items_parsed = Column(Integer, default=0)
    total_cost_detected = Column(Float, default=0.0)
    providers_detected = Column(JSON)  # ["AWS", "Azure"]
    results_json = Column(JSON)  # Résultats parsés détaillés
    errors = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Connector(Base):
    __tablename__ = "connectors"
    
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)  # AWS, Azure, GCP, Kubernetes, Datadog, OpenAI, GitHub
    name = Column(String, nullable=False)
    connector_type = Column(String, nullable=False)  # billing_api, metrics_api, cost_export, log_stream
    status = Column(String, default="Disconnected")  # Connected, Disconnected, Error, Syncing
    config_json = Column(JSON)  # Configuration spécifique au connecteur
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_items = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # aws_cur, azure_cost, gcp_billing, kubernetes, file_upload
    source_ref = Column(String, nullable=True)  # connector_id, file name, bucket path...
    status = Column(String, default="Queued")  # Queued, Running, Succeeded, Failed
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processed_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncSchedule(Base):
    __tablename__ = "sync_schedules"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    connector_id = Column(String, ForeignKey("connectors.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    interval_minutes = Column(Integer, default=360)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)  # finops_kb, connector, report
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    recommendation_id = Column(String, nullable=False)
    automation_type = Column(String, default="github_pr")  # github_pr, terraform_plan
    status = Column(String, default="Pending")  # Pending, Success, Failed
    pr_url = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
