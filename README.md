# BNCC na prática

Aplicação local para gerar planos de aula com pesquisa de habilidades da BNCC usando Gemini e Google Search grounding.

## Requisitos

- Python 3.10 ou superior
- Acesso à internet
- Uma chave da API Gemini configurada no ambiente (`GEMINI_API_KEY`)

## Executar no Windows

No PowerShell, na pasta do projeto:

```powershell
$env:GEMINI_API_KEY = "sua-chave-da-api"
python app.py
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) no navegador. A chave pode ser obtida no [Google AI Studio](https://aistudio.google.com/apikey). O servidor usa `127.0.0.1` por padrão, então a aplicação fica acessível apenas no próprio computador. Para alterar a porta, defina `PORT` antes de iniciar.

Opcionalmente, escolha outro modelo compatível definindo `GEMINI_MODEL`; o padrão é `gemini-2.5-flash`.

## O que o gerador prepara

- Habilidades da BNCC relacionadas ao componente, à etapa, à faixa etária/ano e ao tema
- Objetivos de aprendizagem
- Atividades em passos
- Sugestão de avaliação
- Recursos didáticos
- Links das fontes encontradas na pesquisa

A aplicação não substitui a consulta ao documento oficial. A disponibilidade e a precisão das referências dependem das fontes retornadas pela pesquisa; revise os códigos e as propostas, considerando o currículo da rede e as necessidades da turma. Se não for possível confirmar uma habilidade específica, o gerador deve sinalizar isso em vez de inventar um código.
