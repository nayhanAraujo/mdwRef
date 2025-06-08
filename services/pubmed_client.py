import requests
import json
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_SEARCH_URL = f"{PUBMED_BASE_URL}/esearch.fcgi"
PUBMED_FETCH_URL = f"{PUBMED_BASE_URL}/efetch.fcgi"

def search_pubmed_references(measure_name, years_back=5, max_results=10):
    try:
        date_limit = (datetime.now() - timedelta(days=years_back*365)).strftime("%Y/%m/%d")
        
        # 1. Tratamento da medida para evitar problemas com caracteres especiais
        safe_measure = measure_name.replace('"', '').strip()  # Remove aspas se houver
        
        # 2. Construção da query dinâmica
        query = (
            f'("{safe_measure}"[Title/Abstract] OR "{safe_measure}"[MeSH Terms]) '  # Busca no título, resumo OU termos MeSH
            f'AND ("reference values"[Title/Abstract] OR "normal range"[Title/Abstract] OR "guidelines"[Publication Type]) '
            f'AND ("echocardiography"[MeSH Terms] OR "cardiac imaging"[Title/Abstract]) '
            f'AND ("{date_limit}"[Date - Publication] : "3000"[Date - Publication])'
        )
        
        # 3. Parâmetros da requisição
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': str(max_results),
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        logger.info(f"Buscando artigos para: '{measure_name}' | Query: {query}")
        search_response = requests.get(PUBMED_SEARCH_URL, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        if not search_data.get('esearchresult', {}).get('idlist'):
            logger.info("Nenhum artigo encontrado para a busca")
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
                
                # Extrai DOI
                doi = article.find('.//ELocationID[@EIdType="doi"]')
                doi_text = doi.text if doi is not None else "N/A"
                
                # Extrai PMID
                pmid = article.find('.//PMID').text
                
                # Constrói o link para o artigo
                article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                
                articles.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'doi': doi_text,
                    'abstract': abstract_text,
                    'url': article_url,
                    'pmid': pmid
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