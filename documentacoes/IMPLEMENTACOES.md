# DATAcare — Histórias de Usuário

> Sistema de triagem comunitária para ACS e gestores de saúde.

---

## Sumário

| ID | História | Status |
|----|----------|--------|
| [HU-01](#hu-01-formulário-para-acs) | Formulário para ACS | - |
| [HU-02](#hu-02-banco-de-dados) | Banco de Dados | - |
| [HU-03](#hu-03-autenticação-login) | Autenticação (Login) | - |
| [HU-04](#hu-04-análise-exploratória-de-dados-eda) | Análise Exploratória de Dados | - |
| [HU-05](#hu-05-feature-engineering) | Feature Engineering | - |
| [HU-06](#hu-06-modelo-de-machine-learning) | Modelo de Machine Learning | - |
| [HU-07](#hu-07-pipeline-de-dados-automático) | Pipeline de Dados Automático | - |
| [HU-08](#hu-08-api-rest) | API REST | - |
| [HU-09](#hu-09-dashboard-para-gestor) | Dashboard para Gestor | - |
| [HU-10](#hu-10-sistema-de-alertas) | Sistema de Alertas | - |
| [HU-11](#hu-11-docker-compose) | Docker-Compose | - |
| [HU-12](#hu-12-documentação) | Documentação | - |
| [HU-13](#hu-13-testes) | Testes | - |

---

## HU-01: Formulário para ACS

**O que é:** Formulário digital para o ACS coletar dados durante visitas domiciliares — principal ponto de entrada de dados do sistema.

**Objetivo:** Criar uma experiência de coleta segura, validada e integrada ao backend.

### Campos do Formulário

| Seção | Campos |
|-------|--------|
| 1. Dados Pessoais | Nome completo, data de nascimento, gênero, telefone, endereço |
| 2. Sintomas | Seleção múltipla + severidade e duração por sintoma |
| 3. Comorbidades | Seleção múltipla |
| 4. Medicações | Medicações em uso |
| 5. Observações | Observações gerais |

### Validações

- **Nome:** obrigatório, mínimo 3 caracteres
- **Data de nascimento:** obrigatória, não pode ser futura
- **Telefone:** obrigatório, 10–11 dígitos
- **Sintomas:** mínimo 1 selecionado
- **Severidade:** obrigatória quando sintoma está marcado

### Frontend React

**Componentes a criar:**
- `src/pages/FormularioTriagem.jsx`
- `src/components/FormField.jsx`
- `src/components/FormDate.jsx`
- `src/components/FormCheckbox.jsx`
- `src/components/FormRange.jsx`
- `src/components/FormTextarea.jsx`

**Comportamentos:**
- Validação em tempo real com feedback instantâneo e mensagens de erro claras
- Botão de submit desabilitado enquanto formulário inválido
- Condicionalidades: severidade aparece só se sintoma selecionado; campo específico para diabetes só se diabetes marcada
- Rascunho salvo no `localStorage`, recuperado ao voltar à página, limpo após submit com sucesso

### Integração com API

- Validar no frontend e no backend
- Tratar resposta de sucesso: _"Visita registrada! Obrigado."_
- Tratar resposta de erro: _"Erro ao registrar. Tente novamente."_
- Exibir spinner durante carregamento

### Testes

- Formulário vazio → erro
- Nome curto → erro
- Data futura → erro
- Sem sintomas → erro
- Marcar febre → aparecer campo de severidade
- Desmarcar febre → desaparecer campo de severidade
- Dados chegam ao backend e salvam no banco corretamente

### Entregáveis

- [ ] Formulário React completo e funcional
- [ ] Integração com API
- [ ] Validações funcionando
- [ ] Layout e fluxo consistentes

---

## HU-02: Banco de Dados

**O que é:** Estrutura de banco de dados que armazena todos os dados do sistema.

**Objetivo:** Ter um modelo de dados consistente, migrável e testável.

### Tarefas

- Definir schema e diagrama ER
- Implementar PostgreSQL
- Criar migrations com Alembic
- Gerar seed data para testes
- Criar SQLAlchemy models
- Validar integridade e relacionamentos

### Testes

- Criar paciente e verificar persistência
- Criar visita e verificar vínculo com paciente
- Criar sintoma e verificar vínculo com visita

### Entregáveis

- [ ] PostgreSQL rodando em Docker
- [ ] Schema com 8–10 tabelas
- [ ] Migrations funcionando (Alembic)
- [ ] Seed com 100–200 pacientes
- [ ] SQLAlchemy models prontos

---

## HU-03: Autenticação (Login)

**O que é:** Login e controle de acesso para ACS e gestor.

**Objetivo:** Garantir que cada usuário acesse apenas as funcionalidades de sua permissão.

### Tarefas

- Criar tabela de usuários no backend
- Criar endpoint de login
- Criar tela de login no frontend
- Implementar logout
- Implementar RBAC (controle de acesso por perfil)

### Entregáveis

- [ ] Login funcional
- [ ] Logout funcional
- [ ] Controle de perfil (ACS × Gestor)
- [ ] Acesso seguro às rotas

---

## HU-04: Análise Exploratória de Dados (EDA)

**O que é:** Exploração dos dados coletados para entender distribuição, estrutura e padrões.

**Objetivo:** Gerar insights que guiem o feature engineering e a modelagem.

### Tarefas

- Extrair dados para análise
- Fazer análise descritiva
- Identificar valores faltantes e outliers
- Documentar findings e hipóteses

### Entregáveis

- [ ] Notebook Jupyter com análise
- [ ] Gráficos e estatísticas
- [ ] Insights documentados
- [ ] Dataset limpo em CSV

---

## HU-05: Feature Engineering

**O que é:** Transformação de dados brutos em features que o modelo ML consegue aprender.

**Objetivo:** Gerar um dataset estruturado com features relevantes.

### Features Sugeridas

| Categoria | Features |
|-----------|----------|
| **Demográficas** | `idade`, `genero_M`, `genero_F`, `faixa_etaria` |
| **Sintomas** | `tem_febre`, `tem_tosse`, `tem_espirro`, `severidade_media`, `num_sintomas`, `duracao_media_dias`, `tem_sintoma_respiratorio` |
| **Comorbidades** | `tem_diabetes`, `tem_hipertensao`, `tem_asma`, `num_comorbidades`, `tem_comorbidade_critica` |
| **Contexto** | `dias_desde_ultima_visita`, `num_visitas_historico` |

### Exemplos de Código

```python
# Idade a partir da data de nascimento
df['idade'] = (pd.Timestamp.now() - df['data_nascimento']).dt.days / 365.25

# Flag binária de sintoma
df['tem_febre'] = df['sintomas'].str.contains('febre').astype(int)

# Contagem de comorbidades por paciente
df['num_comorbidades'] = df.groupby('paciente_id')['tipo_comorbidade'].transform('count')
```

### Tarefas

- Extrair informações demográficas
- Criar features de sintomas, comorbidades e contexto
- Normalizar, tratar ausentes e selecionar features
- Salvar dataset final em CSV

### Entregáveis

- [ ] Dataset com features criadas
- [ ] Features normalizadas e escaladas
- [ ] Valores ausentes tratados
- [ ] Features irrelevantes removidas
- [ ] CSV final pronto
- [ ] Documentação das features

---

## HU-06: Modelo de Machine Learning

**O que é:** Modelo que classifica o risco do paciente em **BAIXO**, **MÉDIO** ou **ALTO**.

**Objetivo:** Criar modelo previsível, mensurável e reproduzível.

### Tarefas

1. Definir target e classes de risco
2. Construir coluna target no dataset
3. Dividir em treino / validação / teste (estratificado)
4. Criar baseline simples
5. Treinar modelo principal
6. Ajustar hiperparâmetros
7. Validar com cross-validation
8. Avaliar com métricas e matriz de confusão
9. Salvar modelo e scaler
10. Documentar model card

### Métricas

- Accuracy, Precision, Recall, F1-score
- Matriz de confusão
- Importância das features

### Entregáveis

- [ ] Modelo treinado (`.joblib`)
- [ ] Métricas documentadas
- [ ] Análise de importância de features
- [ ] Matriz de confusão
- [ ] Model card
- [ ] Código de treinamento limpo

---

## HU-07: Pipeline de Dados Automático

**O que é:** Pipeline automatizado que executa extração, transformação, modelagem e carga (ETL).

**Objetivo:** Ter um fluxo de dados confiável e repetível.

### Tarefas

- Criar script do pipeline
- Agendar execução diária ou sob demanda
- Implementar validações de qualidade de dados
- Adicionar logging de execução
- Testar o pipeline completo

### Entregáveis

- [ ] Script Python do pipeline
- [ ] Agendamento configurado
- [ ] Validações de dados
- [ ] Logging completo
- [ ] Testes do pipeline
- [ ] Documentação de execução

---

## HU-08: API REST

**O que é:** Endpoints que conectam frontend, backend e modelo ML.

**Objetivo:** Entregar uma API robusta, documentada e testável.

### Tarefas

- Configurar backend (FastAPI ou Django)
- Criar endpoints CRUD para pacientes e visitas
- Criar endpoint de prioridade / modelo
- Criar endpoints para dashboard e alertas
- Gerar documentação automática (Swagger / OpenAPI)
- Implementar tratamento de erros consistente
- Escrever testes de API

### Entregáveis

- [ ] API funcional
- [ ] Swagger / OpenAPI
- [ ] Validações de entrada
- [ ] Tratamento de erros
- [ ] Testes de endpoints

---

## HU-09: Dashboard para Gestor

**O que é:** Painel visual com KPIs, gráficos e tabelas para apoio à tomada de decisão.

**Objetivo:** Fornecer visão rápida e acionável do risco e da operação.

### Tarefas

- Definir layout responsivo
- Criar cards de KPI
- Criar gráficos relevantes
- Criar tabelas e filtros
- Integrar com API
- Testar responsividade e filtros

### Entregáveis

- [ ] Dashboard rodando
- [ ] Cards de KPI presentes
- [ ] Gráficos corretos
- [ ] Tabela de pacientes críticos
- [ ] Filtros funcionando
- [ ] Dados atualizando via API

---

## HU-10: Sistema de Alertas

**O que é:** Detecção automática de situações críticas com notificação ao gestor.

**Objetivo:** Criar regras de alerta confiáveis e visíveis.

### Tarefas

- Definir regras de alerta com especialistas
- Implementar backend de detecção
- Criar tabela de alertas no banco
- Exibir alertas no frontend
- Evitar alertas duplicados
- Adicionar notificações adicionais (email — bônus)

### Entregáveis

- [ ] Regras de alerta definidas
- [ ] Backend de detecção
- [ ] Tabela de alertas no banco
- [ ] Visualização de alertas no frontend
- [ ] Deduplicação de alertas

---

## HU-11: Docker-Compose

**O que é:** Orquestração para iniciar todos os serviços com um único comando.

**Objetivo:** Permitir implantação simples e repetível.

### Tarefas

- Escrever Dockerfile do backend
- Escrever Dockerfile do frontend
- Criar `docker-compose.yml`
- Conectar serviços no compose
- Testar execução completa
- Documentar comandos de startup e cleanup

### Entregáveis

- [ ] Dockerfiles prontos
- [ ] `docker-compose.yml` funcionando
- [ ] `docker-compose up` sobe todos os serviços
- [ ] Sistema integrado e funcional

---

## HU-12: Documentação

**O que é:** Documentação completa do projeto para uso, manutenção e entrega.

**Objetivo:** Ter documentação clara para desenvolvedores e usuários finais.

### Tarefas

- Escrever README com setup passo a passo
- Descrever arquitetura e estrutura de pastas
- Documentar endpoints e integrações
- Documentar pipeline, modelo e deploy
- Criar model card e instruções de uso

### Entregáveis

- [ ] README completo
- [ ] Guia de arquitetura
- [ ] Instruções de uso e execução
- [ ] Model card

---

## HU-13: Testes

**O que é:** Validação de que o sistema inteiro funciona sem bugs óbvios.

**Objetivo:** Garantir qualidade com cobertura em backend, frontend, ML e pipeline.

### Tarefas

- Testar API e backend
- Testar o modelo e o pipeline de dados
- Testar o formulário e o frontend
- Testar fluxos de ponta a ponta

### Entregáveis

- [ ] Testes da API
- [ ] Testes do modelo
- [ ] Testes do pipeline
- [ ] Testes do formulário
- [ ] Testes de fluxo completo
- [ ] Todos os testes executando sem erros

---

## Visão Geral dos Entregáveis

| ID | História | Entregável Principal |
|----|----------|----------------------|
| HU-01 | Formulário para ACS | Formulário React completo e integrado |
| HU-02 | Banco de Dados | PostgreSQL + Migrations + Seed |
| HU-03 | Autenticação | Login/logout com RBAC |
| HU-04 | EDA | Notebook Jupyter + dataset limpo |
| HU-05 | Feature Engineering | CSV com features prontas |
| HU-06 | Modelo ML | Modelo `.joblib` + métricas |
| HU-07 | Pipeline | Script ETL agendado + logs |
| HU-08 | API REST | API com Swagger |
| HU-09 | Dashboard | Painel com KPIs e gráficos |
| HU-10 | Alertas | Sistema de detecção e notificação |
| HU-11 | Docker-Compose | `docker-compose up` funcional |
| HU-12 | Documentação | README + guias |
| HU-13 | Testes | Suite completa sem erros |
