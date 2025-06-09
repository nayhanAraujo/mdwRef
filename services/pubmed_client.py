import requests
import json
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_SEARCH_URL = f"{PUBMED_BASE_URL}/esearch.fcgi"
PUBMED_FETCH_URL = f"{PUBMED_BASE_URL}/efetch.fcgi"

def search_pubmed_references(measure_name):
    try:
        # 1. Tratamento da medida para evitar problemas com caracteres especiais
        safe_measure = measure_name.replace('"', '').strip()
        
        # 2. Construção da query mais flexível
        query = (
            f'("{safe_measure}"[Title/Abstract] OR "{safe_measure}"[MeSH Terms]) '
            f'AND ("echocardiography"[MeSH Terms] OR "echocardiography"[Title/Abstract]) '
            f'AND ("reference values"[Title/Abstract] OR "normal values"[Title/Abstract] OR "normal range"[Title/Abstract] OR "guidelines"[Publication Type])'
        )
        
        # 3. Parâmetros da requisição
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': '20',  # Limita a 20 resultados mais relevantes
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        logger.info(f"Buscando diretrizes para: '{measure_name}' | Query: {query}")
        search_response = requests.get(PUBMED_SEARCH_URL, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        if not search_data.get('esearchresult', {}).get('idlist'):
            logger.info("Nenhuma diretriz encontrada para a busca")
            return []
        
        # Obtém os detalhes dos artigos encontrados
        article_ids = search_data['esearchresult']['idlist']
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(article_ids),
            'retmode': 'xml'
        }
        
        fetch_response = requests.get(PUBMED_FETCH_URL, params=fetch_params)
        fetch_response.raise_for_status()
        
        # Processa o XML retornado
        root = ET.fromstring(fetch_response.content)
        articles = []
        
        for article in root.findall('.//PubmedArticle'):
            try:
                # Extrai informações básicas do artigo
                title = article.find('.//ArticleTitle').text
                abstract = article.find('.//Abstract/AbstractText')
                abstract_text = abstract.text if abstract is not None else ""
                
                # Extrai autores
                authors = []
                for author in article.findall('.//Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')
                    if last_name is not None and fore_name is not None:
                        authors.append(f"{last_name.text} {fore_name.text}")
                
                # Extrai data de publicação
                pub_date = article.find('.//PubDate')
                year = pub_date.find('Year').text if pub_date is not None else "N/A"
                
                # Extrai PMID
                pmid = article.find('.//PMID').text
                
                # Constrói o link para o artigo
                article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                
                # Identifica a fonte (ASE, EACVI, etc.)
                source = "Outro"
                if "ASE" in abstract_text or "American Society of Echocardiography" in abstract_text:
                    source = "ASE"
                elif "EACVI" in abstract_text:
                    source = "EACVI"
                
                articles.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'abstract': abstract_text,
                    'url': article_url,
                    'pmid': pmid,
                    'source': source
                })
                
            except Exception as e:
                logger.error(f"Erro ao processar artigo: {e}")
                continue
        
        return articles
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API PubMed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Detalhes da resposta do erro: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar artigos: {e}")
        return None

def extract_reference_ranges(articles, measure_name):
    """
    Extrai faixas de normalidade dos resumos/artigos encontrados.
    Retorna um JSON organizado por estudo.
    """
    results = []
    
    for article in articles:
        try:
            # Usa o Grok Client para extrair dados do resumo (já implementado)
            extracted_data = get_reference_ranges_from_grok(article['abstract'])
            
            if extracted_data:
                # Filtra apenas as medidas relevantes (caso o artigo fale sobre múltiplas)
                relevant_measures = [
                    item for item in extracted_data 
                    if measure_name.lower() in item['nome_medida'].lower()
                ]
                
                if relevant_measures:
                    results.append({
                        'pmid': article['pmid'],
                        'title': article['title'],
                        'year': article['year'],
                        'url': article['url'],
                        'reference_ranges': relevant_measures  # Lista de normalidades encontradas
                    })
                    
        except Exception as e:
            logger.error(f"Erro ao extrair normalidades do artigo {article['pmid']}: {e}")
            continue
    
    return results