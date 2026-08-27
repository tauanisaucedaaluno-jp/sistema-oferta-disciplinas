"""
Script para executar o pipeline de ETL completo a partir dos CSVs de teste (run_etl.py).

Pode ser executado com (na raiz do projeto):
    python scripts/run_etl.py
"""
import os
import sys
from dotenv import load_dotenv

# Adiciona os caminhos ao sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "src/backend")
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, BASE_DIR)

from db.database import SessionLocal
from db.models import (
    Curso,
    ConceitoDisciplina,
    CodigoDisciplina,
    VinculoCurricular,
    PreRequisito,
    Aluno,
    Historico,
    Usuario,
    LogAcesso,
)

from etl.importar_curriculo import (
    ler_csv_curriculo,
    deduplicar_versoes,
    construir_conceitos,
    montar_vinculos_curriculares,
    montar_pre_requisitos,
    relatorio_excecoes as relatorio_curriculo_excecoes,
)
from etl.importar_historico import (
    ler_historico,
    normalizar_situacao,
    excluir_evadidos,
    inferir_periodicidade,
    gravar_historico,
)


def limpar_tabelas_academicas(db):
    """Limpa tabelas para evitar duplicidade durante os testes do ETL."""
    print("Limpando tabelas acadêmicas...")
    db.query(PreRequisito).delete()
    db.query(VinculoCurricular).delete()
    db.query(CodigoDisciplina).delete()
    db.query(ConceitoDisciplina).delete()
    db.query(Historico).delete()
    db.query(Aluno).delete()
    db.query(Curso).delete()
    db.commit()


def main():
    db = SessionLocal()
    try:
        # Caminhos dos arquivos de teste
        caminho_curriculo = os.path.join(BASE_DIR, "data/sample/curriculo_sample.csv")
        caminho_historico = os.path.join(BASE_DIR, "data/sample/historico_sample.csv")
        
        if not os.path.exists(caminho_curriculo) or not os.path.exists(caminho_historico):
            print("Erro: Arquivos de teste não encontrados em data/sample/.")
            return

        limpar_tabelas_academicas(db)

        print("--- PASSO 1: Processando Currículo ---")
        df_curriculo_raw = ler_csv_curriculo(caminho_curriculo)
        print(f"Total de linhas lidas no currículo: {len(df_curriculo_raw)}")
        
        df_curriculo = deduplicar_versoes(df_curriculo_raw)
        print(f"Total de linhas após deduplicação de PPC: {len(df_curriculo)}")

        print("--- PASSO 2: Lendo Histórico ---")
        df_historico_raw = ler_historico(caminho_historico)
        print(f"Total de linhas lidas no histórico: {len(df_historico_raw)}")
        
        df_historico = normalizar_situacao(df_historico_raw)
        df_historico = excluir_evadidos(df_historico)

        print("--- PASSO 3: Construindo Conceitos e Códigos ---")
        conceitos_map = construir_conceitos(db, df_curriculo, df_historico)
        print(f"Total de códigos mapeados para conceitos: {len(conceitos_map)}")

        print("--- PASSO 4: Criando Vínculos Curriculares ---")
        montar_vinculos_curriculares(db, df_curriculo, conceitos_map)

        print("--- PASSO 5: Criando Pré-requisitos ---")
        montar_pre_requisitos(db, df_curriculo, conceitos_map)

        print("--- PASSO 6: Gravando Histórico e Alunos ---")
        gravar_historico(db, df_historico, conceitos_map)

        print("--- PASSO 7: Inferindo Periodicidade de Oferta ---")
        inferir_periodicidade(db, df_historico, conceitos_map)

        print("\n=== ETL CONCLUÍDO COM SUCESSO ===")
        
        # Relatório de exceções
        excecoes = relatorio_curriculo_excecoes()
        if excecoes:
            print(f"\n[Exceções de Importação - {len(excecoes)} encontradas]:")
            for exc in excecoes:
                print(f" - {exc}")
            
            # Grava o relatório de exceções em disco (RF05)
            caminho_relatorio = os.path.join(BASE_DIR, "data/sample/relatorio_excecoes.txt")
            with open(caminho_relatorio, "w", encoding="utf-8") as f:
                f.write("\n".join(excecoes))
            print(f"Relatório de exceções gravado em: {caminho_relatorio}")
        else:
            print("\nNenhuma exceção ou inconsistência encontrada no mapeamento!")

    except Exception as e:
        print(f"\nErro fatal durante a execução do ETL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
