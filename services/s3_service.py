import boto3
import json
import streamlit as st
from PIL import Image
from io import BytesIO
import os
from botocore.exceptions import ClientError, NoCredentialsError

class S3GalleryService:
    """Service pour interagir avec le bucket S3 des plans d'étage"""
    
    def __init__(self):
        """Initialise le client S3 avec les credentials depuis .env"""
        try:
            self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
            self.bucket_name = os.getenv('S3_BUCKET_NAME')
            
            if not all([self.aws_access_key, self.aws_secret_key, self.bucket_name]):
                raise ValueError("Variables d'environnement AWS manquantes dans le fichier .env")
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            # Test de connexion
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
        except NoCredentialsError:
            st.error("Erreur d'authentification AWS. Vérifiez vos credentials.")
            raise
        except ClientError as e:
            st.error(f"Erreur de connexion au bucket S3: {e}")
            raise
        except Exception as e:
            st.error(f"Erreur d'initialisation du service S3: {e}")
            raise
    
    def get_all_generations(self):
        """Récupère toutes les générations depuis le dossier metadata/by_generation/"""
        try:
            generations = []
            
            # Liste tous les fichiers JSON dans metadata/by_generation/
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='metadata/by_generation/'
            )
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # Traite seulement les fichiers JSON
                    if key.endswith('.json'):
                        try:
                            metadata = self._load_metadata_from_s3(key)
                            if metadata and self._validate_generation_metadata(metadata):
                                # Ajoute les informations de localisation S3
                                metadata['metadata_key'] = key
                                metadata['image_key'] = self._get_image_key_from_metadata(metadata)
                                generations.append(metadata)
                        except Exception as e:
                            st.warning(f"Erreur lors du traitement de {key}: {e}")
                            continue
            
            return generations
            
        except Exception as e:
            st.error(f"Erreur lors de la récupération des générations: {e}")
            return []
    
    def _load_metadata_from_s3(self, metadata_key):
        """Charge un fichier de métadonnées JSON depuis S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            st.warning(f"Impossible de charger les métadonnées {metadata_key}: {e}")
            return None
    
    def _validate_generation_metadata(self, metadata):
        """Valide que les métadonnées ont la structure attendue"""
        required_fields = ['generation_id', 'approach', 'model_config']
        return all(field in metadata for field in required_fields)
    
    def _get_image_key_from_metadata(self, metadata):
        """Construit la clé S3 de l'image depuis les métadonnées"""
        try:
            generation_id = metadata['generation_id']
            approach = metadata['approach']
            
            # Construit le chemin selon la structure: images/by_approach/{approach}/{generation_id}.png
            image_key = f"images/by_approach/{approach}/{generation_id}.png"
            
            # Vérifie si l'image existe, sinon essaie avec .jpg
            if self._object_exists(image_key):
                return image_key
            
            image_key_jpg = f"images/by_approach/{approach}/{generation_id}.jpg"
            if self._object_exists(image_key_jpg):
                return image_key_jpg
                
            # Si aucune image n'est trouvée, utilise l'URL des métadonnées si disponible
            if 's3_paths' in metadata and 'main_image' in metadata['s3_paths']:
                s3_url = metadata['s3_paths']['main_image']
                # Extrait la clé S3 depuis l'URL
                if '.s3.amazonaws.com/' in s3_url:
                    return s3_url.split('.s3.amazonaws.com/')[-1]
            
            return None
            
        except Exception as e:
            st.warning(f"Erreur lors de la construction du chemin image: {e}")
            return None
    
    def _object_exists(self, key):
        """Vérifie si un objet existe dans S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def get_image(self, image_key):
        """Récupère une image depuis S3 et la retourne comme objet PIL"""
        if not image_key:
            return None
            
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=image_key)
            image_data = response['Body'].read()
            image = Image.open(BytesIO(image_data))
            return image
        except Exception as e:
            st.warning(f"Impossible de charger l'image {image_key}: {e}")
            return None
    
    def get_available_filters(self):
        """Analyse toutes les générations pour extraire les valeurs de filtres disponibles"""
        try:
            generations = self.get_all_generations()
            
            approaches = set()
            base_models = set()
            lora_models = set()
            
            for gen in generations:
                # Approches
                if 'approach' in gen:
                    approaches.add(gen['approach'])
                
                # Modèles de base et LoRA
                model_config = gen.get('model_config', {})
                if isinstance(model_config, dict):
                    if 'base_model' in model_config:
                        base_models.add(model_config['base_model'])
                    if 'lora_model' in model_config:
                        lora_models.add(model_config['lora_model'])
            
            return {
                'approaches': sorted(list(approaches)),
                'base_models': sorted(list(base_models)),
                'lora_models': sorted(list(lora_models))
            }
            
        except Exception as e:
            st.error(f"Erreur lors de l'extraction des filtres: {e}")
            return {
                'approaches': [],
                'base_models': [],
                'lora_models': []
            }
    
    def get_comparisons(self):
        """Récupère les comparaisons depuis metadata/comparisons/"""
        try:
            comparisons = []
            
            # Liste tous les fichiers de comparaison
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='metadata/comparisons/'
            )
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    if key.endswith('.json') and 'comp_' in key:
                        try:
                            comparison = self._load_metadata_from_s3(key)
                            if comparison:
                                comparisons.append(comparison)
                        except Exception as e:
                            st.warning(f"Erreur lors du traitement de la comparaison {key}: {e}")
                            continue
            
            return comparisons
            
        except Exception as e:
            st.error(f"Erreur lors de la récupération des comparaisons: {e}")
            return []
    
    def get_generations_by_prompt_hash(self, prompt_hash):
        """Récupère les générations pour un prompt_hash donné via l'index"""
        try:
            index_key = f"indexes/by_prompt_hash/{prompt_hash}.json"
            index_data = self._load_metadata_from_s3(index_key)
            
            if not index_data or 'entries' not in index_data:
                return []
            
            generations = []
            for entry in index_data['entries']:
                # Récupère les métadonnées complètes de chaque génération
                generation_id = entry['generation_id']
                metadata_key = f"metadata/by_generation/{generation_id}.json"
                full_metadata = self._load_metadata_from_s3(metadata_key)
                
                if full_metadata:
                    full_metadata['image_key'] = self._get_image_key_from_metadata(full_metadata)
                    generations.append(full_metadata)
            
            return generations
            
        except Exception as e:
            st.error(f"Erreur lors de la récupération des générations pour {prompt_hash}: {e}")
            return []
    
    def search_generations(self, query, generations=None):
        """Recherche dans les prompts des générations"""
        if generations is None:
            generations = self.get_all_generations()
        
        if not query:
            return generations
        
        query_lower = query.lower()
        filtered = []
        
        for gen in generations:
            # Recherche dans le prompt original
            prompt_info = gen.get('prompt_info', {})
            original_prompt = prompt_info.get('original', '').lower()
            
            # Recherche aussi dans les tags
            tags = gen.get('tags', [])
            tags_text = ' '.join(tags).lower()
            
            if query_lower in original_prompt or query_lower in tags_text:
                filtered.append(gen)
        
        return filtered
    
    def get_bucket_structure_info(self):
        """Analyse la structure du bucket S3 pour debug"""
        try:
            structure = {
                'images': {'by_approach': {}, 'debug': 0},
                'metadata': {'by_generation': 0, 'comparisons': 0},
                'indexes': {'by_approach': 0, 'by_prompt_hash': 0, 'recent': 0}
            }
            
            # Compte les objets par préfixe
            prefixes = [
                'images/by_approach/single_lora/',
                'images/by_approach/combined_approach/',
                'images/debug/',
                'metadata/by_generation/',
                'metadata/comparisons/',
                'indexes/by_approach/',
                'indexes/by_prompt_hash/',
                'indexes/recent.json'
            ]
            
            for prefix in prefixes:
                count = self._count_objects_with_prefix(prefix)
                
                # Parse le chemin pour mettre à jour la structure
                parts = prefix.split('/')
                if parts[0] == 'images':
                    if parts[1] == 'by_approach' and len(parts) > 2:
                        structure['images']['by_approach'][parts[2]] = count
                    elif parts[1] == 'debug':
                        structure['images']['debug'] = count
                elif parts[0] == 'metadata':
                    structure['metadata'][parts[1]] = count
                elif parts[0] == 'indexes':
                    if parts[1] == 'recent.json':
                        structure['indexes']['recent'] = count
                    else:
                        structure['indexes'][parts[1]] = count
            
            return structure
            
        except Exception as e:
            st.error(f"Erreur lors de l'analyse de la structure: {e}")
            return None
    
    def _count_objects_with_prefix(self, prefix):
        """Compte le nombre d'objets avec un préfixe donné"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            count = 0
            for page in pages:
                count += len(page.get('Contents', []))
            
            return count
        except Exception:
            return 0