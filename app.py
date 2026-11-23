import streamlit as st
import pandas as pd
import io
import random
from itertools import cycle, islice

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Alocador Pro V3",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    h1 {color: #2c3e50; font-family: 'Helvetica', sans-serif;}
    .stMetric {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px;}
    .dataframe {font-size: 12px;}
</style>
""", unsafe_allow_html=True)


# --- CLASSE DE DISTRIBUIÇÃO ---
class DistribuidorSeparado:
    def __init__(self, fixos, rotativos, n_amostras_teste, n_colunas_excel):
        self.fixos = fixos
        self.rotativos = rotativos

        # Quantos produtos a pessoa VAI USAR
        self.n_amostras = n_amostras_teste

        # Quantas colunas o Excel VAI TER
        self.n_colunas = n_colunas_excel

        # Quantos rotativos precisamos sortear para completar as amostras
        self.n_rotativos_necessarios = self.n_amostras - len(fixos)

    def processar(self, df_input, cols_cota):
        df = df_input.copy()

        # Validações de Segurança
        if self.n_rotativos_necessarios < 0:
            st.error(
                f"Erro: Você pediu {self.n_amostras} amostras, mas já tem "
                f"{len(self.fixos)} produtos fixos. O total excede o pedido."
            )
            return None

        if self.n_colunas < self.n_amostras:
            st.error(
                f"Erro: O Excel tem menos colunas ({self.n_colunas}) do que "
                f"produtos a testar ({self.n_amostras})."
            )
            return None

        cols_output = [f'Posicao_{i+1}' for i in range(self.n_colunas)]
        for col in cols_output:
            df[col] = None

        todos_produtos = list(dict.fromkeys(self.fixos + self.rotativos))

        # Se não houver rotativos, distribui apenas os fixos equilibrando posições
        if not self.rotativos:
            self._distribuir_apenas_fixos(df, cols_output, todos_produtos)
            return df

        # Lógica de Distribuição por Cota (ou Geral)
        if not cols_cota:
            self._distribuir_grupo(df, df.index, cols_output, todos_produtos)
        else:
            try:
                for c in cols_cota:
                    df[c] = df[c].fillna("Indefinido")

                grupos = df.groupby(cols_cota)
                for _, group in grupos:
                    self._distribuir_grupo(df, group.index, cols_output, todos_produtos)
            except Exception as e:
                st.error(f"Erro ao processar colunas de cota: {e}")
                return None

        return df

    def _posicionar_mao_equilibrada(self, mao, cols_output, contagem_pos):
        """
        Posiciona os produtos da mão do participante buscando equilíbrio entre
        as colunas de posição dentro do grupo, mantendo desempate aleatório.
        """
        qtd_itens = min(len(mao), len(cols_output))
        mao_ordenada = [None] * qtd_itens
        posicoes_disponiveis = list(range(qtd_itens))

        itens = mao[:qtd_itens].copy()
        random.shuffle(itens)

        for produto in itens:
            livres = [p for p in posicoes_disponiveis if mao_ordenada[p] is None]
            random.shuffle(livres)
            melhor_pos = min(livres, key=lambda p: contagem_pos[produto][p])
            mao_ordenada[melhor_pos] = produto
            contagem_pos[produto][melhor_pos] += 1

        return mao_ordenada

    def _distribuir_grupo(self, df_geral, indices_grupo, cols_output, todos_produtos):
        qtd_pessoas = len(indices_grupo)
        total_itens_necessarios = qtd_pessoas * self.n_rotativos_necessarios

        if total_itens_necessarios > 0:
            baralho = list(islice(cycle(self.rotativos), total_itens_necessarios))
            random.shuffle(baralho)
        else:
            baralho = []

        contagem_pos = {
            prod: [0] * len(cols_output) for prod in todos_produtos
        }

        contador_baralho = 0

        for idx in indices_grupo:
            minha_mao = self.fixos.copy()

            for _ in range(self.n_rotativos_necessarios):
                if contador_baralho < len(baralho):
                    carta = baralho[contador_baralho]

                    # Evita repetição imediata na mesma mão quando houver alternativa
                    if carta in minha_mao and len(self.rotativos) > 1:
                        if contador_baralho + 1 < len(baralho):
                            carta_prox = baralho[contador_baralho + 1]
                            if carta_prox not in minha_mao:
                                baralho[contador_baralho], baralho[contador_baralho + 1] = (
                                    baralho[contador_baralho + 1],
                                    baralho[contador_baralho],
                                )
                                carta = baralho[contador_baralho]

                    minha_mao.append(carta)
                    contador_baralho += 1

            mao_posicionada = self._posicionar_mao_equilibrada(
                minha_mao, cols_output, contagem_pos
            )

            for i, produto in enumerate(mao_posicionada):
                df_geral.at[idx, cols_output[i]] = produto

    def _distribuir_apenas_fixos(self, df, cols_output, todos_produtos):
        contagem_pos = {
            prod: [0] * len(cols_output) for prod in todos_produtos
        }
        for idx in df.index:
            mao_posicionada = self._posicionar_mao_equilibrada(
                self.fixos.copy(), cols_output, contagem_pos
            )
            for i, prod in enumerate(mao_posicionada):
                df.at[idx, cols_output[i]] = prod


# --- INTERFACE SIDEBAR ---
with st.sidebar:
    col_logo, col_txt = st.columns([1, 4])
    try:
        st.image("logo.png", use_container_width=True)
    except Exception:
        st.write("## 🧪 Allocator")

    st.markdown("---")
    st.header("1. Configuração")

    tipo_input = st.radio("Fonte de Dados:", ["Upload de Arquivo", "Gerar IDs (Simples)"])

    df_upload = None
    cols_cota = []

    if tipo_input == "Upload de Arquivo":
        arquivo = st.file_uploader("Arraste o Excel/CSV aqui", type=['xlsx', 'csv'])
        if arquivo:
            try:
                if arquivo.name.endswith('.csv'):
                    df_upload = pd.read_csv(arquivo)
                else:
                    df_upload = pd.read_excel(arquivo)
                st.success(f"✅ {len(df_upload)} participantes carregados.")

                st.markdown("**Balanceamento (Cotas):**")
                cols_ignorar = ['id', 'nome', 'celular', 'obs', 'data', 'email', 'telefone']
                cols_possiveis = [c for c in df_upload.columns if c.lower() not in cols_ignorar]
                cols_cota = st.multiselect("Equilibrar produtos por:", options=cols_possiveis)

            except Exception:
                st.error("Erro ao ler arquivo.")
    else:
        num_ids = st.number_input("Quantidade de IDs", value=50, step=10)
        df_upload = pd.DataFrame({'ID': range(1, num_ids + 1)})

    st.markdown("---")
    st.header("2. Produtos")

    col1, col2 = st.columns(2)
    with col1:
        fixos_txt = st.text_area("Fixos (Obrigatórios)", placeholder="Ex: Controle", height=100)
    with col2:
        rot_txt = st.text_area("Rotativos (Sorteio)", value="P1, P2, P3", height=100)

    l_fixos = [x.strip() for x in fixos_txt.split(',') if x.strip()]
    l_rotativos = [x.strip() for x in rot_txt.split(',') if x.strip()]

    st.markdown("---")
    st.header("3. Regras do Estudo")

    col_dias, col_amostras = st.columns(2)

    with col_dias:
        n_colunas = st.number_input(
            "Colunas no Excel",
            min_value=1, value=5,
            help="Quantas colunas de 'Posição' serão criadas no arquivo final? (Ex: Duração do estudo)"
        )

    with col_amostras:
        n_amostras = st.number_input(
            "Amostras por Pessoa",
            min_value=1, value=5,
            help="Quantos produtos cada pessoa vai testar de fato?"
        )

    if n_amostras > n_colunas:
        st.error("⚠️ Erro: Você quer testar mais produtos do que existem colunas disponíveis!")

    st.markdown("---")
    btn_gerar = st.button("🚀 GERAR DISTRIBUIÇÃO", type="primary")


# --- ÁREA PRINCIPAL ---
st.title("Gerador de Rodízio Balanceado")

if btn_gerar:
    if df_upload is None:
        st.warning("Por favor, carregue um arquivo ou defina os IDs.")
    elif (len(l_fixos) + len(l_rotativos)) == 0:
        st.warning("Cadastre os produtos antes de continuar.")
    else:
        motor = DistribuidorSeparado(l_fixos, l_rotativos, n_amostras, n_colunas)

        with st.spinner("Calculando equidade e distribuindo posições..."):
            df_final = motor.processar(df_upload, cols_cota)

            if df_final is not None:
                st.session_state['resultado_v3'] = df_final
                st.session_state['params_v3'] = (l_fixos, l_rotativos)
                st.toast("Matriz gerada com sucesso!", icon="✅")


# --- VISUALIZAÇÃO E AUDITORIA ---
if 'resultado_v3' in st.session_state:
    df = st.session_state['resultado_v3']
    fixos, rotativos = st.session_state['params_v3']

    tab1, tab2, tab3 = st.tabs(["📄 Base Final", "🔍 Auditoria (Visual Melhorado)", "📥 Download"])

    with tab1:
        st.dataframe(df, use_container_width=True)
        st.caption(f"Total de Linhas: {len(df)}")

    with tab2:
        st.markdown("### 📊 Raio-X da Distribuição")

        if cols_cota:
            st.markdown(f"**Verificando equilíbrio dentro de: {cols_cota[0]}**")
            opcoes = ["Todos"] + sorted(list(df[cols_cota[0]].astype(str).unique()))
            escolha = st.selectbox("Filtrar Grupo:", opcoes)

            if escolha != "Todos":
                df_audit = df[df[cols_cota[0]].astype(str) == escolha]
            else:
                df_audit = df
        else:
            df_audit = df

        cols_pos = [c for c in df_audit.columns if 'Posicao' in c]
        produtos_usados = df_audit[cols_pos].values.flatten()
        produtos_usados = [x for x in produtos_usados if pd.notna(x)]

        if produtos_usados:
            contagem = pd.Series(produtos_usados).value_counts().reset_index()
            contagem.columns = ['Produto', 'Qtd Real']

            c1, c2 = st.columns([1, 2])
            with c1:
                st.write("**Contagem Total**")
                st.dataframe(
                    contagem.style.bar(subset=['Qtd Real'], color='#d65f5f'),
                    use_container_width=True,
                    hide_index=True
                )
            with c2:
                st.write("**Distribuição por Posição (Heatmap)**")
                st.info("Verifique se as frequências estão equilibradas entre posições mantendo a aleatoriedade.")

                df_melt = df_audit.melt(value_vars=cols_pos, var_name="Ordem", value_name="Produto")
                df_melt = df_melt.dropna(subset=["Produto"])
                heatmap = pd.crosstab(df_melt['Produto'], df_melt['Ordem'])

                st.dataframe(heatmap.style.background_gradient(cmap="Blues"), use_container_width=True)

                st.write("**Gráfico de Colunas por Posição**")
                st.bar_chart(heatmap)
        else:
            st.warning("Nenhum produto encontrado nas colunas de posição.")

    with tab3:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Base_Gerada")
            if produtos_usados:
                contagem.to_excel(writer, index=False, sheet_name="Resumo_Auditoria")

        st.download_button(
            label="📥 Baixar Excel Completo",
            data=buffer.getvalue(),
            file_name="Rodizio_Final_Pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
