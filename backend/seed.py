from __future__ import annotations
import json
from pathlib import Path
from database import init_db, session_scope
from models import Assunto, FundamentoTopico, Questao

BASE = Path(__file__).resolve().parent

def seed() -> dict:
    init_db()
    data = json.loads((BASE / "questions.json").read_text(encoding="utf-8"))
    counts = {"subjects": 0, "questions": 0, "foundation_questions": 0, "foundation_topics": 0}
    with session_scope() as db:
        for pos, topic in enumerate(data.get("foundation_topics", []), 1):
            row = db.get(FundamentoTopico, topic["id"]) or FundamentoTopico(id=topic["id"])
            row.titulo = topic["title"]; row.resumo = topic["summary"]; row.teoria = topic["theory"]; row.ordem = pos
            db.add(row); counts["foundation_topics"] += 1
        for qpos, q in enumerate(data.get("foundation", []), 1):
            code = f"foundation:{qpos}"
            row = db.get(Questao, code) or Questao(codigo=code)
            row.assunto_id = None
            row.fundamento_topico_id = "n" + str((qpos - 1) // 4 + 1) if qpos <= 40 else "n" + str((qpos - 41) % 10 + 1)
            row.indice = qpos
            row.enunciado = q["q"]
            row.alternativa_a, row.alternativa_b, row.alternativa_c, row.alternativa_d = q["options"]
            row.resposta_correta = q["correct"]
            row.explicacao = q.get("exp", "Revise o conceito e confira cada etapa.")
            db.add(row); counts["foundation_questions"] += 1
        for s in data.get("subjects", []):
            row = db.get(Assunto, s["id"]) or Assunto(id=s["id"], teoria_json="{}")
            row.ano=s["year"]; row.numero=s["num"]; row.titulo=s["title"]; row.resumo=s["summary"]; row.detalhe=s.get("detail", "")
            row.teoria_json=json.dumps(s.get("theory", {}), ensure_ascii=False)
            db.add(row); counts["subjects"] += 1
            for qpos, q in enumerate(s.get("questions", []), 1):
                code=f"{s['id']}:{qpos}"
                item=db.get(Questao, code) or Questao(codigo=code)
                item.assunto_id=s["id"]; item.fundamento_topico_id=None; item.indice=qpos
                item.enunciado=q["q"]; item.alternativa_a, item.alternativa_b, item.alternativa_c, item.alternativa_d=q["options"]
                item.resposta_correta=q["correct"]; item.explicacao=q.get("exp", "Revise o conceito e confira os passos.")
                db.add(item); counts["questions"] += 1
        # Remove only question codes no longer present in the source. Never delete attempts.
        valid={f"foundation:{i}" for i in range(1,len(data.get("foundation",[]))+1)}
        for s in data.get("subjects",[]): valid.update(f"{s['id']}:{i}" for i in range(1,len(s.get('questions',[]))+1))
        for stale in db.query(Questao).all():
            if stale.codigo not in valid:
                db.delete(stale)
    return counts

if __name__ == "__main__":
    print("Conteúdo sincronizado:", seed())
