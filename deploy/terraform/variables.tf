variable "aws_region" {
  description = "Région AWS pour le déploiement"
  type        = string
  default     = "eu-west-3" # Paris (Faible intensité carbone - GreenOps)
}

variable "environment" {
  description = "Environnement cible (dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "db_password" {
  description = "Mot de passe administrateur pour la base de données PostgreSQL RDS"
  type        = string
  sensitive   = true
}
