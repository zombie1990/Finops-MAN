from datetime import datetime, timedelta
import random
import math
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import CostItem, KubernetesCost, Recommendation

class CostAnalyzerService:
    @staticmethod
    def seed_data_if_empty(db: Session, tenant_id: str):
        # Vérifier si les données existent déjà
        count = db.query(CostItem).filter(CostItem.tenant_id == tenant_id).count()
        if count > 0:
            return
            
        print(f"Génération de données FinOps d'exemple pour {tenant_id}...")
        
        providers = {
            "AWS": {
                "accounts": ["aws_prod_12345", "aws_staging_67890"],
                "services": ["Amazon EC2", "Amazon RDS", "Amazon S3", "Elastic Load Balancing", "Amazon EKS", "Amazon SageMaker"],
                "regions": ["us-east-1", "eu-west-3", "us-west-2"],
                "base_cost": 250.0
            },
            "Azure": {
                "accounts": ["azure_sub_prod", "azure_sub_dev"],
                "services": ["Virtual Machines", "Azure SQL Database", "Blob Storage", "AKS", "Azure Machine Learning"],
                "regions": ["westeurope", "eastus", "francecentral"],
                "base_cost": 180.0
            },
            "GCP": {
                "accounts": ["gcp-prod-infra", "gcp-dev-sandbox"],
                "services": ["Compute Engine", "Cloud SQL", "Cloud Storage", "Google Kubernetes Engine", "BigQuery"],
                "regions": ["us-central1", "europe-west9", "asia-east1"],
                "base_cost": 120.0
            },
            "OpenAI": {
                "accounts": ["openai_billing_api"],
                "services": ["GPT-4o API", "GPT-3.5 API", "Embeddings API", "Fine-Tuning"],
                "regions": ["global"],
                "base_cost": 45.0
            }
        }
        
        # Générer sur les 30 derniers jours
        today = datetime.utcnow().date()
        for i in range(45):
            date_val = datetime.combine(today - timedelta(days=i), datetime.min.time())
            
            for provider, meta in providers.items():
                for account in meta["accounts"]:
                    # Fluctuation hebdomadaire et tendance générale
                    day_factor = 1.0 + (0.15 * math.sin(i / 7.0))
                    # Ajouter un pic ou une anomalie à J-5
                    anomaly_factor = 2.5 if i == 5 and provider == "AWS" else 1.0
                    
                    for service in meta["services"]:
                        # Répartition réaliste des coûts par service
                        service_weight = 0.4 if "EC2" in service or "Virtual Machines" in service or "Compute" in service else 0.15
                        if "S3" in service or "Storage" in service:
                            service_weight = 0.1
                        if "SageMaker" in service or "Machine Learning" in service or "GPT" in service:
                            service_weight = 0.2
                            
                        cost_val = meta["base_cost"] * service_weight * random.uniform(0.85, 1.15) * day_factor * anomaly_factor
                        carbon_val = cost_val * 0.085 * random.uniform(0.7, 1.3) # 0.085 kg CO2 par dollar environ
                        
                        item = CostItem(
                            tenant_id=tenant_id,
                            account_id=account,
                            date=date_val,
                            provider=provider,
                            service=service,
                            resource_id=f"{provider.lower()}-{service.lower().replace(' ', '-')}-{random.randint(1000, 9999)}",
                            resource_name=f"{service} Resource",
                            region=random.choice(meta["regions"]),
                            cost=round(cost_val, 2),
                            usage_quantity=round(cost_val * random.uniform(2, 5), 2),
                            usage_unit="Hrs/GB/Tokens",
                            tags={"env": "prod" if "prod" in account else "dev", "team": "platform" if random.random() > 0.5 else "data"},
                            carbon_emissions=round(carbon_val, 2)
                        )
                        db.add(item)
                        
        # Générer des coûts Kubernetes
        namespaces = ["default", "kube-system", "production-app", "staging-app", "ai-inference", "data-analytics"]
        for i in range(30):
            date_val = datetime.combine(today - timedelta(days=i), datetime.min.time())
            for ns in namespaces:
                cpu_req = random.uniform(5, 50)
                cpu_used = cpu_req * (random.uniform(0.1, 0.3) if ns in ["staging-app", "default"] else random.uniform(0.6, 0.85))
                mem_req = cpu_req * 4
                mem_used = mem_req * (random.uniform(0.15, 0.35) if ns in ["staging-app", "default"] else random.uniform(0.7, 0.9))
                
                # Le coût K8s
                cost_val = (cpu_req * 0.04 + mem_req * 0.005) * 24 * random.uniform(0.95, 1.05)
                # Score d'efficacité basé sur l'usage vs requête
                efficiency = ((cpu_used / cpu_req) + (mem_used / mem_req)) / 2.0 * 100.0
                
                k8s_cost = KubernetesCost(
                    tenant_id=tenant_id,
                    cluster_id="k8s-prod-cluster-01",
                    namespace=ns,
                    pod_name=f"pod-{ns}-{random.randint(100, 999)}",
                    date=date_val,
                    cpu_cores_requested=round(cpu_req, 2),
                    cpu_cores_used=round(cpu_used, 2),
                    memory_gb_requested=round(mem_req, 2),
                    memory_gb_used=round(mem_used, 2),
                    cost=round(cost_val, 2),
                    efficiency_score=round(efficiency, 2)
                )
                db.add(k8s_cost)

        # Générer des recommandations FinOps d'optimisation
        recoms = [
            Recommendation(
                id="rec-aws-ec2-01",
                tenant_id=tenant_id,
                resource_id="aws-amazon-ec2-7843",
                resource_name="prod-web-server-node-3",
                provider="AWS",
                service="Amazon EC2",
                recommendation_type="Rightsizing",
                description="L'instance EC2 'prod-web-server-node-3' (m5.4xlarge) est surprovisionnée. Le CPU moyen est de 6.2% et la mémoire utilisée est de 14%. Il est recommandé de rétrograder vers une instance m5.xlarge.",
                current_cost=345.60,
                estimated_saving=259.20,
                roi_days=7,
                operational_risk="Low",
                remediation_effort="Medium",
                status="Pending",
                remediation_script_type="terraform",
                remediation_script="""# Mise à jour de la ressource instance AWS
resource "aws_instance" "web_server_3" {
  # ... autres configurations
-  instance_type = "m5.4xlarge"
+  instance_type = "m5.xlarge"
}
""",
                rollback_script="""# Annulation du Rightsizing
resource "aws_instance" "web_server_3" {
  instance_type = "m5.4xlarge"
}
"""
            ),
            Recommendation(
                id="rec-azure-vm-02",
                tenant_id=tenant_id,
                resource_id="azure-virtual-machines-1192",
                resource_name="dev-sandbox-vm-01",
                provider="Azure",
                service="Virtual Machines",
                recommendation_type="Idle",
                description="La machine virtuelle 'dev-sandbox-vm-01' n'a enregistré aucune activité réseau ou CPU significative sur les 14 derniers jours (Ressource Zombie). Il est conseillé de l'éteindre et de la supprimer après snapshot.",
                current_cost=112.50,
                estimated_saving=112.50,
                roi_days=1,
                operational_risk="Medium",
                remediation_effort="Low",
                status="Pending",
                remediation_script_type="azure_cli",
                remediation_script="""# Éteindre et supprimer la machine virtuelle zombie Azure
az vm deallocate --resource-group rg-dev-infra --name dev-sandbox-vm-01
az vm delete --resource-group rg-dev-infra --name dev-sandbox-vm-01 --yes
""",
                rollback_script="""# Ré-instancier la VM nécessite de la redéployer depuis le dernier snapshot ou backup
echo "Annulation impossible sans re-déploiement de la VM depuis son disque d'OS sauvegardé."
"""
            ),
            Recommendation(
                id="rec-gcp-gke-03",
                tenant_id=tenant_id,
                resource_id="gcp-google-kubernetes-engine-5561",
                resource_name="ai-inference-deployment",
                provider="GCP",
                service="Google Kubernetes Engine",
                recommendation_type="Rightsizing",
                description="Les limites et requêtes du conteneur d'inférence d'IA du namespace 'ai-inference' sont surdimensionnées (16 cœurs requis vs 2.1 cœurs utilisés). Optimiser la spécification du Pod réduira les coûts.",
                current_cost=450.00,
                estimated_saving=320.00,
                roi_days=3,
                operational_risk="Medium",
                remediation_effort="Medium",
                status="Pending",
                remediation_script_type="kubectl",
                remediation_script="""# Modifier la configuration des ressources du Deployment K8s
kubectl set resources deployment ai-inference-service -n ai-inference --requests=cpu=3,memory=12Gi --limits=cpu=6,memory=24Gi
""",
                rollback_script="""# Rétablir les anciennes limites K8s
kubectl set resources deployment ai-inference-service -n ai-inference --requests=cpu=16,memory=64Gi --limits=cpu=32,memory=128Gi
"""
            ),
            Recommendation(
                id="rec-aws-s3-04",
                tenant_id=tenant_id,
                resource_id="aws-amazon-s3-1122",
                resource_name="finoptica-raw-data-archive",
                provider="AWS",
                service="Amazon S3",
                recommendation_type="Carbon",
                description="Le bucket S3 d'archive contient 42 TB de données sans Lifecycle Policy active. Transférer ces fichiers vers S3 Glacier Flexible Archive réduira les coûts de 75% et réduira l'empreinte carbone indirecte de stockage.",
                current_cost=920.00,
                estimated_saving=690.00,
                roi_days=30,
                operational_risk="Low",
                remediation_effort="Low",
                status="Pending",
                remediation_script_type="terraform",
                remediation_script="""# Définir des règles de cycle de vie S3 pour l'archivage
resource "aws_s3_bucket_lifecycle_configuration" "archive_lifecycle" {
  bucket = "finoptica-raw-data-archive"
  rule {
    id     = "archive-to-glacier"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}
""",
                rollback_script="""# Supprimer la configuration de cycle de vie S3
# Note : Les données déjà archivées dans Glacier resteront dans Glacier sauf si re-transférées manuellement.
"""
            ),
            Recommendation(
                id="rec-openai-05",
                tenant_id=tenant_id,
                resource_id="openai-gpt-4o-api",
                resource_name="Copilot System",
                provider="OpenAI",
                service="GPT-4o API",
                recommendation_type="GPU",
                description="90% des appels API du Copilot pour l'analyse syntaxique simple utilisent GPT-4o. Rediriger ces requêtes simples vers gpt-4o-mini ou utiliser du caching sémantique permet d'économiser massivement.",
                current_cost=150.00,
                estimated_saving=105.00,
                roi_days=1,
                operational_risk="Low",
                remediation_effort="Medium",
                status="Pending",
                remediation_script_type="bash",
                remediation_script="""# Activer la redirection de modèle dans le service d'orchestration IA
# Changer la variable d'environnement pour utiliser le modèle mini optimisé en coûts
export COPILOT_LIGHTWEIGHT_MODEL="gpt-4o-mini"
""",
                rollback_script="""# Revenir à GPT-4o
export COPILOT_LIGHTWEIGHT_MODEL="gpt-4o"
"""
            )
        ]
        for r in recoms:
            db.add(r)
            
        db.commit()
        print("Données FinOps d'exemple insérées avec succès !")

    @staticmethod
    def get_cost_summary(db: Session, tenant_id: str, days: int = 30):
        # S'assurer d'abord qu'il y a des données
        CostAnalyzerService.seed_data_if_empty(db, tenant_id)
        
        today = datetime.utcnow().date()
        start_date = datetime.combine(today - timedelta(days=days), datetime.min.time())
        
        # Coût Total
        total_cost = db.query(func.sum(CostItem.cost)).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= start_date
        ).scalar() or 0.0
        
        # Coût Période Précédente pour comparaison
        prev_start_date = datetime.combine(today - timedelta(days=days*2), datetime.min.time())
        prev_total_cost = db.query(func.sum(CostItem.cost)).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= prev_start_date,
            CostItem.date < start_date
        ).scalar() or 1.0
        
        percentage_change = ((total_cost - prev_total_cost) / prev_total_cost) * 100.0
        
        # Empreinte carbone
        total_carbon = db.query(func.sum(CostItem.carbon_emissions)).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= start_date
        ).scalar() or 0.0
        
        # Économies potentielles
        potential_savings = db.query(func.sum(Recommendation.estimated_saving)).filter(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == "Pending"
        ).scalar() or 0.0
        
        # Score d'efficacité FinOps (calculé à partir des ressources optimisées)
        total_rec_cost = db.query(func.sum(Recommendation.current_cost)).filter(
            Recommendation.tenant_id == tenant_id
        ).scalar() or 1.0
        efficiency_score = 100.0 - (min(potential_savings / total_rec_cost * 100.0, 45.0) if total_rec_cost > 0 else 0)
        
        return {
            "total_cost": round(total_cost, 2),
            "percentage_change": round(percentage_change, 2),
            "total_carbon_kg": round(total_carbon, 2),
            "potential_savings": round(potential_savings, 2),
            "efficiency_score": round(efficiency_score, 1),
            "days_analyzed": days
        }

    @staticmethod
    def get_cost_by_provider(db: Session, tenant_id: str, days: int = 30):
        today = datetime.utcnow().date()
        start_date = datetime.combine(today - timedelta(days=days), datetime.min.time())
        
        results = db.query(
            CostItem.provider,
            func.sum(CostItem.cost).label("total_cost"),
            func.sum(CostItem.carbon_emissions).label("total_carbon")
        ).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= start_date
        ).group_by(CostItem.provider).all()
        
        return [
            {
                "provider": r[0],
                "cost": round(r[1], 2),
                "carbon_kg": round(r[2], 2)
            } for r in results
        ]

    @staticmethod
    def get_cost_trend(db: Session, tenant_id: str, days: int = 30):
        today = datetime.utcnow().date()
        start_date = datetime.combine(today - timedelta(days=days), datetime.min.time())
        
        # Grouper les coûts par jour
        results = db.query(
            func.date(CostItem.date).label("cost_date"),
            CostItem.provider,
            func.sum(CostItem.cost).label("total_cost")
        ).filter(
            CostItem.tenant_id == tenant_id,
            CostItem.date >= start_date
        ).group_by(func.date(CostItem.date), CostItem.provider).order_by("cost_date").all()
        
        # Structurer pour les graphiques du frontend
        trend_map = {}
        for r in results:
            d_str = str(r[0])
            provider = r[1]
            cost = round(r[2], 2)
            
            if d_str not in trend_map:
                trend_map[d_str] = {"date": d_str, "total": 0.0}
            trend_map[d_str][provider] = cost
            trend_map[d_str]["total"] = round(trend_map[d_str]["total"] + cost, 2)
            
        return sorted(list(trend_map.values()), key=lambda x: x["date"])

    @staticmethod
    def get_kubernetes_efficiency(db: Session, tenant_id: str):
        # Récupérer l'efficacité des Namespaces Kubernetes sur les 7 derniers jours
        today = datetime.utcnow().date()
        start_date = datetime.combine(today - timedelta(days=7), datetime.min.time())
        
        results = db.query(
            KubernetesCost.namespace,
            func.avg(KubernetesCost.cpu_cores_requested).label("cpu_req"),
            func.avg(KubernetesCost.cpu_cores_used).label("cpu_used"),
            func.avg(KubernetesCost.memory_gb_requested).label("mem_req"),
            func.avg(KubernetesCost.memory_gb_used).label("mem_used"),
            func.sum(KubernetesCost.cost).label("total_cost"),
            func.avg(KubernetesCost.efficiency_score).label("avg_efficiency")
        ).filter(
            KubernetesCost.tenant_id == tenant_id,
            KubernetesCost.date >= start_date
        ).group_by(KubernetesCost.namespace).all()
        
        return [
            {
                "namespace": r[0],
                "cpu_requested": round(r[1], 2),
                "cpu_used": round(r[2], 2),
                "memory_requested_gb": round(r[3], 2),
                "memory_used_gb": round(r[4], 2),
                "total_cost": round(r[5], 2),
                "efficiency_score": round(r[6], 1)
            } for r in results
        ]
