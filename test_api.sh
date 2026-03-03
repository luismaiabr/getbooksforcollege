#!/usr/bin/env bash
# Batch rename all non-standard books via the API
BASE="http://localhost:8000"

rename_book() {
  local fid="$1"
  local new_name="$2"
  echo "   POST /books/rename/$fid → $new_name"
  curl -s -X POST "$BASE/books/rename/$fid" \
    -H 'Content-Type: application/json' \
    -d "{\"new_book_name\": \"$new_name\"}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print('   cache_renamed:', d.get('cache_renamed'), '| old:', d.get('old_name'))"
  echo ""
}

echo "=== Renomeando livros não conformes com o padrão 'Título - Autor' ==="
echo ""

echo "[2] Designing Data-Intensive Applications [Kleppmann]"
rename_book "1AT2hniVxNJq5dFGj_jDDwh-kq071_z5N" "Designing Data-Intensive Applications - Kleppmann"

echo "[3] Alireza-Parandeh-Building-Generative-AI-Services-..."
rename_book "1tPALTHwV4lV13S_D5TpQjf79aa-Qj8zD" "Building Generative AI Services with FastAPI - Parandeh"

echo "[4] Introduction to Modern Statistics"
rename_book "1TOKujdv-IWkkWCpdOnazLW-y0JBIDyGE" "Introduction to Modern Statistics - Cetinkaya-Rundel"

echo "[5] LOGICA PARTE 2 - NUNES"
rename_book "1i7-gaeNpOnpdvNEY9AJzBpXc0IY-4LxQ" "Lógica para Ciência da Computação - Nunes (Parte 2)"

echo "[6] LOGICA PARTE 1"
rename_book "1-kmmfrUV_k5fo10l5r2XZyXgQZqDNm59" "Lógica para Ciência da Computação - Nunes (Parte 1)"

echo "[7] seguir_Jesus,projeto_de_vida_-_semeadores_da_palavra inverted"
rename_book "1XXGa4Dbn98h-APB3Iz2CfAyxy3s483kt" "Seguir Jesus - Caio Fábio"

echo "[8] Lutz M. - Learning Python, 5th Edition (2013, O'Reilly) - libgen.li"
rename_book "1Cz23USHstp_2cJJZvoWnl6vgYPcI8mh-" "Learning Python - Lutz"

echo "[9] POSTGRESQL"
rename_book "14kuj1NzuclobKWhjZWpNUbPFJP7m7uzN" "PostgreSQL: Up and Running - Obe & Hsu"

echo "[10] MAT COMP  ← na verdade: Introduction to Operations Research"
rename_book "1zwdNxyWSZKnK1uyHpU71Wob_NLIL2xid" "Introduction to Operations Research - Hillier & Lieberman"

echo "[11] David Sale - Testing Python_... - libgen.li"
rename_book "1GBgiGRth4nfXW5aytSMqFBKn3gES_qht" "Testing Python - Sale"

echo "[12] POSTGRESQL (Copy)"
rename_book "1l-YdOI_D10W6vYQg22sqSa2zwpFvSHib" "PostgreSQL: Up and Running - Obe & Hsu (Cópia)"

echo "[13] Pesquisa Operacional 170: Aplicações... — Amostra de Livro"
rename_book "1J0_5qGl1YmgZ0HtU-QpRXt1GUWBb4N6G" "Pesquisa Operacional - Amostra"

echo "[14] TESTES → SKIP (sem conteúdo acessível, nome de arquivo de teste)"
echo "   PULADO"
echo ""

echo "[15] Small Business Management CUSTOMER RELATIONSHIPS → SKIP (sem conteúdo)"
echo "   PULADO"
echo ""

echo "=== Concluído ==="
