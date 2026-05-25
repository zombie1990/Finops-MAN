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
