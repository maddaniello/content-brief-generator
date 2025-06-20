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
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ContentBriefGenerator:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
    def scrape_url(self, url: str) -> Dict[str, str]:
        """Scraping completo di una pagina web per estrarre tutti i contenuti rilevanti"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Rimuove script, style, nav, footer, sidebar
            for element in soup(["script", "style", "nav", "footer", "aside", "header"]):
                element.decompose()
            
            # Estrae il titolo
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Estrae meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if not meta_desc:
                meta_desc = soup.find('meta', attrs={'property': 'og:description'})
            meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
            
            # Estrae meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            meta_keywords_text = meta_keywords.get('content', '') if meta_keywords else ""
            
            # Estrae headings con gerarchia
            headings = []
            for i in range(1, 7):
                for heading in soup.find_all(f'h{i}'):
                    headings.append(f"H{i}: {heading.get_text().strip()}")
            
            # Estrae tutto il contenuto testuale
            # Prima rimuove elementi non necessari
            for unwanted in soup.find_all(['button', 'form', 'input', 'select', 'textarea']):
                unwanted.decompose()
            
            # Estrae il contenuto principale
            main_content = ""
            
            # Cerca il contenuto principale in vari modi
            main_selectors = [
                'main', 'article', '[role="main"]', 
                '.content', '.main-content', '.post-content',
                '.entry-content', '.article-content', '#content'
            ]
            
            for selector in main_selectors:
                main_element = soup.select_one(selector)
                if main_element:
                    main_content = main_element.get_text()
                    break
            
            # Se non trova un contenitore principale, prende tutto il body
            if not main_content:
                body = soup.find('body')
                if body:
                    main_content = body.get_text()
                else:
                    main_content = soup.get_text()
            
            # Pulisce il contenuto
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            # Estrae paragrafi strutturati
            paragraphs = []
            for p in soup.find_all('p'):
                p_text = p.get_text().strip()
                if len(p_text) > 50:  # Solo paragrafi significativi
                    paragraphs.append(p_text)
            
            # Estrae liste
            lists = []
            for ul in soup.find_all(['ul', 'ol']):
                list_items = [li.get_text().strip() for li in ul.find_all('li')]
                if list_items:
                    lists.append(list_items)
            
            return {
                'url': url,
                'title': title_text,
                'meta_description': meta_desc_text,
                'meta_keywords': meta_keywords_text,
                'headings': '\n'.join(headings),
                'content': main_content,
                'paragraphs': paragraphs[:10],  # Primi 10 paragrafi
                'lists': lists[:5],  # Prime 5 liste
                'word_count': len(main_content.split()),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'url': url,
                'title': "",
                'meta_description': "",
                'meta_keywords': "",
                'headings': "",
                'content': "",
                'paragraphs': [],
                'lists': [],
                'word_count': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def get_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Estrae le URL dalla sitemap con gestione di sitemap multiple"""
        urls = []
        processed_sitemaps = set()
        
        def process_sitemap(url: str):
            if url in processed_sitemaps:
                return
            processed_sitemaps.add(url)
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SEO-Tool/1.0; +http://www.example.com/bot)'
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Prova a parsare come XML
                root = ET.fromstring(response.content)
                
                # Namespace per sitemap
                namespaces = {
                    'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                    'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
                }
                
                # Controlla se è un indice di sitemap
                sitemapindex = root.findall('.//ns:sitemap', namespaces)
                if sitemapindex:
                    # È un indice di sitemap, processa ogni sitemap
                    for sitemap in sitemapindex[:10]:  # Limita a 10 sitemap
                        loc_elem = sitemap.find('ns:loc', namespaces)
                        if loc_elem is not None:
                            process_sitemap(loc_elem.text)
                else:
                    # È una sitemap normale, estrae le URL
                    for url_elem in root.findall('.//ns:url', namespaces):
                        loc_elem = url_elem.find('ns:loc', namespaces)
                        if loc_elem is not None:
                            urls.append(loc_elem.text)
                            if len(urls) >= 100:  # Limita a 100 URL totali
                                break
                
            except ET.ParseError:
                # Se non è XML valido, prova a cercare URL nel testo
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    text = response.text
                    url_pattern = r'https?://[^\s<>"\']+(?:/[^\s<>"\']*)?'
                    found_urls = re.findall(url_pattern, text)
                    urls.extend(found_urls[:50])
                except:
                    pass
                    
            except Exception as e:
                st.warning(f"Errore nell'elaborazione della sitemap {url}: {str(e)}")
        
        try:
            process_sitemap(sitemap_url)
            return list(set(urls))  # Rimuove duplicati
            
        except Exception as e:
            st.error(f"Errore critico nell'estrazione della sitemap: {str(e)}")
            return []
    
    def generate_content_brief(self, data: Dict) -> str:
        """Genera il content brief usando OpenAI con focus su E-E-A-T"""
        
        # Prepara i dati dei competitor
        competitor_data = ""
        for i, comp in enumerate(data['competitors'], 1):
            competitor_data += f"\n--- COMPETITOR {i} ---\n"
            competitor_data += f"URL: {comp['url']}\n"
            competitor_data += f"Titolo: {comp['title']}\n"
            competitor_data += f"Meta Description: {comp['meta_description']}\n"
            competitor_data += f"Meta Keywords: {comp['meta_keywords']}\n"
            competitor_data += f"Struttura Headings:\n{comp['headings']}\n"
            competitor_data += f"Numero parole: {comp['word_count']}\n"
            if comp['status'] == 'success':
                competitor_data += f"Contenuto (estratto): {comp['content'][:2000]}...\n"
            else:
                competitor_data += f"Contenuto manuale: {comp.get('manual_content', 'Non disponibile')}\n"
        
        # Prepara le URL interne per i link
        internal_urls = "\n".join(data['sitemap_urls'][:30]) if data['sitemap_urls'] else data.get('manual_urls', 'Nessuna URL interna disponibile')
        
        prompt = f"""
Sei un esperto SEO copywriter e content strategist specializzato in E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness). Devi creare un content brief dettagliato per un articolo ottimizzato SEO che raggiunga il massimo punteggio E-E-A-T.

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

IMPORTANTE: 
- Il brand "{data['brand']}" DEVE apparire nel meta title alla fine
- Il brand "{data['brand']}" DEVE apparire nella meta description
- Usa la capitalizzazione naturale italiana (solo prima parola maiuscola, nomi propri maiuscoli)
- Esempio CORRETTO: "Come ottenere il mutuo prima casa"
- Esempio SBAGLIATO: "Come Ottenere Il Mutuo Prima Casa"

Genera un content brief completo che includa:

1. **ANALISI INTENTO DI RICERCA E OBIETTIVO**
   - Analizza l'intento dietro le keyword principali
   - Definisci l'obiettivo dell'articolo e target
   - Strategia per battere i competitor

2. **LINEE GUIDA SEO E STILE**
   - Come utilizzare le keyword (densità, posizionamento)
   - Tone of voice e stile di scrittura specifico
   - Lunghezza consigliata del contenuto (analizza competitor)

3. **META TITLE E DESCRIPTION**
   - Meta title ottimizzato (50-60 caratteri) con brand alla fine
   - Meta description ottimizzata (150-160 caratteri) con brand incluso
   - Usa capitalizzazione naturale italiana

4. **STRATEGIA E-E-A-T**
   Per ogni sezione, specifica come implementare:
   
   **EXPERIENCE (Esperienza):**
   - Esempi pratici diversificati da includere
   - Casi studio del mondo reale
   - Scenari applicabili in diversi contesti
   - Testimonianze o esperienze dirette
   
   **EXPERTISE (Competenza):**
   - Insight originali da inserire
   - Dati e statistiche approfondite
   - Analisi tecniche dettagliate
   - Ricerche originali o citazioni di studi
   
   **AUTHORITATIVENESS (Autorevolezza):**
   - Fonti autorevoli da citare (istituzioni, enti, studi)
   - Link a ricerche accademiche
   - Riferimenti a normative e leggi
   - Citazioni di esperti del settore
   
   **TRUSTWORTHINESS (Affidabilità):**
   - Trasparenza su limiti e conflitti di interesse
   - Dati aziendali da includere se pertinenti
   - Approccio obiettivo e bilanciato
   - Disclaimers necessari

5. **STRUTTURA CONTENUTO DETTAGLIATA**
   Per ogni sezione specifica (usa capitalizzazione naturale):
   - H1 principale ottimizzato
   - H2 e H3 con descrizione dettagliata del contenuto
   - Parole chiave da includere in ogni sezione
   - Elementi E-E-A-T specifici per ogni paragrafo
   - Link interni suggeriti con anchor text naturali
   - Elementi aggiuntivi (immagini, infografiche, fonti, dati)

6. **LINK INTERNI STRATEGICI**
   - Elenco dettagliato di link interni da inserire
   - Anchor text naturali e pertinenti
   - Posizionamento strategico nel contenuto
   - Valore aggiunto per l'utente

7. **FONTI E CREDIBILITÀ**
   - Lista di fonti autorevoli da consultare e citare
   - Studi e ricerche da referenziare
   - Enti e istituzioni da menzionare
   - Dati statistici recenti da includere

8. **CALL TO ACTION E CONVERSIONE**
   - CTA strategiche da inserire nel contenuto
   - CTA finale di conversione ottimizzata
   - Micro-conversioni intermedie

Analizza i competitor per identificare lacune da colmare e opportunità per creare contenuto superiore. Fornisci indicazioni specifiche, actionable e orientate al massimo punteggio E-E-A-T.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sei un esperto SEO content strategist specializzato in E-E-A-T che crea content brief dettagliati, ottimizzati e superiori alla concorrenza."},
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
    title = doc.add_heading(f'Content brief - {topic}', 0)
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
    st.markdown('<h1 class="main-header">📝 Content Brief Generator Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Genera content brief ottimizzati E-E-A-T con analisi competitor avanzata</p>', unsafe_allow_html=True)
    
    # Sidebar per API Key
    with st.sidebar:
        st.markdown("### 🔑 Configurazione")
        api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua API key di OpenAI")
        
        if api_key:
            st.success("✅ API Key configurata")
        else:
            st.warning("⚠️ Inserisci la tua API Key per continuare")
        
        st.markdown("---")
        st.markdown("### 📊 E-E-A-T Focus")
        st.info("Questo tool è ottimizzato per creare content brief che massimizzano il punteggio E-E-A-T di Google")
    
    if not api_key:
        st.info("👈 Inserisci la tua OpenAI API Key nella sidebar per iniziare")
        return
    
    # Inizializza il generatore
    generator = ContentBriefGenerator(api_key)
    
    # Form principale
    with st.form("content_brief_form"):
        st.markdown('<h2 class="section-header">📋 Informazioni cliente</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            brand = st.text_input("🏢 Nome del brand", placeholder="Es: TassoMutuo")
            website = st.text_input("🌐 URL del sito", placeholder="https://www.esempio.it")
            sitemap_url = st.text_input("🗺️ URL Sitemap.xml", placeholder="https://www.esempio.it/sitemap.xml")
            topic = st.text_area("📝 Argomento del contenuto", placeholder="Descrivi l'argomento principale dell'articolo")
        
        with col2:
            keywords = st.text_area("🔍 Keyword utili", placeholder="Inserisci le keyword separate da virgola")
            faqs = st.text_area("❓ Domande frequenti (PAA)", placeholder="Inserisci le domande frequenti, una per riga")
            
            # Tone of voice con multiselect
            tone_options = [
                "Professionale", "Minimalista", "Persuasivo", 
                "Informativo", "Ricercato", "Popolare", "Personalizzato"
            ]
            tone_of_voice = st.multiselect("🎯 Tone of voice", tone_options, default=["Professionale"])
        
        # Gestione sitemap alternativa
        st.markdown('<h3 class="section-header">🔗 URL interne (fallback)</h3>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Se la sitemap non è accessibile, puoi incollare manualmente le URL interne principali (una per riga)</div>', unsafe_allow_html=True)
        
        manual_urls = st.text_area("📎 URL interne manuali", placeholder="https://www.sito.it/pagina1\nhttps://www.sito.it/pagina2", height=100)
        
        st.markdown('<h3 class="section-header">🔍 Analisi competitor</h3>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Inserisci 3 URL di competitor. Se il sistema non riesce ad accedere, potrai incollare il contenuto manualmente</div>', unsafe_allow_html=True)
        
        competitor_data = []
        for i in range(3):
            st.markdown(f"**Competitor {i+1}**")
            col_url, col_manual = st.columns([2, 1])
            
            with col_url:
                url = st.text_input(f"🌐 URL Competitor {i+1}", key=f"comp_url_{i}", placeholder="https://competitor.example.com/articolo")
            
            with col_manual:
                use_manual = st.checkbox(f"Contenuto manuale", key=f"manual_{i}")
            
            manual_content = ""
            if use_manual:
                manual_content = st.text_area(f"📝 Contenuto testuale Competitor {i+1}", key=f"comp_content_{i}", placeholder="Incolla qui tutto il contenuto testuale della pagina competitor", height=150)
            
            if url:
                competitor_data.append({
                    'url': url,
                    'manual_content': manual_content,
                    'use_manual': use_manual
                })
        
        submitted = st.form_submit_button("🚀 Genera content brief E-E-A-T", use_container_width=True)
    
    if submitted:
        # Validazione input
        if not all([brand, website, topic, keywords]):
            st.error("❌ Compila tutti i campi obbligatori: Brand, Website, Argomento e Keywords")
            return
        
        if not competitor_data:
            st.error("❌ Inserisci almeno un URL competitor")
            return
        
        with st.spinner("🔄 Generazione del content brief E-E-A-T in corso..."):
            progress_bar = st.progress(0)
            
            # Step 1: Estrazione sitemap
            st.info("📡 Estrazione URL dalla sitemap...")
            sitemap_urls = []
            sitemap_error = False
            
            if sitemap_url:
                sitemap_urls = generator.get_sitemap_urls(sitemap_url)
                if not sitemap_urls:
                    sitemap_error = True
                    st.warning("⚠️ Impossibile accedere alla sitemap. Utilizzo URL manuali.")
            
            # Usa URL manuali se sitemap fallisce o se fornite
            if sitemap_error or manual_urls.strip():
                manual_url_list = [url.strip() for url in manual_urls.split('\n') if url.strip()]
                sitemap_urls.extend(manual_url_list)
            
            progress_bar.progress(20)
            
            # Step 2: Scraping competitor
            st.info("🕷️ Analisi competitor in corso...")
            competitors_scraped = []
            
            for i, comp_data in enumerate(competitor_data):
                if comp_data['use_manual'] and comp_data['manual_content']:
                    # Usa contenuto manuale
                    scraped_data = {
                        'url': comp_data['url'],
                        'title': f"Competitor {i+1} (contenuto manuale)",
                        'meta_description': "",
                        'meta_keywords': "",
                        'headings': "",
                        'content': comp_data['manual_content'],
                        'paragraphs': comp_data['manual_content'].split('\n\n')[:10],
                        'lists': [],
                        'word_count': len(comp_data['manual_content'].split()),
                        'status': 'manual'
                    }
                else:
                    # Prova scraping automatico
                    scraped_data = generator.scrape_url(comp_data['url'])
                    
                    # Se scraping fallisce, chiede contenuto manuale
                    if scraped_data['status'] == 'error':
                        st.error(f"❌ Impossibile accedere a {comp_data['url']}")
                        st.markdown('<div class="error-box">Per continuare, usa l\'opzione "Contenuto manuale" e incolla il testo della pagina</div>', unsafe_allow_html=True)
                
                competitors_scraped.append(scraped_data)
                progress_bar.progress(20 + (i + 1) * 20)
            
            # Verifica che almeno un competitor sia stato analizzato
            valid_competitors = [c for c in competitors_scraped if c['status'] in ['success', 'manual']]
            if not valid_competitors:
                st.error("❌ Nessun competitor analizzato con successo. Riprova con contenuto manuale.")
                return
            
            # Step 3: Preparazione dati
            st.info("📊 Preparazione dati per analisi E-E-A-T...")
            data = {
                'brand': brand,
                'website': website,
                'topic': topic,
                'keywords': keywords,
                'faqs': faqs,
                'tone_of_voice': tone_of_voice,
                'competitors': valid_competitors,
                'sitemap_urls': sitemap_urls,
                'manual_urls': manual_urls
            }
            progress_bar.progress(80)
            
            # Step 4: Generazione content brief
            st.info("🤖 Generazione content brief E-E-A-T con AI...")
            content_brief = generator.generate_content_brief(data)
            progress_bar.progress(90)
            
            # Step 5: Creazione documento
            st.info("📄 Creazione documento DOCX...")
            docx_buffer = create_docx(content_brief, brand, topic)
            progress_bar.progress(100)
            
            st.success("✅ Content brief E-E-A-T generato con successo!")
        
        # Mostra risultati
        st.markdown('<h2 class="section-header">📋 Content brief E-E-A-T generato</h2>', unsafe_allow_html=True)
        
        # Preview del contenuto
        with st.expander("👁️ Anteprima content brief", expanded=True):
            st.markdown(content_brief)
        
        # Download button
        st.download_button(
            label="📥 Scarica content brief (DOCX)",
            data=docx_buffer.getvalue(),
            file_name=f"content_brief_EEAT_{brand}_{topic.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
        
        # Informazioni aggiuntive
        st.markdown('<h3 class="section-header">📊 Riepilogo analisi</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔍 Competitor analizzati", len(valid_competitors))
        with col2:
            st.metric("🔗 URL interne trovate", len(sitemap_urls))
        with col3:
            st.metric("🎯 Tone of voice", len(tone_of_voice))
        with col4:
            total_words = sum([c.get('word_count', 0) for c in valid_competitors])
            st.metric("📝 Parole analizzate", total_words)
        
        # Dettagli competitor
        with st.expander("🔍 Dettagli analisi competitor"):
            for i, comp in enumerate(valid_competitors, 1):
                st.markdown(f"**Competitor {i}:** {comp['url']}")
                if comp['status'] == 'success':
                    st.write(f"✅ Scraping automatico riuscito")
                    st.write(f"Titolo: {comp['title']}")
                    st.write(f"Meta Description: {comp['meta_description']}")
                    st.write(f"Numero parole: {comp['word_count']}")
                elif comp['status'] == 'manual':
                    st.write(f"📝 Contenuto inserito manualmente")
                    st.write(f"Numero parole: {comp['word_count']}")
                else:
                    st.write(f"❌ Errore: {comp.get('error', 'Sconosciuto')}")
                st.markdown("---")
        
        # Consigli E-E-A-T
        st.markdown('<h3 class="section-header">🏆 Checklist E-E-A-T</h3>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Il content brief generato include suggerimenti specifici per massimizzare il punteggio E-E-A-T:</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **📚 Experience (Esperienza)**
            - ✅ Esempi pratici diversificati
            - ✅ Casi studio del mondo reale
            - ✅ Scenari applicabili
            - ✅ Testimonianze dirette
            
            **🎓 Expertise (Competenza)**
            - ✅ Insight originali
            - ✅ Dati e statistiche approfondite
            - ✅ Analisi tecniche dettagliate
            - ✅ Ricerche e citazioni
            """)
        
        with col2:
            st.markdown("""
            **⭐ Authoritativeness (Autorevolezza)**
            - ✅ Fonti autorevoli da citare
            - ✅ Link a ricerche accademiche
            - ✅ Riferimenti normativi
            - ✅ Citazioni di esperti
            
            **🛡️ Trustworthiness (Affidabilità)**
            - ✅ Trasparenza su limiti
            - ✅ Dati aziendali pertinenti
            - ✅ Approccio obiettivo
            - ✅ Disclaimers necessari
            """)

if __name__ == "__main__":
    main()
