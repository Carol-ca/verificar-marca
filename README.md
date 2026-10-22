# 🔍 Verificador de Marcas Marketplace

Sistema completo de verificação de marcas registradas para uso em marketplaces brasileiros (Mercado Livre, Shopee, Amazon, etc).

## 📋 Funcionalidades

- **🔗 Verificação por Link** — Cole o link do anúncio e o sistema extrai título, descrição e termos automaticamente
- **📸 Verificação por Imagem** — Envie print/foto do anúncio e o OCR lê todo o texto
- **✍️ Verificação por Texto** — Cole título e descrição diretamente
- **🇧🇷 Consulta INPI** — Pesquisa na base oficial do Instituto Nacional da Propriedade Industrial
- **🌐 Pesquisa Google** — Confirma titularidade e existência de marcas
- **📊 Classificação Clara** — Resultado com ✅ Pode, ⚠️ Atenção ou ❌ Não Pode

## 🚀 Instalação

### 1. Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 2. (Opcional) Instalar Tesseract OCR para leitura de imagens
- Baixe em: https://github.com/UB-Mannheim/tesseract/wiki
- Instale e adicione ao PATH do sistema
- Ou defina o caminho no sistema

### 3. Executar o sistema
```bash
python app.py
```

### 4. Acessar no navegador
Abra: http://localhost:5000

## 📖 Como Usar

1. Acesse http://localhost:5000 no navegador
2. Escolha o modo de entrada (Link, Imagem ou Texto)
3. Insira os dados do anúncio
4. Clique em "Verificar Marcas"
5. Aguarde o resultado da análise

## ⚖️ Aviso Legal

Esta ferramenta é apoio prévio para análise de marcas registradas.
Não substitui consulta jurídica ou advogado de propriedade intelectual.

## 🛠️ Tecnologias

- Python 3.11+
- Flask (servidor web)
- BeautifulSoup4 (web scraping)
- Tesseract OCR (leitura de imagens)
- API INPI (consulta de marcas)
- Google Search (verificação complementar)
