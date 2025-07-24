# 🏠 Floor Plan Gallery - Application Streamlit

Application de galerie pour visualiser et comparer les images de plans d'étage générées par vos modèles LoRA basés sur Stable Diffusion.

## 📋 Prérequis

- Python 3.11
- Credentials AWS avec accès au bucket S3
- Bucket S3 contenant vos images et métadonnées

## 🚀 Installation

### 1. Clone

Créez la structure de dossiers suivante :

```
floor-plan-gallery-streamlit/
├── app.py
├── services/
│   ├── __init__.py
│   └── s3_service.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── requirements.txt
├── .env.example
└── README.md
```

### 2. Installer dépendances

```bash
pip install -r requirements.txt
```

### 3. Configuration variables d'environnement

1. Copiez le fichier `.env.example` vers `.env` :
   ```bash
   cp .env.example .env
   ```

2. Éditez le fichier `.env` avec vraies credentials :
   ```env
   AWS_ACCESS_KEY_ID=votre_access_key_ici
   AWS_SECRET_ACCESS_KEY=votre_secret_key_ici
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=floor-plan-gallery-3344
   ```

## 🎯 Lancement de l'application

```bash
streamlit run app.py
```

L'application sera accessible à l'adresse : `http://localhost:8501`

## 📊 Fonctionnalités

### 🖼️ Galerie Principale
- Grille responsive d'images avec métadonnées
- Pagination automatique (12 images par page)
- Vue détaillée avec expandeurs
- Affichage des prompts, approches et modèles

### 🔍 Filtres Avancés
- **Approche** : LoRA simple, approche combinée, etc.
- **Modèle de base** : sdxl_base, juggernautXL
- **Modèle LoRA** : lora_plan_v1, lora_plan_v2, wall_lora
- **Recherche textuelle** : Dans les prompts (en développement)


### Format des métadonnées JSON

```json
{
  "prompt": "Floor plan with 2 bedrooms and living room",
  "approach": "single_lora",
  "model_config": {
    "base_model": "sdxl_base",
    "lora_model": "lora_plan_v1"
  },
  "generation_params": {
    "steps": 25,
    "cfg_scale": 7.5,
    "width": 1024,
    "height": 1024
  },
  "generation_time": 25.3,
  "timestamp": "2024-01-15T14:30:25.123Z"
}
```

## 🔧 Personnalisation

### Modifier le nombre d'images par page
Dans `app.py`, ligne ~108 :
```python
items_per_page = 12
```

### Ajouter de nouveaux filtres
Dans `s3_service.py`, méthode `get_available_filters()`, ajoutez vos nouveaux critères.

### Personnaliser l'affichage des cartes
Modifiez la fonction `display_image_card()` dans `app.py`.

## 🐛 Résolution de problèmes

### Erreur de connexion S3
- Vérifiez vos credentials AWS dans le fichier `.env`
- Assurez-vous que votre utilisateur AWS a les permissions `s3:GetObject` et `s3:ListBucket`
- Vérifiez que le nom du bucket est correct

### Images qui ne s'affichent pas
- Vérifiez que les fichiers JSON pointent vers des images existantes
- Assurez-vous que la convention de nommage est respectée (`nom_metadata.json` → `nom.png/jpg`)

### Performance lente
- Réduisez le nombre d'images par page

## 📝 Logs et Debug

Pour activer le mode debug, ajoutez dans votre `.env` :
```env
DEBUG=true
```
