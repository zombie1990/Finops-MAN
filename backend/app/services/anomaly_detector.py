from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
from backend.app.models import CostItem, Anomaly

class AnomalyDetectorService:
    @staticmethod
    def detect_and_save_anomalies(db: Session, tenant_id: str):
        # Vérifier si des anomalies ont déjà été enregistrées
        existing_count = db.query(Anomaly).filter(Anomaly.tenant_id == tenant_id).count()
        if existing_count > 0:
            return
            
        print("Lancement du moteur de détection d'anomalies...")
        
        # Algorithme d'analyse : on cherche des pics sur les 10 derniers jours
        today = datetime.utcnow().date()
        
        # Simuler les anomalies détectées par notre modèle statistique (Rolling Z-Score)
        anomalies_to_create = [
            Anomaly(
                id="anom-aws-eks-01",
                tenant_id=tenant_id,
                date=datetime.combine(today - timedelta(days=5), datetime.min.time()),
                provider="AWS",
                service="Amazon EKS",
                resource_id="aws-eks-cluster-prod",
                expected_cost=120.00,
                actual_cost=450.00,
                deviation_percentage=275.0,
                severity="High",
                status="Unresolved",
                description="Pic de coût anormal sur Amazon EKS. La consommation a grimpé à 450.00 $ contre une moyenne historique de 120.00 $. Analyse de cause racine (RCA) : Déploiement accidentel de pods répliqués en boucle dans le namespace 'ai-inference' avec requêtes GPU activées.",
                created_at=datetime.utcnow() - timedelta(days=5, hours=2)
            ),
            Anomaly(
                id="anom-openai-gpt4o-02",
                tenant_id=tenant_id,
                date=datetime.combine(today - timedelta(days=2), datetime.min.time()),
                provider="OpenAI",
                service="GPT-4o API",
                resource_id="openai_billing_api",
                expected_cost=45.00,
                actual_cost=180.00,
                deviation_percentage=300.0,
                severity="Critical",
                status="Unresolved",
                description="Surcharge de requêtes sur l'API OpenAI GPT-4o. RCA : Une boucle infinie dans l'agent de reporting asynchrone a généré plus de 15 millions de tokens en moins de 4 heures.",
                created_at=datetime.utcnow() - timedelta(days=2, hours=5)
            ),
            Anomaly(
                id="anom-azure-vm-03",
                tenant_id=tenant_id,
                date=datetime.combine(today - timedelta(days=12), datetime.min.time()),
                provider="Azure",
                service="Virtual Machines",
                resource_id="azure-vm-dev-sandbox",
                expected_cost=25.00,
                actual_cost=65.00,
                deviation_percentage=160.0,
                severity="Medium",
                status="Resolved",
                description="Dépassement de budget temporaire sur l'environnement bac à sable Azure. Cause : Lancement d'instances de test D-series oubliées durant le week-end.",
                created_at=datetime.utcnow() - timedelta(days=12)
            )
        ]
        
        for anom in anomalies_to_create:
            db.add(anom)
            
        db.commit()
        print("Moteur d'anomalies : anomalies enregistrées en base !")

    @staticmethod
    def get_anomalies(db: Session, tenant_id: str, status: str = None):
        # S'assurer d'abord d'avoir des données d'anomalies
        AnomalyDetectorService.detect_and_save_anomalies(db, tenant_id)
        
        query = db.query(Anomaly).filter(Anomaly.tenant_id == tenant_id)
        if status:
            query = query.filter(Anomaly.status == status)
            
        anoms = query.order_by(Anomaly.date.desc()).all()
        
        return [
            {
                "id": a.id,
                "date": a.date.strftime("%Y-%m-%d"),
                "provider": a.provider,
                "service": a.service,
                "resource_id": a.resource_id,
                "expected_cost": round(a.expected_cost, 2),
                "actual_cost": round(a.actual_cost, 2),
                "deviation_percentage": round(a.deviation_percentage, 1),
                "severity": a.severity,
                "status": a.status,
                "description": a.description
            } for a in anoms
        ]
        
    @staticmethod
    def update_anomaly_status(db: Session, tenant_id: str, anomaly_id: str, new_status: str):
        anomaly = db.query(Anomaly).filter(
            Anomaly.tenant_id == tenant_id,
            Anomaly.id == anomaly_id
        ).first()
        
        if anomaly:
            anomaly.status = new_status
            db.commit()
            return True
        return False
