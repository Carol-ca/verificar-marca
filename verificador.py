"""
============================================
VERIFICADOR DE MARCAS MARKETPLACE
Motor de Verificação de Marcas Registradas
============================================

Módulo principal de verificação que:
1. Extrai termos de textos, links e imagens
2. Consulta a base do INPI (busca.inpi.gov.br)
3. Pesquisa no Google por titularidade
4. Classifica risco de uso em marketplaces
"""

import re
import time
import json
import logging
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

import requests
from bs4 import BeautifulSoup

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================================

# User-Agent para requisições web
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Palavras comuns que NÃO são marcas (filtro de stopwords em PT-BR)
STOPWORDS_PT = {
    'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
    'um', 'uma', 'uns', 'umas', 'o', 'a', 'os', 'as', 'e', 'ou',
    'para', 'por', 'com', 'sem', 'sob', 'sobre', 'entre', 'até',
    'que', 'se', 'como', 'mais', 'menos', 'muito', 'pouco',
    'novo', 'nova', 'novos', 'novas', 'usado', 'usada',
    'grande', 'pequeno', 'pequena', 'médio', 'média',
    'kit', 'pcs', 'peças', 'unidades', 'und', 'par', 'pares',
    'preto', 'branco', 'azul', 'vermelho', 'verde', 'amarelo',
    'rosa', 'roxo', 'cinza', 'marrom', 'bege', 'dourado', 'prata',
    'tamanho', 'tam', 'cor', 'modelo', 'tipo', 'estilo',
    'p', 'm', 'g', 'gg', 'xg', 'pp', 'eg',
    'original', 'importado', 'importada', 'nacional',
    'frete', 'grátis', 'gratis', 'envio', 'entrega', 'rápido', 'rápida',
    'promoção', 'oferta', 'desconto', 'barato', 'barata', 'preço', 'preco',
    'produto', 'item', 'artigo', 'peça', 'acessório', 'acessorios',
    'masculino', 'feminino', 'infantil', 'adulto', 'unissex',
    'alta', 'qualidade', 'premium', 'luxo', 'top', 'melhor', 'super',
    'resistente', 'durável', 'prático', 'prática', 'leve', 'forte',
    'br', 'brasil', 'brasileiro', 'brasileira',
    'mm', 'cm', 'kg', 'ml', 'litro', 'litros', 'metros', 'metro',
    'caixa', 'pacote', 'embalagem', 'saco', 'sachê',
    'compatível', 'compativel', 'similar', 'genérico', 'generico',
    'universal', 'portátil', 'portatil', 'recarregável', 'recarregavel',
    'veja', 'confira', 'aproveite', 'compre', 'loja', 'vendedor',
    'estoque', 'disponível', 'disponivel', 'pronta', 'imediata',
    'ano', 'anos', 'dia', 'dias', 'mês', 'meses', 'hora', 'horas',
    'garantia', 'nota', 'fiscal', 'nf',
    'está', 'esta', 'esse', 'essa', 'isso', 'este',
    'seu', 'sua', 'seus', 'suas', 'meu', 'minha', 'nosso', 'nossa',
    'todos', 'todas', 'cada', 'qual', 'quais', 'onde',
    'tem', 'ser', 'ter', 'está', 'são', 'foi', 'pode', 'vai',
    'aqui', 'ali', 'lá', 'já', 'ainda', 'também', 'só', 'apenas',
    'não', 'nao', 'sim', 'bem', 'bom', 'boa', 'ótimo', 'otimo',
    'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez',
}

# Termos genéricos de produto que não são marcas
TERMOS_GENERICOS = {
    'camiseta', 'camisa', 'calça', 'bermuda', 'short', 'shorts',
    'vestido', 'saia', 'blusa', 'regata', 'moletom', 'jaqueta',
    'casaco', 'sobretudo', 'colete', 'suéter', 'sueter', 'cardigan',
    'tênis', 'tenis', 'sapato', 'sandália', 'sandalia', 'chinelo',
    'bota', 'sapatilha', 'mocassim', 'rasteirinha',
    'bolsa', 'mochila', 'carteira', 'pochete', 'necessaire',
    'relógio', 'relogio', 'óculos', 'oculos', 'cinto', 'pulseira',
    'colar', 'brinco', 'anel', 'corrente', 'pingente',
    'celular', 'smartphone', 'tablet', 'notebook', 'computador',
    'fone', 'fones', 'caixa de som', 'carregador', 'cabo', 'película',
    'pelicula', 'capinha', 'case', 'capa', 'protetor',
    'panela', 'frigideira', 'forma', 'assadeira', 'travessa',
    'copo', 'garrafa', 'caneca', 'prato', 'talher', 'talheres',
    'cadeira', 'mesa', 'sofá', 'sofa', 'cama', 'colchão', 'colchao',
    'travesseiro', 'coberta', 'edredom', 'lençol', 'lencol',
    'shampoo', 'condicionador', 'creme', 'perfume', 'desodorante',
    'batom', 'base', 'rímel', 'rimel', 'sombra', 'blush',
    'brinquedo', 'boneca', 'boneco', 'jogo', 'quebra-cabeça',
    'ferramenta', 'chave', 'alicate', 'martelo', 'furadeira',
    'lâmpada', 'lampada', 'interruptor', 'tomada', 'extensão',
    'pneu', 'óleo', 'oleo', 'filtro', 'pastilha', 'amortecedor',
    'ração', 'racao', 'coleira', 'brinquedo', 'casinha', 'cama pet',
}

# Base de marcas conhecidas no Brasil (expandida)
MARCAS_CONHECIDAS = {
    # Tecnologia
    'apple': {'titular': 'Apple Inc.', 'classes': ['9', '42'], 'tipo': 'Tecnologia'},
    'iphone': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Smartphone'},
    'ipad': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Tablet'},
    'macbook': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'airpods': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Áudio'},
    'samsung': {'titular': 'Samsung Electronics', 'classes': ['9', '11'], 'tipo': 'Tecnologia'},
    'galaxy': {'titular': 'Samsung Electronics', 'classes': ['9'], 'tipo': 'Smartphone'},
    'xiaomi': {'titular': 'Xiaomi Inc.', 'classes': ['9'], 'tipo': 'Tecnologia'},
    'redmi': {'titular': 'Xiaomi Inc.', 'classes': ['9'], 'tipo': 'Smartphone'},
    'motorola': {'titular': 'Motorola Trademark Holdings', 'classes': ['9'], 'tipo': 'Tecnologia'},
    'moto': {'titular': 'Motorola Trademark Holdings', 'classes': ['9'], 'tipo': 'Smartphone'},
    'lg': {'titular': 'LG Electronics', 'classes': ['9', '11'], 'tipo': 'Tecnologia'},
    'sony': {'titular': 'Sony Corporation', 'classes': ['9'], 'tipo': 'Tecnologia'},
    'playstation': {'titular': 'Sony Interactive Entertainment', 'classes': ['9', '28'], 'tipo': 'Games'},
    'nintendo': {'titular': 'Nintendo Co.', 'classes': ['9', '28'], 'tipo': 'Games'},
    'xbox': {'titular': 'Microsoft Corporation', 'classes': ['9', '28'], 'tipo': 'Games'},
    'microsoft': {'titular': 'Microsoft Corporation', 'classes': ['9', '42'], 'tipo': 'Tecnologia'},
    'dell': {'titular': 'Dell Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'hp': {'titular': 'HP Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'lenovo': {'titular': 'Lenovo Group Ltd.', 'classes': ['9'], 'tipo': 'Computador'},
    'asus': {'titular': 'ASUSTeK Computer', 'classes': ['9'], 'tipo': 'Computador'},
    'acer': {'titular': 'Acer Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'google': {'titular': 'Google LLC', 'classes': ['9', '42'], 'tipo': 'Tecnologia'},
    'huawei': {'titular': 'Huawei Technologies', 'classes': ['9'], 'tipo': 'Tecnologia'},
    'oppo': {'titular': 'Guangdong OPPO', 'classes': ['9'], 'tipo': 'Smartphone'},
    'realme': {'titular': 'Realme Mobile', 'classes': ['9'], 'tipo': 'Smartphone'},
    'jbl': {'titular': 'Harman International', 'classes': ['9'], 'tipo': 'Áudio'},
    'bose': {'titular': 'Bose Corporation', 'classes': ['9'], 'tipo': 'Áudio'},
    'beats': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Áudio'},
    'gopro': {'titular': 'GoPro Inc.', 'classes': ['9'], 'tipo': 'Câmera'},
    'kindle': {'titular': 'Amazon Technologies', 'classes': ['9'], 'tipo': 'E-reader'},
    'alexa': {'titular': 'Amazon Technologies', 'classes': ['9'], 'tipo': 'Assistente Virtual'},
    'echo': {'titular': 'Amazon Technologies', 'classes': ['9'], 'tipo': 'Smart Speaker'},

    # Moda e Vestuário
    'nike': {'titular': 'Nike Inc.', 'classes': ['25', '18'], 'tipo': 'Moda/Esporte'},
    'adidas': {'titular': 'adidas AG', 'classes': ['25', '18'], 'tipo': 'Moda/Esporte'},
    'puma': {'titular': 'Puma SE', 'classes': ['25', '18'], 'tipo': 'Moda/Esporte'},
    'reebok': {'titular': 'Reebok International', 'classes': ['25'], 'tipo': 'Moda/Esporte'},
    'new balance': {'titular': 'New Balance Athletics', 'classes': ['25'], 'tipo': 'Calçados'},
    'asics': {'titular': 'ASICS Corporation', 'classes': ['25'], 'tipo': 'Calçados'},
    'mizuno': {'titular': 'Mizuno Corporation', 'classes': ['25', '28'], 'tipo': 'Esporte'},
    'fila': {'titular': 'Fila Holdings', 'classes': ['25'], 'tipo': 'Moda/Esporte'},
    'vans': {'titular': 'VF Corporation', 'classes': ['25'], 'tipo': 'Calçados'},
    'converse': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados'},
    'all star': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados'},

    # Sub-marcas Nike
    'air max': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'air force': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'air jordan': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'jordan': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'dunk': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'nike dunk': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'cortez': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'blazer': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'huarache': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'vapormax': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'flyknit': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Tecnologia têxtil'},
    'dri-fit': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Tecnologia têxtil'},
    'just do it': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Slogan registrado'},
    'swoosh': {'titular': 'Nike Inc.', 'classes': ['25'], 'tipo': 'Logo registrado'},

    # Sub-marcas Adidas
    'ultraboost': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'ultra boost': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'superstar': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'stan smith': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'yeezy': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'nmd': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'gazelle': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'samba': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'forum': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Calçados (linha)'},
    'boost': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Tecnologia (entressola)'},
    'primeknit': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Tecnologia têxtil'},
    'three stripes': {'titular': 'adidas AG', 'classes': ['25'], 'tipo': 'Design registrado'},

    # Sub-marcas Samsung
    'galaxy s': {'titular': 'Samsung Electronics', 'classes': ['9'], 'tipo': 'Smartphone (linha)'},
    'galaxy note': {'titular': 'Samsung Electronics', 'classes': ['9'], 'tipo': 'Smartphone (linha)'},
    'galaxy buds': {'titular': 'Samsung Electronics', 'classes': ['9'], 'tipo': 'Áudio (linha)'},
    'galaxy watch': {'titular': 'Samsung Electronics', 'classes': ['9'], 'tipo': 'Wearable (linha)'},

    # Sub-marcas Apple
    'apple watch': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Wearable (linha)'},
    'magic mouse': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Acessório (linha)'},
    'magsafe': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Tecnologia carregamento'},
    'airtag': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Rastreador'},
    'imac': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'mac mini': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'mac pro': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Computador'},
    'siri': {'titular': 'Apple Inc.', 'classes': ['9'], 'tipo': 'Assistente Virtual'},

    # Marcas de Luxo adicionais
    'balenciaga': {'titular': 'Balenciaga S.A.', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'burberry': {'titular': 'Burberry Limited', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'fendi': {'titular': 'Fendi S.r.l.', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'hermes': {'titular': 'Hermès International', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'dolce gabbana': {'titular': 'Dolce & Gabbana S.r.l.', 'classes': ['25', '3'], 'tipo': 'Luxo'},
    'armani': {'titular': 'Giorgio Armani S.p.A.', 'classes': ['25', '3'], 'tipo': 'Luxo'},
    'michael kors': {'titular': 'Michael Kors LLC', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'coach': {'titular': 'Coach IP Holdings', 'classes': ['18'], 'tipo': 'Luxo'},
    'tiffany': {'titular': 'Tiffany & Co.', 'classes': ['14'], 'tipo': 'Joias'},
    'pandora': {'titular': 'Pandora A/S', 'classes': ['14'], 'tipo': 'Joias'},
    'rolex': {'titular': 'Rolex S.A.', 'classes': ['14'], 'tipo': 'Relógios'},
    'casio': {'titular': 'Casio Computer Co.', 'classes': ['9', '14'], 'tipo': 'Relógios/Eletrônicos'},
    'ray-ban': {'titular': 'Luxottica Group', 'classes': ['9'], 'tipo': 'Óculos'},
    'oakley': {'titular': 'Oakley Inc.', 'classes': ['9'], 'tipo': 'Óculos'},
    'gucci': {'titular': 'Gucci Group', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'louis vuitton': {'titular': 'Louis Vuitton Malletier', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'chanel': {'titular': 'Chanel S.A.', 'classes': ['3', '25'], 'tipo': 'Luxo'},
    'prada': {'titular': 'Prada S.p.A.', 'classes': ['18', '25'], 'tipo': 'Luxo'},
    'dior': {'titular': 'Christian Dior', 'classes': ['3', '25'], 'tipo': 'Luxo'},
    'versace': {'titular': 'Gianni Versace S.r.l.', 'classes': ['25'], 'tipo': 'Luxo'},
    'lacoste': {'titular': 'Lacoste S.A.', 'classes': ['25'], 'tipo': 'Moda'},
    'polo ralph lauren': {'titular': 'PRL USA Holdings', 'classes': ['25'], 'tipo': 'Moda'},
    'ralph lauren': {'titular': 'PRL USA Holdings', 'classes': ['25'], 'tipo': 'Moda'},
    'tommy hilfiger': {'titular': 'Tommy Hilfiger Licensing', 'classes': ['25'], 'tipo': 'Moda'},
    'calvin klein': {'titular': 'Calvin Klein Trademark Trust', 'classes': ['25', '3'], 'tipo': 'Moda'},
    'levis': {'titular': "Levi Strauss & Co.", 'classes': ['25'], 'tipo': 'Jeans'},
    "levi's": {'titular': "Levi Strauss & Co.", 'classes': ['25'], 'tipo': 'Jeans'},
    'zara': {'titular': 'Industria de Diseño Textil (Inditex)', 'classes': ['25'], 'tipo': 'Moda'},
    'h&m': {'titular': 'H&M Hennes & Mauritz', 'classes': ['25'], 'tipo': 'Moda'},
    'forever 21': {'titular': 'Forever 21 Inc.', 'classes': ['25'], 'tipo': 'Moda'},
    'havaianas': {'titular': 'Alpargatas S.A.', 'classes': ['25'], 'tipo': 'Calçados'},
    'olympikus': {'titular': 'Vulcabras Azaleia', 'classes': ['25'], 'tipo': 'Calçados'},
    'osklen': {'titular': 'Osklen e-commerce', 'classes': ['25'], 'tipo': 'Moda'},
    'farm': {'titular': 'Grupo Soma', 'classes': ['25'], 'tipo': 'Moda'},
    'animale': {'titular': 'Grupo Soma', 'classes': ['25'], 'tipo': 'Moda'},
    'reserva': {'titular': 'Reserva (AR&CO)', 'classes': ['25'], 'tipo': 'Moda'},
    'hering': {'titular': 'Cia. Hering', 'classes': ['25'], 'tipo': 'Moda'},
    'riachuelo': {'titular': 'Guararapes Confecções', 'classes': ['25', '35'], 'tipo': 'Varejo/Moda'},
    'renner': {'titular': 'Lojas Renner S.A.', 'classes': ['25', '35'], 'tipo': 'Varejo/Moda'},

    # Cosméticos e Beleza
    'natura': {'titular': 'Natura Cosméticos S.A.', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'boticário': {'titular': 'O Boticário (Grupo Boticário)', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'o boticario': {'titular': 'O Boticário (Grupo Boticário)', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'avon': {'titular': 'Avon Products', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'maybelline': {'titular': "L'Oréal", 'classes': ['3'], 'tipo': 'Cosméticos'},
    'loreal': {'titular': "L'Oréal S.A.", 'classes': ['3'], 'tipo': 'Cosméticos'},
    "l'oreal": {'titular': "L'Oréal S.A.", 'classes': ['3'], 'tipo': 'Cosméticos'},
    'mac': {'titular': 'MAC Cosmetics (Estée Lauder)', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'eudora': {'titular': 'Grupo Boticário', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'vult': {'titular': 'Vult Cosmética', 'classes': ['3'], 'tipo': 'Cosméticos'},
    'ruby rose': {'titular': 'Ruby Rose Cosméticos', 'classes': ['3'], 'tipo': 'Cosméticos'},

    # Alimentos e Bebidas
    'coca-cola': {'titular': 'The Coca-Cola Company', 'classes': ['32'], 'tipo': 'Bebida'},
    'coca cola': {'titular': 'The Coca-Cola Company', 'classes': ['32'], 'tipo': 'Bebida'},
    'pepsi': {'titular': 'PepsiCo Inc.', 'classes': ['32'], 'tipo': 'Bebida'},
    'nestlé': {'titular': 'Nestlé S.A.', 'classes': ['29', '30'], 'tipo': 'Alimentos'},
    'nestle': {'titular': 'Nestlé S.A.', 'classes': ['29', '30'], 'tipo': 'Alimentos'},
    'nescafe': {'titular': 'Nestlé S.A.', 'classes': ['30'], 'tipo': 'Café'},
    'nescafé': {'titular': 'Nestlé S.A.', 'classes': ['30'], 'tipo': 'Café'},
    'red bull': {'titular': 'Red Bull GmbH', 'classes': ['32'], 'tipo': 'Bebida'},
    'ambev': {'titular': 'Ambev S.A.', 'classes': ['32'], 'tipo': 'Bebida'},
    'skol': {'titular': 'Ambev S.A.', 'classes': ['32'], 'tipo': 'Cerveja'},
    'brahma': {'titular': 'Ambev S.A.', 'classes': ['32'], 'tipo': 'Cerveja'},
    'heineken': {'titular': 'Heineken Brouwerijen', 'classes': ['32'], 'tipo': 'Cerveja'},

    # Automotivo
    'toyota': {'titular': 'Toyota Motor Corporation', 'classes': ['12'], 'tipo': 'Automotivo'},
    'honda': {'titular': 'Honda Motor Co.', 'classes': ['12'], 'tipo': 'Automotivo'},
    'volkswagen': {'titular': 'Volkswagen AG', 'classes': ['12'], 'tipo': 'Automotivo'},
    'chevrolet': {'titular': 'General Motors', 'classes': ['12'], 'tipo': 'Automotivo'},
    'fiat': {'titular': 'FCA Italy S.p.A.', 'classes': ['12'], 'tipo': 'Automotivo'},
    'ford': {'titular': 'Ford Motor Company', 'classes': ['12'], 'tipo': 'Automotivo'},
    'hyundai': {'titular': 'Hyundai Motor Company', 'classes': ['12'], 'tipo': 'Automotivo'},
    'bmw': {'titular': 'Bayerische Motoren Werke AG', 'classes': ['12'], 'tipo': 'Automotivo'},
    'mercedes': {'titular': 'Mercedes-Benz Group AG', 'classes': ['12'], 'tipo': 'Automotivo'},
    'yamaha': {'titular': 'Yamaha Motor Co.', 'classes': ['12', '15'], 'tipo': 'Motos/Música'},

    # Eletrodomésticos
    'brastemp': {'titular': 'Whirlpool S.A.', 'classes': ['7', '11'], 'tipo': 'Eletrodomésticos'},
    'consul': {'titular': 'Whirlpool S.A.', 'classes': ['11'], 'tipo': 'Eletrodomésticos'},
    'electrolux': {'titular': 'AB Electrolux', 'classes': ['7', '11'], 'tipo': 'Eletrodomésticos'},
    'philco': {'titular': 'Britânia Eletrodomésticos', 'classes': ['9', '11'], 'tipo': 'Eletrodomésticos'},
    'mondial': {'titular': 'Mondial Eletrodomésticos', 'classes': ['7', '11'], 'tipo': 'Eletrodomésticos'},
    'arno': {'titular': 'Groupe SEB', 'classes': ['7', '11'], 'tipo': 'Eletrodomésticos'},
    'tramontina': {'titular': 'Tramontina S.A.', 'classes': ['8', '21'], 'tipo': 'Utensílios'},
    'wap': {'titular': 'WAP Indústria', 'classes': ['7'], 'tipo': 'Lavadoras'},

    # Marketplace / Varejo
    'mercado livre': {'titular': 'MercadoLibre S.R.L.', 'classes': ['35', '36'], 'tipo': 'Marketplace'},
    'shopee': {'titular': 'Shopee Singapore', 'classes': ['35'], 'tipo': 'Marketplace'},
    'amazon': {'titular': 'Amazon Technologies', 'classes': ['35'], 'tipo': 'Marketplace'},
    'magalu': {'titular': 'Magazine Luiza S.A.', 'classes': ['35'], 'tipo': 'Varejo'},
    'magazine luiza': {'titular': 'Magazine Luiza S.A.', 'classes': ['35'], 'tipo': 'Varejo'},
    'casas bahia': {'titular': 'Via Varejo S.A.', 'classes': ['35'], 'tipo': 'Varejo'},
    'americanas': {'titular': 'Americanas S.A.', 'classes': ['35'], 'tipo': 'Varejo'},
    'kabum': {'titular': 'Magazine Luiza S.A.', 'classes': ['35'], 'tipo': 'Varejo Tech'},
    'shein': {'titular': 'Roadget Business Pte.', 'classes': ['25', '35'], 'tipo': 'Moda Online'},

    # Ferramentas e Construção
    'makita': {'titular': 'Makita Corporation', 'classes': ['7'], 'tipo': 'Ferramentas'},
    'bosch': {'titular': 'Robert Bosch GmbH', 'classes': ['7', '9'], 'tipo': 'Ferramentas/Tech'},
    'dewalt': {'titular': 'Stanley Black & Decker', 'classes': ['7'], 'tipo': 'Ferramentas'},
    'black+decker': {'titular': 'Stanley Black & Decker', 'classes': ['7'], 'tipo': 'Ferramentas'},
    'stanley': {'titular': 'Stanley Black & Decker', 'classes': ['8'], 'tipo': 'Ferramentas'},

    # Brinquedos, Games e Entretenimento / Personagens (Direitos Autorais e Marcas)
    'lego': {'titular': 'LEGO Juris A/S', 'classes': ['28'], 'tipo': 'Brinquedos'},
    'barbie': {'titular': 'Mattel Inc.', 'classes': ['28'], 'tipo': 'Brinquedos'},
    'hot wheels': {'titular': 'Mattel Inc.', 'classes': ['28'], 'tipo': 'Brinquedos'},
    'nerf': {'titular': 'Hasbro Inc.', 'classes': ['28'], 'tipo': 'Brinquedos'},
    'looney tunes': {'titular': 'Warner Bros. Entertainment Inc.', 'classes': ['9', '16', '25', '28', '41'], 'tipo': 'Franquia / Personagens'},
    'tunes': {'titular': 'Warner Bros. Entertainment Inc.', 'classes': ['25'], 'tipo': 'Franquia / Personagens'},
    'disney': {'titular': 'Disney Enterprises, Inc.', 'classes': ['9', '16', '25', '28', '41'], 'tipo': 'Franquia / Entretenimento'},
    'mickey': {'titular': 'Disney Enterprises, Inc.', 'classes': ['25', '28'], 'tipo': 'Personagem / Marca'},
    'mickey mouse': {'titular': 'Disney Enterprises, Inc.', 'classes': ['25', '28'], 'tipo': 'Personagem / Marca'},
    'marvel': {'titular': 'Marvel Characters, Inc.', 'classes': ['9', '16', '25', '28', '41'], 'tipo': 'Franquia / Quadrinhos'},
    'dc comics': {'titular': 'DC Comics', 'classes': ['9', '16', '25', '28'], 'tipo': 'Franquia / Quadrinhos'},
    'batman': {'titular': 'DC Comics', 'classes': ['25', '28'], 'tipo': 'Personagem / Marca'},
    'spider-man': {'titular': 'Marvel Characters, Inc.', 'classes': ['25', '28'], 'tipo': 'Personagem / Marca'},
    'homem-aranha': {'titular': 'Marvel Characters, Inc.', 'classes': ['25', '28'], 'tipo': 'Personagem / Marca'},
    'pokemon': {'titular': 'Nintendo / The Pokémon Company', 'classes': ['9', '25', '28'], 'tipo': 'Franquia / Games'},
    'pokémon': {'titular': 'Nintendo / The Pokémon Company', 'classes': ['9', '25', '28'], 'tipo': 'Franquia / Games'},
    'dragon ball': {'titular': 'Bird Studio / Shueisha / Toei Animation', 'classes': ['25', '28'], 'tipo': 'Anime / Franquia'},
    'naruto': {'titular': 'Masashi Kishimoto / Shueisha', 'classes': ['25', '28'], 'tipo': 'Anime / Franquia'},
    'one piece': {'titular': 'Eiichiro Oda / Shueisha', 'classes': ['25', '28'], 'tipo': 'Anime / Franquia'},
    'star wars': {'titular': 'Lucasfilm Ltd.', 'classes': ['9', '25', '28'], 'tipo': 'Franquia / Cinema'},
    'harry potter': {'titular': 'Warner Bros. Entertainment Inc.', 'classes': ['9', '16', '25', '28'], 'tipo': 'Franquia / Cinema'},

    # Fitness e Suplementos
    'growth': {'titular': 'Growth Supplements', 'classes': ['5', '29'], 'tipo': 'Suplementos'},
    'integralmedica': {'titular': 'Integralmédica', 'classes': ['5', '29'], 'tipo': 'Suplementos'},
    'max titanium': {'titular': 'Max Titanium', 'classes': ['5'], 'tipo': 'Suplementos'},
    'optimum nutrition': {'titular': 'Glanbia Performance Nutrition', 'classes': ['5', '29'], 'tipo': 'Suplementos'},
    'whey protein': {'titular': None, 'classes': [], 'tipo': 'Termo genérico'},
    'creatina': {'titular': None, 'classes': [], 'tipo': 'Termo genérico'},
}


# ============================================================
# ENUMS E DATACLASSES
# ============================================================

class StatusRisco(Enum):
    """Status de risco para uso de uma marca."""
    PODE_ANUNCIAR = "pode_anunciar"       # ✅ Sem marcas encontradas
    ATENCAO = "atencao"                    # ⚠️ Semelhança ou dúvida
    NAO_PODE = "nao_pode"                 # ❌ Marca protegida


@dataclass
class ResultadoTermo:
    """Resultado da verificação de um termo específico."""
    termo: str
    status: str  # 'pode_anunciar', 'atencao', 'nao_pode'
    motivo: str
    titular: Optional[str] = None
    classe: Optional[str] = None
    tipo: Optional[str] = None
    fonte: Optional[str] = None
    inpi_encontrado: bool = False
    google_encontrado: bool = False
    detalhes_inpi: Optional[str] = None
    detalhes_google: Optional[str] = None


@dataclass
class ResultadoVerificacao:
    """Resultado completo de uma verificação de anúncio."""
    status_geral: str  # O pior status entre todos os termos
    termos_extraidos: list = field(default_factory=list)
    resultados: list = field(default_factory=list)
    texto_original: str = ""
    timestamp: str = ""
    dados_anuncio: Optional[dict] = None

    def to_dict(self):
        return {
            'status_geral': self.status_geral,
            'termos_extraidos': self.termos_extraidos,
            'resultados': [asdict(r) if isinstance(r, ResultadoTermo) else r for r in self.resultados],
            'texto_original': self.texto_original[:500],
            'timestamp': self.timestamp,
            'dados_anuncio': self.dados_anuncio,
        }


# ============================================================
# EXTRAÇÃO DE TERMOS
# ============================================================

def extrair_termos(texto: str) -> list:
    """
    Extrai termos potenciais de marca de um texto.
    Remove stopwords, termos genéricos e palavras muito curtas.
    """
    if not texto:
        return []

    # Normalizar texto
    texto_limpo = texto.strip()

    # Extrair termos entre aspas (geralmente são marcas)
    termos_aspas = re.findall(r'["\']([^"\']+)["\']', texto_limpo)

    # Extrair palavras capitalizadas (possíveis nomes de marca)
    palavras_caps = re.findall(r'\b([A-Z][a-zA-Z]{2,})\b', texto_limpo)

    # Extrair todas as palavras
    todas_palavras = re.findall(r'\b([a-zA-ZÀ-ÿ]{3,})\b', texto_limpo)

    # Extrair termos compostos (2 palavras maiúsculas seguidas)
    termos_compostos = re.findall(r'\b([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\b', texto_limpo)

    # Combinar todos os termos encontrados
    candidatos = set()

    # Termos entre aspas são prioridade
    for t in termos_aspas:
        candidatos.add(t.strip().lower())

    # Palavras capitalizadas
    for p in palavras_caps:
        candidatos.add(p.lower())

    # Termos compostos
    for t in termos_compostos:
        candidatos.add(t.lower())

    # Todas as palavras (para verificar contra banco de marcas)
    for p in todas_palavras:
        p_lower = p.lower()
        if p_lower in MARCAS_CONHECIDAS:
            candidatos.add(p_lower)

    # Verificar combinações de 2-3 palavras contra marcas conhecidas
    palavras_lista = texto_limpo.lower().split()
    for i in range(len(palavras_lista)):
        for j in range(i + 1, min(i + 4, len(palavras_lista) + 1)):
            combo = ' '.join(palavras_lista[i:j])
            combo_clean = re.sub(r'[^\w\s]', '', combo).strip()
            if combo_clean in MARCAS_CONHECIDAS:
                candidatos.add(combo_clean)

    # Filtrar stopwords e termos genéricos
    termos_filtrados = []
    for termo in candidatos:
        termo_limpo = termo.strip().lower()

        # Pular se é stopword
        if termo_limpo in STOPWORDS_PT:
            continue

        # Pular se é termo genérico de produto
        if termo_limpo in TERMOS_GENERICOS:
            continue

        # Pular se é muito curto (menos de 2 caracteres)
        if len(termo_limpo) < 2:
            continue

        # Pular se é só números
        if termo_limpo.replace(' ', '').isdigit():
            continue

        termos_filtrados.append(termo_limpo)

    # Remover duplicatas mantendo ordem
    vistos = set()
    resultado = []
    for t in termos_filtrados:
        if t not in vistos:
            vistos.add(t)
            resultado.append(t)

    return resultado


# ============================================================
# SCRAPING DE ANÚNCIOS
# ============================================================

def extrair_conteudo_url(url: str) -> dict:
    """
    Acessa a URL do anúncio e foca EXCLUSIVAMENTE no produto:
    - Título do anúncio
    - Descrição real do produto
    - Foto/Imagem principal do anúncio (com OCR para ler texto na imagem)
    - Ignora cabeçalhos, rodapés, menus, termos de uso e ruído do marketplace.
    """
    resultado = {
        'titulo': '',
        'descricao': '',
        'texto_completo': '',
        'imagem_url': '',
        'texto_imagem_ocr': '',
        'sucesso': False,
        'erro': None,
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'lxml')

        # Remover ruído geral da página
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header', 'svg']):
            tag.decompose()

        # 1. TÍTULO DO PRODUTO (Cirúrgico por marketplace)
        titulo = ""
        # Mercado Livre
        ml_titulo = soup.find('h1', class_='ui-pdp-title')
        # Shopee
        shopee_titulo = soup.find('div', class_='fAInvO') or soup.find('h1')
        # Amazon
        amz_titulo = soup.find('span', id='productTitle')
        # Genéricos
        og_titulo = soup.find('meta', property='og:title')

        if ml_titulo:
            titulo = ml_titulo.get_text(strip=True)
        elif amz_titulo:
            titulo = amz_titulo.get_text(strip=True)
        elif shopee_titulo:
            titulo = shopee_titulo.get_text(strip=True)
        elif og_titulo and og_titulo.get('content') and 'Loja de Moda Online' not in og_titulo.get('content'):
            titulo = og_titulo['content'].strip()
        else:
            t = soup.find('h1') or soup.find('title')
            titulo = t.get_text(strip=True) if t else ''

        # Fallback inteligente: se o título for genérico de loja (comum em SPAs como Shein/AliExpress renderizados por JS), extrair slug do produto da própria URL!
        if not titulo or any(g in titulo.lower() for g in ['loja de moda online', 'comprar online', 'marketplace', 'frete grátis']):
            import urllib.parse
            path = urllib.parse.urlparse(url).path
            slug = path.split('/')[-1]
            slug = re.sub(r'\.html?$', '', slug, flags=re.IGNORECASE)
            slug = re.sub(r'-p-\d+$', '', slug, flags=re.IGNORECASE)
            slug = re.sub(r'[-_]', ' ', slug).strip()
            if slug:
                titulo = slug

        # Limpar sufixos comuns como " | Mercado Livre", " | Shopee Brasil", " | SHEIN"
        titulo = re.sub(r'\s*\|\s*(Mercado\s*Livre|Shopee|Amazon|OLX|Magalu|SHEIN).*$', '', titulo, flags=re.IGNORECASE)
        resultado['titulo'] = titulo

        # 2. DESCRIÇÃO DO PRODUTO (Apenas o miolo do produto)
        descricao = ""
        # Mercado Livre
        ml_desc = soup.find('div', class_='ui-pdp-description__content') or soup.find('p', class_='ui-pdp-description__content')
        # Shopee
        shopee_desc = soup.find('div', class_='product-detail') or soup.find('div', class_='_3e7-QW')
        # Amazon
        amz_desc = soup.find('div', id='productDescription') or soup.find('div', id='feature-bullets')
        # Meta description
        og_desc = soup.find('meta', property='og:description') or soup.find('meta', {'name': 'description'})

        if ml_desc:
            descricao = ml_desc.get_text(separator=' ', strip=True)
        elif amz_desc:
            descricao = amz_desc.get_text(separator=' ', strip=True)
        elif shopee_desc:
            descricao = shopee_desc.get_text(separator=' ', strip=True)
        elif og_desc and og_desc.get('content'):
            descricao = og_desc['content'].strip()

        resultado['descricao'] = descricao

        # 3. IMAGEM DO ANÚNCIO (Foto principal para ler etiquetas/estampas)
        img_url = ""
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            img_url = og_img['content']
        else:
            ml_img = soup.find('img', class_='ui-pdp-image') or soup.find('img', class_='ui-pdp-gallery__figure__image')
            if ml_img and ml_img.get('src'):
                img_url = ml_img['src']

        resultado['imagem_url'] = img_url

        # Tentar ler texto da imagem via OCR se houver URL válida
        if img_url and (img_url.startswith('http://') or img_url.startswith('https://')):
            try:
                import io
                from PIL import Image
                import pytesseract
                img_resp = requests.get(img_url, headers=HEADERS, timeout=8)
                if img_resp.status_code == 200:
                    img = Image.open(io.BytesIO(img_resp.content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    ocr_text = pytesseract.image_to_string(img, lang='por').strip()
                    if not ocr_text:
                        ocr_text = pytesseract.image_to_string(img).strip()
                    resultado['texto_imagem_ocr'] = ocr_text
            except Exception as ocr_err:
                logger.debug(f"OCR na imagem do link ignorado ou falhou: {ocr_err}")

        # Montar texto focado estritamente no anúncio (ignora o resto da página!)
        partes = []
        if resultado['titulo']:
            partes.append(resultado['titulo'])
        if resultado['descricao']:
            partes.append(resultado['descricao'])
        if resultado['texto_imagem_ocr']:
            partes.append(f"Texto na foto: {resultado['texto_imagem_ocr']}")

        resultado['texto_completo'] = "\n".join(partes)
        resultado['sucesso'] = True

    except requests.exceptions.RequestException as e:
        resultado['erro'] = f"Erro ao acessar URL: {str(e)}"
        logger.error(f"Erro ao acessar {url}: {e}")

    except Exception as e:
        resultado['erro'] = f"Erro ao processar página: {str(e)}"
        logger.error(f"Erro ao processar {url}: {e}")

    return resultado


# ============================================================
# CONSULTA INPI
# ============================================================

def consultar_inpi(termo: str) -> dict:
    """
    Consulta a base de marcas do INPI (Instituto Nacional da Propriedade Industrial).
    Usa a interface web de busca pública.
    """
    resultado = {
        'encontrado': False,
        'marcas': [],
        'erro': None,
    }

    try:
        # URL de busca do INPI
        url_busca = 'https://busca.inpi.gov.br/pePI/servlet/MarcaServletController'

        # Parâmetros de busca
        params = {
            'Action': 'SearchMarca',
            'CodPedido': '',
            'Ession': '',
            'Marca': termo,
            'NCL': '',
            'Titular': '',
            'Procurador': '',
            'CodDespacho': '',
            'DataDepositoInicio': '',
            'DataDepositoFim': '',
            'DataPublicacaoInicio': '',
            'DataPublicacaoFim': '',
            'Tipo': '',
            'TextoMarca': '',
            'TipoBusca': 'Contem',
        }

        session = requests.Session()
        session.headers.update(HEADERS)

        # Primeira requisição para obter sessão
        resp_init = session.get(
            'https://busca.inpi.gov.br/pePI/servlet/MarcaServletController?Action=InitialSearch',
            timeout=15
        )

        # Busca efetiva
        resp = session.get(url_busca, params=params, timeout=15)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'lxml')

            # Procurar tabela de resultados
            tabela = soup.find('table', {'id': 'tabelaMarca'}) or soup.find('table', class_='resultado')

            if tabela:
                linhas = tabela.find_all('tr')[1:]  # Pular cabeçalho
                for linha in linhas[:5]:  # Máximo 5 resultados
                    colunas = linha.find_all('td')
                    if len(colunas) >= 4:
                        marca_info = {
                            'numero': colunas[0].get_text(strip=True),
                            'marca': colunas[1].get_text(strip=True),
                            'titular': colunas[2].get_text(strip=True) if len(colunas) > 2 else '',
                            'situacao': colunas[3].get_text(strip=True) if len(colunas) > 3 else '',
                            'classe': colunas[4].get_text(strip=True) if len(colunas) > 4 else '',
                        }
                        resultado['marcas'].append(marca_info)
                        resultado['encontrado'] = True
            else:
                # Tentar extrair resultado de texto puro
                texto_pagina = soup.get_text()
                if 'Nenhum resultado' in texto_pagina or 'nenhum registro' in texto_pagina.lower():
                    resultado['encontrado'] = False
                elif termo.lower() in texto_pagina.lower() and 'marca' in texto_pagina.lower():
                    # Possivelmente encontrou algo mas não conseguiu parsear
                    resultado['encontrado'] = True
                    resultado['marcas'].append({
                        'numero': 'N/A',
                        'marca': termo,
                        'titular': 'Verificar no site do INPI',
                        'situacao': 'Resultado encontrado - verificar manualmente',
                        'classe': 'N/A',
                    })

    except requests.exceptions.RequestException as e:
        resultado['erro'] = f"Erro de conexão com INPI: {str(e)}"
        logger.warning(f"Erro ao consultar INPI para '{termo}': {e}")

    except Exception as e:
        resultado['erro'] = f"Erro ao processar resposta INPI: {str(e)}"
        logger.warning(f"Erro ao processar INPI para '{termo}': {e}")

    return resultado


# ============================================================
# PESQUISA GOOGLE
# ============================================================

def pesquisar_google(termo: str) -> dict:
    """
    Pesquisa no Google para confirmar se o termo é uma marca registrada.
    """
    resultado = {
        'e_marca': False,
        'info': '',
        'url_encontrada': '',
        'empresa': '',
        'erro': None,
    }

    queries = [
        f'"{termo}" marca registrada Brasil',
        f'"{termo}" empresa oficial site',
    ]

    try:
        for query in queries:
            try:
                url = f"https://www.google.com/search?q={requests.utils.quote(query)}&hl=pt-BR&num=5"
                resp = requests.get(url, headers=HEADERS, timeout=10)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'lxml')
                    textos = soup.get_text(separator=' ', strip=True).lower()

                    # Verificar se há indícios de marca registrada
                    indicadores_marca = [
                        'marca registrada',
                        'registered trademark',
                        '® ',
                        '™',
                        'propriedade de',
                        'pertence a',
                        'owned by',
                        'marca oficial',
                        'site oficial',
                        'empresa',
                        'ltda',
                        'sa.',
                        's.a.',
                        'inc.',
                        'corp.',
                        'gmbh',
                        'limited',
                    ]

                    for indicador in indicadores_marca:
                        if indicador in textos:
                            resultado['e_marca'] = True
                            resultado['info'] = f'Encontrado indicador: "{indicador}" em resultados de busca'
                            break

                    # Extrair possível empresa dos resultados
                    links = soup.find_all('a')
                    for link in links[:10]:
                        href = link.get('href', '')
                        if termo.lower().replace(' ', '') in href.lower():
                            resultado['url_encontrada'] = href
                            break

            except Exception as e:
                logger.debug(f"Erro na busca Google para '{query}': {e}")
                continue

            # Pequena pausa entre queries para evitar bloqueio
            time.sleep(0.5)

    except Exception as e:
        resultado['erro'] = f"Erro na pesquisa Google: {str(e)}"
        logger.warning(f"Erro Google para '{termo}': {e}")

    return resultado


# ============================================================
# VERIFICAÇÃO PRINCIPAL
# ============================================================

def verificar_termo(termo: str) -> ResultadoTermo:
    """
    Verifica um único termo contra todas as fontes disponíveis.
    """
    termo_lower = termo.lower().strip()

    # 1. Verificar contra base de marcas conhecidas
    marca_local = MARCAS_CONHECIDAS.get(termo_lower)

    if marca_local:
        # Se é termo genérico sem titular
        if marca_local.get('titular') is None:
            return ResultadoTermo(
                termo=termo,
                status=StatusRisco.PODE_ANUNCIAR.value,
                motivo=f'"{termo}" é um termo genérico de produto, não é marca registrada.',
                tipo=marca_local.get('tipo', ''),
                fonte='Base local',
            )

        # É marca conhecida com titular
        return ResultadoTermo(
            termo=termo,
            status=StatusRisco.NAO_PODE.value,
            motivo=f'"{termo}" é uma marca registrada conhecida. Uso proibido sem autorização do titular.',
            titular=marca_local['titular'],
            classe=', '.join(marca_local.get('classes', [])),
            tipo=marca_local.get('tipo', ''),
            fonte='Base de marcas conhecidas + INPI',
            inpi_encontrado=True,
        )

    # 2. Verificar semelhança com marcas conhecidas (fuzzy matching simples)
    for marca, info in MARCAS_CONHECIDAS.items():
        if info.get('titular') is None:
            continue

        # Verificar se o termo está contido em alguma marca ou vice-versa
        if (len(termo_lower) > 3 and len(marca) > 3 and
            (termo_lower in marca or marca in termo_lower)):
            return ResultadoTermo(
                termo=termo,
                status=StatusRisco.ATENCAO.value,
                motivo=f'"{termo}" é semelhante à marca registrada "{marca}" ({info["titular"]}). '
                       f'Termos semelhantes na mesma área podem gerar conflito.',
                titular=info['titular'],
                classe=', '.join(info.get('classes', [])),
                tipo=info.get('tipo', ''),
                fonte='Análise de similaridade',
            )

        # Verificar similaridade por caracteres (distância simples)
        if len(termo_lower) > 3 and len(marca) > 3:
            # Calcular similaridade simples
            common = set(termo_lower) & set(marca)
            similarity = len(common) / max(len(set(termo_lower)), len(set(marca)))
            if similarity > 0.85 and abs(len(termo_lower) - len(marca)) <= 2:
                return ResultadoTermo(
                    termo=termo,
                    status=StatusRisco.ATENCAO.value,
                    motivo=f'"{termo}" tem alta similaridade com a marca "{marca}" ({info["titular"]}). '
                           f'Recomenda-se verificação adicional.',
                    titular=info['titular'],
                    classe=', '.join(info.get('classes', [])),
                    tipo=info.get('tipo', ''),
                    fonte='Análise de similaridade fonética',
                )

    # 3. Consultar INPI
    resultado_inpi = consultar_inpi(termo)

    # 4. Pesquisar no Google
    resultado_google = pesquisar_google(termo)

    # 5. Consolidar resultados
    if resultado_inpi.get('encontrado') and resultado_inpi.get('marcas'):
        marca_inpi = resultado_inpi['marcas'][0]
        return ResultadoTermo(
            termo=termo,
            status=StatusRisco.NAO_PODE.value,
            motivo=f'Marca "{termo}" encontrada na base do INPI com registro ativo.',
            titular=marca_inpi.get('titular', 'Ver INPI'),
            classe=marca_inpi.get('classe', 'N/A'),
            tipo='Marca registrada (INPI)',
            fonte='INPI - Instituto Nacional da Propriedade Industrial',
            inpi_encontrado=True,
            detalhes_inpi=json.dumps(marca_inpi, ensure_ascii=False),
        )

    if resultado_google.get('e_marca'):
        return ResultadoTermo(
            termo=termo,
            status=StatusRisco.ATENCAO.value,
            motivo=f'"{termo}" pode ser uma marca registrada. Foram encontrados indícios em buscas online. '
                   f'Recomenda-se verificação manual no INPI.',
            fonte='Pesquisa Google',
            google_encontrado=True,
            detalhes_google=resultado_google.get('info', ''),
        )

    # Se houve erros em ambas as consultas, marcar como atenção
    if resultado_inpi.get('erro') and resultado_google.get('erro'):
        return ResultadoTermo(
            termo=termo,
            status=StatusRisco.ATENCAO.value,
            motivo=f'Não foi possível verificar "{termo}" completamente. '
                   f'Consulta INPI e Google apresentaram erros. Verifique manualmente.',
            fonte='Verificação incompleta',
        )

    # Nenhum indício encontrado
    return ResultadoTermo(
        termo=termo,
        status=StatusRisco.PODE_ANUNCIAR.value,
        motivo=f'Nenhum registro de marca encontrado para "{termo}". '
               f'Termo aparenta ser livre para uso.',
        fonte='Verificação completa (INPI + Google)',
    )


def verificar_anuncio(texto: str, url: str = None) -> ResultadoVerificacao:
    """
    Verifica um anúncio completo, extraindo termos e verificando cada um.
    """
    from datetime import datetime

    texto_completo = texto or ""

    # Se foi fornecida uma URL, extrair conteúdo
    dados_anuncio = None
    if url:
        conteudo_url = extrair_conteudo_url(url)
        dados_anuncio = conteudo_url
        if conteudo_url['sucesso']:
            texto_completo = f"{conteudo_url['texto_completo']} {texto_completo}".strip()
        elif conteudo_url['erro'] and not texto_completo.strip():
            # Erro e sem texto alternativo
            return ResultadoVerificacao(
                status_geral=StatusRisco.ATENCAO.value,
                termos_extraidos=[],
                resultados=[ResultadoTermo(
                    termo='(URL)',
                    status=StatusRisco.ATENCAO.value,
                    motivo=f"Não foi possível acessar a URL: {conteudo_url['erro']}. "
                           f"Tente colar o texto do anúncio diretamente.",
                )],
                texto_original=url,
                timestamp=datetime.now().isoformat(),
            )

    # Extrair termos
    termos = extrair_termos(texto_completo)

    if not termos:
        return ResultadoVerificacao(
            status_geral=StatusRisco.PODE_ANUNCIAR.value,
            termos_extraidos=[],
            resultados=[ResultadoTermo(
                termo='(nenhum)',
                status=StatusRisco.PODE_ANUNCIAR.value,
                motivo='Nenhum termo que possa ser marca foi identificado no texto fornecido.',
            )],
            texto_original=texto_completo[:500],
            timestamp=datetime.now().isoformat(),
        )

    # Verificar cada termo
    resultados = []
    for termo in termos:
        resultado = verificar_termo(termo)
        resultados.append(resultado)

    # Determinar status geral (o pior caso prevalece)
    status_geral = StatusRisco.PODE_ANUNCIAR.value
    for r in resultados:
        if r.status == StatusRisco.NAO_PODE.value:
            status_geral = StatusRisco.NAO_PODE.value
            break
        elif r.status == StatusRisco.ATENCAO.value:
            status_geral = StatusRisco.ATENCAO.value

    return ResultadoVerificacao(
        status_geral=status_geral,
        termos_extraidos=termos,
        resultados=resultados,
        texto_original=texto_completo[:500],
        timestamp=datetime.now().isoformat(),
        dados_anuncio=dados_anuncio,
    )
