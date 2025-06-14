from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, g, jsonify
from services import pubmed_client, db_updater, grok_client
from services.grok_client import get_reference_ranges_from_grok
from services.pubmed_client import search_pubmed_references
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)
agente_bp = Blueprint('agente_referencias', __name__, url_prefix='/agente')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session['usuario'].get('role') != 'admin':
            flash("Acesso negado. Requer privilégios de administrador.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@agente_bp.route('/processar_documento', methods=['GET', 'POST'])
@admin_required
def processar_documento():
    # Carrega a lista de variáveis para o template
    variaveis_db_para_template = []
    try:
        _conn, _cur = db_updater.get_db_from_g()
        _cur.execute("SELECT SIGLA, NOME, NOME_INGLES FROM VARIAVEIS ORDER BY SIGLA")
        variaveis_db_para_template = _cur.fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar lista de variáveis para template: {e}", exc_info=True)
        flash('Erro ao carregar dados iniciais da página.', 'danger')
        return render_template('interface_agente.html', variaveis_db=[])

    if request.method == 'POST':
        variable_sigla = request.form.get('variable_sigla', '').strip()
        years_back = request.form.get('years_back', '5')
        max_results = request.form.get('max_results', '10')

        if not variable_sigla:
            flash('Selecione uma medida para pesquisar.', 'warning')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

        try:
            years_back = int(years_back)
            max_results = int(max_results)
            
            if years_back < 1 or years_back > 20:
                flash('O número de anos deve estar entre 1 e 20.', 'warning')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            if max_results < 1 or max_results > 50:
                flash('O número máximo de resultados deve estar entre 1 e 50.', 'warning')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

            # Obtém o nome em inglês da variável
            _conn_nome_var, _cur_nome_var = db_updater.get_db_from_g()
            _cur_nome_var.execute("SELECT NOME, NOME_INGLES FROM VARIAVEIS WHERE SIGLA = ?", (variable_sigla,))
            var_record = _cur_nome_var.fetchone()
            
            if not var_record:
                flash(f'Variável com sigla "{variable_sigla}" não encontrada no banco de dados.', 'danger')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            measure_name = var_record[0]  # Nome em português para exibição
            measure_name_english = var_record[1]  # Nome em inglês para busca
            logger.info(f"Buscando artigos na PubMed para a medida '{measure_name_english}'")
            
            # Busca artigos na PubMed
            articles = pubmed_client.search_pubmed_references(
                measure_name=measure_name_english,
                years_back=years_back,
                max_results=max_results
            )

            if articles is None:
                flash('Erro ao consultar a API PubMed. Verifique os logs.', 'danger')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
            
            if not articles:
                flash(f'Nenhum artigo encontrado para a medida "{measure_name}" nos últimos {years_back} anos.', 'info')
                return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

            # Extrai normalidades de cada artigo
            normalized_data = []
            for article in articles:
                try:
                    extracted_ranges = get_reference_ranges_from_grok(article['abstract'])
                    if extracted_ranges:
                        # Filtra apenas as medidas relevantes
                        relevant_ranges = [
                            range_data for range_data in extracted_ranges
                            if measure_name_english.lower() in range_data['nome_medida'].lower()
                        ]
                        if relevant_ranges:
                            normalized_data.append({
                                'pmid': article['pmid'],
                                'title': article['title'],
                                'year': article['year'],
                                'url': article['url'],
                                'reference_ranges': relevant_ranges
                            })
                except Exception as e:
                    logger.error(f"Erro ao processar artigo {article['pmid']}: {e}")
                    continue

            return render_template(
                'interface_agente.html',
                variaveis_db=variaveis_db_para_template,
                articles=articles,
                normalized_data=normalized_data,
                measure_name=measure_name
            )

        except ValueError:
            flash('Valores inválidos para anos ou número máximo de resultados.', 'warning')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)
        except Exception as e:
            logger.error(f"Erro ao processar a busca: {e}", exc_info=True)
            flash(f'Erro ao processar a busca: {str(e)}', 'danger')
            return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

    return render_template('interface_agente.html', variaveis_db=variaveis_db_para_template)

@agente_bp.route('/agente-referencias', methods=['GET'])
def interface_agente():
    return render_template('interface_agente.html')

@agente_bp.route('/buscar-faixas-normalidade', methods=['POST'])
def buscar_faixas_normalidade():
    try:
        data = request.get_json()
        measure_name = data.get('measure_name')
        
        if not measure_name:
            return jsonify({'error': 'Nome da medida é obrigatório'}), 400
            
        # Busca diretrizes na PubMed
        articles = search_pubmed_references(measure_name)
        
        if articles is None:
            return jsonify({'error': 'Erro ao buscar diretrizes na PubMed'}), 500
            
        if not articles:
            return jsonify({'message': 'Nenhuma diretriz encontrada para esta medida'}), 404
            
        # Processa os artigos para extrair as faixas de normalidade
        processed_articles = []
        for article in articles:
            try:
                extracted_ranges = get_reference_ranges_from_grok(article['abstract'])
                if extracted_ranges:
                    article['reference_ranges'] = extracted_ranges
                processed_articles.append(article)
            except Exception as e:
                logger.error(f"Erro ao processar artigo {article.get('pmid', 'N/A')}: {e}")
                continue
            
        return jsonify({
            'success': True,
            'articles': processed_articles
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar faixas de normalidade: {e}")
        return jsonify({'error': str(e)}), 500

@agente_bp.route('/adicionar-normalidade', methods=['POST'])
@admin_required
def adicionar_normalidade():
    try:
        data = request.get_json()
        
        # Validação dos dados
        required_fields = ['nome_medida', 'valor_min', 'valor_max', 'unidade', 'fonte', 'pmid']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
        
        # Conecta ao banco de dados
        conn, cur = db_updater.get_db_from_g()
        
        # Primeiro, busca o CODVARIAVEL baseado no nome da medida
        cur.execute("SELECT CODVARIAVEL FROM VARIAVEIS WHERE NOME = ?", (data['nome_medida'],))
        var_record = cur.fetchone()
        
        if not var_record:
            return jsonify({'error': 'Variável não encontrada no banco de dados'}), 404
        
        codvariavel = var_record[0]
        
        # Busca o CODREFERENCIA baseado no PMID
        cur.execute("SELECT CODREFERENCIA FROM REFERENCIAS WHERE PMID = ?", (data['pmid'],))
        ref_record = cur.fetchone()
        
        if not ref_record:
            # Se a referência não existe, cria uma nova
            cur.execute("""
                INSERT INTO REFERENCIAS (
                    TITULO,
                    AUTORES,
                    ANO,
                    PMID,
                    URL,
                    RESUMO
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get('titulo', ''),
                data.get('autores', ''),
                data.get('ano', datetime.now().year),
                data['pmid'],
                data.get('url', ''),
                data['fonte']
            ))
            conn.commit()
            
            # Busca o CODREFERENCIA recém-criado
            cur.execute("SELECT CODREFERENCIA FROM REFERENCIAS WHERE PMID = ?", (data['pmid'],))
            ref_record = cur.fetchone()
        
        codreferencia = ref_record[0]
        
        # Extrai informações de sexo e idade da condição adicional, se existir
        sexo = None
        idade_min = None
        idade_max = None
        
        if data.get('condicao'):
            condicao = data['condicao'].lower()
            # Tenta extrair informações de sexo
            if 'masculino' in condicao:
                sexo = 'M'
            elif 'feminino' in condicao:
                sexo = 'F'
            
            # Tenta extrair informações de idade
            import re
            idade_match = re.search(r'(\d+)\s*(?:a|até|-)\s*(\d+)\s*(?:anos|ano)', condicao)
            if idade_match:
                idade_min = int(idade_match.group(1))
                idade_max = int(idade_match.group(2))
        
        # Insere o valor de normalidade
        cur.execute("""
            INSERT INTO NORMALIDADE (
                CODVARIAVEL,
                CODREFERENCIA,
                VALORMIN,
                VALORMAX,
                SEXO,
                IDADE_MIN,
                IDADE_MAX,
                CODUSUARIO,
                DTHRULTMODIFICACAO
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codvariavel,
            codreferencia,
            data['valor_min'],
            data['valor_max'],
            sexo,
            idade_min,
            idade_max,
            session['usuario']['codusuario'],
            datetime.now()
        ))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Valor de normalidade adicionado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao adicionar valor de normalidade: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@agente_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    try:
        conn, cur = db_updater.get_db_from_g()
        
        # Conta total de normalidades
        cur.execute("SELECT COUNT(*) FROM NORMALIDADE")
        total_normalidades = cur.fetchone()[0]
        
        # Conta total de artigos processados
        cur.execute("SELECT COUNT(DISTINCT CODREFERENCIA) FROM NORMALIDADE")
        total_artigos = cur.fetchone()[0]
        
        # Por enquanto, total_formulas é 0 pois ainda não implementamos
        total_formulas = 0
        
        return render_template(
            'agentes_dashboard.html',
            total_normalidades=total_normalidades,
            total_formulas=total_formulas,
            total_artigos=total_artigos
        )
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
        flash('Erro ao carregar dashboard', 'danger')
        return redirect(url_for('index'))

@agente_bp.route('/processar-formulas', methods=['GET', 'POST'])
@admin_required
def processar_formulas():
    # Carrega a lista de variáveis para o template
    variaveis_db_para_template = []
    try:
        _conn, _cur = db_updater.get_db_from_g()
        _cur.execute("SELECT SIGLA, NOME, NOME_INGLES FROM VARIAVEIS ORDER BY SIGLA")
        variaveis_db_para_template = _cur.fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar lista de variáveis para template: {e}", exc_info=True)
        flash('Erro ao carregar dados iniciais da página.', 'danger')
        return render_template('interface_agente_formulas.html', variaveis_db=[])

    if request.method == 'POST':
        variable_sigla = request.form.get('variable_sigla', '').strip()
        years_back = request.form.get('years_back', '5')
        max_results = request.form.get('max_results', '10')

        if not variable_sigla:
            flash('Selecione uma medida para pesquisar.', 'warning')
            return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)

        try:
            years_back = int(years_back)
            max_results = int(max_results)
            
            if years_back < 1 or years_back > 20:
                flash('O número de anos deve estar entre 1 e 20.', 'warning')
                return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)
            
            if max_results < 1 or max_results > 50:
                flash('O número máximo de resultados deve estar entre 1 e 50.', 'warning')
                return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)

            # Obtém o nome em inglês da variável
            _conn_nome_var, _cur_nome_var = db_updater.get_db_from_g()
            _cur_nome_var.execute("SELECT NOME, NOME_INGLES FROM VARIAVEIS WHERE SIGLA = ?", (variable_sigla,))
            var_record = _cur_nome_var.fetchone()
            
            if not var_record:
                flash(f'Variável com sigla "{variable_sigla}" não encontrada no banco de dados.', 'danger')
                return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)
            
            measure_name = var_record[0]  # Nome em português para exibição
            measure_name_english = var_record[1]  # Nome em inglês para busca
            logger.info(f"Buscando fórmulas na PubMed para a medida '{measure_name_english}'")
            
            # TODO: Implementar a busca de fórmulas
            flash('Funcionalidade em desenvolvimento', 'info')
            return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)

        except ValueError:
            flash('Valores inválidos para anos ou número máximo de resultados.', 'warning')
            return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)
        except Exception as e:
            logger.error(f"Erro ao processar a busca: {e}", exc_info=True)
            flash(f'Erro ao processar a busca: {str(e)}', 'danger')
            return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)

    return render_template('interface_agente_formulas.html', variaveis_db=variaveis_db_para_template)