import streamlit as st
import pandas as pd
from PIL import Image
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Import des services personnalisés
from services.s3_service import S3GalleryService
from utils.helpers import format_metadata, truncate_text, parse_generation_time

# Chargement des variables d'environnement
load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="Floor Plan Gallery",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation du service S3
@st.cache_resource
def init_s3_service():
    return S3GalleryService()

# Cache pour les données S3
@st.cache_data(ttl=300)  # Cache de 5 minutes
def load_all_generations():
    s3_service = init_s3_service()
    return s3_service.get_all_generations()

@st.cache_data(ttl=300)
def get_available_filters():
    s3_service = init_s3_service()
    return s3_service.get_available_filters()

def main():
    # Titre principal
    st.title("🏠 Floor Plan Gallery")
    st.markdown("---")
    
    # Chargement des données
    with st.spinner("Chargement de la galerie..."):
        try:
            generations = load_all_generations()
            filters_data = get_available_filters()
            
            if not generations:
                st.warning("Aucune image trouvée dans le bucket S3.")
                return
                
        except Exception as e:
            st.error(f"Erreur lors du chargement des données : {str(e)}")
            return
    
    # Sidebar - Filtres
    st.sidebar.header("🔍 Filtres")
    
    # Filtre par approche
    approaches = st.sidebar.multiselect(
        "Approche de génération",
        options=filters_data.get('approaches', []),
        default=filters_data.get('approaches', [])
    )
    
    # Filtre par modèle de base
    base_models = st.sidebar.multiselect(
        "Modèle de base",
        options=filters_data.get('base_models', []),
        default=filters_data.get('base_models', [])
    )
    
    # Filtre par modèle LoRA
    lora_models = st.sidebar.multiselect(
        "Modèle LoRA",
        options=filters_data.get('lora_models', []),
        default=filters_data.get('lora_models', [])
    )
    
    # Recherche par texte
    search_query = st.sidebar.text_input("🔍 Rechercher dans les prompts")
    
    # Bouton reset
    if st.sidebar.button("🔄 Réinitialiser les filtres"):
        st.rerun()
    
    # Application des filtres
    filtered_generations = apply_filters(
        generations, approaches, base_models, lora_models, search_query
    )
    
    # Onglets principaux
    tab1, tab2, tab3 = st.tabs(["📊 Galerie", "🔄 Comparaisons", "📈 Statistiques"])
    
    with tab1:
        display_gallery(filtered_generations)
    
    with tab2:
        display_comparisons(filtered_generations)
    
    with tab3:
        display_statistics(filtered_generations)

def apply_filters(generations, approaches, base_models, lora_models, search_query):
    """Applique les filtres sélectionnés aux générations"""
    filtered = generations.copy()
    
    # Filtre par approche
    if approaches:
        filtered = [g for g in filtered if g.get('approach') in approaches]
    
    # Filtre par modèle de base
    if base_models:
        filtered = [g for g in filtered if g.get('model_config', {}).get('base_model') in base_models]
    
    # Filtre par modèle LoRA
    if lora_models:
        filtered = [g for g in filtered if g.get('model_config', {}).get('lora_model') in lora_models]
    
    # Recherche textuelle - utilise la nouvelle structure prompt_info
    if search_query:
        query_lower = search_query.lower()
        filtered_search = []
        for g in filtered:
            # Recherche dans le prompt original
            prompt_info = g.get('prompt_info', {})
            original_prompt = prompt_info.get('original', '').lower()
            
            # Recherche aussi dans les tags
            tags = g.get('tags', [])
            tags_text = ' '.join(tags).lower()
            
            if query_lower in original_prompt or query_lower in tags_text:
                filtered_search.append(g)
        
        filtered = filtered_search
    
    return filtered

def display_gallery(generations):
    """Affiche la galerie principale"""
    st.header(f"📊 Galerie ({len(generations)} images)")
    
    if not generations:
        st.info("Aucune image ne correspond aux filtres sélectionnés.")
        return
    
    # Pagination
    items_per_page = 12
    total_pages = (len(generations) - 1) // items_per_page + 1
    
    if total_pages > 1:
        page = st.selectbox("Page", range(1, total_pages + 1)) - 1
    else:
        page = 0
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(generations))
    page_generations = generations[start_idx:end_idx]
    
    # Grille d'images (4 colonnes)
    cols_per_row = 4
    for i in range(0, len(page_generations), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(page_generations):
                generation = page_generations[i + j]
                display_image_card(generation, col)

def display_image_card(generation, col):
    """Affiche une carte d'image individuelle"""
    with col:
        try:
            # Chargement et affichage de l'image
            s3_service = init_s3_service()
            image = s3_service.get_image(generation['image_key'])
            
            if image:
                # Redimensionnement pour l'affichage
                image.thumbnail((300, 300))
                st.image(image, use_column_width=True)
                
                # Métadonnées de base - utilise la nouvelle structure
                prompt_info = generation.get('prompt_info', {})
                original_prompt = prompt_info.get('original', 'N/A')
                
                st.write(f"**Prompt:** {truncate_text(original_prompt, 80)}")
                st.write(f"**Approche:** {generation.get('approach', 'N/A')}")
                st.write(f"**Modèle:** {generation.get('model_config', {}).get('lora_model', 'N/A')}")
                
                # Affichage des tags si disponibles
                tags = generation.get('tags', [])
                if tags:
                    st.write(f"**Tags:** {', '.join(tags[:3])}{'...' if len(tags) > 3 else ''}")
                
                # Expandeur pour les détails
                with st.expander("Voir détails"):
                    display_detailed_metadata(generation)
            else:
                st.error("Image non trouvée")
                st.write(f"**ID:** {generation.get('generation_id', 'N/A')}")
                st.write(f"**Approche:** {generation.get('approach', 'N/A')}")
                st.write(f"**Chemin:** {generation.get('image_key', 'N/A')}")
            
        except Exception as e:
            st.error(f"Erreur lors du chargement de l'image : {str(e)}")
            st.write(f"**ID:** {generation.get('generation_id', 'N/A')}")
            st.write(f"**Chemin image:** {generation.get('image_key', 'N/A')}")

def display_detailed_metadata(generation):
    """Affiche les métadonnées détaillées d'une génération"""
    
    # Informations de base
    st.write(f"**ID de génération:** {generation.get('generation_id', 'N/A')}")
    
    # Prompt complet avec structure
    prompt_info = generation.get('prompt_info', {})
    if prompt_info:
        st.write("**Prompt original:**")
        st.write(prompt_info.get('original', 'N/A'))
        
        # Structure du prompt
        structure = prompt_info.get('structure', {})
        if structure:
            st.write("**Structure détectée:**")
            rooms = structure.get('rooms', [])
            if rooms:
                st.write(f"- Pièces: {', '.join(rooms)}")
            
            counts = structure.get('counts', {})
            if counts:
                count_text = [f"{room}: {count}" for room, count in counts.items()]
                st.write(f"- Quantités: {', '.join(count_text)}")
    
    # Configuration du modèle
    st.write("**Configuration du modèle:**")
    model_config = generation.get('model_config', {})
    for key, value in model_config.items():
        st.write(f"- {key}: {value}")
    
    # Paramètres de génération
    st.write("**Paramètres de génération:**")
    params = generation.get('generation_params', {})
    for key, value in params.items():
        st.write(f"- {key}: {value}")
    
    # Informations temporelles
    if 'generation_time' in generation:
        st.write(f"**Temps de génération:** {generation['generation_time']} secondes")
    
    if 'timestamp' in generation:
        st.write(f"**Date de création:** {generation['timestamp']}")
    
    # Tags
    tags = generation.get('tags', [])
    if tags:
        st.write(f"**Tags:** {', '.join(tags)}")
    
    # Informations sur le device
    device_info = generation.get('device_info', {})
    if device_info:
        st.write("**Informations système:**")
        for key, value in device_info.items():
            st.write(f"- {key}: {value}")

def display_comparisons(generations):
    """Affiche les comparaisons groupées par prompt similaire"""
    st.header("🔄 Comparaisons")
    
    # Utilise le service S3 pour récupérer les vraies comparaisons
    s3_service = init_s3_service()
    
    try:
        # Récupère les comparaisons depuis S3
        comparisons = s3_service.get_comparisons()
        
        if not comparisons:
            st.info("Aucune comparaison disponible dans metadata/comparisons/.")
            return
        
        # Affiche chaque comparaison
        for comparison in comparisons:
            prompt = comparison.get('original_prompt', '')
            comparison_generations = comparison.get('generations', [])
            
            if len(comparison_generations) <= 1:
                continue
            
            st.subheader(f"Prompt: {truncate_text(prompt, 100)}")
            
            # Affichage côte à côte
            cols = st.columns(min(len(comparison_generations), 4))  # Max 4 colonnes
            
            for i, comp_gen in enumerate(comparison_generations):
                if i >= 4:  # Limite à 4 images par ligne
                    break
                    
                with cols[i]:
                    try:
                        # Utilise l'URL d'image directement depuis la comparaison
                        image_url = comp_gen.get('image_url', '')
                        
                        # Extrait la clé S3 depuis l'URL
                        if '.s3.amazonaws.com/' in image_url:
                            image_key = image_url.split('.s3.amazonaws.com/')[-1]
                            image = s3_service.get_image(image_key)
                            
                            if image:
                                image.thumbnail((250, 250))
                                st.image(image, use_column_width=True)
                            else:
                                st.error("Image non trouvée")
                        
                        # Informations sur la génération
                        st.write(f"**{comp_gen.get('approach', 'N/A')}**")
                        
                        model = comp_gen.get('model', {})
                        if 'lora_model' in model:
                            st.write(f"Modèle: {model['lora_model']}")
                        elif 'base_model' in model:
                            st.write(f"Modèle: {model['base_model']}")
                        
                        if 'generation_time' in comp_gen:
                            st.write(f"Temps: {comp_gen['generation_time']}s")
                        
                        # ID pour référence
                        st.caption(f"ID: {comp_gen.get('generation_id', 'N/A')[:8]}...")
                        
                    except Exception as e:
                        st.error(f"Erreur: {str(e)}")
            
            st.markdown("---")
    
    except Exception as e:
        st.error(f"Erreur lors du chargement des comparaisons: {e}")
        
        # Fallback: groupement simple par structure de prompt
        st.info("Tentative de groupement automatique...")
        
        # Groupement par hash de prompt depuis les métadonnées
        grouped = {}
        for gen in generations:
            prompt_info = gen.get('prompt_info', {})
            prompt_hash = prompt_info.get('hash', 'unknown')
            
            if prompt_hash not in grouped:
                grouped[prompt_hash] = []
            grouped[prompt_hash].append(gen)
        
        # Affichage des groupes avec plus d'une image
        comparison_groups = {k: v for k, v in grouped.items() if len(v) > 1}
        
        if not comparison_groups:
            st.info("Aucune comparaison automatique disponible.")
            return
        
        for prompt_hash, group_generations in comparison_groups.items():
            # Utilise le premier prompt comme titre
            first_prompt = group_generations[0].get('prompt_info', {}).get('original', 'Prompt inconnu')
            st.subheader(f"Hash: {prompt_hash} - {truncate_text(first_prompt, 80)}")
            
            cols = st.columns(min(len(group_generations), 4))
            for i, generation in enumerate(group_generations):
                if i >= 4:
                    break
                    
                with cols[i]:
                    try:
                        image = s3_service.get_image(generation['image_key'])
                        if image:
                            image.thumbnail((250, 250))
                            st.image(image, use_column_width=True)
                            st.write(f"**{generation.get('approach', 'N/A')}**")
                            st.write(f"Modèle: {generation.get('model_config', {}).get('lora_model', 'N/A')}")
                            if 'generation_time' in generation:
                                st.write(f"Temps: {generation['generation_time']}s")
                    except Exception as e:
                        st.error(f"Erreur: {str(e)}")
            
            st.markdown("---")

def display_statistics(generations):
    """Affiche des statistiques sur les générations"""
    st.header("📈 Statistiques")
    
    if not generations:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Conversion en DataFrame pour faciliter l'analyse
    df = pd.DataFrame(generations)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Répartition par approche")
        if 'approach' in df.columns:
            approach_counts = df['approach'].value_counts()
            st.bar_chart(approach_counts)
        
        st.subheader("Temps de génération moyen")
        if 'generation_time' in df.columns:
            avg_time = df['generation_time'].mean()
            st.metric("Temps moyen", f"{avg_time:.2f}s")
    
    with col2:
        st.subheader("Répartition par modèle LoRA")
        if 'model_config' in df.columns:
            lora_models = [config.get('lora_model', 'Unknown') for config in df['model_config'] if isinstance(config, dict)]
            if lora_models:
                lora_counts = pd.Series(lora_models).value_counts()
                st.bar_chart(lora_counts)
        
        st.subheader("Total des générations")
        st.metric("Nombre total", len(generations))

if __name__ == "__main__":
    main()