import requests
import json
import logging,re
from flask import current_app # Para acessar config

logger = logging.getLogger(__name__)


GROK_API_URL = "https://api.x.ai/v1/chat/completions" 

def get_reference_ranges_from_grok(text_content):
    api_key = "xai-ImHSuNwvu1OyXNplrIcAdRNSnidIwgUGZygTpNrgcs6zAqMneYrUlzTJuQKrIhQTvrN3EwnnUCJmux0x"
    if not api_key:
        logger.error("GROK_API_KEY não configurada.")
        return None

    prompt = f"""
    Analise o seguinte texto acadêmico e extraia TODAS as medidas que possuem valores de referência ou faixas de normalidade.
    Para cada medida encontrada, forneça:
    - "nome_medida": O nome da medida encontrada (ex: "Diâmetro da Aorta", "Volume do Ventrículo Esquerdo").
    - "valor_min": O valor mínimo da faixa (numérico, use null se não aplicável ou se for < X).
    - "valor_max": O valor máximo da faixa (numérico, use null se não aplicável ou se for > X).
    - "unidade_medida": A unidade de medida (ex: "mm", "cm/m²", "%").
    - "sexo": O sexo ao qual se aplica ('M' para Masculino, 'F' para Feminino, 'A' para Ambos/Não especificado).
    - "idade_min": A idade mínima em anos (numérico, use null se não aplicável).
    - "idade_max": A idade máxima em anos (numérico, use null se não aplicável).
    - "condicao_adicional": Qualquer outra condição relevante (ex: "indexado pela superfície corporal", "em repouso", "percentil 5-95"). Deixe como null se não houver.
    - "texto_original_relevante": O trecho exato do texto de onde a informação foi extraída, para fins de auditoria (máximo 300 caracteres).

    Regras para extração:
    1. Se uma faixa for descrita como "menor que X", coloque X em "valor_max" e "valor_min" como null.
    2. Se for "maior que X", coloque X em "valor_min" e "valor_max" como null.
    3. Se for um valor único de referência, coloque-o em "valor_max" e "valor_min" como null.
    4. Se for um intervalo "X-Y", use "valor_min": X e "valor_max": Y.
    5. Se não encontrar nenhuma medida com valores de referência, retorne uma lista vazia.
    6. Extraia TODAS as medidas que encontrar no texto, não apenas uma específica.

    Retorne os dados estritamente em formato JSON como uma lista de objetos. Exemplo de um item na lista:
    {{
        "nome_medida": "Diâmetro da Aorta Ascendente",
        "valor_min": 2.5,
        "valor_max": 4.0,
        "unidade_medida": "cm",
        "sexo": "M",
        "idade_min": 20,
        "idade_max": 40,
        "condicao_adicional": "indexado pela SC",
        "texto_original_relevante": "Para homens entre 20-40 anos, o diâmetro da aorta ascendente indexado é 2.5-4.0 cm."
    }}

    Texto para análise:
    ---
    {text_content[:15000]}
    ---
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-3-mini-beta",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        logger.debug(f"Enviando request para Grok. Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        response_data = response.json()
        logger.debug(f"Resposta da API Grok: {json.dumps(response_data, indent=2)}")

        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message_content = response_data["choices"][0].get("message", {}).get("content", "")
            try:
                extracted_data = json.loads(message_content)
                logger.info(f"Dados JSON extraídos e parseados com sucesso: {extracted_data}")
                return extracted_data
            except json.JSONDecodeError as je:
                logger.error(f"Erro ao decodificar JSON da resposta do Grok: {je}. Conteúdo: {message_content}")
                return None
        else:
            logger.warning(f"Resposta inesperada da API Grok ou sem 'choices': {response_data}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API Grok: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Detalhes da resposta do erro: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar resposta do Grok: {e}")
        return None