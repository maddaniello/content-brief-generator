import streamlit as st
import openai
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import time
from typing import List, Dict, Optional

# Configurazione della pagina
st.set_page_config(
    page_title="Content Brief Generator",
    page_icon="📝",
    layout="wide"
)

# CSS personalizzato
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f1f1f;
        margin-bottom: 2rem;
    }
    .section-header {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ContentBriefGenerator:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
    def scrape_url(self, url: str) -> Dict[str, str]:
        """Scraping di una pagina web per estrarre contenuti rilevanti"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Rimuove script e style
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Estrae il titolo
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Estrae meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
            
            # Estrae headings
            headings = []
            for i in range(1, 7):
                for heading in soup.find_all(f'h{i}'):
                    headings.append(f"H{i}: {heading.get_text().strip()}")
            
            # Estrae il contenuto principale
            content = soup.get_text()
            # Pulisce il contenuto
            content = re.sub(r'\s+', ' ', content).strip()
            content = content[:3000]  # Limita a 3000 caratteri
            
            return {
                'url': url,
                'title': title_text,
                'meta_description': meta_desc_text,
                'headings': '\n'.join(headings[:20]),  # Primi 20 headings
                'content': content
            }
            
        except Exception as e:
            st.warning(f"Errore durante lo scraping di {url}: {str(e)}")
            return {
                'url': url,
                'title': "",
                'meta_description': "",
                'headings': "",
                'content': f"Impossibile fare scraping di {url}"
            }
    
    def get_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Estrae le URL dalla sitemap"""
        try:
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            urls = []
            
            # Namespace per sitemap
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_elem in root.findall('.//ns:url', namespaces):
                loc_elem = url_elem.find('ns:loc', namespaces)
                if loc_elem is not None:
                    urls.append(loc_elem.text)
            
            return urls[:50]  # Limita a 50 URL per performance
            
        except Exception as e:
            st.warning(f"Errore durante l'estrazione della sitemap: {str(e)}")
            return []
    
    def generate_content_brief(self, data: Dict) -> str:
        """Genera il content brief usando OpenAI"""
        
        # Prepara i dati dei competitor
        competitor_data = ""
        for i, comp in enumerate(data['competitors'], 1):
            competitor_data += f"\n--- COMPETITOR {i} ---\n"
            competitor_data += f"URL: {comp['url']}\n"
            competitor_data += f"Titolo: {comp['title']}\n"
            competitor_data += f"Meta Description: {comp['meta_description']}\n"
            competitor_data += f"Struttura Headings:\n{comp['headings']}\n"
            competitor_data += f"Contenuto (estratto): {comp['content'][:1000]}...\n"
        
        # Prepara le URL interne per i link
        internal_urls = "\n".join(data['sitemap_urls'][:20]) if data['sitemap_urls'] else "Nessuna URL interna disponibile"
        
        prompt = f"""
Sei un esperto SEO copywriter e content strategist. Devi creare un content brief dettagliato per un articolo ottimizzato SEO.

INFORMAZIONI CLIENTE:
- Brand: {data['brand']}
- Sito web: {data['website']}
- Argomento: {data['topic']}
- Keyword principali: {data['keywords']}
- Domande frequenti (PAA): {data['faqs']}
- Tone of voice: {', '.join(data['tone_of_voice'])}

ANALISI COMPETITOR:
{competitor_data}

URL INTERNE DISPONIBILI (per link interni):
{internal_urls}

Genera un content brief completo che includa:

1. **ANALISI INTENTO DI RICERCA E OBIETTIVO**
   - Analizza l'intento dietro le keyword principali
   - Definisci l'obiettivo dell'articolo
   - Identifica il target di riferimento

2. **LINEE GUIDA SEO E STILE**
   - Come utilizzare le keyword (densità, posizionamento)
   - Tone of voice e stile di scrittura
   - Lunghezza consigliata del contenuto

3. **META TITLE E DESCRIPTION**
   - Proposta di meta title ottimizzata (max 60 caratteri)
   - Proposta di meta description ottimizzata (max 160 caratteri)

4. **STRUTTURA CONTENUTO DETTAGLIATA**
   Per ogni sezione specifica:
   - H1 principale
   - H2 e H3 con descrizione dettagliata del contenuto
   - Parole chiave da includere in ogni sezione
   - Link interni suggeriti con anchor text specifiche
   - Elementi aggiuntivi (immagini, infografiche, fonti)

5. **LINK INTERNI STRATEGICI**
   - Elenco dettagliato di link interni da inserire
   - Anchor text specifiche per ogni link
   - Posizionamento strategico nel contenuto

6. **CALL TO ACTION**
   - CTA da inserire nel contenuto
   - CTA finale di conversione

Basati sull'analisi dei competitor per migliorare e superare i loro contenuti. Fornisci indicazioni specifiche e actionable.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sei un esperto SEO content strategist che crea content brief dettagliati e ottimizzati."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            st.error(f"Errore nella generazione del content brief: {str(e)}")
            return "Errore nella generazione del contenuto."

def create_docx(content: str, brand: str, topic: str) -> io.BytesIO:
    """Crea un documento DOCX formattato con il content brief"""
    doc = Document()
    
    # Configurazione del documento
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Titolo principale
    title = doc.add_heading(f'Content Brief - {topic}', 0)
    title_format = title.runs[0].font
    title_format.name = 'Figtree'
    title_format.size = Pt(20)
    title_format.color.rgb = None  # Nero
    
    # Sottotitolo
    subtitle = doc.add_paragraph(f'Brand: {brand}')
    subtitle_format = subtitle.runs[0].font
    subtitle_format.name = 'Figtree'
    subtitle_format.size = Pt(12)
    subtitle_format.bold = True
    
    doc.add_paragraph("")  # Spazio
    
    # Processa il contenuto
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Gestisce i titoli
        if line.startswith('# '):
            heading = doc.add_heading(line[2:], 1)
            heading_format = heading.runs[0].font
            heading_format.name = 'Figtree'
            heading_format.size = Pt(17)
            
        elif line.startswith('## '):
            heading = doc.add_heading(line[3:], 2)
            heading_format = heading.runs[0].font
            heading_format.name = 'Figtree'
            heading_format.size = Pt(17)
            
        elif line.startswith('### '):
            heading = doc.add_heading(line[4:], 3)
            heading_format = heading.runs[0].font
            heading_format.name = 'Figtree'
            heading_format.size = Pt(17)
            
        elif line.startswith('**') and line.endswith('**'):
            # Testo in grassetto
            p = doc.add_paragraph()
            run = p.add_run(line[2:-2])
            run.font.name = 'Figtree'
            run.font.size = Pt(11)
            run.font.bold = True
            
        elif line.startswith('- ') or line.startswith('* '):
            # Lista puntata
            p = doc.add_paragraph(line[2:], style='List Bullet')
            p.runs[0].font.name = 'Figtree'
            p.runs[0].font.size = Pt(11)
            
        else:
            # Testo normale
            if line:
                p = doc.add_paragraph(line)
                p.runs[0].font.name = 'Figtree'
                p.runs[0].font.size = Pt(11)
    
    # Salva in BytesIO
    doc_buffer = io.BytesIO()
    doc.save(doc_buffer)
    doc_buffer.seek(0)
    
    return doc_buffer

def main():
    st.markdown('<h1 class="main-header">📝 Content Brief Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Genera content brief ottimizzati SEO con analisi competitor automatica</p>', unsafe_allow_html=True)
    
    # Sidebar per API Key
    with st.sidebar:
        st.markdown("### 🔑 Configurazione")
        api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua API key di OpenAI")
        
        if api_key:
            st.success("✅ API Key configurata")
        else:
            st.warning("⚠️ Inserisci la tua API Key per continuare")
    
    if not api_key:
        st.info("👈 Inserisci la tua OpenAI API Key nella sidebar per iniziare")
        return
    
    # Inizializza il generatore
    generator = ContentBriefGenerator(api_key)
    
    # Form principale
    with st.form("content_brief_form"):
        st.markdown('<h2 class="section-header">📋 Informazioni Cliente</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            brand = st.text_input("🏢 Nome del Brand", placeholder="Es: TassoMutuo")
            website = st.text_input("🌐 URL del Sito", placeholder="https://www.esempio.it")
            sitemap_url = st.text_input("🗺️ URL Sitemap.xml", placeholder="https://www.esempio.it/sitemap.xml")
            topic = st.text_area("📝 Argomento del Contenuto", placeholder="Descrivi l'argomento principale dell'articolo")
        
        with col2:
            keywords = st.text_area("🔍 Keyword Utili", placeholder="Inserisci le keyword separate da virgola")
            faqs = st.text_area("❓ Domande Frequenti (PAA)", placeholder="Inserisci le domande frequenti, una per riga")
            
            # Tone of voice con multiselect
            tone_options = [
                "Professionale", "Minimalista", "Persuasivo", 
                "Informativo", "Ricercato", "Popolare", "Personalizzato"
            ]
            tone_of_voice = st.multiselect("🎯 Tone of Voice", tone_options, default=["Professionale"])
        
        st.markdown('<h3 class="section-header">🔍 URL Competitor</h3>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Inserisci 3 URL di competitor che trattano lo stesso argomento per l\'analisi automatica</div>', unsafe_allow_html=True)
        
        competitor_urls = []
        for i in range(3):
            url = st.text_input(f"🌐 URL Competitor {i+1}", key=f"comp_{i}", placeholder="https://competitor.example.com/articolo")
            if url:
                competitor_urls.append(url)
        
        submitted = st.form_submit_button("🚀 Genera Content Brief", use_container_width=True)
    
    if submitted:
        # Validazione input
        if not all([brand, website, topic, keywords]):
            st.error("❌ Compila tutti i campi obbligatori: Brand, Website, Argomento e Keywords")
            return
        
        if not competitor_urls:
            st.error("❌ Inserisci almeno un URL competitor")
            return
        
        with st.spinner("🔄 Generazione del content brief in corso..."):
            progress_bar = st.progress(0)
            
            # Step 1: Estrazione sitemap
            st.info("📡 Estrazione URL dalla sitemap...")
            sitemap_urls = []
            if sitemap_url:
                sitemap_urls = generator.get_sitemap_urls(sitemap_url)
            progress_bar.progress(20)
            
            # Step 2: Scraping competitor
            st.info("🕷️ Analisi competitor in corso...")
            competitors_data = []
            for i, url in enumerate(competitor_urls):
                scraped_data = generator.scrape_url(url)
                competitors_data.append(scraped_data)
                progress_bar.progress(20 + (i + 1) * 20)
            
            # Step 3: Preparazione dati
            st.info("📊 Preparazione dati...")
            data = {
                'brand': brand,
                'website': website,
                'topic': topic,
                'keywords': keywords,
                'faqs': faqs,
                'tone_of_voice': tone_of_voice,
                'competitors': competitors_data,
                'sitemap_urls': sitemap_urls
            }
            progress_bar.progress(80)
            
            # Step 4: Generazione content brief
            st.info("🤖 Generazione content brief con AI...")
            content_brief = generator.generate_content_brief(data)
            progress_bar.progress(90)
            
            # Step 5: Creazione documento
            st.info("📄 Creazione documento DOCX...")
            docx_buffer = create_docx(content_brief, brand, topic)
            progress_bar.progress(100)
            
            st.success("✅ Content brief generato con successo!")
        
        # Mostra risultati
        st.markdown('<h2 class="section-header">📋 Content Brief Generato</h2>', unsafe_allow_html=True)
        
        # Preview del contenuto
        with st.expander("👁️ Anteprima Content Brief", expanded=True):
            st.markdown(content_brief)
        
        # Download button
        st.download_button(
            label="📥 Scarica Content Brief (DOCX)",
            data=docx_buffer.getvalue(),
            file_name=f"content_brief_{brand}_{topic.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
        
        # Informazioni aggiuntive
        st.markdown('<h3 class="section-header">📊 Riepilogo Analisi</h3>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔍 Competitor Analizzati", len(competitors_data))
        with col2:
            st.metric("🔗 URL Interne Trovate", len(sitemap_urls))
        with col3:
            st.metric("🎯 Tone of Voice", len(tone_of_voice))
        
        # Dettagli competitor
        with st.expander("🔍 Dettagli Analisi Competitor"):
            for i, comp in enumerate(competitors_data, 1):
                st.markdown(f"**Competitor {i}:** {comp['url']}")
                st.write(f"Titolo: {comp['title']}")
                st.write(f"Meta Description: {comp['meta_description']}")
                st.markdown("---")

if __name__ == "__main__":
    main()