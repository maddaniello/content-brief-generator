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
import json
from typing import List, Dict, Optional

# Configurazione della pagina
st.set_page_config(
    page_title="Content Brief Generator Pro",
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
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

class SEODataEnhancer:
    def __init__(self, semrush_api_key: str = None, serper_api_key: str = None):
        self.semrush_api_key = semrush_api_key
        self.serper_api_key = serper_api_key
        
    def get_semrush_keyword_data(self, keyword: str, country: str = "IT") -> Dict:
        """Ottiene dati dalle API di SEMrush per una keyword"""
        if not self.semrush_api_key:
            return {'status': 'error', 'message': 'SEMrush API key non configurata'}
        
        try:
            # API SEMrush per keyword overview
            url = "https://api.semrush.com/"
            params = {
                'type': 'phrase_organic',
                'key': self.semrush_api_key,
                'phrase': keyword,
                'database': country.lower(),
                'export_columns': 'Ph,Nq,Cp,Co,Nr,Td'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parsing dei risultati SEMrush
            lines = response.text.strip().split('\n')
            if len(lines) > 1:
                data = lines[1].split(';')
                return {
                    'status': 'success',
                    'keyword': data[0] if len(data) > 0 else keyword,
                    'search_volume': int(data[1]) if len(data) > 1 and data[1].isdigit() else 0,
                    'cpc': float(data[2]) if len(data) > 2 and data[2].replace('.', '').isdigit() else 0,
                    'competition': float(data[3]) if len(data) > 3 and data[3].replace('.', '').isdigit() else 0,
                    'results_count': int(data[4]) if len(data) > 4 and data[4].isdigit() else 0,
                    'trend': data[5] if len(data) > 5 else ''
                }
            else:
                return {'status': 'no_data', 'keyword': keyword}
                
        except Exception as e:
            return {'status': 'error', 'keyword': keyword, 'error': str(e)}
    
    def get_semrush_related_keywords(self, keyword: str, country: str = "IT", limit: int = 20) -> List[Dict]:
        """Ottiene keyword correlate da SEMrush"""
        if not self.semrush_api_key:
            return []
        
        try:
            url = "https://api.semrush.com/"
            params = {
                'type': 'phrase_related',
                'key': self.semrush_api_key,
                'phrase': keyword,
                'database': country.lower(),
                'export_columns': 'Ph,Nq,Cp,Co',
                'display_limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            related_keywords = []
            
            for line in lines[1:]:  # Skip header
                data = line.split(';')
                if len(data) >= 4:
                    related_keywords.append({
                        'keyword': data[0],
                        'search_volume': int(data[1]) if data[1].isdigit() else 0,
                        'cpc': float(data[2]) if data[2].replace('.', '').isdigit() else 0,
                        'competition': float(data[3]) if data[3].replace('.', '').isdigit() else 0
                    })
            
            return related_keywords
            
        except Exception as e:
            st.warning(f"Errore nell'ottenimento keyword correlate SEMrush: {str(e)}")
            return []
    
    def get_serper_search_data(self, query: str, country: str = "it") -> Dict:
        """Ottiene dati SERP da Serper API"""
        if not self.serper_api_key:
            return {'status': 'error', 'message': 'Serper API key non configurata'}
        
        try:
            url = "https://google.serper.dev/search"
            payload = {
                'q': query,
                'gl': country,
                'hl': 'it',
                'num': 10
            }
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Estrae People Also Ask
            people_also_ask = []
            if 'peopleAlsoAsk' in data:
                for paa in data['peopleAlsoAsk']:
                    people_also_ask.append(paa.get('question', ''))
            
            # Estrae Related Searches
            related_searches = []
            if 'relatedSearches' in data:
                for rs in data['relatedSearches']:
                    related_searches.append(rs.get('query', ''))
            
            # Estrae Featured Snippet
            featured_snippet = None
            if 'answerBox' in data:
                featured_snippet = {
                    'snippet': data['answerBox'].get('snippet', ''),
                    'title': data['answerBox'].get('title', ''),
                    'link': data['answerBox'].get('link', '')
                }
            
            # Estrae top 10 risultati organici
            organic_results = []
            if 'organic' in data:
                for result in data['organic'][:10]:
                    organic_results.append({
                        'position': result.get('position', 0),
                        'title': result.get('title', ''),
                        'link': result.get('link', ''),
                        'snippet': result.get('snippet', ''),
                        'domain': urlparse(result.get('link', '')).netloc
                    })
            
            return {
                'status': 'success',
                'query': query,
                'people_also_ask': people_also_ask,
                'related_searches': related_searches,
                'featured_snippet': featured_snippet,
                'organic_results': organic_results,
                'total_results': data.get('searchInformation', {}).get('totalResults', 0)
            }
            
        except Exception as e:
            return {'status': 'error', 'query': query, 'error': str(e)}

class ContentBriefGenerator:
    def __init__(self, api_key: str, seo_enhancer: SEODataEnhancer = None):
        self.client = openai.OpenAI(api_key=api_key)
        self.seo_enhancer = seo_enhancer or SEODataEnhancer()
        
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
            for unwanted in soup.find_all(['button', 'form', 'input', 'select', 'textarea']):
                unwanted.decompose()
            
            # Estrae il contenuto principale
            main_content = ""
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
            
            if not main_content:
                body = soup.find('body')
                if body:
                    main_content = body.get_text()
                else:
                    main_content = soup.get_text()
            
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            # Estrae paragrafi strutturati
            paragraphs = []
            for p in soup.find_all('p'):
                p_text = p.get_text().strip()
                if len(p_text) > 50:
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
                'paragraphs': paragraphs[:10],
                'lists': lists[:5],
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
                
                root = ET.fromstring(response.content)
                namespaces = {
                    'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                    'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
                }
                
                sitemapindex = root.findall('.//ns:sitemap', namespaces)
                if sitemapindex:
                    for sitemap in sitemapindex[:10]:
                        loc_elem = sitemap.find('ns:loc', namespaces)
                        if loc_elem is not None:
                            process_sitemap(loc_elem.text)
                else:
                    for url_elem in root.findall('.//ns:url', namespaces):
                        loc_elem = url_elem.find('ns:loc', namespaces)
                        if loc_elem is not None:
                            urls.append(loc_elem.text)
                            if len(urls) >= 100:
                                break
                
            except ET.ParseError:
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
            return list(set(urls))
        except Exception as e:
            st.error(f"Errore critico nell'estrazione della sitemap: {str(e)}")
            return []
    
    def analyze_keywords_with_apis(self, keywords: str) -> Dict:
        """Analizza le keyword usando SEMrush e Serper"""
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        main_keyword = keyword_list[0] if keyword_list else ""
        
        # Dati SEMrush
        semrush_data = {}
        related_keywords = []
        
        if main_keyword:
            semrush_data = self.seo_enhancer.get_semrush_keyword_data(main_keyword)
            if semrush_data.get('status') == 'success':
                related_keywords = self.seo_enhancer.get_semrush_related_keywords(main_keyword)
        
        # Dati Serper
        serper_data = {}
        if main_keyword:
            serper_data = self.seo_enhancer.get_serper_search_data(main_keyword)
        
        return {
            'main_keyword': main_keyword,
            'all_keywords': keyword_list,
            'semrush_data': semrush_data,
            'related_keywords': related_keywords,
            'serper_data': serper_data
        }
    
    def generate_content_brief(self, data: Dict, keyword_analysis: Dict) -> str:
        """Genera il content brief usando OpenAI con dati SEO reali"""
        
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
        
        # Prepara dati SEMrush
        semrush_info = ""
        if keyword_analysis['semrush_data'].get('status') == 'success':
            sd = keyword_analysis['semrush_data']
            semrush_info = f"""
DATI SEMRUSH KEYWORD PRINCIPALE "{keyword_analysis['main_keyword']}":
- Volume di ricerca mensile: {sd.get('search_volume', 'N/A')}
- CPC: €{sd.get('cpc', 'N/A')}
- Competizione: {sd.get('competition', 'N/A')}/1.0
- Risultati totali: {sd.get('results_count', 'N/A')}
"""
        
        # Prepara keyword correlate
        related_kw = ""
        if keyword_analysis['related_keywords']:
            related_kw = "KEYWORD CORRELATE DA SEMRUSH:\n"
            for kw in keyword_analysis['related_keywords'][:10]:
                related_kw += f"- {kw['keyword']} (Vol: {kw['search_volume']}, Comp: {kw['competition']})\n"
        
        # Prepara dati Serper
        serper_info = ""
        if keyword_analysis['serper_data'].get('status') == 'success':
            sd = keyword_analysis['serper_data']
            
            if sd.get('people_also_ask'):
                serper_info += "PEOPLE ALSO ASK DA GOOGLE:\n"
                for paa in sd['people_also_ask'][:8]:
                    serper_info += f"- {paa}\n"
            
            if sd.get('related_searches'):
                serper_info += "\nRICERCHE CORRELATE DA GOOGLE:\n"
                for rs in sd['related_searches'][:5]:
                    serper_info += f"- {rs}\n"
            
            if sd.get('featured_snippet'):
                serper_info += f"\nFEATURED SNIPPET ATTUALE:\n"
                serper_info += f"Titolo: {sd['featured_snippet']['title']}\n"
                serper_info += f"Snippet: {sd['featured_snippet']['snippet'][:200]}...\n"
        
        # Prepara le URL interne
        internal_urls = "\n".join(data['sitemap_urls'][:30]) if data['sitemap_urls'] else data.get('manual_urls', 'Nessuna URL interna disponibile')
        
        prompt = f"""
Sei un esperto SEO copywriter e content strategist specializzato in E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness). Devi creare un content brief dettagliato basato su DATI SEO REALI per un articolo che raggiunga il massimo punteggio E-E-A-T e batta la concorrenza.

INFORMAZIONI CLIENTE:
- Brand: {data['brand']}
- Sito web: {data['website']}
- Argomento: {data['topic']}
- Keyword principali: {data['keywords']}
- Domande frequenti inserite: {data['faqs']}
- Tone of voice: {', '.join(data['tone_of_voice'])}

{semrush_info}

{related_kw}

{serper_info}

ANALISI COMPETITOR:
{competitor_data}

URL INTERNE DISPONIBILI (per link interni):
{internal_urls}

IMPORTANTE: 
- Il brand "{data['brand']}" DEVE apparire nel meta title alla fine
- Il brand "{data['brand']}" DEVE apparire nella meta description
- Usa la capitalizzazione naturale italiana (solo prima parola maiuscola, nomi propri maiuscoli)
- Utilizza i dati REALI di volumi di ricerca e People Also Ask per ottimizzare il contenuto
- Considera le keyword correlate di SEMrush per arricchire il contenuto
- Analizza il featured snippet esistente per superarlo

Genera un content brief completo che includa:

1. **ANALISI INTENTO DI RICERCA E OBIETTIVO BASATA SU DATI REALI**
   - Analizza l'intento basandoti sui dati di volume SEMrush e le PAA di Google
   - Definisci l'obiettivo considerando la competizione reale (CPC e competition score)
   - Strategia per battere i competitor analizzando featured snippet e top 10

2. **LINEE GUIDA SEO E STILE CON KEYWORD DATA-DRIVEN**
   - Utilizza keyword correlate di SEMrush per densità e posizionamento
   - Incorpora naturalmente le ricerche correlate di Google
   - Stile basato sui volumi di ricerca e competizione
   - Lunghezza ottimale basata sull'analisi competitor

3. **META TITLE E DESCRIPTION OTTIMIZZATE**
   - Meta title (50-60 caratteri) con keyword principale e brand
   - Meta description (150-160 caratteri) che incorpori PAA e brand
   - Capitalizzazione naturale italiana

4. **STRATEGIA E-E-A-T POTENZIATA CON DATI REALI**
   
   **EXPERIENCE:** 
   - Esempi basati su ricerche correlate reali di Google
   - Casi studio che rispondano alle PAA
   
   **EXPERTISE:**
   - Dati statistici reali (volume ricerche, trend del settore)
   - Insight basati sui gap nei competitor
   
   **AUTHORITATIVENESS:**
   - Fonti che i competitor non citano
   - Opportunità di superare il featured snippet attuale
   
   **TRUSTWORTHINESS:**
   - Trasparenza su dati e fonti reali
   - Riconoscimento dei limiti dove competitors falliscono

5. **STRUTTURA CONTENUTO OTTIMIZZATA PER GOOGLE**
   - H1 ottimizzato per keyword principale
   - H2/H3 che rispondono alle People Also Ask
   - Sezioni per keyword correlate ad alto volume
   - Strategia per conquistare featured snippet
   - Risposte specifiche alle PAA di Google nel contenuto

6. **INTEGRAZIONE PEOPLE ALSO ASK**
   Per ogni PAA di Google:
   - Dove inserirla nella struttura
   - Come rispondere meglio dei competitor
   - Keyword correlate da usare nella risposta

7. **KEYWORD CORRELATE E SEMANTICHE**
   - Come integrare keyword correlate SEMrush
   - Ricerche correlate Google da includere
   - Densità ottimale basata su competition score

8. **LINK INTERNI STRATEGICI DATA-DRIVEN**
   - Link basati su analisi del traffico potenziale
   - Anchor text con keyword correlate
   - Distribuzione strategica per topic clustering

9. **FONTI E CREDIBILITÀ SUPERIORI AI COMPETITOR**
   - Fonti che mancano nei competitor top 10
   - Dati più recenti di quelli usati dai competitor
   - Authority sources che aumentano E-E-A-T

10. **CALL TO ACTION OTTIMIZZATE PER CONVERSIONE**
    - CTA basate sull'intento di ricerca reale
    - Micro-conversioni intermediate per high-competition keyword
    - CTA finali ottimizzate per volume/valore keyword

Utilizza ESCLUSIVAMENTE i dati reali forniti (volumi SEMrush, PAA Google, ricerche correlate) per creare una strategia superiore ai competitor. Focus su superare il featured snippet attuale e rispondere meglio alle PAA.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sei un esperto SEO content strategist che utilizza dati reali di SEMrush e Serper per creare content brief superiori alla concorrenza, ottimizzati per E-E-A-T e ranking Google."},
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
    title = doc.add_heading(f'Content brief SEO data-driven - {topic}', 0)
    title_format = title.runs[0].font
    title_format.name = 'Figtree'
    title_format.size = Pt(20)
    title_format.color.rgb = None
    
    # Sottotitolo
    subtitle = doc.add_paragraph(f'Brand: {brand}')
    subtitle_format = subtitle.runs[0].font
    subtitle_format.name = 'Figtree'
    subtitle_format.size = Pt(12)
    subtitle_format.bold = True
    
    doc.add_paragraph("")
    
    # Processa il contenuto
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
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
            p = doc.add_paragraph()
            run = p.add_run(line[2:-2])
            run.font.name = 'Figtree'
            run.font.size = Pt(11)
            run.font.bold = True
            
        elif line.startswith('- ') or line.startswith('* '):
            p = doc.add_paragraph(line[2:], style='List Bullet')
            p.runs[0].font.name = 'Figtree'
            p.runs[0].font.size = Pt(11)
            
        else:
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
    st.markdown('<p style="text-align: center; color: #666;">Genera content brief con dati SEO reali da SEMrush e Serper</p>', unsafe_allow_html=True)
    
    # Sidebar per API Keys
    with st.sidebar:
        st.markdown("### 🔑 Configurazione API")
        
        # OpenAI API Key
        openai_api_key = st.text_input("OpenAI API Key", type="password", help="Inserisci la tua API key di OpenAI")
        
        # SEMrush API Key
        st.markdown("---")
        st.markdown("#### 📊 SEMrush (Opzionale)")
        semrush_api_key = st.text_input("SEMrush API Key", type="password", help="Per dati keyword reali, volumi di ricerca e keyword correlate")
        if semrush_api_key:
            st.success("✅ SEMrush configurato")
        else:
            st.info("💡 Aggiungi per dati keyword reali")
        
        # Serper API Key
        st.markdown("#### 🔍 Serper (Opzionale)")
        serper_api_key = st.text_input("Serper API Key", type="password", help="Per People Also Ask e analisi SERP in tempo reale")
        if serper_api_key:
            st.success("✅ Serper configurato")
        else:
            st.info("💡 Aggiungi per PAA da Google")
        
        st.markdown("---")
        st.markdown("### 🚀 Miglioramenti")
        st.markdown("""
        **Con SEMrush + Serper:**
        - 📈 Volumi di ricerca reali
        - 🎯 Keyword correlate precise
        - ❓ People Also Ask live
        - 🏆 Featured snippet analysis
        - 📊 Competition data
        """)
    
    if not openai_api_key:
        st.info("👈 Inserisci almeno la OpenAI API Key nella sidebar per iniziare")
        return
    
    # Inizializza i servizi
    seo_enhancer = SEODataEnhancer(semrush_api_key, serper_api_key)
    generator = ContentBriefGenerator(openai_api_key, seo_enhancer)
    
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
            keywords = st.text_area("🔍 Keyword utili", placeholder="keyword principale, keyword secondaria, keyword long tail")
            faqs = st.text_area("❓ Domande frequenti (PAA)", placeholder="Inserisci domande conosciute, verranno integrate con PAA reali da Google se Serper è configurato")
            
            # Tone of voice con multiselect
            tone_options = [
                "Professionale", "Minimalista", "Persuasivo", 
                "Informativo", "Ricercato", "Popolare", "Personalizzato"
            ]
            tone_of_voice = st.multiselect("🎯 Tone of voice", tone_options, default=["Professionale"])
        
        # Preview API status
        if semrush_api_key or serper_api_key:
            st.markdown('<div class="success-box">🎯 <strong>Modalità Enhanced SEO attiva!</strong> Il content brief includerà dati reali da:', unsafe_allow_html=True)
            if semrush_api_key:
                st.markdown("✅ SEMrush: volumi di ricerca, keyword correlate, competition data")
            if serper_api_key:
                st.markdown("✅ Serper: People Also Ask live, ricerche correlate, featured snippets")
            st.markdown('</div>', unsafe_allow_html=True)
        
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
        
        submitted = st.form_submit_button("🚀 Genera content brief con dati SEO reali", use_container_width=True)
    
    if submitted:
        # Validazione input
        if not all([brand, website, topic, keywords]):
            st.error("❌ Compila tutti i campi obbligatori: Brand, Website, Argomento e Keywords")
            return
        
        if not competitor_data:
            st.error("❌ Inserisci almeno un URL competitor")
            return
        
        with st.spinner("🔄 Generazione del content brief con dati SEO reali..."):
            progress_bar = st.progress(0)
            
            # Step 1: Analisi keyword con API
            if semrush_api_key or serper_api_key:
                st.info("🔍 Analisi keyword con SEMrush e Serper...")
                keyword_analysis = generator.analyze_keywords_with_apis(keywords)
                progress_bar.progress(15)
                
                # Mostra preview dati SEO
                if keyword_analysis['semrush_data'].get('status') == 'success':
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📈 Volume ricerca", f"{keyword_analysis['semrush_data']['search_volume']:,}")
                    with col2:
                        st.metric("💰 CPC", f"€{keyword_analysis['semrush_data']['cpc']:.2f}")
                    with col3:
                        st.metric("⚔️ Competition", f"{keyword_analysis['semrush_data']['competition']:.2f}")
                
                if keyword_analysis['serper_data'].get('people_also_ask'):
                    st.success(f"✅ Trovate {len(keyword_analysis['serper_data']['people_also_ask'])} People Also Ask da Google")
            else:
                st.info("📊 Analisi keyword base (senza API esterne)...")
                keyword_analysis = {'main_keyword': keywords.split(',')[0].strip(), 'semrush_data': {}, 'serper_data': {}}
                progress_bar.progress(15)
            
            # Step 2: Estrazione sitemap
            st.info("📡 Estrazione URL dalla sitemap...")
            sitemap_urls = []
            sitemap_error = False
            
            if sitemap_url:
                sitemap_urls = generator.get_sitemap_urls(sitemap_url)
                if not sitemap_urls:
                    sitemap_error = True
                    st.warning("⚠️ Impossibile accedere alla sitemap. Utilizzo URL manuali.")
            
            if sitemap_error or manual_urls.strip():
                manual_url_list = [url.strip() for url in manual_urls.split('\n') if url.strip()]
                sitemap_urls.extend(manual_url_list)
            
            progress_bar.progress(35)
            
            # Step 3: Scraping competitor
            st.info("🕷️ Analisi competitor in corso...")
            competitors_scraped = []
            
            for i, comp_data in enumerate(competitor_data):
                if comp_data['use_manual'] and comp_data['manual_content']:
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
                    scraped_data = generator.scrape_url(comp_data['url'])
                    
                    if scraped_data['status'] == 'error':
                        st.error(f"❌ Impossibile accedere a {comp_data['url']}")
                        st.markdown('<div class="error-box">Per continuare, usa l\'opzione "Contenuto manuale" e incolla il testo della pagina</div>', unsafe_allow_html=True)
                
                competitors_scraped.append(scraped_data)
                progress_bar.progress(35 + (i + 1) * 20)
            
            # Verifica competitor validi
            valid_competitors = [c for c in competitors_scraped if c['status'] in ['success', 'manual']]
            if not valid_competitors:
                st.error("❌ Nessun competitor analizzato con successo. Riprova con contenuto manuale.")
                return
            
            # Step 4: Preparazione dati
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
            progress_bar.progress(85)
            
            # Step 5: Generazione content brief
            st.info("🤖 Generazione content brief con AI e dati SEO reali...")
            content_brief = generator.generate_content_brief(data, keyword_analysis)
            progress_bar.progress(95)
            
            # Step 6: Creazione documento
            st.info("📄 Creazione documento DOCX...")
            docx_buffer = create_docx(content_brief, brand, topic)
            progress_bar.progress(100)
            
            st.success("✅ Content brief SEO data-driven generato con successo!")
        
        # Mostra risultati
        st.markdown('<h2 class="section-header">📋 Content brief SEO data-driven generato</h2>', unsafe_allow_html=True)
        
        # Dati SEO summary
        if keyword_analysis.get('semrush_data') or keyword_analysis.get('serper_data'):
            st.markdown('<h3 class="section-header">📊 Dati SEO reali utilizzati</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if keyword_analysis.get('semrush_data', {}).get('status') == 'success':
                    st.markdown("**🎯 Dati SEMrush**")
                    semrush = keyword_analysis['semrush_data']
                    st.write(f"• Volume: {semrush['search_volume']:,} ricerche/mese")
                    st.write(f"• CPC: €{semrush['cpc']:.2f}")
                    st.write(f"• Competition: {semrush['competition']:.2f}/1.0")
                    
                    if keyword_analysis.get('related_keywords'):
                        st.write(f"• {len(keyword_analysis['related_keywords'])} keyword correlate trovate")
            
            with col2:
                if keyword_analysis.get('serper_data', {}).get('status') == 'success':
                    st.markdown("**🔍 Dati Serper**")
                    serper = keyword_analysis['serper_data']
                    if serper.get('people_also_ask'):
                        st.write(f"• {len(serper['people_also_ask'])} People Also Ask")
                    if serper.get('related_searches'):
                        st.write(f"• {len(serper['related_searches'])} ricerche correlate")
                    if serper.get('featured_snippet'):
                        st.write("• Featured snippet attuale analizzato")
            
            # Preview PAA
            if keyword_analysis.get('serper_data', {}).get('people_also_ask'):
                with st.expander("❓ People Also Ask da Google"):
                    for paa in keyword_analysis['serper_data']['people_also_ask']:
                        st.write(f"• {paa}")
        
        # Preview del contenuto
        with st.expander("👁️ Anteprima content brief", expanded=True):
            st.markdown(content_brief)
        
        # Download button
        st.download_button(
            label="📥 Scarica content brief SEO data-driven (DOCX)",
            data=docx_buffer.getvalue(),
            file_name=f"content_brief_SEO_{brand}_{topic.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
        
        # Informazioni aggiuntive
        st.markdown('<h3 class="section-header">📊 Riepilogo analisi completa</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔍 Competitor analizzati", len(valid_competitors))
        with col2:
            st.metric("🔗 URL interne trovate", len(sitemap_urls))
        with col3:
            paa_count = len(keyword_analysis.get('serper_data', {}).get('people_also_ask', []))
            st.metric("❓ PAA da Google", paa_count)
        with col4:
            kw_count = len(keyword_analysis.get('related_keywords', []))
            st.metric("🎯 Keyword correlate", kw_count)
        
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
        
        # Enhanced E-E-A-T checklist
        st.markdown('<h3 class="section-header">🏆 Checklist E-E-A-T Enhanced</h3>', unsafe_allow_html=True)
        st.markdown('<div class="success-box">Il content brief generato include suggerimenti basati su <strong>dati SEO reali</strong> per massimizzare E-E-A-T:</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **📚 Experience (Data-driven)**
            - ✅ Esempi basati su ricerche correlate reali
            - ✅ Casi studio che rispondono alle PAA
            - ✅ Scenari ottimizzati per volumi di ricerca
            - ✅ Testimonianze mirate al search intent
            
            **🎓 Expertise (SEO-optimized)**
            - ✅ Insight basati su keyword correlate
            - ✅ Dati statistici reali (volumi, trend)
            - ✅ Gap analysis vs competitor top 10
            - ✅ Featured snippet optimization
            """)
        
        with col2:
            st.markdown("""
            **⭐ Authoritativeness (SERP-focused)**
            - ✅ Fonti che battono competitor attuali
            - ✅ Strategia per featured snippet
            - ✅ Authority building per high-volume keywords
            - ✅ Topical relevance enhancement
            
            **🛡️ Trustworthiness (Search-aligned)**
            - ✅ Trasparenza su dati e metodologie
            - ✅ Riconoscimento limiti vs competitor
            - ✅ User intent satisfaction
            - ✅ Search quality guidelines compliance
            """)
        
        # API usage tips
        if not semrush_api_key or not serper_api_key:
            st.markdown('<h3 class="section-header">💡 Migliora ulteriormente i risultati</h3>', unsafe_allow_html=True)
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            if not semrush_api_key:
                st.write("🔹 **Aggiungi SEMrush API** per: volumi di ricerca precisi, keyword difficulty, competitor traffic analysis")
            if not serper_api_key:
                st.write("🔹 **Aggiungi Serper API** per: People Also Ask live, featured snippets, real-time SERP data")
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
