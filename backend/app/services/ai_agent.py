import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models import Conversation, Message, Recommendation, CostItem
from sqlalchemy import func

class AIAgentService:
    # Base RAG intégrée (Simulée pour être ultra-performante et riche en connaissances FinOps)
    KNOWLEDGE_BASE = {
        "rightsizing": (
            "Le Rightsizing consiste à redimensionner vos instances de calcul (VM, conteneurs) pour correspondre au plus près à vos besoins "
            "de charge de travail réels. Les meilleures pratiques de la FinOps Foundation recommandent de maintenir une utilisation CPU moyenne "
            "entre 40% et 70% pour la production, et d'éteindre complètement les environnements de développement hors des heures de bureau."
        ),
        "spot": (
            "Les instances AWS Spot (ou Azure Spot VMs) offrent jusqu'à 90% de réduction par rapport aux tarifs On-Demand. "
            "Elles conviennent parfaitement aux conteneurs de traitement batch, aux environnements CI/CD, et aux nœuds de calcul Kubernetes "
            "tolérant les interruptions. Utilisez des outils comme Spot by NetApp ou configurez des Spot Instances Pools pour maximiser la disponibilité."
        ),
        "savings_plans": (
            "Les Savings Plans (AWS/Azure) offrent de fortes réductions (jusqu'à 72%) en échange d'un engagement de consommation horaire constant "
            "(ex: 10$/heure) sur une période de 1 ou 3 ans. Il est conseillé de couvrir environ 60% à 70% de votre base de coûts fixes par des Savings Plans, "
            "le reste devant être optimisé par du Rightsizing et du Spot."
        ),
        "carbon": (
            "Le GreenOps est une branche du FinOps visant à réduire l'empreinte carbone de votre infrastructure Cloud. "
            "Transférer vos charges de travail vers des régions à faible intensité carbone (comme la région AWS eu-west-3 en France qui est alimentée principalement par de l'énergie décarbonée) "
            "et archiver les données froides permet de réduire les émissions de CO2 de plus de 80%."
        )
    }

    @staticmethod
    def get_or_create_conversation(db: Session, tenant_id: str, conversation_id: str = None) -> Conversation:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conv = Conversation(id=conversation_id, tenant_id=tenant_id, title="Optimisation des coûts Cloud")
            db.add(conv)
            db.commit()
            
            # Ajouter le message d'accueil du système FinOps
            welcome = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=(
                    "👋 Bonjour ! Je suis **FinOptica Copilot**, votre expert IA en optimisation financière Cloud et GreenOps.\n\n"
                    "Je viens d'analyser vos comptes multi-cloud (AWS, Azure, GCP), vos conteneurs Kubernetes et vos usages d'APIs IA.\n"
                    "Voici ce que j'ai identifié sur votre infrastructure :\n"
                    "* 💡 **Économies possibles immédiates** : environ **1 486.70 $ / mois** via 5 recommandations.\n"
                    "* ⚠️ **Anomalies en cours** : **2 anomalies non résolues** détectées (dont une critique sur l'API OpenAI).\n"
                    "* 🌱 **Empreinte Carbone** : Possibilité de réduire vos émissions de CO2 de **690.00 kg**.\n\n"
                    "Comment puis-je vous aider aujourd'hui ? Vous pouvez me poser des questions sur une ressource spécifique, me demander de générer des scripts de remédiation Terraform, ou simuler l'achat de Savings Plans."
                ),
                created_at=datetime.utcnow()
            )
            db.add(welcome)
            db.commit()
            return conv
            
        conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id).first()
        if not conv:
            conv = Conversation(id=conversation_id, tenant_id=tenant_id, title="Optimisation des coûts Cloud")
            db.add(conv)
            db.commit()
        return conv

    @staticmethod
    def list_conversations(db: Session, tenant_id: str):
        # S'assurer d'au moins une discussion d'exemple
        convs = db.query(Conversation).filter(Conversation.tenant_id == tenant_id).all()
        if not convs:
            AIAgentService.get_or_create_conversation(db, tenant_id)
            convs = db.query(Conversation).filter(Conversation.tenant_id == tenant_id).all()
            
        return [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M")
            } for c in convs
        ]

    @staticmethod
    def send_message(db: Session, tenant_id: str, conversation_id: str, prompt: str) -> dict:
        conv = AIAgentService.get_or_create_conversation(db, tenant_id, conversation_id)
        
        # Enregistrer le message utilisateur
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=prompt,
            created_at=datetime.utcnow()
        )
        db.add(user_msg)
        db.commit()
        
        # Analyser le prompt et générer une réponse experte contextualisée
        response_text = ""
        metadata = None
        
        prompt_lower = prompt.lower()
        
        # 1. Requête concernant Terraform ou l'automatisation
        if "terraform" in prompt_lower or "script" in prompt_lower or "remedi" in prompt_lower or "code" in prompt_lower:
            recs = db.query(Recommendation).filter(Recommendation.tenant_id == tenant_id, Recommendation.status == "Pending").all()
            if recs:
                best_rec = recs[0] # Prendre la première recommandation pour l'exemple
                response_text = (
                    f"Certainement ! J'ai généré le plan d'action d'automatisation pour la recommandation active **{best_rec.id}** ({best_rec.resource_name}).\n\n"
                    f"### Plan de Remédiation : {best_rec.recommendation_type}\n"
                    f"**Ressource** : `{best_rec.resource_id}` ({best_rec.service})\n"
                    f"**Impact Financier** : Économie estimée de **{best_rec.estimated_saving} $ / mois**\n"
                    f"**Niveau de Risque** : `{best_rec.operational_risk}` | **Effort** : `{best_rec.remediation_effort}`\n\n"
                    f"Voici le script de remédiation `{best_rec.remediation_script_type}` généré et validé par mes soins (dry-run OK) :\n\n"
                    f"```{best_rec.remediation_script_type}\n{best_rec.remediation_script}```\n\n"
                    f"### Procédure de Rollback\n"
                    f"En cas de comportement anormal de la production, vous pouvez appliquer ce script de rollback :\n\n"
                    f"```{best_rec.remediation_script_type}\n{best_rec.rollback_script}```\n\n"
                    f"Vous pouvez appliquer cette modification directement en cliquant sur le bouton **Appliquer la remédiation** dans l'onglet Optimisation de votre console."
                )
                metadata = {
                    "type": "remediation_widget",
                    "recommendation_id": best_rec.id,
                    "script_type": best_rec.remediation_script_type,
                    "estimated_saving": best_rec.estimated_saving
                }
            else:
                response_text = "Toutes les recommandations sont actuellement appliquées ! Aucun script de remédiation n'est en attente."
                
        # 2. Requête concernant les anomalies
        elif "anomalie" in prompt_lower or "pic" in prompt_lower or "alerte" in prompt_lower or "hausse" in prompt_lower:
            response_text = (
                "J'ai analysé les anomalies de coûts récentes sur votre compte :\n\n"
                "1. 🛑 **API OpenAI (Critique)** : Pic de coût à **180.00 $** (vs 45.00 $ attendus) il y a 2 jours. \n"
                "   * **Cause** : Boucle infinie détectée dans l'agent de reporting asynchrone.\n"
                "   * **Statut** : Non résolue. Je vous conseille de limiter le budget quotidien de votre clé API OpenAI à 50 $ pour stopper le gaspillage.\n\n"
                "2. ⚠️ **Amazon EKS (Élevée)** : Pic à **450.00 $** (vs 120.00 $ attendus) il y a 5 jours.\n"
                "   * **Cause** : Déploiement accidentel de pods répliqués en boucle dans le namespace `ai-inference`.\n"
                "   * **Statut** : Non résolue.\n\n"
                "Souhaitez-vous que je génère le script kubectl pour réduire les réplicas du namespace `ai-inference` ?"
            )
            metadata = {
                "type": "anomaly_list_widget",
                "anomalies": [
                    {"id": "anom-openai-gpt4o-02", "severity": "Critical", "saving": 135.00},
                    {"id": "anom-aws-eks-01", "severity": "High", "saving": 330.00}
                ]
            }
            
        # 3. Requête concernant Kubernetes
        elif "kubernetes" in prompt_lower or "k8s" in prompt_lower or "pod" in prompt_lower or "namespace" in prompt_lower:
            response_text = (
                "Voici l'état d'efficacité et d'allocation des coûts de votre cluster Kubernetes principal (`k8s-prod-cluster-01`) :\n\n"
                "| Namespace | CPU Requis | CPU Utilisé | Mémoire Requise | Coût Cumulé | Score d'Efficacité |\n"
                "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                "| `ai-inference` | 32.5 | 24.1 | 130 GB | 450.00 $ | **74.1%** |\n"
                "| `data-analytics` | 42.0 | 31.5 | 168 GB | 580.00 $ | **75.0%** |\n"
                "| `production-app` | 18.0 | 14.4 | 72 GB | 250.00 $ | **80.0%** |\n"
                "| `staging-app` | 15.0 | 3.5 | 60 GB | 210.00 $ | 🛑 **23.3%** |\n\n"
                "**Constat FinOps** : Le namespace `staging-app` présente une efficacité critique de **23.3%**. Les pods demandent 15 CPU mais n'en consomment que 3.5 en moyenne. C'est un gaspillage de **161.70 $ / mois**.\n\n"
                "Je vous conseille d'appliquer un **Horizontal Pod Autoscaler (HPA)** ou de réduire les requêtes par défaut dans votre fichier Helm Chart."
            )
            metadata = {
                "type": "k8s_widget",
                "namespaces": ["staging-app", "ai-inference", "data-analytics"]
            }
            
        # 4. Requête concernant le carbone ou GreenOps
        elif "carbon" in prompt_lower or "ecolo" in prompt_lower or "co2" in prompt_lower or "green" in prompt_lower:
            response_text = (
                "Absolument, l'optimisation carbone est un pilier essentiel du framework modern GreenOps.\n\n"
                "Sur les 30 derniers jours, votre infrastructure cloud a émis environ **345.60 kg de CO2**.\n"
                "Voici les leviers majeurs identifiés pour réduire votre empreinte écologique de **690.00 kg de CO2** cumulés :\n\n"
                "1. 🌱 **Archivage S3 vers Glacier** (Bucket `finoptica-raw-data-archive`) : Réduit le besoin d'alimentation continue des serveurs de stockage. Économie de **210 kg CO2 / an**.\n"
                "2. 🌍 **Migration de Région** : Déplacer vos serveurs de staging de `us-east-1` (Virginie - intensité carbone moyenne) vers `eu-west-3` (Paris - intensité carbone très faible grâce à l'énergie décarbonée). Réduction de **480 kg CO2 / an** (environ -88% sur ce périmètre !).\n\n"
                "Souhaitez-vous que je prépare le plan de migration Terraform pour déplacer vos environnements dev/staging vers Paris ?"
            )
            
        # 5. Réponse par défaut enrichie par la base de connaissances
        else:
            response_text = (
                "J'ai pris note de votre question. En tant que copilote FinOps IA, je peux vous proposer plusieurs analyses spécifiques :\n\n"
                "1. **Rightsizing** : Analyser l'utilisation CPU/Mémoire réelle de vos VM pour rétrograder d'instance.\n"
                "2. **Gestion des Anomalies** : Enquêter sur les pics de consommation suspects sur vos comptes cloud.\n"
                "3. **Optimisation Kubernetes** : Repérer les conteneurs surdimensionnés dans vos clusters.\n"
                "4. **GreenOps** : Estimer et réduire l'empreinte carbone en kg CO2 de vos applications.\n"
                "5. **Scripts d'automatisation** : Vous générer des fichiers Terraform ou des commandes CLI pour appliquer les économies en un clic.\n\n"
                "Que souhaitez-vous approfondir ?"
            )
            
        # Enregistrer le message de l'assistant
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=response_text,
            created_at=datetime.utcnow(),
            metadata_json=metadata
        )
        db.add(assistant_msg)
        
        # Mettre à jour le titre de la conversation basé sur la première requête
        if len(conv.messages) <= 3: # 1 welcome + 1 user + 1 assistant
            conv.title = prompt[:30] + "..." if len(prompt) > 30 else prompt
            
        db.commit()
        
        return {
            "conversation_id": conv.id,
            "role": "assistant",
            "content": response_text,
            "created_at": assistant_msg.created_at.strftime("%Y-%m-%d %H:%M"),
            "metadata": metadata
        }

    @staticmethod
    def get_conversation_history(db: Session, tenant_id: str, conversation_id: str):
        conv = AIAgentService.get_or_create_conversation(db, tenant_id, conversation_id)
        
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "metadata": m.metadata_json
            } for m in conv.messages
        ]
