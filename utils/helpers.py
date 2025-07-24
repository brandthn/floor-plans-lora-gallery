import json
from datetime import datetime
import re

def truncate_text(text, max_length=100):
    """Tronque un texte à une longueur maximale avec '...'"""
    if not text:
        return "N/A"
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def format_metadata(metadata):
    """Formate les métadonnées pour l'affichage"""
    if not isinstance(metadata, dict):
        return "Métadonnées invalides"
    
    formatted = {}
    
    # Prompt
    if 'prompt' in metadata:
        formatted['Prompt'] = metadata['prompt']
    
    # Approche
    if 'approach' in metadata:
        approach_names = {
            'single_lora': 'LoRA Simple',
            'combined_approach': 'Approche Combinée',
            'lora_plan_v1': 'LoRA Plan v1',
            'lora_plan_v2': 'LoRA Plan v2'
        }
        formatted['Approche'] = approach_names.get(metadata['approach'], metadata['approach'])
    
    # Configuration du modèle
    if 'model_config' in metadata and isinstance(metadata['model_config'], dict):
        config = metadata['model_config']
        if 'base_model' in config:
            formatted['Modèle de base'] = config['base_model']
        if 'lora_model' in config:
            formatted['Modèle LoRA'] = config['lora_model']
    
    # Paramètres de génération
    if 'generation_params' in metadata and isinstance(metadata['generation_params'], dict):
        params = metadata['generation_params']
        if 'steps' in params:
            formatted['Steps'] = params['steps']
        if 'cfg_scale' in params:
            formatted['CFG Scale'] = params['cfg_scale']
        if 'width' in params and 'height' in params:
            formatted['Dimensions'] = f"{params['width']}x{params['height']}"
    
    # Temps de génération
    if 'generation_time' in metadata:
        formatted['Temps de génération'] = f"{metadata['generation_time']} secondes"
    
    # Timestamp
    if 'timestamp' in metadata:
        formatted['Date de création'] = format_timestamp(metadata['timestamp'])
    
    return formatted

def format_timestamp(timestamp):
    """Formate un timestamp en date lisible"""
    try:
        if isinstance(timestamp, str):
            # Essaie différents formats de timestamp
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.strftime("%d/%m/%Y à %H:%M")
                except ValueError:
                    continue
            
            return timestamp  # Retourne tel quel si aucun format ne marche
        
        elif isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%d/%m/%Y à %H:%M")
        
        else:
            return str(timestamp)
    
    except Exception:
        return "Date invalide"

def parse_generation_time(time_str):
    """Parse le temps de génération depuis différents formats"""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    if isinstance(time_str, str):
        # Enlève les unités et caractères non numériques
        time_clean = re.sub(r'[^\d.]', '', time_str)
        try:
            return float(time_clean)
        except ValueError:
            return 0.0
    
    return 0.0

def extract_tags_from_prompt(prompt):
    """Extrait des tags depuis un prompt"""
    if not prompt:
        return []
    
    # Mots-clés courants dans les plans d'étage
    keywords = [
        'bedroom', 'living room', 'kitchen', 'bathroom', 'dining room',
        'office', 'studio', 'apartment', 'house', 'floor plan',
        'modern', 'traditional', 'open space', 'balcony', 'garden'
    ]
    
    prompt_lower = prompt.lower()
    found_tags = []
    
    for keyword in keywords:
        if keyword in prompt_lower:
            found_tags.append(keyword.title())
    
    return found_tags

def group_by_prompt_similarity(generations, similarity_threshold=0.7):
    """Groupe les générations par similarité de prompt"""
    # Algorithme simple basé sur les premiers mots du prompt
    groups = {}
    
    for gen in generations:
        prompt = gen.get('prompt', '')
        if not prompt:
            continue
        
        # Utilise les 5 premiers mots comme clé de groupement
        words = prompt.split()[:5]
        key = ' '.join(words).lower()
        
        if key not in groups:
            groups[key] = []
        groups[key].append(gen)
    
    # Retourne seulement les groupes avec plus d'une génération
    return {k: v for k, v in groups.items() if len(v) > 1}

def calculate_statistics(generations):
    """Calcule des statistiques sur les générations"""
    if not generations:
        return {}
    
    stats = {
        'total_generations': len(generations),
        'approaches': {},
        'base_models': {},
        'lora_models': {},
        'avg_generation_time': 0,
        'total_generation_time': 0
    }
    
    generation_times = []
    
    for gen in generations:
        # Comptage par approche
        approach = gen.get('approach', 'Unknown')
        stats['approaches'][approach] = stats['approaches'].get(approach, 0) + 1
        
        # Comptage par modèle de base
        model_config = gen.get('model_config', {})
        if isinstance(model_config, dict):
            base_model = model_config.get('base_model', 'Unknown')
            stats['base_models'][base_model] = stats['base_models'].get(base_model, 0) + 1
            
            lora_model = model_config.get('lora_model', 'Unknown')
            stats['lora_models'][lora_model] = stats['lora_models'].get(lora_model, 0) + 1
        
        # Temps de génération
        gen_time = gen.get('generation_time', 0)
        if isinstance(gen_time, (int, float)) and gen_time > 0:
            generation_times.append(gen_time)
    
    # Calcul des moyennes de temps
    if generation_times:
        stats['avg_generation_time'] = sum(generation_times) / len(generation_times)
        stats['total_generation_time'] = sum(generation_times)
    
    return stats

def validate_generation_data(generation):
    """Valide la structure des données d'une génération"""
    required_fields = ['prompt', 'approach']
    
    for field in required_fields:
        if field not in generation:
            return False, f"Champ manquant: {field}"
    
    # Validation du model_config
    if 'model_config' in generation:
        if not isinstance(generation['model_config'], dict):
            return False, "model_config doit être un dictionnaire"
    
    # Validation des paramètres de génération
    if 'generation_params' in generation:
        if not isinstance(generation['generation_params'], dict):
            return False, "generation_params doit être un dictionnaire"
    
    return True, "OK"

def format_file_size(size_bytes):
    """Formate une taille de fichier en unités lisibles"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def clean_prompt_text(prompt):
    """Nettoie le texte d'un prompt pour l'affichage"""
    if not prompt:
        return ""
    
    # Supprime les caractères de contrôle et les espaces multiples
    cleaned = re.sub(r'\s+', ' ', prompt.strip())
    
    # Supprime les caractères spéciaux potentiellement problématiques
    cleaned = re.sub(r'[^\w\s\-.,!?()]', '', cleaned)
    
    return cleaned