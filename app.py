"""Local BNCC lesson-plan generator using Gemini's Google Search grounding."""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

COMPONENTS = (
    "Matemática",
    "Linguagem",
    "Natureza e cultura",
    "Artes",
    "Projeto",
)
LEVELS = {
    "Educação Infantil": ("Bebês (0 a 1 ano e 6 meses)", "Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)", "Crianças pequenas (4 a 5 anos e 11 meses)"),
    "Ensino Fundamental 1": tuple(f"{year}º ano" for year in range(1, 6)),
    "Ensino Fundamental 2": tuple(f"{year}º ano" for year in range(6, 10)),
}
MAX_REQUEST_BYTES = 20_000
MAX_THEME_LENGTH = 250

PAGE = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f6f7f2">
  <title>BNCC na prática | Gerador de planos de aula</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #182b26;
      --muted: #64746d;
      --green: #176b54;
      --green-dark: #10513f;
      --mint: #e5f1e9;
      --paper: #fffefa;
      --line: #e1e8df;
      --orange: #e7a14c;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: #f6f7f2;
      line-height: 1.55;
    }
    .topbar {
      height: 72px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 max(24px, calc((100% - 1120px) / 2));
      border-bottom: 1px solid var(--line);
      background: rgba(255, 254, 250, .88);
    }
    .brand { display: flex; align-items: center; gap: 11px; font-weight: 750; letter-spacing: -.03em; }
    .brand-mark {
      display: grid; place-items: center; width: 35px; height: 35px;
      border-radius: 12px; color: white; background: var(--green); font-size: 19px;
    }
    .top-note { color: var(--muted); font-size: 13px; }
    main { width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 54px 0 80px; }
    .hero { max-width: 720px; margin: 0 auto 34px; text-align: center; }
    .eyebrow {
      display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
      border: 1px solid #d5e7db; border-radius: 99px; color: var(--green-dark);
      background: #edf5ef; font-size: 12px; font-weight: 700; letter-spacing: .04em;
      text-transform: uppercase;
    }
    .eyebrow span { color: var(--orange); font-size: 16px; }
    h1 { margin: 17px 0 11px; font-size: clamp(36px, 5vw, 56px); line-height: 1.07; letter-spacing: -.055em; }
    h1 em { color: var(--green); font-style: normal; }
    .hero p { margin: 0 auto; max-width: 570px; color: var(--muted); font-size: 16px; }
    .layout { display: grid; grid-template-columns: minmax(0, .88fr) minmax(0, 1.12fr); align-items: start; gap: 22px; }
    .panel {
      overflow: hidden; border: 1px solid var(--line); border-radius: 20px;
      background: var(--paper); box-shadow: 0 12px 40px rgba(32, 57, 43, .055);
    }
    .form-panel { padding: 27px; }
    .panel-heading { display: flex; gap: 13px; align-items: flex-start; margin-bottom: 24px; }
    .step {
      display: grid; place-items: center; flex: 0 0 33px; height: 33px;
      border-radius: 11px; color: var(--green-dark); background: var(--mint); font-weight: 800;
    }
    h2 { margin: 0; font-size: 18px; letter-spacing: -.025em; }
    .panel-heading p { margin: 3px 0 0; color: var(--muted); font-size: 13px; }
    .field { margin: 0 0 18px; }
    label { display: block; margin-bottom: 7px; font-size: 13px; font-weight: 700; }
    select, input, textarea {
      width: 100%; padding: 12px 13px; border: 1px solid #dce4dc; border-radius: 10px;
      color: var(--ink); background: #fff; font: inherit; font-size: 14px; outline: none;
      transition: border-color .16s, box-shadow .16s;
    }
    select:focus, input:focus, textarea:focus { border-color: #72a58d; box-shadow: 0 0 0 3px rgba(23, 107, 84, .1); }
    textarea { min-height: 88px; resize: vertical; }
    .field-hint { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    button {
      width: 100%; min-height: 48px; display: flex; align-items: center; justify-content: center;
      gap: 9px; margin-top: 7px; padding: 12px 16px; border: 0; border-radius: 11px;
      color: #fff; background: var(--green); font: inherit; font-weight: 750; cursor: pointer;
      transition: transform .16s, background .16s;
    }
    button:hover { transform: translateY(-1px); background: var(--green-dark); }
    button:disabled { opacity: .7; cursor: wait; transform: none; }
    .privacy { margin: 12px 2px 0; color: var(--muted); font-size: 11px; text-align: center; }
    .result-panel { min-height: 505px; }
    .result-head {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 21px 24px; border-bottom: 1px solid var(--line);
    }
    .result-head h2 { display: flex; align-items: center; gap: 9px; }
    .result-head h2 span { color: var(--green); }
    .result-body { padding: 22px 24px 26px; }
    .empty-state { min-height: 393px; display: grid; place-content: center; text-align: center; }
    .empty-icon { margin: 0 auto 15px; font-size: 45px; }
    .empty-state h3 { margin: 0 0 7px; font-size: 17px; }
    .empty-state p { max-width: 290px; margin: 0; color: var(--muted); font-size: 13px; }
    .loading { min-height: 393px; display: grid; place-content: center; justify-items: center; text-align: center; }
    .spinner { width: 34px; height: 34px; margin-bottom: 16px; border: 3px solid #dcebe1; border-top-color: var(--green); border-radius: 50%; animation: spin .8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error { padding: 14px 16px; border: 1px solid #f1d0c6; border-radius: 12px; color: #803c2e; background: #fff5f1; font-size: 13px; }
    .plan-title { margin: 0 0 6px; font-size: 23px; letter-spacing: -.04em; }
    .plan-meta { margin: 0 0 19px; color: var(--muted); font-size: 12px; }
    .plan-section { margin: 20px 0; }
    .plan-section h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; font-size: 14px; }
    .plan-section ul, .plan-section ol { margin: 0; padding-left: 21px; }
    .plan-section li { padding: 2px 0 5px; font-size: 13px; }
    .skill {
      margin: 8px 0; padding: 12px 13px; border: 1px solid var(--line);
      border-radius: 11px; background: #fbfcf8;
    }
    .skill-code { display: inline-block; margin-bottom: 5px; padding: 2px 7px; border-radius: 6px; color: var(--green-dark); background: var(--mint); font-size: 11px; font-weight: 800; }
    .skill p, .assessment { margin: 0; font-size: 13px; }
    .skill small { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; }
    .note { margin: 12px 0; padding: 11px 12px; border-left: 3px solid var(--orange); color: #63451e; background: #fff8eb; font-size: 12px; }
    .sources { padding-top: 13px; border-top: 1px solid var(--line); }
    .sources a { color: var(--green-dark); font-size: 12px; text-decoration-thickness: 1px; text-underline-offset: 3px; }
    .sources li { overflow-wrap: anywhere; }
    footer { margin-top: 20px; color: #7a8982; font-size: 11px; text-align: center; }
    @media (max-width: 760px) {
      main { width: min(600px, calc(100% - 28px)); padding-top: 38px; }
      .layout { grid-template-columns: 1fr; }
      .result-panel { min-height: 300px; }
      .empty-state, .loading { min-height: 240px; }
      .topbar { height: 62px; padding: 0 16px; }
      .top-note { font-size: 11px; }
    }
    @media (max-width: 420px) {
      .form-panel { padding: 21px 17px; }
      .result-head, .result-body { padding-right: 17px; padding-left: 17px; }
      .two-col { grid-template-columns: 1fr; gap: 0; }
      .top-note { max-width: 105px; text-align: right; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand"><span class="brand-mark" aria-hidden="true">✳</span> BNCC na prática</div>
    <div class="top-note">Planejamento com intencionalidade</div>
  </header>
  <main>
    <section class="hero">
      <div class="eyebrow"><span aria-hidden="true">✦</span> Planejamento pedagógico inteligente</div>
      <h1>Uma boa aula começa<br>com um <em>bom plano.</em></h1>
      <p>Conte sua ideia. A IA pesquisa as habilidades da BNCC e organiza um plano de aula para você.</p>
    </section>
    <div class="layout">
      <section class="panel form-panel" aria-labelledby="form-title">
        <div class="panel-heading">
          <span class="step" aria-hidden="true">01</span>
          <div><h2 id="form-title">Vamos planejar sua aula</h2><p>Preencha os campos para começar.</p></div>
        </div>
        <form id="plan-form">
          <div class="field">
            <label for="component">Componente curricular</label>
            <select id="component" name="component" required>
              <option>Matemática</option><option>Linguagem</option><option>Natureza e cultura</option><option>Artes</option><option>Projeto</option>
            </select>
          </div>
          <div class="field">
            <label for="theme">Tema da aula</label>
            <textarea id="theme" name="theme" maxlength="250" placeholder="Ex.: descobrindo os animais do jardim" required></textarea>
            <span class="field-hint">Seja específico para receber ideias mais relevantes.</span>
          </div>
          <div class="two-col">
            <div class="field">
              <label for="stage">Etapa de ensino</label>
              <select id="stage" name="stage" required>
                <option>Educação Infantil</option><option>Ensino Fundamental 1</option><option>Ensino Fundamental 2</option>
              </select>
            </div>
            <div class="field">
              <label for="grade">Faixa etária / ano</label>
              <select id="grade" name="grade" required></select>
            </div>
          </div>
          <button id="submit" type="submit"><span aria-hidden="true">✦</span> Gerar plano de aula</button>
          <p class="privacy">A pesquisa usa IA e fontes online; revise as habilidades antes de aplicar.</p>
        </form>
      </section>
      <section class="panel result-panel" aria-labelledby="result-title" aria-live="polite">
        <div class="result-head">
          <h2 id="result-title"><span aria-hidden="true">✺</span> Seu plano de aula</h2>
        </div>
        <div id="result" class="result-body">
          <div class="empty-state">
            <div class="empty-icon" aria-hidden="true">📚</div>
            <h3>Sua próxima aula começa aqui</h3>
            <p>Preencha os detalhes ao lado e seu plano aparecerá neste espaço.</p>
          </div>
        </div>
      </section>
    </div>
    <footer>As habilidades e referências são sugestões geradas por IA. Confira o documento oficial da BNCC e adapte ao contexto da turma.</footer>
  </main>
  <script>
    const levels = {
      "Educação Infantil": ["Bebês (0 a 1 ano e 6 meses)", "Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)", "Crianças pequenas (4 a 5 anos e 11 meses)"],
      "Ensino Fundamental 1": ["1º ano", "2º ano", "3º ano", "4º ano", "5º ano"],
      "Ensino Fundamental 2": ["6º ano", "7º ano", "8º ano", "9º ano"]
    };
    const stage = document.querySelector("#stage");
    const grade = document.querySelector("#grade");
    const form = document.querySelector("#plan-form");
    const result = document.querySelector("#result");
    const submit = document.querySelector("#submit");
    function updateGrades() {
      grade.replaceChildren(...levels[stage.value].map(value => new Option(value, value)));
    }
    stage.addEventListener("change", updateGrades);
    updateGrades();

    function element(tag, text, className) {
      const node = document.createElement(tag);
      if (text !== undefined) node.textContent = text;
      if (className) node.className = className;
      return node;
    }
    function addList(parent, title, icon, items, ordered) {
      const section = element("section", undefined, "plan-section");
      section.append(element("h3", `${icon} ${title}`));
      const list = element(ordered ? "ol" : "ul");
      for (const item of items) list.append(element("li", item));
      section.append(list);
      parent.append(section);
    }
    function renderPlan(plan) {
      result.replaceChildren();
      result.append(element("h3", plan.title, "plan-title"));
      result.append(element("p", `${plan.component} · ${plan.stage} · ${plan.grade}`, "plan-meta"));
      const skills = element("section", undefined, "plan-section");
      skills.append(element("h3", "🎯 Habilidades da BNCC"));
      if (plan.bncc_skills.length) {
        for (const item of plan.bncc_skills) {
          const card = element("div", undefined, "skill");
          card.append(element("span", item.code || "Habilidade relacionada", "skill-code"));
          card.append(element("p", item.description));
          if (item.justification) card.append(element("small", item.justification));
          skills.append(card);
        }
      } else {
        skills.append(element("p", "A pesquisa não encontrou uma habilidade específica que pudesse confirmar para este recorte. Consulte as fontes e valide o alinhamento antes de usar."));
      }
      result.append(skills);
      if (plan.verification_note) result.append(element("div", plan.verification_note, "note"));
      addList(result, "Objetivos de aprendizagem", "◎", plan.learning_objectives, false);
      addList(result, "Ideias de atividades — passo a passo", "✦", plan.activities, true);
      const assessment = element("section", undefined, "plan-section");
      assessment.append(element("h3", "✓ Avaliação"));
      assessment.append(element("p", plan.assessment, "assessment"));
      result.append(assessment);
      addList(result, "Recursos didáticos", "▧", plan.resources, false);
      if (plan.sources.length) {
        const sourceSection = element("section", undefined, "plan-section sources");
        sourceSection.append(element("h3", "↗ Fontes consultadas"));
        const list = element("ul");
        for (const source of plan.sources) {
          const item = element("li");
          const link = element("a", source.title || source.url);
          link.href = source.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          item.append(link);
          list.append(item);
        }
        sourceSection.append(list);
        result.append(sourceSection);
      }
    }
    form.addEventListener("submit", async event => {
      event.preventDefault();
      submit.disabled = true;
      submit.textContent = "Pesquisando a BNCC...";
      result.replaceChildren();
      const loading = element("div", undefined, "loading");
      loading.append(element("div", undefined, "spinner"));
      loading.append(element("strong", "Preparando seu plano"));
      loading.append(element("p", "A IA está pesquisando habilidades e referências oficiais."));
      result.append(loading);
      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        const response = await fetch("/api/generate", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Não foi possível gerar o plano.");
        renderPlan(data);
      } catch (error) {
        result.replaceChildren(element("div", error.message, "error"));
      } finally {
        submit.disabled = false;
        submit.innerHTML = '<span aria-hidden="true">✦</span> Gerar plano de aula';
      }
    });
  </script>
</body>
</html>
"""


class AIProviderError(Exception):
    """An expected error while contacting or interpreting the AI provider."""


def validate_request(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError("Envie os dados do formulário em formato JSON.")

    component = data.get("component")
    theme = data.get("theme")
    stage = data.get("stage")
    grade = data.get("grade")

    if not isinstance(component, str) or component not in COMPONENTS:
        raise ValueError("Selecione um componente curricular válido.")
    if not isinstance(theme, str) or not theme.strip():
        raise ValueError("Informe o tema da aula.")
    if len(theme.strip()) > MAX_THEME_LENGTH:
        raise ValueError(f"O tema deve ter no máximo {MAX_THEME_LENGTH} caracteres.")
    if not isinstance(stage, str) or stage not in LEVELS:
        raise ValueError("Selecione uma etapa de ensino válida.")
    if not isinstance(grade, str) or grade not in LEVELS[stage]:
        raise ValueError("Selecione uma faixa etária ou ano válido para a etapa escolhida.")

    return {
        "component": component,
        "theme": theme.strip(),
        "stage": stage,
        "grade": grade,
    }


def build_prompt(data: dict[str, str]) -> str:
    return f"""Pesquise na web, usando as fontes encontradas, as habilidades oficiais da Base Nacional Comum Curricular (BNCC) adequadas ao planejamento abaixo.
Componente informado: {data["component"]}
Etapa: {data["stage"]}
Faixa etária/ano: {data["grade"]}
Tema da aula: {data["theme"]}

Regras:
- Priorize fontes oficiais do MEC e documentos oficiais da BNCC. Não invente códigos, descrições, etapas ou citações.
- Se não conseguir confirmar uma habilidade específica para o componente, etapa e ano informados, retorne uma lista vazia e explique a limitação em verification_note.
- Diferencie habilidades da BNCC de objetivos e propostas pedagógicas autorais.
- Planeje atividades adequadas à idade, inclusivas, seguras e realizáveis; forneça passos numerados como itens da lista.
- Escreva em português brasileiro, com linguagem clara para docentes.
- Retorne somente um objeto JSON válido com estas chaves e tipos:
{{"title":"string","component":"string","stage":"string","grade":"string","bncc_skills":[{{"code":"string","description":"string","justification":"string"}}],"verification_note":"string","learning_objectives":["string"],"activities":["string"],"assessment":"string","resources":["string"]}}
- Inclua de 2 a 5 objetivos, 3 a 6 passos de atividade e 2 a 6 recursos. verification_note pode ser vazia quando não houver ressalvas.
"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise AIProviderError("A IA não retornou um plano estruturado. Tente novamente.")
    try:
        result = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIProviderError("A IA retornou uma resposta fora do formato esperado. Tente novamente.") from exc
    if not isinstance(result, dict):
        raise AIProviderError("A IA não retornou um plano estruturado. Tente novamente.")
    return result


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise AIProviderError(f"A IA retornou um plano incompleto ({field}). Tente novamente.")
    return [item.strip() for item in value]


def _normalize_plan(result: dict[str, Any], data: dict[str, str], sources: list[dict[str, str]]) -> dict[str, Any]:
    raw_skills = result.get("bncc_skills")
    if not isinstance(raw_skills, list):
        raise AIProviderError("A IA retornou habilidades em formato inválido. Tente novamente.")
    skills: list[dict[str, str]] = []
    for skill in raw_skills:
        if not isinstance(skill, dict) or not isinstance(skill.get("description"), str) or not skill["description"].strip():
            raise AIProviderError("A IA retornou uma habilidade incompleta. Tente novamente.")
        code = skill.get("code", "")
        justification = skill.get("justification", "")
        if not isinstance(code, str) or not isinstance(justification, str):
            raise AIProviderError("A IA retornou uma habilidade incompleta. Tente novamente.")
        skills.append({
            "code": code,
            "description": skill["description"].strip(),
            "justification": justification,
        })

    title = result.get("title")
    assessment = result.get("assessment")
    note = result.get("verification_note", "")
    if not isinstance(title, str) or not title.strip() or not isinstance(assessment, str) or not assessment.strip():
        raise AIProviderError("A IA retornou um plano incompleto. Tente novamente.")
    if not isinstance(note, str):
        raise AIProviderError("A IA retornou uma observação de pesquisa inválida. Tente novamente.")

    return {
        "title": title.strip(),
        "component": data["component"],
        "stage": data["stage"],
        "grade": data["grade"],
        "bncc_skills": skills,
        "verification_note": note.strip(),
        "learning_objectives": _string_list(result.get("learning_objectives"), "objetivos"),
        "activities": _string_list(result.get("activities"), "atividades"),
        "assessment": assessment.strip(),
        "resources": _string_list(result.get("resources"), "recursos"),
        "sources": sources,
    }


def _grounding_sources(response: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    candidates = response.get("candidates", [])
    if not isinstance(candidates, list):
        return sources
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        metadata = candidate.get("groundingMetadata", {})
        chunks = metadata.get("groundingChunks", []) if isinstance(metadata, dict) else []
        if not isinstance(chunks, list):
            continue
        for chunk in chunks:
            web = chunk.get("web", {}) if isinstance(chunk, dict) else {}
            uri = web.get("uri") if isinstance(web, dict) else None
            if not isinstance(uri, str) or not uri.startswith(("https://", "http://")) or uri in seen:
                continue
            seen.add(uri)
            title = web.get("title", "")
            sources.append({"url": uri, "title": title if isinstance(title, str) else ""})
    return sources


def generate_plan(data: dict[str, str]) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise AIProviderError(
            "A chave da IA não está configurada. Defina GEMINI_API_KEY no terminal e reinicie o aplicativo; consulte o README para instruções."
        )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?"
        + urlencode({"key": api_key})
    )
    body = {
        "contents": [{"parts": [{"text": build_prompt(data)}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.3},
    }
    request = Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            provider_response = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise AIProviderError("A chave da IA foi recusada. Confira GEMINI_API_KEY e tente novamente.") from exc
        raise AIProviderError("O serviço de IA não conseguiu concluir a pesquisa. Tente novamente em instantes.") from exc
    except (TimeoutError, URLError):
        raise AIProviderError("Não foi possível conectar ao serviço de IA. Confira sua conexão e tente novamente.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AIProviderError("O serviço de IA retornou uma resposta inválida. Tente novamente.") from None

    if not isinstance(provider_response, dict):
        raise AIProviderError("O serviço de IA retornou uma resposta inválida. Tente novamente.")
    candidates = provider_response.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise AIProviderError("A IA não encontrou uma resposta para esta solicitação. Tente reformular o tema.")
    if not isinstance(candidates[0], dict):
        raise AIProviderError("A IA retornou uma resposta incompleta. Tente novamente.")
    content = candidates[0].get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []
    text = "\n".join(
        part["text"] for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    if not text:
        raise AIProviderError("A IA não retornou conteúdo para o plano. Tente novamente.")
    plan = _extract_json(text)
    return _normalize_plan(plan, data, _grounding_sources(provider_response))


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "BNCCLessonPlanner/1.0"

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self._send_json(404, {"error": "Rota não encontrada."})
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("application/json"):
            self._send_json(415, {"error": "Envie os dados no formato JSON."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Tamanho da solicitação inválido."})
            return
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "A solicitação está vazia ou excede o limite permitido."})
            return
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            data = validate_request(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._send_json(400, {"error": str(exc) or "Os dados enviados são inválidos."})
            return
        try:
            plan = generate_plan(data)
        except AIProviderError as exc:
            self._send_json(502, {"error": str(exc)})
            return
        self._send_json(200, plan)

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid logging user-provided lesson themes.
        if self.path == "/":
            super().log_message(format, *args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"BNCC na prática disponível em http://{HOST}:{PORT}")
    if not os.environ.get("GEMINI_API_KEY"):
        print("Configure GEMINI_API_KEY no ambiente para habilitar a pesquisa com IA.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando o servidor.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
