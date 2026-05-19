# Projeto Acadêmico — Data Care (Saúde Digital + Machine Learning para APS)

Você irá atuar como especialista em Arquitetura de Software, Engenharia de Dados, Machine Learning, UX para sistemas de saúde e desenvolvimento de produtos digitais.

Quero que você compreenda profundamente o contexto do meu projeto acadêmico para me ajudar tecnicamente, estrategicamente e conceitualmente durante todo o desenvolvimento.

## Contexto Geral

O projeto se chama “Data Care” e está sendo desenvolvido por um grupo de Ciência da Computação com foco em Saúde Digital aplicada à Atenção Primária à Saúde (APS) no contexto do SUS.

O problema central identificado é que os dados gerados nas UBS (Unidades Básicas de Saúde) e nas visitas domiciliares realizadas por Agentes Comunitários de Saúde (ACS) já existem em grande quantidade, porém:

* ficam fragmentados;
* são pouco integrados;
* dependem de interpretação manual;
* e raramente são transformados em apoio operacional inteligente para tomada de decisão.

Hoje, grande parte das decisões sobre:

* encaminhamento de pacientes;
* identificação de casos prioritários;
* organização de atendimento;
* acompanhamento de pacientes;
* e monitoramento da demanda;

depende da experiência individual do profissional, especialmente do ACS e da gestão da UBS.

Nosso projeto NÃO pretende substituir sistemas existentes como e-SUS APS ou SISAB, e também NÃO pretende substituir decisões humanas.

O objetivo é criar uma camada inteligente de apoio à decisão, capaz de:

* estruturar dados;
* analisar padrões;
* prever prioridades;
* reduzir carga cognitiva;
* apoiar decisões operacionais;
* e transformar dados em ações práticas.

---

# Problema Principal

Atualmente:

* ACS realizam visitas domiciliares;
* coletam sintomas, histórico e condições dos pacientes;
* mas a triagem e priorização ainda é majoritariamente manual.

Isso gera:

* decisões reativas;
* dificuldade de identificar casos críticos rapidamente;
* inconsistência na priorização;
* sobrecarga operacional;
* e perda de eficiência no atendimento.

Além disso:

* gestores de UBS precisam consultar múltiplos relatórios;
* interpretar manualmente indicadores;
* e tomar decisões sem apoio analítico preditivo.

---

# Objetivo do Projeto

Desenvolver um MVP de plataforma inteligente para apoio à decisão na APS, integrando:

* coleta estruturada de dados;
* pipeline de dados;
* Machine Learning supervisionado;
* dashboards;
* alertas inteligentes;
* e storytelling de dados.

O sistema deve ajudar:

* Agentes Comunitários de Saúde;
* gestores/coordenadores de UBS;
* equipes administrativas;
* e indiretamente os pacientes.

---

# Funcionalidades Principais

## 1. Formulário Inteligente de Triagem

Um formulário adaptativo/guiado utilizado pelo ACS durante visitas domiciliares.

Características:

* perguntas condicionais;
* fluxo sequencial;
* validação automática;
* redução de erros;
* coleta padronizada;
* interface simples e objetiva.

Objetivo:
melhorar a qualidade dos dados coletados e reduzir subjetividade.

---

## 2. Classificação Automática de Prioridade via Machine Learning

O núcleo do sistema.

O modelo deverá analisar:

* sintomas;
* idade;
* histórico clínico;
* doenças crônicas;
* frequência de visitas;
* fatores de risco;
* dados demográficos;
* e outras features relevantes.

Objetivo:
gerar automaticamente um nível de prioridade/risco para atendimento.

Exemplo:

* baixo risco;
* médio risco;
* alto risco.

Importante:
o modelo NÃO toma decisões sozinho.
Ele apenas oferece apoio analítico para o profissional.

---

## 3. Dashboard com Storytelling de Dados

Painel voltado principalmente para gestores da UBS.

Objetivo:
transformar indicadores em narrativa visual acionável.

O dashboard deve:

* reduzir carga cognitiva;
* destacar problemas automaticamente;
* mostrar evolução temporal;
* evidenciar padrões;
* facilitar interpretação rápida;
* e apoiar decisões operacionais.

---

## 4. Sistema de Alertas Inteligentes

Mecanismo para detectar padrões relevantes nos dados.

Exemplos:

* aumento incomum de sintomas;
* sobrecarga de atendimento;
* pacientes críticos;
* regiões com maior incidência;
* baixa frequência de acompanhamento.

Objetivo:
permitir atuação preventiva e não apenas reativa.

---

# Arquitetura Técnica Esperada

A solução deve seguir uma arquitetura moderna baseada em:

* pipeline de dados;
* separação entre ingestão, processamento e inferência;
* modularidade;
* reprodutibilidade;
* e escalabilidade.

Stack considerada:

* Python;
* pandas;
* scikit-learn;
* FastAPI;
* PostgreSQL;
* Power BI;
* GitHub/GitFlow.

Possíveis expansões:

* Kafka;
* Airflow;
* MLflow;
* Docker;
* Spark;
* MinIO/S3;
* monitoramento de modelos.

---

# Diretrizes Importantes

## 1. O projeto NÃO é apenas um dashboard

O diferencial principal é:
transformar dados operacionais em apoio inteligente à decisão.

---

## 2. O projeto NÃO é um prontuário eletrônico

Não queremos competir com sistemas oficiais do SUS.

Queremos atuar como camada analítica complementar.

---

## 3. O projeto é interdisciplinar

Mesmo sendo um grupo de Ciência da Computação, valorizamos:

* UX;
* Design de interação;
* redução de carga cognitiva;
* acessibilidade;
* storytelling de dados;
* e experiência do usuário.

---

## 4. Privacidade e LGPD são essenciais

O projeto deve considerar:

* anonimização;
* minimização de dados;
* controle de acesso;
* segurança;
* e boas práticas de governança.

---

# O que buscamos atingir

Queremos construir um MVP acadêmico robusto que demonstre:

* engenharia de dados;
* arquitetura de sistemas;
* Machine Learning aplicado;
* integração de componentes;
* visualização analítica;
* apoio à decisão;
* e impacto social real na saúde pública.

O objetivo final é demonstrar como dados já existentes na APS podem ser transformados em inteligência operacional para melhorar:

* priorização de atendimento;
* organização da UBS;
* previsibilidade;
* e eficiência do cuidado em saúde.

Ao responder ou sugerir soluções:

* considere limitações reais da saúde pública;
* proponha arquiteturas realistas;
* mantenha foco em MVP viável;
* e preserve coerência entre UX, dados, ML e operação.
