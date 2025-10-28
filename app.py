import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import re

# --- Configuração da Página ---
st.set_page_config(
    page_title="Análise de Algoritmos Híbridos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Funções de Carregamento de Dados (com Cache) ---

@st.cache_data
def load_data():
    """Carrega todos os arquivos CSV necessários."""
    try:
        df_bubble = pd.read_csv("merge-bubble-summary_results.csv")
        df_insertion = pd.read_csv("merge-insertion-summary_results.csv")
        df_best = pd.read_csv("melhores_resultados_merge_hibridos.csv")
        df_bubble_raw = pd.read_csv("merge-bubble-raw_times.csv")
        df_insertion_raw = pd.read_csv("merge-insertion-raw_times.csv")
        return df_bubble, df_insertion, df_best, df_bubble_raw, df_insertion_raw
    except FileNotFoundError as e:
        st.error(f"Erro ao carregar o arquivo: {e.filename}. Certifique-se de que todos os arquivos CSV (e imagens) estão na mesma pasta que o app.py.")
        return None, None, None

@st.cache_data
def load_code(file_path):
    """Carrega os arquivos de código .c como texto."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: Arquivo {file_path} não encontrado."

def extract_function(code, function_name):
    """Extrai uma função específica do código C para exibição."""
    try:
        match = re.search(r'void\s+' + re.escape(function_name) + r'\s*\([^\)]*\)\s*\{[^\}]*\}', code, re.S)
        if match:
            return match.group(0)
        return f"Função {function_name} não encontrada."
    except Exception:
        return "Erro ao processar o código."

@st.cache_data
def analyze_thresholds(df_raw, name):
    """Analisa o dataframe para encontrar o melhor threshold para cada tamanho."""
    # Encontra o índice (linha) do menor 'MediaReal' para cada 'Tamanho'
    idx_best_times = df_raw.groupby('Tamanho')['MediaReal'].idxmin()
    # Usa esses índices para selecionar as linhas correspondentes
    best_thresholds_df = df_raw.loc[idx_best_times][['Tamanho', 'Threshold', 'MediaReal']]
    best_thresholds_df = best_thresholds_df.rename(columns={'Threshold': f'Melhor_Threshold_{name}'})
    return best_thresholds_df

# --- Funções de Geração de Gráficos ---

def create_theory_chart(df_raw, title):
    """Cria o gráfico de comparação do tempo real vs. complexidade teórica."""
    
    # 1. Processar: Agrupar por 'Tamanho' e pegar o menor tempo (melhor threshold)
    df_agg = df_raw.groupby('Tamanho')['MediaReal'].min().reset_index()
    df_agg = df_agg.rename(columns={'MediaReal': 'TempoRealMinimo'})

    # 2. Adicionar Funções Teóricas
    df_agg['n'] = df_agg['Tamanho']
    df_agg['n log n'] = df_agg['Tamanho'] * np.log(df_agg['Tamanho'])
    # Removida a linha n^2 conforme solicitação #5

    # 3. Escalar Funções Teóricas
    max_time = df_agg['TempoRealMinimo'].max()
    df_agg['n log n'] = df_agg['n log n'].replace(0, 1e-9)

    df_agg['n (escalado)'] = df_agg['n'] * (max_time / df_agg['n'].max())
    df_agg['n log n (escalado)'] = df_agg['n log n'] * (max_time / df_agg['n log n'].max())
    # Removida a linha n^2 (escalado)

    # 4. Preparar para o Gráfico (Melt)
    df_melt = df_agg.melt(
        id_vars=['Tamanho'],
        # Removido 'n^2 (escalado)' da lista
        value_vars=['TempoRealMinimo', 'n (escalado)', 'n log n (escalado)'],
        var_name='Métrica',
        value_name='Tempo (s)'
    )

    # 5. Criar o Gráfico Altair
    # Solicitação #6: Gráficos interativos com filtros.
    # O .interactive() já permite zoom/pan e clique na legenda para filtrar.
    chart = alt.Chart(df_melt).mark_line(point=True).encode(
        x=alt.X('Tamanho', title='Tamanho da Entrada (n)'),
        y=alt.Y('Tempo (s)', title='Tempo de Execução (escalado)'),
        color=alt.Color('Métrica', title='Métrica de Desempenho'),
        tooltip=['Tamanho', 'Métrica', alt.Tooltip('Tempo (s)', format='.8f')]
    ).properties(
        title=title
    ).interactive() # Habilita zoom, pan e filtro pela legenda
    
    return chart

def create_comparison_chart(df_raw):
    """Cria o gráfico comparativo final garantindo que Merge+Insertion, Merge+Bubble e Merge Puro apareçam."""

    # Separar dados
    df_merge = df_raw[df_raw['Threshold'] == -1].copy()
    df_hybrid = df_raw[df_raw['Threshold'] > -1].copy()

    # Padronizar nomes
    df_hybrid['Algoritmo'] = df_hybrid['Algoritmo'].replace({
        'merge+insertion': 'Merge+Insertion',
        'merge+bubble': 'Merge+Bubble'
    })
    df_merge['Algoritmo'] = 'Merge Puro'

    # Selecionar o melhor threshold para cada híbrido
    best_hybrid_list = []
    for algo in ['Merge+Insertion', 'Merge+Bubble']:
        df_algo = df_hybrid[df_hybrid['Algoritmo'] == algo]
        if not df_algo.empty:
            idx_best = df_algo.groupby('Tamanho')['MediaReal'].idxmin()
            best_hybrid_list.append(df_algo.loc[idx_best])
    df_best_hybrid = pd.concat(best_hybrid_list, ignore_index=True)

    # Concatenar Merge Puro
    df_plot = pd.concat([df_best_hybrid, df_merge], ignore_index=True)

    # Preparar Altair
    df_melt = df_plot.melt(
        id_vars=['Tamanho', 'Algoritmo'],
        value_vars=['MediaReal'],
        var_name='Métrica',
        value_name='Tempo (s)'
    )

    # Linhas teóricas
    n_vals = np.linspace(df_plot['Tamanho'].min(), df_plot['Tamanho'].max(), 200)
    max_obs = df_plot['MediaReal'].max()

    df_theory_log = pd.DataFrame({
        'Tamanho': n_vals,
        'Tempo (s)': n_vals * np.log2(n_vals) * (max_obs / (n_vals * np.log2(n_vals)).max()),
        'Algoritmo': 'n·log(n)'
    })

    df_theory_n = pd.DataFrame({
        'Tamanho': n_vals,
        'Tempo (s)': n_vals * (max_obs / n_vals.max()),
        'Algoritmo': 'n'
    })

    df_final = pd.concat([df_melt[['Tamanho', 'Tempo (s)', 'Algoritmo']], df_theory_log, df_theory_n], ignore_index=True)

    # Cores fixas
    color_scale = alt.Scale(domain=[
        'Merge+Insertion', 'Merge Puro', 'Merge+Bubble', 'n·log(n)', 'n'
    ], range=[
        'blue', 'orange', 'red', 'green', 'purple'
    ])

    chart = alt.Chart(df_final).mark_line().encode(
        x=alt.X('Tamanho', title='Tamanho da Entrada (n)'),
        y=alt.Y('Tempo (s)', title='Tempo de Execução (s)'),
        color=alt.Color('Algoritmo', scale=color_scale, title='Algoritmo/Teórico'),
        tooltip=['Tamanho', 'Algoritmo', 'Tempo (s)']
    ).properties(
        title='Análise Comparativa Final: Híbridos vs. Merge Puro'
    ).interactive()

    return chart

# --- Carregamento Principal ---
df_bubble, df_insertion, df_best, df_bubble_raw, df_insertion_raw = load_data()
code_merge4 = load_code('merge4_final.c')
code_merge5 = load_code('merge5_final.c')
code_best_merge = load_code('process_best_merge_results.c')
code_best_insertion = load_code('process_best_mergeinsertion_results.c')
code_best_bubble = load_code('process_best_mergebubble_results.c')

# Análise de Threshold (para Solicitação #8)
if df_insertion is not None and df_bubble is not None:
    best_thresholds_insertion = analyze_thresholds(df_insertion, "Insertion")
    best_thresholds_bubble = analyze_thresholds(df_bubble, "Bubble")
else:
    best_thresholds_insertion = pd.DataFrame()
    best_thresholds_bubble = pd.DataFrame()


# --- Interface do Streamlit (Navegação) ---
st.sidebar.title("Navegação da Análise")
page = st.sidebar.radio("Ir para:", [
    "Apresentação",
    "Introdução",
    "1. Fundamentos (Algoritmos Base)",
    "2. Metodologia Experimental",
    "3. Análise de Complexidade Teórica",
    "4. Resultados Visuais (Gráficos)",
    "5. Conclusões",
    "Apêndice: Códigos-Fonte (.c)",
    "Apêndice: Dados Brutos (.csv)"
])

# --- Conteúdo das Páginas ---
if page == "Apresentação":
    st.set_page_config(page_title="Análise Mergesort Híbrido")
    st.title("Análise de Desempenho: Otimizando o Merge Sort com Hibridização")
    st.markdown("---")
    st.markdown("Universidade Federal do Rio Grande do Sul (UFRGS) | Pós-Graduação em Ciência da Computação | CMP 625 - Algorithms")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Aluno:** Tiago Rios da Rocha")
    with col2:
        st.markdown("**Professor:** Nicolas Maillard")
    st.divider()
    st.subheader("Objetivo da Análise")
    st.markdown("""
    Bem-vindos. Esta apresentação investiga um problema clássico na otimização de algoritmos: o **custo da recursão**.

    O Merge Sort é mundialmente famoso por sua excelente complexidade teórica de $\Theta(n \log n)$. No entanto, o *overhead* (custo computacional) de suas chamadas de função pode ser ineficiente para ordenar sub-arrays muito pequenos.

    **A hipótese deste trabalho é que podemos obter um ganho de desempenho prático ao criar um algoritmo híbrido.**
    
    A estratégia é parar a recursão quando o array for pequeno o suficiente (definido por um `THRESHOLD`) e usar um algoritmo quadrático mais simples, como o Insertion Sort ou o Bubble Sort, para finalizar o trabalho.
    """)    

elif page == "Introdução":
    st.title("Análise de Desempenho: Otimizando o Merge Sort com Hibridização")
    st.markdown("""
    Esta aplicação apresenta uma análise completa de algoritmos de ordenação híbridos.
    O objetivo é investigar se a substituição da recursão profunda do Merge Sort
    por algoritmos quadráticos (Bubble Sort e Insertion Sort) em sub-arrays pequenos
    resulta em uma otimização de desempenho.
    """)
    
    # Solicitação #1: Adicionar imagem do processo híbrido
    st.subheader("Visualização da Estratégia Híbrida (THRESHOLD = 6)")
    try:
        # Você deve criar e nomear esta imagem
        st.image("merge_bubble_threshold_6.png", 
                 caption="Ilustração do Merge Sort dividindo o array até o THRESHOLD=6. "
                         "A partir daí, o Bubble Sort (ou Insertion Sort) assume para ordenar os sub-arrays.", width=500)
    except FileNotFoundError:
        st.warning("Arquivo 'merge_bubble_threshold_6.png' não encontrado. "
                   "Por favor, crie a imagem e coloque na pasta.")

    st.markdown("Use a barra de navegação à esquerda para explorar as diferentes seções da análise.")


elif page == "1. Fundamentos (Algoritmos Base)":
    st.header("1. Fundamentos: Os Blocos de Construção")
    
    tab1, tab2, tab3 = st.tabs(["Merge Sort", "Bubble Sort", "Insertion Sort"])
    
    with tab1:
        st.subheader("Merge Sort")
        # Solicitação #2: Adicionar imagem
        try:
            st.image("merge.png", caption="Visualização do processo de Divisão e Conquista do Merge Sort.")
        except FileNotFoundError:
            st.warning("Arquivo 'merge.png' não encontrado.")
            
        st.markdown("""
        - **Conceito:** Um algoritmo clássico de "Divisão e Conquista".
        - **Complexidade Teórica:** $\Theta(n \log n)$ em todos os casos.
        - **Problema:** A recursão tem um "custo" (overhead) que pode ser ineficiente para arrays muito pequenos.
        """)
        
    with tab2:
        st.subheader("Bubble Sort")
        # Solicitação #3: Adicionar imagem
        try:
            st.image("bubble.png", caption="Visualização do processo de 'borbulhamento' do Bubble Sort.")
        except FileNotFoundError:
            st.warning("Arquivo 'bubble.png' não encontrado.")
            
        st.markdown("""
        - **Conceito:** Um algoritmo de ordenação quadrático simples ($\Theta(n^2)$).
        - **Como funciona:** Compara repetidamente elementos adjacentes e os troca se estiverem na ordem errada.
        """)
        st.code(extract_function(code_merge4, "bubbleSort"), language='c')

    with tab3:
        st.subheader("Insertion Sort")
        # Solicitação #4: Adicionar imagem
        try:
            st.image("insertion.png", caption="Visualização do processo de 'inserção' do Insertion Sort.")
        except FileNotFoundError:
            st.warning("Arquivo 'insertion.png' não encontrado.")
            
        st.markdown("""
        - **Conceito:** Outro algoritmo quadrático ($\Theta(n^2)$).
        - **Característica Especial:** Extremamente rápido para arrays pequenos e arrays "quase ordenados".
        """)
        st.code(extract_function(code_merge5, "insertionSort"), language='c')

elif page == "2. Metodologia Experimental":
    st.header("2. Metodologia Experimental")
    
    st.subheader("A Estratégia Híbrida")
    st.markdown("""
    O objetivo é combinar o melhor dos dois mundos:
    - Usar a eficiência $\Theta(n \log n)$ do **Merge Sort** para dividir o problema grande.
    - Usar a eficiência do **Insertion/Bubble Sort** em arrays pequenos para eliminar o custo da recursão profunda.
    
    A estratégia é definida por um **Limiar (THRESHOLD)**:
    - **Se `n > THRESHOLD`:** O algoritmo se comporta como o Merge Sort (divide e conquista).
    - **Se `n <= THRESHOLD`:** O algoritmo para de recorrer e ordena o sub-array pequeno usando o método quadrático.
    """)
    
    st.subheader("Lógica de Hibridização no Código (merge5_final.c)")
    st.code("""
    void mergeSort(int arr[], int l, int r, int THRESHOLD) {
        if (l < r) {
            // Condição de Hibridização
            if (r - l + 1 <= THRESHOLD) {
                insertionSort(arr, l, r); // Caso Base Otimizado
            } else {
                int m = l + (r - l) / 2;
                mergeSort(arr, l, m, THRESHOLD);
                mergeSort(arr, m + 1, r, THRESHOLD);
                merge(arr, l, m, r);
            }
        }
    }
    """, language='c')
    
    st.divider()
    st.subheader("Execução dos Testes e Coleta de Dados")
    st.markdown("""
    Para garantir a confiabilidade estatística dos resultados, cada algoritmo foi submetido a um rigoroso processo de benchmarking. A análise dos arquivos `raw_times.csv` revela uma metodologia adaptativa:
    
    1.  **Execuções de 50x (Testes Rápidos):**
        * Para a grande maioria das entradas (ex: `Tamanho` de 3 até 335,544,320), cada combinação de `Tamanho` e `Threshold` foi executada **50 vezes**. Isso garante uma alta confiança estatística nos resultados para os casos de teste mais rápidos.
    
    2.  **Execuções de 10x (Testes Lentos):**
        * Para as entradas de `Tamanho` muito grande (ex: 671,088,640 e 1,342,177,280), que são computacionalmente caras, o número de execuções foi reduzido para **10 vezes** para manter o tempo total de benchmark viável.

    Para **todas** as combinações, foram calculadas as seguintes métricas (presentes nas planilhas `summary_results`):
    """)
    
    st.markdown(r"""
    * **Média (MediaCPU, MediaReal):** O tempo médio de execução das corridas (10 ou 50). Esta é a métrica central usada para comparar o desempenho.
        $$\text{Média} = \frac{\sum_{i=1}^{N} \text{Tempo}_i}{N} \quad (N=10 \text{ ou } 50)$$
    * **Desvio Padrão (DesvioCPU, DesvioReal):** Mede a *variabilidade* ou *dispersão* dos tempos. Um desvio padrão baixo (próximo de zero), como os observados nos dados, indica que os resultados das execuções foram muito consistentes e confiáveis.
    
    Os gráficos nas seções seguintes utilizam a **menor média** (`MediaReal.min()`) encontrada para cada `Tamanho`, representando o desempenho ótimo do algoritmo (ou seja, o melhor `Threshold` para aquele `Tamanho`).
    """)

elif page == "3. Análise de Complexidade Teórica":
    st.header("3. Análise de Complexidade Teórica")
    st.markdown("A recorrência para **todos** os três algoritmos (Puro e Híbridos) é a mesma:")
    st.latex(r"T(n) = 2T(n/2) + \Theta(n)")
    
    st.markdown("""
    - **`a = 2`**: O algoritmo faz duas chamadas recursivas.
    - **`b = 2`**: O problema é dividido pela metade.
    - **`f(n) = \Theta(n)`**: O custo da função `merge` para combinar as metades é linear.
    
    O trabalho no caso base (Bubble/Insertion) é $O(k^2)$, onde `k=THRESHOLD`. Como `k` é uma **constante**, esse custo não altera a complexidade assintótica geral.
    """)
    
    st.subheader("Aplicando o Teorema Mestre (Caso 2)")
    st.markdown("1. **Calcular Função Crítica:** $n^{\log_b a} = n^{\log_2 2} = n^1 = n$")
    st.markdown("2. **Comparar:** O custo $f(n) = \Theta(n)$ está em equilíbrio com a função crítica $\Theta(n)$.")
    st.markdown("3. **Concluir:** A solução é $\Theta(n^{\log_b a} \log n)$, o que resulta em:")
    st.latex(r"T(n) = \Theta(n \log n)")
    
    st.success("**Conclusão Teórica:** Todos os algoritmos analisados possuem uma complexidade de tempo assintótica de $\Theta(n \log n)$.")

elif page == "4. Resultados Visuais (Gráficos)":
    st.header("4. Resultados Visuais (Gráficos)")
    st.markdown("Os dados empíricos validam a nossa análise teórica.")
    
    # Solicitação #7: O gráfico comparativo é o de best_results_analysis.ipynb
    if df_best is not None:
        st.subheader("Análise Comparativa Final: Híbridos vs. Puro")
        chart_comparison = create_comparison_chart(df_best)
        st.altair_chart(chart_comparison, use_container_width=True)
        st.markdown("""
        **Análise:** Este gráfico compara o melhor desempenho de cada algoritmo:
        - **Linha Azul (Merge+Insertion):** É o algoritmo mais rápido na prática.
        - **Linha Laranja (Merge Puro):** É a nossa linha de base.
        - **Linha Vermelha (Merge+Bubble):** É o algoritmo mais lento.
        - **Linha Verde (n·log(n)):** Representa o crescimento esperado pela complexidade teórica $\Theta(n \log n)$.
        - **Linha Roxa (n):** Representa o crescimento linear de referência.
        """)
    else:
        st.warning("Arquivo 'melhores_resultados_merge_hibridos.csv' não encontrado.")

    # Solicitação #5: Remover n^2 dos gráficos de teoria
    st.subheader("Verificação de Complexidade (Gráficos de Teoria)")
    st.markdown("Os gráficos abaixo confirmam que o desempenho real (TempoRealMinimo) segue a curva $\Theta(n \log n)$, e não $\Theta(n)$.")

    col1, col2 = st.columns(2)
    with col1:
        if df_bubble is not None:
            chart_bubble = create_theory_chart(df_bubble, "Desempenho: Merge+Bubble vs. Teoria")
            st.altair_chart(chart_bubble, use_container_width=True)
    with col2:
        if df_insertion is not None:
            chart_insertion = create_theory_chart(df_insertion, "Desempenho: Merge+Insertion vs. Teoria")
            st.altair_chart(chart_insertion, use_container_width=True)


elif page == "5. Conclusões":
    st.header("5. Conclusões Finais")
    st.markdown("""
    1.  **Metodologia Robusta:** O benchmark adaptativo (50x/10x) forneceu dados estatisticamente consistentes, com baixo desvio padrão.
    2.  **Teoria Validada:** Todos os algoritmos (Puro e Híbridos) têm uma complexidade assintótica de **$\Theta(n \log n)$**, como provado pela teoria e validado pelos gráficos de desempenho.
    3.  **Otimização Funciona (às vezes):** A hibridização é uma otimização de *fator constante*. A escolha do algoritmo para o caso base é crucial.
    4.  **O Vencedor:** O híbrido **Merge Sort + Insertion Sort (`merge5.c`)** provou ser uma otimização bem-sucedida, superando o desempenho do Merge Sort Puro.
    5.  **O Perdedor:** O híbrido **Merge Sort + Bubble Sort (`merge4.c`)** foi ineficaz, sendo consistentemente mais lento que a versão original pura.
    """)

    # Solicitação #8: Análise do Threshold
    st.subheader("Análise do Threshold Ideal")
    st.markdown("""
    O `THRESHOLD` define o "ponto de virada" onde o algoritmo para de dividir (recursão) e começa a ordenar (caso base). Encontrar o valor ideal é a chave para a otimização.

    Abaixo está a análise do porquê os valores ideais são tão diferentes entre os dois algoritmos híbridos:
    """)

    # Criando duas colunas para a comparação
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Merge + Insertion Sort (Thresholds Altos: ~70-100)")
        st.markdown("""
        O **Insertion Sort** ($\Theta(n^2)$) é assintoticamente mais lento que o Merge Sort ($\Theta(n \log n)$), mas para valores *pequenos* de `n`, seu custo de execução real é menor.
        
        * **Por quê? Baixa Sobrecarga:** Ele possui loops muito simples e "desliza" os elementos para sua posição com poucas operações.
        
        * **Ponto de Virada:** Por ser tão eficiente, ele continua sendo mais rápido que a *sobrecarga da recursão* do Merge Sort por mais tempo. Nossos testes mostram que o custo da recursão só supera o custo do Insertion Sort quando as listas atingem um tamanho considerável (ex: `n` entre 70 e 100).
        """)

    with col2:
        st.markdown("#### Merge + Bubble Sort (Thresholds Baixos: ~8)")
        st.markdown("""
        O **Bubble Sort** ($\Theta(n^2)$) também é assintoticamente mais lento, mas sua performance no mundo real é drasticamente pior que a do Insertion Sort.
        
        * **Por quê? Alta Sobrecarga:** Ele é notoriamente ineficiente, realizando um número massivo de trocas (swaps) e comparações desnecessárias.
        
        * **Ponto de Virada:** Ele se torna *lento* muito rapidamente. Nossos testes mostram que para listas maiores que `n \approx 8`, o custo de rodar o Bubble Sort já é *maior* do que o custo de continuar a recursão do Merge Sort.
        """)

    st.markdown("---") # Uma linha divisória

    st.markdown("""
    **Em resumo:** O Insertion Sort é uma escolha vastamente superior para o caso base, pois sua baixa sobrecarga o torna viável para otimizar listas de tamanhos muito maiores.

    Abaixo estão os valores de `THRESHOLD` que resultaram no menor tempo de execução para cada `Tamanho` de entrada, lidos do arquivo que corrigimos:
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Híbrido: Merge + Insertion")
        if not best_thresholds_insertion.empty:
            st.dataframe(best_thresholds_insertion, use_container_width=True)
            st.caption("Menores tempos médios para cada tamanho de entrada.")
        else:
            st.warning("Dados de threshold do Insertion Sort não puderam ser analisados.")
            
    with col2:
        st.markdown("##### Híbrido: Merge + Bubble")
        if not best_thresholds_bubble.empty:
            st.dataframe(best_thresholds_bubble, use_container_width=True)
            st.caption("Menores tempos médios para cada tamanho de entrada.")
        else:
            st.warning("Dados de threshold do Bubble Sort não puderam ser analisados.")


elif page == "Apêndice: Códigos-Fonte (.c)":
    st.header("Apêndice: Códigos-Fonte (.c)")
    
    with st.expander("merge4_final.c (Híbrido Merge + Bubble)"):
        st.code(code_merge4, language='c')
        st.download_button(
            label="Baixar merge4_final.c",
            data=code_merge4,
            file_name="merge4_final.c",
            mime="text/x-csrc"
        )
        
    with st.expander("merge5_final.c (Híbrido Merge + Insertion)"):
        st.code(code_merge5, language='c')
        st.download_button(
            label="Baixar merge5_final.c",
            data=code_merge5,
            file_name="merge5_final.c",
            mime="text/x-csrc"
        )

    with st.expander("process_best_merge_results.c (Pegar melhores tempos Merge Puro)"):
        st.code(code_best_merge, language='c')
        st.download_button(
            label="Baixar process_best_merge_results.c.c",
            data=code_best_merge,
            file_name="process_best_merge_results.c",
            mime="text/x-csrc"
        )

    with st.expander("process_best_mergebubble_results.c (Pegar melhores tempos Merge + Bubble)"):
        st.code(code_best_bubble, language='c')
        st.download_button(
            label="Baixar process_best_mergebubble_results.c",
            data=code_best_bubble,
            file_name="process_best_mergebubble_results.c",
            mime="text/x-csrc"
        )

    with st.expander("process_best_mergeinsertion_results.c (Pegar melhores tempos Merge + Insertion)"):
        st.code(code_best_insertion, language='c')
        st.download_button(
            label="Baixar process_best_mergeinsertion_results.c",
            data=code_best_insertion,
            file_name="process_best_mergeinsertion_results.c",
            mime="text/x-csrc"
        )

elif page == "Apêndice: Dados Brutos (.csv)":
    st.header("Apêndice: Dados Brutos (.csv)")
    
    st.subheader("Melhores Resultados (Comparativo Final - três .csv de melhores tempos combinados)")
    with st.expander("Mostrar dados de 'melhores_resultados_merge_hibridos.csv'"):
        if df_best is not None:
            st.dataframe(df_best)
            st.download_button(
                label="Baixar melhores_resultados_merge_hibridos.csv",
                data=df_best.to_csv(index=False).encode('utf-8'),
                file_name="melhores_resultados_merge_hibridos.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")

    st.subheader("Resultados Sumarizados (Médias e Desvios)")
    with st.expander("Mostrar dados de 'merge-insertion-summary_results.csv'"):
        if df_insertion is not None:
            st.dataframe(df_insertion)
            st.download_button(
                label="Baixar merge-insertion-summary_results.csv",
                data=df_insertion.to_csv(index=False).encode('utf-8'),
                file_name="merge-insertion-summary_results.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")
            
    with st.expander("Mostrar dados de 'merge-bubble-summary_results.csv'"):
        if df_bubble is not None:
            st.dataframe(df_bubble)
            st.download_button(
                label="Baixar merge-bubble-summary_results.csv",
                data=df_bubble.to_csv(index=False).encode('utf-8'),
                file_name="merge-bubble-summary_results.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")
            
    st.subheader("Dados Brutos (Execuções Individuais)")
    with st.expander("Mostrar dados de 'merge-insertion-raw_times.csv'"):
        if df_insertion_raw is not None:
            st.dataframe(df_insertion_raw)
            st.download_button(
                label="Baixar merge-insertion-raw_times.csv",
                data=df_insertion_raw.to_csv(index=False).encode('utf-8'),
                file_name="merge-insertion-raw_times.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")
            
    with st.expander("Mostrar dados de 'merge-bubble-raw_times.csv'"):
        if df_bubble_raw is not None:
            st.dataframe(df_bubble_raw)
            st.download_button(
                label="Baixar merge-bubble-raw_times.csv",
                data=df_bubble_raw.to_csv(index=False).encode('utf-8'),
                file_name="merge-bubble-raw_times.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")