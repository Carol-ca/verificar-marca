"""
============================================
VERIFICADOR DE MARCAS MARKETPLACE
Aplicação Web Flask
============================================

Servidor web que expõe a interface de verificação
de marcas registradas para marketplaces brasileiros.

Uso:
    python app.py

Acesse: http://localhost:5000
"""

import os
import sys
import json
import logging
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Importar motor de verificação
from verificador import (
    verificar_anuncio,
    extrair_termos,
    extrair_conteudo_url,
    MARCAS_CONHECIDAS,
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# No ambiente Serverless (Vercel), apenas /tmp é gravável
if os.environ.get('VERCEL'):
    app.config['UPLOAD_FOLDER'] = '/tmp'
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['SECRET_KEY'] = 'verificador-marcas-2024'

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

# Extensões de imagem permitidas
EXTENSOES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp'}


def extensao_permitida(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


# ============================================================
# ROTAS - PÁGINAS
# ============================================================

@app.route('/')
def index():
    """Página principal com a interface de verificação."""
    return render_template('index.html')


# ============================================================
# ROTAS - API
# ============================================================

@app.route('/api/verificar', methods=['POST'])
def api_verificar():
    """
    API de verificação por link ou texto.

    Payload JSON:
    {
        "tipo": "link" | "texto",
        "url": "https://...",        (se tipo == "link")
        "texto": "título e descrição" (se tipo == "texto")
    }
    """
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400

        tipo = dados.get('tipo', 'texto')
        url = dados.get('url', '').strip()
        texto = dados.get('texto', '').strip()

        logger.info(f"Verificação solicitada - Tipo: {tipo}")

        if tipo == 'link':
            if not url:
                return jsonify({'erro': 'URL não fornecida'}), 400
            logger.info(f"Verificando URL: {url}")
            resultado = verificar_anuncio(texto='', url=url)

        elif tipo == 'texto':
            if not texto:
                return jsonify({'erro': 'Texto não fornecido'}), 400
            logger.info(f"Verificando texto ({len(texto)} chars)")
            resultado = verificar_anuncio(texto=texto)

        else:
            return jsonify({'erro': f'Tipo inválido: {tipo}'}), 400

        # Converter resultado para dicionário serializável
        resposta = resultado.to_dict()
        logger.info(f"Resultado: {resposta['status_geral']} | "
                    f"Termos: {len(resposta['termos_extraidos'])} | "
                    f"Resultados: {len(resposta['resultados'])}")

        return jsonify(resposta)

    except Exception as e:
        logger.error(f"Erro na verificação: {e}", exc_info=True)
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/api/verificar-imagem', methods=['POST'])
def api_verificar_imagem():
    """
    API de verificação por imagem (OCR).

    Recebe upload de imagem, extrai texto via OCR e verifica marcas.
    """
    try:
        if 'imagem' not in request.files:
            return jsonify({'erro': 'Nenhuma imagem enviada'}), 400

        arquivo = request.files['imagem']
        if arquivo.filename == '':
            return jsonify({'erro': 'Arquivo sem nome'}), 400

        if not extensao_permitida(arquivo.filename):
            return jsonify({
                'erro': f'Formato não suportado. Use: {", ".join(EXTENSOES_PERMITIDAS)}'
            }), 400

        # Salvar arquivo temporariamente
        nome_seguro = secure_filename(arquivo.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"{timestamp}_{nome_seguro}"
        caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
        arquivo.save(caminho_arquivo)

        logger.info(f"Imagem salva: {caminho_arquivo}")

        # Tentar OCR com pytesseract
        texto_extraido = ""
        ocr_disponivel = False

        try:
            import pytesseract
            from PIL import Image

            # Tentar encontrar o Tesseract no sistema
            possiveis_caminhos = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(
                    os.environ.get('USERNAME', '')
                ),
            ]

            for caminho in possiveis_caminhos:
                if os.path.exists(caminho):
                    pytesseract.pytesseract.tesseract_cmd = caminho
                    break

            # Abrir imagem e aplicar OCR
            img = Image.open(caminho_arquivo)

            # Converter para RGB se necessário
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # OCR com idioma português
            try:
                texto_extraido = pytesseract.image_to_string(img, lang='por')
            except Exception:
                # Fallback sem idioma específico
                texto_extraido = pytesseract.image_to_string(img)

            ocr_disponivel = True
            logger.info(f"OCR extraiu {len(texto_extraido)} caracteres")

        except ImportError:
            logger.warning("pytesseract não instalado")
            texto_extraido = ""
        except Exception as e:
            logger.warning(f"Erro no OCR: {e}")
            texto_extraido = ""

        # Se OCR não extraiu texto, tentar leitura básica de metadados
        if not texto_extraido.strip():
            try:
                from PIL import Image
                img = Image.open(caminho_arquivo)
                # Extrair metadados EXIF que podem conter texto
                info = img.info
                if info:
                    for key, value in info.items():
                        if isinstance(value, str):
                            texto_extraido += f" {value}"
            except Exception:
                pass

        if not texto_extraido.strip():
            # Limpar arquivo temporário
            try:
                os.remove(caminho_arquivo)
            except Exception:
                pass

            if not ocr_disponivel:
                return jsonify({
                    'status_geral': 'atencao',
                    'termos_extraidos': [],
                    'resultados': [{
                        'termo': '(imagem)',
                        'status': 'atencao',
                        'motivo': 'OCR (Tesseract) não está instalado no sistema. '
                                  'Para usar a verificação por imagem, instale o Tesseract OCR: '
                                  'https://github.com/UB-Mannheim/tesseract/wiki\n'
                                  'Ou use a opção de Texto Direto, colando o conteúdo do anúncio manualmente.',
                        'titular': None,
                        'classe': None,
                        'tipo': None,
                        'fonte': 'Sistema',
                        'inpi_encontrado': False,
                        'google_encontrado': False,
                        'detalhes_inpi': None,
                        'detalhes_google': None,
                    }],
                    'texto_original': '',
                    'timestamp': datetime.now().isoformat(),
                })
            else:
                return jsonify({
                    'status_geral': 'atencao',
                    'termos_extraidos': [],
                    'resultados': [{
                        'termo': '(imagem)',
                        'status': 'atencao',
                        'motivo': 'Não foi possível extrair texto da imagem. '
                                  'A imagem pode estar muito pequena, desfocada ou sem texto legível. '
                                  'Tente enviar uma imagem com melhor resolução ou use a opção de Texto Direto.',
                        'titular': None,
                        'classe': None,
                        'tipo': None,
                        'fonte': 'OCR',
                        'inpi_encontrado': False,
                        'google_encontrado': False,
                        'detalhes_inpi': None,
                        'detalhes_google': None,
                    }],
                    'texto_original': '',
                    'timestamp': datetime.now().isoformat(),
                })

        # Verificar marcas no texto extraído
        resultado = verificar_anuncio(texto=texto_extraido)
        resposta = resultado.to_dict()
        resposta['texto_ocr'] = texto_extraido[:1000]

        # Limpar arquivo temporário
        try:
            os.remove(caminho_arquivo)
        except Exception:
            pass

        logger.info(f"Resultado imagem: {resposta['status_geral']} | "
                    f"Termos: {len(resposta['termos_extraidos'])}")

        return jsonify(resposta)

    except Exception as e:
        logger.error(f"Erro na verificação de imagem: {e}", exc_info=True)
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/api/marcas-conhecidas', methods=['GET'])
def api_marcas_conhecidas():
    """
    Retorna a lista de marcas na base local.
    Útil para debug e consulta rápida.
    """
    marcas = {}
    for nome, info in MARCAS_CONHECIDAS.items():
        if info.get('titular'):
            marcas[nome] = {
                'titular': info['titular'],
                'classes': info.get('classes', []),
                'tipo': info.get('tipo', ''),
            }
    return jsonify({
        'total': len(marcas),
        'marcas': marcas,
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check."""
    return jsonify({
        'status': 'ok',
        'versao': '1.0.0',
        'timestamp': datetime.now().isoformat(),
    })


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    import sys
    import io
    # Fix Windows console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print()
    print("=" * 60)
    print("  VERIFICADOR DE MARCAS MARKETPLACE")
    print("  Sistema de Verificacao de Marcas Registradas")
    print("=" * 60)
    print()
    print("  Acesse: http://localhost:5000")
    print("  API:    http://localhost:5000/api/health")
    print()
    print("  Pressione Ctrl+C para parar o servidor")
    print("=" * 60)
    print()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
    )
