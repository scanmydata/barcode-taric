# 🔄 Sistema Bidirecional 2-Way - Guia Completo

## O que é?

Um sistema **completo** que permite:

### 1️⃣ **Busca por Barcode** (Código → TARIC)
```bash
python taric_lookup.py "5901234123457"
```
**Entrada**: Código de barras (13 dígitos)  
**Saída**: Nome do produto + TARIC + Descrição

### 2️⃣ **Busca por Descrição** (Descrição → Barcode + TARIC)
```bash
python taric_lookup.py "Corona Extra beer" --mode description
```
**Entrada**: Nome ou descrição do produto  
**Saída**: Barcode (se disponível) + TARIC + Detalhes completos

### 3️⃣ **Busca Automática** (Detecta automaticamente)
```bash
python taric_lookup.py "5901234123457"        # Detecta como barcode
python taric_lookup.py "red wine"             # Detecta como descrição
```

---

## 📊 Banco de Dados - Campos Completos

Cada produto armazenado contém:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| ⏰ **DATE/TIME** | Data e hora da inserção | 2026-05-15 09:49:18 |
| 🏷️ **BARCODE** | Código EAN-13 | 5901234123457 |
| 📦 **TARIC CODE** | Código TARIC (10 dígitos) | 2203000000 |
| 📝 **HS4** | Classificação HS | 2203 |
| 🎯 **TARIC DESCRIPTION** | Descrição oficial TARIC | Beer made from malt |
| 📌 **PRODUCT NAME** | Nome do produto | Corona Extra |
| 📄 **DESCRIPTION** | Descrição completa | Cerveja premium mexicana |
| 🛒 **COMMERCIAL TEXT** | Texto comercial | Corona Extra beer |
| 🔧 **CUSTOMS TEXT** | Texto alfandegário | corona extra beer |
| 🔗 **SOURCE** | Fonte de dados | OpenFoodFacts, api |

---

## 📋 Comandos Disponíveis

### Consultas Simples
```bash
# Buscar por barcode
python taric_lookup.py "5901234123457"

# Buscar por descrição
python taric_lookup.py "Cotton shirt" --mode description

# Processamento em lote
python taric_lookup.py --file produtos.txt --ai-provider none
```

### Gerenciamento de Banco de Dados
```bash
# Ver TODOS os produtos com detalhes completos
python taric_lookup.py --list-db
python taric_lookup.py --view-db  # Alias

# Exportar banco de dados para JSON (backup)
python taric_lookup.py --export-db
# Gera: product_database.json

# Importar produtos de JSON
python taric_lookup.py --import-db product_database.json

# Desabilitar armazenamento (busca única, sem guardar)
python taric_lookup.py "5901234123457" --no-db
```

---

## 🧪 Teste Completo

Execute o teste automatizado:
```bash
python test_2way_system.py
```

Isso fará:
1. Limpar o banco de dados
2. Adicionar 4 produtos de teste
3. Exibir detalhes completos
4. Testar busca reversa (descrição → barcode)
5. Exportar para JSON

---

## 💾 Formato do Banco de Dados

### SQLite (Nativo)
```
product_database.db
  ├─ products (tabela principal)
  └─ products_fts (índice full-text search)
```

### JSON (Exportação)
```json
[
  {
    "barcode": "5901234123457",
    "product_name": "Sauce chiltepin",
    "taric_code": null,
    "hs4": null,
    "customs_text": "sauce chiltepin aceites de oliva la lumbre",
    "source": "OpenFoodFacts"
  }
]
```

---

## 🔍 Busca Full-Text (FTS5)

O banco de dados usa SQLite FTS5 para busca rápida em:
- Nomes de produtos
- Descrições
- Texto comercial
- Texto alfandegário

Exemplo:
```bash
# Buscar "vinho" retorna todos os produtos com "vinho" no nome ou descrição
python taric_lookup.py "vinho" --mode description
```

---

## ⚙️ Opcionalidades

### AI Rewriting (Opcional)
```bash
# Com reescrita por IA (mais lento, mais preciso)
python taric_lookup.py "5901234123457" --ai-provider pollinations

# Sem IA (rápido, direto)
python taric_lookup.py "5901234123457" --ai-provider none
```

### Modo Explícito
```bash
# Força modo barcode
python taric_lookup.py "produto aleatorio" --mode barcode

# Força modo descrição
python taric_lookup.py "5901234123457" --mode description
```

---

## 📁 Saída

Todas as consultas produzem JSON:

```json
{
  "input": "Corona beer",
  "barcode": null,
  "product_name": "",
  "product_description": "",
  "commercial_text": "Corona Extra beer",
  "customs_text": "corona extra beer",
  "match": {
    "taric_code": "2203000000",
    "hs4": "2203",
    "description": "Beer made from malt"
  },
  "source": "database"
}
```

Arquivo: `taric_output.json`

---

## 🚀 Use Case Real

**Cenário**: Você tem uma planilha com 1000 produtos misturando barcodes e descrições.

```bash
# 1. Processar em lote
python taric_lookup.py --file produtos.xlsx --ai-provider none

# 2. Visualizar resultados completos
python taric_lookup.py --list-db | less

# 3. Exportar para integração com sistema
python taric_lookup.py --export-db

# 4. Depois, buscar reversa por descrição
python taric_lookup.py "produto xyz" --mode description
```

---

## ✅ Recursos

- ✅ Barcode → TARIC (busca direta)
- ✅ Descrição → Barcode + TARIC (busca reversa)
- ✅ Detecção automática (barcode vs descrição)
- ✅ Banco de dados persistente (SQLite)
- ✅ Full-text search (FTS5)
- ✅ Export/Import JSON
- ✅ Data/Hora de cada entrada
- ✅ Suporte a lote (batch processing)
- ✅ Reescrita por IA (opcional)
- ✅ Múltiplas fontes de dados

---

**Sistema Desenvolvido**: Mai 2026  
**Status**: ✅ Produção-ready
