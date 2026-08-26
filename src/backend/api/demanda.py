import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import VinculoCurricular, ConceitoDisciplina, Usuario
from api.auth import obter_usuario_atual
from core.groups import grupo_a, grupo_b, grupo_c

router = APIRouter()

@router.get("")
def obter_demandas(
    curso_codigo: str,
    periodo_atual: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Retorna o cálculo de demanda de todas as disciplinas vinculadas ao curso no período."""
    # Busca todas as disciplinas do curso vinculadas à grade curricular
    vinculos = (
        db.query(VinculoCurricular)
        .join(ConceitoDisciplina, VinculoCurricular.conceito_id == ConceitoDisciplina.id)
        .filter(VinculoCurricular.curso_codigo == curso_codigo)
        .all()
    )
    
    if not vinculos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum vínculo curricular encontrado para o curso '{curso_codigo}'",
        )
        
    resultado = []
    for vinc in vinculos:
        conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
        if not conceito:
            continue
            
        ga = grupo_a(db, curso_codigo, vinc.conceito_id, periodo_atual)
        gb = grupo_b(db, curso_codigo, vinc.conceito_id)
        gc = grupo_c(db, curso_codigo, vinc.conceito_id, periodo_atual)
        total = len(ga) + len(gb) + sum(aluno.probabilidade_aprovacao for aluno in gc)
        
        resultado.append({
            "conceito_id": vinc.conceito_id,
            "disciplina_nome": conceito.nome_normalizado,
            "periodo_sugerido": vinc.periodo_sugerido,
            "periodicidade_oferta": vinc.periodicidade_oferta,
            "grupo_a_qtd": len(ga),
            "grupo_b_qtd": len(gb),
            "grupo_c_qtd": len(gc),
            "demanda_estimada": round(total, 2),
        })
        
    return resultado

@router.get("/detalhe")
def obter_detalhe_demanda(
    curso_codigo: str,
    conceito_id: str,
    periodo_atual: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Retorna os detalhes de alunos e probabilidades de uma disciplina específica."""
    conceito = db.query(ConceitoDisciplina).filter(
        ConceitoDisciplina.id == conceito_id,
        ConceitoDisciplina.curso_codigo == curso_codigo
    ).first()
    
    if not conceito:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disciplina '{conceito_id}' não encontrada no curso '{curso_codigo}'",
        )
        
    ga = grupo_a(db, curso_codigo, conceito_id, periodo_atual)
    gb = grupo_b(db, curso_codigo, conceito_id)
    gc = grupo_c(db, curso_codigo, conceito_id, periodo_atual)
    total = len(ga) + len(gb) + sum(aluno.probabilidade_aprovacao for aluno in gc)
    
    return {
        "conceito_id": conceito_id,
        "disciplina_nome": conceito.nome_normalizado,
        "demanda_estimada": round(total, 2),
        "grupo_a": ga,
        "grupo_b": gb,
        "grupo_c": [
            {"matricula": aluno.matricula, "probabilidade": aluno.probabilidade_aprovacao}
            for aluno in gc
        ],
    }

@router.get("/exportar")
def exportar_demandas_csv(
    curso_codigo: str,
    periodo_atual: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Gera um arquivo CSV formatado com a estimativa de demanda do curso no período."""
    vinculos = (
        db.query(VinculoCurricular)
        .join(ConceitoDisciplina, VinculoCurricular.conceito_id == ConceitoDisciplina.id)
        .filter(VinculoCurricular.curso_codigo == curso_codigo)
        .all()
    )
    
    if not vinculos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum vínculo curricular encontrado para o curso '{curso_codigo}'",
        )
        
    # Escreve o CSV na memória
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    
    # Cabeçalho
    writer.writerow([
        "Codigo Disciplina", "Nome Disciplina", "Periodo Sugerido", 
        "Grupo A (Cursando)", "Grupo B (Aptos)", "Grupo C (Potenciais)", "Demanda Estimada"
    ])
    
    for vinc in vinculos:
        conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
        if not conceito:
            continue
            
        ga = grupo_a(db, curso_codigo, vinc.conceito_id, periodo_atual)
        gb = grupo_b(db, curso_codigo, vinc.conceito_id)
        gc = grupo_c(db, curso_codigo, vinc.conceito_id, periodo_atual)
        total = len(ga) + len(gb) + sum(aluno.probabilidade_aprovacao for aluno in gc)
        
        writer.writerow([
            vinc.conceito_id,
            conceito.nome_normalizado,
            vinc.periodo_sugerido or "-",
            len(ga),
            len(gb),
            len(gc),
            round(total, 2)
        ])
        
    output.seek(0)
    
    # Retorna o arquivo como stream para download
    filename = f"demanda_{curso_codigo}_{periodo_atual.replace('/', '-')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Encoding": "utf-8"
        }
    )
