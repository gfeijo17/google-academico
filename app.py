import os
import datetime
import requests
import streamlit as st
from google import genai

st.set_page_config(page_title="Pesquisador Acadêmico & Gemini", page_icon="🎓", layout="wide")

st.title("🎓 Pesquisador de Artigos Acadêmicos & Gemini")
st.markdown("Busque artigos no **Google Acadêmico (somente em Português)**, baixe PDFs e gere análises ou roteiros de Podcast estilo NotebookLM.")

# ==============================================================================
# CONFIGURAÇÃO DAS CHAVES
# ==============================================================================
GEMINI_KEY_PADRAO = "AQ.Ab8RN6IjIonUWlBXKv-rifYP8TYxHzqLX4JvJPHsmwsu3LTowQ"
SERPER_KEY_PADRAO = ""
# ==============================================================================

gemini_api_key = st.secrets.get("GEMINI_API_KEY", GEMINI_KEY_PADRAO).strip()
serper_api_key = st.secrets.get("SERPER_API_KEY", SERPER_KEY_PADRAO).strip()

# --- BARRA LATERAL INFORMATIVA ---
with st.sidebar:
    st.header("⚙️ Status da Conexão")
    if gemini_api_key and gemini_api_key != "SUA_CHAVE_DO_GEMINI_AQUI":
        st.success("✅ Gemini API Conectada")
    else:
        st.error("❌ Configure GEMINI_API_KEY nos Secrets")
        
    if serper_api_key and serper_api_key != "SUA_CHAVE_DO_SERPER_AQUI":
        st.success("✅ Google Scholar (Serper) Ativo")
    else:
        st.info("ℹ️ Modo demonstrativo ativo (Serper Key pendente)")

# --- 1. ENTRADA DO USUÁRIO ---
termo_busca = st.text_input("Qual o tema da pesquisa acadêmica?", placeholder="Ex: inteligência artificial na educação, psicologia cognitiva...")

def buscar_google_scholar(query, api_key, num_results=10):
    """Busca artigos acadêmicos em português via Serper Scholar API."""
    if not api_key or api_key == "SUA_CHAVE_DO_SERPER_AQUI":
        # Dados demonstrativos acadêmicos caso a chave não esteja configurada
        return [
            {
                "title": f"Estudo sobre {query}: Uma Análise Bibliográfica",
                "link": "https://www.scielo.br/pdf/example1.pdf",
                "snippet": "Este artigo analisa os principais avanços e metodologias aplicadas no contexto brasileiro.",
                "publication": "Revista Brasileira de Pesquisa (2024)",
                "pdf_link": "https://www.scielo.br/pdf/example1.pdf"
            } for i in range(1, num_results + 1)
        ]
    
    url = "https://google.serper.dev/scholar"
    payload = {
        "q": query,
        "gl": "br",
        "hl": "pt-br",
        "lr": "lang_pt",
        "num": num_results
    }
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        results = response.json().get('organic', [])
        artigos = []
        for r in results:
            pdf_url = None
            # Verifica se há link direto de PDF nos recursos do resultado
            if 'resources' in r and isinstance(r['resources'], list):
                for res in r['resources']:
                    if res.get('link', '').lower().endswith('.pdf') or 'pdf' in res.get('title', '').lower():
                        pdf_url = res.get('link')
                        break
            if not pdf_url and r.get('link', '').lower().endswith('.pdf'):
                pdf_url = r.get('link')

            artigos.append({
                "title": r.get('title', 'Sem título'),
                "link": r.get('link', '#'),
                "snippet": r.get('snippet', 'Sem resumo disponível.'),
                "publication": r.get('publicationInfo', 'Fonte não informada'),
                "pdf_link": pdf_url
            })
        return artigos
    else:
        st.error("Erro na busca acadêmica. Verifique a chave da API do Serper.")
        return []

@st.cache_data(show_spinner=False)
def baixar_arquivo_pdf(url):
    """Faz o download do PDF para disponibilizar o botão no Streamlit."""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None

# --- 2. BUSCA E EXIBIÇÃO ---
if st.button("Pesquisar no Google Acadêmico (10 Resultados PT-BR)", type="primary"):
    if not termo_busca:
        st.warning("Por favor, digite um tema para pesquisar.")
    else:
        with st.spinner("Buscando artigos científicos em português..."):
            st.session_state['resultados'] = buscar_google_scholar(termo_busca, serper_api_key, num_results=10)
            st.session_state['termo_pesquisado'] = termo_busca

# --- 3. SELEÇÃO E DOWNLOAD DE PDFS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    st.subheader(f"📚 Artigos Acadêmicos encontrados para: '{st.session_state['termo_pesquisado']}'")
    st.write("Marque as produções científicos que deseja analisar e/ou faça o download do PDF:")

    fontes_selecionadas = []
    
    for idx, item in enumerate(st.session_state['resultados']):
        col_check, col_info, col_pdf = st.columns([0.05, 0.75, 0.20])
        
        with col_check:
            marcado = st.checkbox("", key=f"flag_{idx}", value=True)
            
        with col_info:
            st.markdown(f"**[{item['title']}]({item['link']})**")
            st.caption(f"📖 *{item['publication']}*")
            st.write(item['snippet'])
            
        with col_pdf:
            if item['pdf_link']:
                pdf_bytes = baixar_arquivo_pdf(item['pdf_link'])
                if pdf_bytes:
                    st.download_button(
                        label="📄 Baixar PDF",
                        data=pdf_bytes,
                        file_name=f"artigo_{idx+1}.pdf",
                        mime="application/pdf",
                        key=f"pdf_down_{idx}"
                    )
                else:
                    st.markdown(f"[🔗 Acessar PDF]({item['pdf_link']})")
            else:
                st.caption("PDF direto indisponível")
                
        st.write("---")
        
        if marcado:
            fontes_selecionadas.append(item)

    # --- 4. CONEXÃO COM O GEMINI & OPÇÕES TIPO NOTEBOOK ---
    st.subheader("🚀 Processamento e Síntese no Gemini")
    
    if fontes_selecionadas:
        st.success(f"{len(fontes_selecionadas)} artigo(s) selecionado(s).")
        
        col_opcao, col_btn = st.columns([0.7, 0.3])
        with col_opcao:
            modelo_consumo = st.selectbox(
                "Escolha o formato de síntese (Estilo Notebook):",
                [
                    "🎙️ Roteiro de Podcast / Audio Overview (Diálogo entre 2 Apresentadores)",
                    "📚 Guia de Estudo Acadêmico & Principais Conceitos",
                    "📝 Resumo Executivo & Metodologias",
                    "📊 Análise Crítica e Lacunas de Pesquisa",
                    "❓ FAQ (Perguntas e Respostas Frequentes)"
                ]
            )
            
        with col_btn:
            st.write(" ")
            st.write(" ")
            enviar_notebook = st.button("Gerar com Gemini", type="primary")

        if enviar_notebook:
            if not gemini_api_key or gemini_api_key == "SUA_CHAVE_DO_GEMINI_AQUI":
                st.error("Configure sua GEMINI_API_KEY nos Secrets do Streamlit Cloud.")
            else:
                with st.spinner("Analisando referências científicas e gerando o material..."):
                    try:
                        client = genai.Client(api_key=gemini_api_key.strip())
                        
                        contexto_fontes = "\n\n".join([
                            f"Título: {f['title']}\nPublicação: {f['publication']}\nLink: {f['link']}\nResumo: {f['snippet']}"
                            for f in fontes_selecionadas
                        ])
                        
                        instrucao_formato = ""
                        if "Podcast" in modelo_consumo:
                            instrucao_formato = """
                            Crie um roteiro dinâmico e envolvente de áudio/podcast no estilo 'Audio Overview' (estilo NotebookLM) entre dois apresentadores:
                            - **Apresentador A (Anfitrião):** Conduz a conversa, traz tópicos e faz perguntas inteligentes.
                            - **Apresentador B (Especialista):** Explica os conceitos técnicos de forma clara e acessível, citando os estudos encontrados.
                            Mantenha um tom natural, educativo e entusiasmado em português do Brasil.
                            """
                        else:
                            instrucao_formato = f"Elabore um relatório técnico-acadêmico estruturado no formato: {modelo_consumo}."

                        prompt_sistema = f"""
                        Você é um pesquisador acadêmico sênior.
                        Analise os seguintes artigos científicos sobre '{st.session_state['termo_pesquisado']}':

                        --- ARTIGOS SELECIONADOS ---
                        {contexto_fontes}
                        --- FIM DOS ARTIGOS ---

                        {instrucao_formato}

                        Sempre cite os títulos dos artigos e autoria/fontes quando indicar descobertas ou dados específicos.
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt_sistema
                        )
                        
                        st.session_state['relatorio_gerado'] = response.text
                        st.session_state['modelo_escolhido'] = modelo_consumo
                        
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar com a API do Gemini: {e}")

        # --- EXIBIÇÃO DO RESULTADO E BOTÃO DE DOWNLOAD ---
        if 'relatorio_gerado' in st.session_state:
            st.balloons()
            st.subheader(f"📑 Resultado: {st.session_state['modelo_escolhido']}")
            st.markdown(st.session_state['relatorio_gerado'])

            data_atual = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
            conteudo_download = f"""================================================================================
RELATÓRIO ACADÊMICO: {st.session_state['termo_pesquisado'].upper()}
Formato: {st.session_state['modelo_escolhido']}
Data da Geracão: {data_atual}
================================================================================

{st.session_state['relatorio_gerado']}

================================================================================
Referências Bibliográficas Utilizadas:
"""
            for f in fontes_selecionadas:
                conteudo_download += f"- {f['title']} | {f['publication']} | Link: {f['link']}\n"

            nome_arquivo = f"relatorio_academico_{st.session_state['termo_pesquisado'].lower().replace(' ', '_')}.txt"

            st.write("---")
            st.download_button(
                label="📥 Baixar Análise / Roteiro em Arquivo de Texto (.txt)",
                data=conteudo_download,
                file_name=nome_arquivo,
                mime="text/plain",
                type="secondary"
            )

    else:
        st.warning("Selecione pelo menos um artigo para continuar.")
