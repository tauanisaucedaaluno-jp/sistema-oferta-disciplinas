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
    filtrar_por_ano_corte,
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


import argparse
import glob
import pandas as pd


def encontrar_arquivos(modo_raw: bool):
    """Localiza o arquivo de currículo e os arquivos de histórico escolar."""
    if modo_raw:
        dir_raw = os.path.join(BASE_DIR, "data/raw")
        dir_hist = os.path.join(dir_raw, "historicos")

        # 1. Busca currículo
        curriculos = [
            f for f in glob.glob(os.path.join(dir_raw, "*.csv"))
            if "hist" not in os.path.basename(f).lower()
        ]
        if not curriculos:
            raise FileNotFoundError(f"Nenhum arquivo CSV de currículo encontrado em {dir_raw}")
        caminho_curriculo = curriculos[0]

        # 2. Busca históricos
        if os.path.exists(dir_hist):
            arquivos_historico = sorted(glob.glob(os.path.join(dir_hist, "*.csv")))
        else:
            arquivos_historico = sorted([
                f for f in glob.glob(os.path.join(dir_raw, "*.csv"))
                if "hist" in os.path.basename(f).lower()
            ])

        if not arquivos_historico:
            raise FileNotFoundError(f"Nenhum arquivo CSV de histórico encontrado em {dir_hist} ou {dir_raw}")

        dir_saida = dir_raw
    else:
        dir_sample = os.path.join(BASE_DIR, "data/sample")
        caminho_curriculo = os.path.join(dir_sample, "curriculo_sample.csv")
        caminho_hist = os.path.join(dir_sample, "historico_sample.csv")
        if not os.path.exists(caminho_curriculo) or not os.path.exists(caminho_hist):
            raise FileNotFoundError("Arquivos de teste não encontrados em data/sample/")
        arquivos_historico = [caminho_hist]
        dir_saida = dir_sample

    return caminho_curriculo, arquivos_historico, dir_saida


def garantir_usuario_coordenador(db):
    """Garante a existência do usuário coordenador para acesso ao painel após o ETL."""
    usuario = db.query(Usuario).filter(Usuario.email == "coordenador@unipampa.edu.br").first()
    if not usuario:
        import bcrypt
        senha_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.add(Usuario(
            email="coordenador@unipampa.edu.br",
            senha_hash=senha_hash,
            papel="coordenador",
            ativo=True
        ))
        db.commit()
        print("Usuário coordenador@unipampa.edu.br criado para acesso ao painel.")


def main():
    parser = argparse.ArgumentParser(description="Executa o pipeline de ETL de Oferta de Disciplinas.")
    parser.add_argument("--raw", action="store_true", help="Usa dados reais de data/raw/")
    parser.add_argument("--sample", action="store_true", help="Força uso de dados de teste de data/sample/")
    args = parser.parse_args()

    # Se não foi explicitamente passado --sample, verifica se existem arquivos em data/raw/
    modo_raw = True
    if args.sample:
        modo_raw = False
    elif not args.raw:
        # Auto-detecção: se houver histórico em raw/historicos ou raw, usa raw
        dir_raw = os.path.join(BASE_DIR, "data/raw")
        dir_hist = os.path.join(dir_raw, "historicos")
        tem_raw = os.path.exists(dir_hist) and len(glob.glob(os.path.join(dir_hist, "*.csv"))) > 0
        modo_raw = tem_raw

    tipo_dados = "DADOS REAIS (data/raw)" if modo_raw else "DADOS DE TESTE (data/sample)"
    print(f"\n=== INICIANDO ETL - MODO: {tipo_dados} ===")

    db = SessionLocal()
    try:
        caminho_curriculo, arquivos_historico, dir_saida = encontrar_arquivos(modo_raw)

        print(f"\nArquivo de Currículo: {os.path.basename(caminho_curriculo)}")
        print(f"Arquivos de Histórico encontrados ({len(arquivos_historico)}):")
        for f in arquivos_historico:
            print(f" - {os.path.basename(f)}")

        limpar_tabelas_academicas(db)
        garantir_usuario_coordenador(db)

        print("\n--- PASSO 1: Processando Currículo ---")
        df_curriculo_raw = ler_csv_curriculo(caminho_curriculo)
        print(f"Total de linhas lidas no currículo: {len(df_curriculo_raw)}")

        df_curriculo = deduplicar_versoes(df_curriculo_raw)
        print(f"Total de disciplinas/versões vigentes após deduplicação: {len(df_curriculo)}")

        print("\n--- PASSO 2: Lendo Arquivos de Histórico ---")
        dfs_historico = []
        for f in arquivos_historico:
            df_hist_arq = ler_historico(f)
            print(f" - {os.path.basename(f)}: {len(df_hist_arq)} linhas")
            dfs_historico.append(df_hist_arq)

        df_historico_raw = pd.concat(dfs_historico, ignore_index=True)
        print(f"Total consolidado de linhas de histórico: {len(df_historico_raw)}")

        print("Normalizando situações das disciplinas...")
        df_historico = normalizar_situacao(df_historico_raw)
        df_historico = excluir_evadidos(df_historico)
        df_historico = filtrar_por_ano_corte(df_historico)

        print("\n--- PASSO 3: Construindo Conceitos e Códigos ---")
        conceitos_map = construir_conceitos(db, df_curriculo, df_historico)
        print(f"Total de códigos mapeados para conceitos: {len(conceitos_map)}")

        print("\n--- PASSO 4: Criando Vínculos Curriculares ---")
        montar_vinculos_curriculares(db, df_curriculo, conceitos_map)

        print("\n--- PASSO 5: Criando Pré-requisitos ---")
        montar_pre_requisitos(db, df_curriculo, conceitos_map)

        print("\n--- PASSO 6: Gravando Alunos e Histórico no Banco ---")
        gravar_historico(db, df_historico, conceitos_map)

        print("\n--- PASSO 7: Inferindo Periodicidade de Oferta ---")
        inferir_periodicidade(db, df_historico, conceitos_map)

        print("\n=== ETL CONCLUÍDO COM SUCESSO! ===")

        # Relatório de exceções
        excecoes = relatorio_curriculo_excecoes()
        caminho_relatorio = os.path.join(dir_saida, "relatorio_excecoes.txt")
        if excecoes:
            # Elimina eventuais duplicatas preservando a ordem
            excecoes_unicas = list(dict.fromkeys(excecoes))
            print(f"\n[Exceções/Avisos de Importação - {len(excecoes_unicas)} únicos encontrados]:")
            for exc in excecoes_unicas[:10]:
                print(f" - {exc}")
            if len(excecoes_unicas) > 10:
                print(f" ... e mais {len(excecoes_unicas) - 10} avisos gravados no relatório.")

            with open(caminho_relatorio, "w", encoding="utf-8") as f:
                f.write("\n".join(excecoes_unicas))
            print(f"\nRelatório completo de exceções gravado em: {caminho_relatorio}")
        else:
            print("\nNenhuma exceção ou inconsistência encontrada no mapeamento!")
            if os.path.exists(caminho_relatorio):
                os.remove(caminho_relatorio)

    except Exception as e:
        print(f"\nErro fatal durante a execução do ETL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
