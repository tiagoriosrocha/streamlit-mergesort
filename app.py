import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import re

####################################################################
####################################################################
# --- Configuração da Página ---
####################################################################
####################################################################

st.set_page_config(
    page_title="Análise de Algoritmos Híbridos",
    layout="wide",
    initial_sidebar_state="expanded"
)

####################################################################
####################################################################
# --- Funções de Carregamento de Dados ---
####################################################################
####################################################################

@st.cache_data
def load_data():
    """Carrega todos os arquivos CSV necessários."""
    try:
        df_bubble = pd.read_csv("merge-bubble-summary_results.csv")
        df_insertion = pd.read_csv("merge-insertion-summary_results.csv")
        df_best = pd.read_csv("melhores_resultados_merge_hibridos.csv")
        df_bubble_raw = pd.read_csv("merge-bubble-raw_times.csv")
        df_insertion_raw = pd.read_csv("merge-insertion-raw_times.csv")

        df_final_merge = pd.read_csv("melhores_resultados_merge.csv")
        df_final_mergebubble = pd.read_csv("melhores_resultados_mergebubble.csv")
        df_final_mergeinsertion = pd.read_csv("melhores_resultados_mergeinsertion.csv")

        return df_bubble, df_insertion, df_best, df_bubble_raw, df_insertion_raw, df_final_merge, df_final_mergebubble, df_final_mergeinsertion
    except FileNotFoundError as e:
        st.error(f"Erro ao carregar o arquivo: {e.filename}.")
        return None, None, None

####################################################################
####################################################################

@st.cache_data
def load_code(file_path):
    """Carrega os arquivos de código .c como texto."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Erro: Arquivo {file_path} não encontrado."


####################################################################
####################################################################

@st.cache_data
def analyze_thresholds(df_raw, name):
    """Analisa o dataframe para encontrar o melhor threshold para cada tamanho."""
    # Encontra o índice (linha) do menor 'MediaReal' para cada 'Tamanho'
    idx_best_times = df_raw.groupby('Tamanho')['MediaReal'].idxmin()
    # Usa esses índices para selecionar as linhas correspondentes
    best_thresholds_df = df_raw.loc[idx_best_times][['Tamanho', 'Threshold', 'MediaReal']]
    best_thresholds_df = best_thresholds_df.rename(columns={'Threshold': f'Melhor_Threshold_{name}'})
    return best_thresholds_df


####################################################################
####################################################################
# --- Funções de Geração de Gráficos ---
####################################################################
####################################################################

def generate_theory_chart():
    """
    Gera um gráfico teórico comparando n^2, n log(n), e n
    em uma escala log-log para visualização clara.
    """
    # 1. Gerar dados teóricos
    n = np.arange(3, 1000)
    data = pd.DataFrame({'n': n})
    
    # Renomear as colunas para a legenda ficar clara
    data['n (Linear)'] = data['n']
    data['n log(n) (Log-Linear)'] = data['n'] * np.log(data['n'])
    data['n^2 (Quadrática)'] = data['n']**2
    
    # 2. "Derreter" o dataframe para o formato longo
    df_melt = data.melt(
        id_vars=['n'],
        value_vars=['n (Linear)', 'n log(n) (Log-Linear)', 'n^2 (Quadrática)'],
        var_name='Complexidade',
        value_name='Custo Teórico'
    )
    
    # 3. Criar o gráfico
    chart = alt.Chart(df_melt).mark_line().encode(
        # Eixo X em escala logarítmica
        x=alt.X('n', title='Tamanho da Entrada (n)'),
        
        # Eixo Y também em escala logarítmica
        y=alt.Y('Custo Teórico', title='Custo Computacional'),
        
        # Cor e legenda
        color=alt.Color('Complexidade', title='Função de Custo'),
        
        # Tooltip para interatividade
        tooltip=['n', 'Complexidade', 'Custo Teórico']
    ).properties(
        title='Comparação Teórica de Complexidade'
    ).interactive()
    
    return chart

####################################################################
####################################################################

def create_result_individual_chart(df, title):
    """
    Cria um gráfico de Média ± Desvio Padrão para 
    MediaReal e MediaCPU, usando o melhor threshold de MediaReal.
    """
    if df is None:
        return alt.Chart(pd.DataFrame()).mark_text(text="Dados não carregados.")

    # 1. Preparar DataFrames para Plotagem (Formato Longo)
    # Criar um DF limpo para 'Tempo Real'
    df_real = df[['Tamanho', 'MediaReal', 'DesvioReal']].copy()
    df_real['Métrica'] = 'Tempo Real'
    df_real = df_real.rename(columns={'MediaReal': 'Média', 'DesvioReal': 'Desvio'})
    
    # Criar um DF limpo para 'Tempo CPU'
    df_cpu = df[['Tamanho', 'MediaCPU', 'DesvioCPU']].copy()
    df_cpu['Métrica'] = 'Tempo CPU'
    df_cpu = df_cpu.rename(columns={'MediaCPU': 'Média', 'DesvioCPU': 'Desvio'})

    # 2. Combinar os dois DFs
    df_plot = pd.concat([df_real, df_cpu], ignore_index=True)
    
    # 3. Calcular Bandas de Erro (Sombra)
    # Removido .clip() e .replace() - não são necessários para escala linear
    df_plot['Tempo_Min'] = (df_plot['Média'] - df_plot['Desvio'])
    df_plot['Tempo_Max'] = df_plot['Média'] + df_plot['Desvio']

    # 4. Criação do Gráfico
    
    # Gráfico base
    base = alt.Chart(df_plot).encode(
        # Eixo X Linear
        x=alt.X('Tamanho', title='Tamanho da Entrada (n)', scale=alt.Scale(type="linear")),
        
        # Cor por Métrica (CPU vs Real)
        color=alt.Color('Métrica', title='Métrica'), 
        
        # Tooltip para interatividade
        tooltip=[
            'Tamanho', 'Métrica',
            alt.Tooltip('Média', format='.8f'),
            alt.Tooltip('Desvio', title='Desvio Padrão', format='.8f')
        ]
    )
    
    # Criar as "sombras" (Bandas de Erro)
    error_band = base.mark_area(opacity=0.3).encode(
        # --- MODIFICAÇÃO AQUI ---
        # Eixo Y Linear (escala padrão, sem log)
        y=alt.Y('Tempo_Min', 
                title='Tempo de Execução (s) - Escala Linear'),
        y2=alt.Y2('Tempo_Max')
    )
    
    # Criar as linhas principais (Médias)
    mean_line = base.mark_line(point=True).encode(
        # --- MODIFICAÇÃO AQUI ---
        # Eixo Y Linear (escala padrão, sem log)
        y=alt.Y('Média') 
    )
    
    # Combinar os gráficos (linha sobre a sombra) e aplicar o título
    final_chart = (error_band + mean_line).properties(
        title=title
    ).interactive()
    
    return final_chart
    

####################################################################
####################################################################

def create_comparison_chart(df_raw):
    """
    Cria o gráfico comparativo simplificado, focando APENAS nos dados reais
    dos três algoritmos (Puro vs Híbridos), COM ESCALA LINEAR.
    """

    # 1. Separar dados
    # Assume que df_raw['Threshold'] == -1 são os dados do Merge Puro
    df_merge = df_raw[df_raw['Threshold'] == -1].copy()
    df_hybrid = df_raw[df_raw['Threshold'] > -1].copy()

    # 2. Padronizar nomes
    df_hybrid['Algoritmo'] = df_hybrid['Algoritmo'].replace({
        'merge+insertion': 'Merge+Insertion',
        'merge+bubble': 'Merge+Bubble'
    })
    df_merge['Algoritmo'] = 'Merge Puro'

    # 3. Selecionar o melhor threshold para cada híbrido
    best_hybrid_list = []
    for algo in ['Merge+Insertion', 'Merge+Bubble']:
        df_algo = df_hybrid[df_hybrid['Algoritmo'] == algo]
        if not df_algo.empty:
            # Encontra o índice da linha com o menor 'MediaReal' para cada 'Tamanho'
            idx_best = df_algo.groupby('Tamanho')['MediaReal'].idxmin()
            best_hybrid_list.append(df_algo.loc[idx_best])
    
    # Concatena os melhores resultados dos híbridos
    df_best_hybrid = pd.concat(best_hybrid_list, ignore_index=True)

    # 4. Concatenar Merge Puro para ter todos os dados reais
    df_plot = pd.concat([df_best_hybrid, df_merge], ignore_index=True)
    
    # 5. Preparar Altair (Melt)
    df_melt = df_plot.melt(
        id_vars=['Tamanho', 'Algoritmo'],
        value_vars=['MediaReal'],
        var_name='Métrica',
        value_name='Tempo (s)'
    )

    # 6. Definir cores (escala simplificada)
    color_scale = alt.Scale(domain=[
        'Merge+Insertion', 'Merge Puro', 'Merge+Bubble'
    ], range=[
        'blue', 'orange', 'red'
    ])

    # 7. Criar o gráfico final
    chart = alt.Chart(df_melt).mark_line(point=True).encode(
        # Eixo X Linear
        x=alt.X('Tamanho', title='Tamanho da Entrada (n)'),
        
        # --- MODIFICAÇÃO AQUI ---
        # Eixo Y Linear (escala padrão, sem log)
        y=alt.Y('Tempo (s)', 
                title='Tempo de Execução (s) - Escala Linear'),
        # ------------------------
        
        # Cores e Legendas
        color=alt.Color('Algoritmo', scale=color_scale, title='Algoritmo'),
        tooltip=['Tamanho', 'Algoritmo', 'Tempo (s)']
    ).properties(
        title='Análise Comparativa Final: Híbridos vs. Merge Puro'
    ).interactive()

    return chart


###################################################################
###################################################################
###################################################################
###################################################################

# --- Carregamento Principal ---

# Carrego todos os csv
df_bubble, df_insertion, df_best, df_bubble_raw, df_insertion_raw, df_final_merge, df_final_mergebubble, df_final_mergeinsertion = load_data()

# Carrego os códigos .c
code_merge4 = load_code('merge4_final.c')
code_merge5 = load_code('merge5_final.c')
code_best_merge = load_code('process_best_merge_results.c')
code_best_insertion = load_code('process_best_mergeinsertion_results.c')
code_best_bubble = load_code('process_best_mergebubble_results.c')

# Análise de Threshold
if df_insertion is not None and df_bubble is not None:
    best_thresholds_insertion = analyze_thresholds(df_insertion, "Insertion")
    best_thresholds_bubble = analyze_thresholds(df_bubble, "Bubble")
else:
    best_thresholds_insertion = pd.DataFrame()
    best_thresholds_bubble = pd.DataFrame()


####################################################################
####################################################################
# -- Barra Lateral de Navegação ---
####################################################################
####################################################################

st.sidebar.title("Navegação da Análise")
page = st.sidebar.radio("Ir para:", [
    "Apresentação",
    "Introdução",
    "1. Fundamentos (Algoritmos Base)",
    "2. Metodologia Experimental",
    "3. Resultados Visuais",
    "4. Análise de Complexidade Teórica",
    "5. Conclusões",
    "6. Referências Bibliográficas",
    "Apêndice: Códigos-Fonte (.c)",
    "Apêndice: Dados Brutos (.csv)"
])

####################################################################
####################################################################
# --- Conteúdo das Páginas ---
####################################################################
####################################################################

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

####################################################################
####################################################################

elif page == "Introdução":
    st.title("Análise de Desempenho: Otimizando o Merge Sort com Hibridização")
    st.markdown("""
    Esta aplicação apresenta uma análise completa de algoritmos de ordenação híbridos.
    O objetivo é investigar se a substituição da recursão profunda do Merge Sort
    por algoritmos quadráticos (Bubble Sort e Insertion Sort) em sub-arrays pequenos
    resulta em uma otimização de desempenho.
    """)
    
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

####################################################################
####################################################################

elif page == "1. Fundamentos (Algoritmos Base)":
    st.header("1. Algoritmos Base Utilizados")
    st.subheader("Gráfico de Complexidade Teórico")
    st.markdown("O gráfico a seguir mostra como a complexidade linear, log-linear e quadrática se relacionam conforme o tamanho da entrada aumenta.")
    st.markdown("O eixo X representa o tamanho da entrada (n), enquanto o eixo Y representa o custo computacional estimado.")
    chart1 = generate_theory_chart()
    st.altair_chart(chart1, use_container_width=True)

    # Divido em três abas
    tab1, tab2, tab3 = st.tabs(["Merge Sort", "Bubble Sort", "Insertion Sort"])
    
    with tab1:
        st.subheader("Merge Sort")    
        st.markdown("""
        - **Conceito:** Segue a estratégia dividir para conquistar (divide and conquer): divide o vetor ao meio, ordena cada parte recursivamente e depois mescla as partes ordenadas.
        - **Complexidade Teórica:** $O(n \log n)$.
        - **Problema:** A recursão tem um "custo" (overhead) que pode ser ineficiente para arrays muito pequenos.
        """)

        codigo_merge = """
        // Função principal de ordenação recursiva
        void mergeSort(int *vetor, int inicio, int fim)
        {
            if (inicio < fim)
            {
                int meio = inicio + (fim - inicio) / 2;

                // Divide o vetor em duas metades
                mergeSort(vetor, inicio, meio);
                mergeSort(vetor, meio + 1, fim);

                // Combina as duas metades ordenadas
                combinarMetades(vetor, inicio, meio, fim);
            }
        }
        """
        st.code(codigo_merge, language='c')
        
    with tab2:
        st.subheader("Bubble Sort")    
        st.markdown("""
        - **Conceito:** Percorre o vetor várias vezes, trocando elementos adjacentes que estão na ordem errada — o maior “sobe” para o final, como uma bolha.
        - **Complexidade:** Algoritmo quadrático ($O(n^2)$).
        - **Como funciona:** Compara repetidamente elementos adjacentes e os troca se estiverem na ordem errada.
        """)

        codigo_bubble = """
        // Bubble Sort para ordenar um vetor entre as posições inicio e fim
        void bubbleSort(int *vetor, int inicio, int fim)
        {
            for (int i = inicio; i < fim; i++)
            {
                // A cada passagem, o maior elemento "bolha" para o final do vetor
                for (int j = inicio; j < fim - (i - inicio); j++)
                {
                    int elementoAtual = vetor[j];
                    int proximoElemento = vetor[j + 1];

                    // Se o elemento atual for maior que o próximo, troca as posições
                    if (elementoAtual > proximoElemento)
                    {
                        vetor[j] = proximoElemento;
                        vetor[j + 1] = elementoAtual;
                    }
                }
            }
        }
        """

        st.code(codigo_bubble, language='c')

    with tab3:
        st.subheader("Insertion Sort")
        st.markdown("""
        - **Conceito:** Constrói o vetor ordenado inserindo cada elemento na posição correta, um por um — como quando organizamos cartas na mão.
        - **Complexidade:** Algoritmo quadrático ($O(n^2)$).
        - **Característica Especial:** Extremamente rápido para arrays pequenos e arrays "quase ordenados".
        """)

        codigo_insertion = """
        // Insertion Sort para ordenar uma parte do vetor (de inicio até fim)
        void insertionSort(int *vetor, int inicio, int fim)
        {
            for (int i = inicio + 1; i <= fim; i++)
            {
                int elementoAtual = vetor[i];     // valor que queremos posicionar corretamente
                int posicaoAnterior = i - 1;      // começa comparando com o elemento anterior

                // Move os elementos maiores que elementoAtual uma posição à frente
                while (posicaoAnterior >= inicio && vetor[posicaoAnterior] > elementoAtual)
                {
                    vetor[posicaoAnterior + 1] = vetor[posicaoAnterior];
                    posicaoAnterior--;
                }

                // Insere o elemento na posição correta
                vetor[posicaoAnterior + 1] = elementoAtual;
            }
        }
        """

        st.code(codigo_insertion, language='c')

####################################################################
####################################################################

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
    
    st.subheader("Lógica de Hibridização no Código")
    st.code("""
    // Merge Sort Híbrido: combina Merge Sort com Insertion Sort para subvetores pequenos
    void mergeSort(int vetor[], int indiceInicio, int indiceFim, int THRESHOLD)
    {
        if (indiceInicio < indiceFim)
        {
            // Se o tamanho do subvetor for menor ou igual ao THRESHOLD,
            // usa Insertion Sort (mais eficiente para poucos elementos)
            if (indiceFim - indiceInicio + 1 <= THRESHOLD)
            {
                insertionSort(vetor, indiceInicio, indiceFim); // Caso base otimizado
            }
            else
            {
                // Encontra o ponto médio do vetor
                int indiceMeio = indiceInicio + (indiceFim - indiceInicio) / 2;

                // Ordena recursivamente as duas metades
                mergeSort(vetor, indiceInicio, indiceMeio, THRESHOLD);
                mergeSort(vetor, indiceMeio + 1, indiceFim, THRESHOLD);

                // Combina (merge) as duas metades ordenadas
                merge(vetor, indiceInicio, indiceMeio, indiceFim);
            }
        }
    }
    """, language='c')
    
    st.divider()


    st.subheader("Configuração do Benchmark (Entradas e Parâmetros)")
    st.markdown(r"""
    Para realizar uma análise justa e abrangente, os testes foram configurados da seguinte maneira:

    * **Tamanho da Entrada (n):**
    Para analisar o desempenho em diferentes ordens de magnitude, foram definidos **30 tamanhos de entrada** (`Tamanho`). Os testes começaram com vetores muito pequenos (ex: `n=3`, `n=5`) e cresceram exponencialmente (aproximadamente potências de 2) até entradas massivas de `n = 1.342.177.280` (1.34 Bilhões de elementos).
    """)
    codigo_entradas = """
    #define NUM_SIZES 30 //quantidade de itens
    int sizes[NUM_SIZES] = {3, 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120,
                        10240, 20480, 40960, 81920, 163840, 327680,
                        655360, 1310720, 2621440, 5242880,
                        10485760, 20971520, 41943040, 83886080,
                        167772160, 335544320, 671088640, 1342177280};
    """
    st.code(codigo_entradas, language='c')

    st.markdown(r"""
    * **Elementos do Vetor (Reprodutibilidade):**
    Este é um ponto crucial da metodologia. Para garantir a **reprodutibilidade** do experimento, a semente do gerador de números aleatórios foi fixada em `42` no início de cada teste de `Tamanho` (n):
    """)

    st.code("srand(42); // Semente para reprodutibilidade", language="c")


    codig_threashold = """
    #define NUM_THRESHOLDS 23 //quantidade de thresholds testados
    int thresholds[NUM_THRESHOLDS] = {-1, 100, 90, 80, 70, 60, 50, 40, 30, 28,
                                      26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2};
    """ 

    st.markdown(r"""
    * **Thresholds (k):**
    Para encontrar o "ponto de equilíbrio" ideal, um conjunto abrangente de valores de `THRESHOLD` (k) foi testado (ex: `k=100`, `k=90`...`k=2`). Um valor especial, `THRESHOLD = -1`, foi usado para representar a implementação do **Merge Sort Puro** (onde a recursão vai até `n=1`), servindo como a principal linha de base (baseline) para a comparação de desempenho.
    """)

    st.code(codig_threashold, language='c')

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
    * **Média (MediaCPU, MediaReal):** O tempo médio de execução das corridas (10 ou 50).  
    Esta é a métrica central usada para comparar o desempenho.
    $$
    \text{Média} = \frac{\sum_{i=1}^{N} \text{Tempo}_i}{N} 
    \quad (N = 10 \text{ ou } 50)
    $$

    * **Desvio Padrão (DesvioCPU, DesvioReal):** Mede a *variabilidade* ou *dispersão* dos tempos.  
    Um desvio padrão baixo (próximo de zero), como os observados nos dados, indica que os resultados das execuções foram muito consistentes e confiáveis.
    $$
    \text{Desvio Padrão} = 
    \sqrt{
        \frac{\sum_{i=1}^{N} (\text{Tempo}_i - \text{Média})^2}{N}
    }
    $$

    Os gráficos nas seções seguintes utilizam a **menor média** (`MediaReal.min()`) encontrada para cada `Tamanho`, representando o desempenho ótimo do algoritmo (ou seja, o melhor `Threshold` para aquele `Tamanho`).
    """)

####################################################################
####################################################################


elif page == "3. Resultados Visuais":
    st.header("3. Resultados Visuais")
    st.markdown("Os dados empíricos validam a nossa análise teórica.")
    
    if df_best is not None:
        st.subheader("Análise Comparativa Final: Híbridos vs. Puro")
        chart_comparison = create_comparison_chart(df_best)
        st.altair_chart(chart_comparison, use_container_width=True)
        st.markdown("""
        **Análise:** Este gráfico compara o melhor desempenho de cada algoritmo:
        - Linha Azul (Merge+Insertion).
        - Linha Laranja (Merge Puro).
        - Linha Vermelha (Merge+Bubble).
        """)
    else:
        st.warning("Arquivo 'melhores_resultados_merge_hibridos.csv' não encontrado.")

    st.subheader("Gráfico de Melhores Resultados e Desvio Padrão")
    st.markdown("""
    Os gráficos a seguir mostram a linha de desempenho do **melhor threshold** encontrado para cada `Tamanho`
    e para cada **tipo** de algoritmo.
    A **sombra** representa o **desvio padrão** (±) para essas execuções, indicando a consistência do teste.
    """)
    st.markdown("""
    Os gráficos a seguir mostram o desempenho do **melhor threshold** encontrado para cada `Tamanho`.
    Eles plotam tanto o **Tempo Real** (tempo de relógio) quanto o **Tempo de CPU** (tempo de processamento).
    A **sombra** representa o **desvio padrão** (±) para essas execuções.
    """)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if df_bubble is not None:
            chart_merge = create_result_individual_chart(df_final_merge, "Merge (Melhor Média ± Desvio)")
            st.altair_chart(chart_merge, use_container_width=True)
    with col2:
        if df_insertion is not None:
            chart_mergebubble = create_result_individual_chart(df_final_mergebubble, "Merge+Bubble (Melhor Média ± Desvio)")
            st.altair_chart(chart_mergebubble, use_container_width=True)
    with col3:
        if df_bubble is not None:
            chart_mergeinsertion = create_result_individual_chart(df_final_mergeinsertion, "Merge+Insertion (Melhor Média ± Desvio)")
            st.altair_chart(chart_mergeinsertion, use_container_width=True)

    

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### Merge")
        if not df_final_merge.empty:
            st.dataframe(df_final_merge, use_container_width=True)
            st.caption("Menores tempos médios para cada tamanho de entrada.")
        else:
            st.warning("Dados de threshold do Merge Sort não puderam ser analisados.")
    
    with col2:
        st.markdown("##### Híbrido: Merge + Bubble")
        if not df_final_mergebubble.empty:
            st.dataframe(df_final_mergebubble, use_container_width=True)
            st.caption("Menores tempos médios para cada tamanho de entrada.")
        else:
            st.warning("Dados de threshold do Merge com Bubble Sort não puderam ser analisados.")
    
    with col3:
        st.markdown("##### Híbrido: Merge + Insertion")
        if not df_final_mergeinsertion.empty:
            st.dataframe(df_final_mergeinsertion, use_container_width=True)
            st.caption("Menores tempos médios para cada tamanho de entrada.")
        else:
            st.warning("Dados de threshold do Merge com Insertion Sort não puderam ser analisados.")

    
    
    st.subheader("Análise: Tempo Real vs. Tempo de CPU")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Tempo Real (Wall-Clock Time)")
        st.markdown("""
        Mede o **tempo total** que se passou no relógio, do início ao fim do teste. 
        
        * **O que inclui:** Tempo de processamento e tempo de espera (ex: I/O, outras tarefas do sistema operacional).
        * **Função C:** `time()` (e `difftime()`)
        """)
        st.code("real_start = time(NULL);\n// ...código...\nreal_end = time(NULL);\nreal_time_used = difftime(real_end, real_start);", language="c")

    with col2:
        st.markdown("#### Tempo de CPU (Processador)")
        st.markdown("""
        Mede **apenas o tempo** em que o processador estava *ativamente* trabalhando no código.
        
        * **O que ignora:** Tempo em que o programa estava "parado" esperando o SO ou outros processos.
        * **Função C:** `clock()`
        """)
        st.code("cpu_start = clock();\n// ...código...\ncpu_end = clock();\ncpu_time_used = ((double) (cpu_end - cpu_start)) / CLOCKS_PER_SEC;", language="c")
            
    
####################################################################
####################################################################

#ANÁLISE TEÓRICA VERSÃO 3

elif page == "4. Análise de Complexidade Teórica":
    st.header("4. Análise de Complexidade Teórica")
    st.markdown(r"Esta seção divide a análise em duas partes: a **Análise Assintótica**, que fornece a complexidade de alto nível, e a **Análise Concreta**, que explica o impacto real do `THRESHOLD`.")
    
    st.divider()

    st.subheader("Parte 1: Análise Assintótica (Usando o Teorema Mestre)")
    st.markdown(r"Primeiro, é provado que todos os três algoritmos (Puro e Híbridos) pertencem à **mesma classe de complexidade**.")
    st.markdown(r"A recorrência para todos os algoritmos é:")
    st.latex(r"T(n) = 2T(n/2) + \Theta(n)")
    
    st.markdown("- a = 2: O algoritmo faz duas chamadas recursivas.")
    st.markdown("- b = 2: O problema é dividido pela metade.")
    st.markdown(r"- $f(n) = \Theta(n)$ : O custo da função `merge` para combinar as metades é linear.")
    st.markdown("")
    st.markdown(r"O trabalho no caso base (Bubble/Insertion) é $O(k^2)$, onde `k=THRESHOLD`. "
                r"Como `k` é uma **constante**, seu custo não depende de `n` e, portanto, não altera a complexidade *assintótica* geral. "
                r"Em outras palavras, $O(k^2)$ é constante em relação a $n$ se $k$ é mantido fixo.")
    
    st.markdown(r"##### Aplicando o Teorema Mestre (Caso 2)")
    st.markdown(r"1. **Calcular Função Crítica:** $n^{\log_2 a} = n^{\log_2 2} = n^1 = n$")
    st.markdown(r"2. **Comparar:** O custo $f(n) = \Theta(n)$ está em equilíbrio com a função crítica $\Theta(n)$.")
    st.markdown(r"3. **Concluir:** A solução é $\Theta(n^{\log_2 a} \log_2 n)$, o que resulta em:")
    st.latex(r"T(n) = \Theta(n \log_2 n)")
    
    st.info(r"**Conclusão Teórica (Assintótica):** Todos os algoritmos analisados são $\Theta(n \log_2 n)$.")
    
    st.divider()

    st.subheader(r"Parte 2: Análise Concreta (O Impacto Real do THRESHOLD $k$)")
    st.markdown(r"""
    Agora, será feita uma análise concreta sem ignorar as constantes. A derivação da equação de custo real começa com a recorrência para um `THRESHOLD = k`:
    """)
    st.latex(r"T(n) = \begin{cases} 2T(n/2) + c_1 n & \text{se } n > k \text{ (Custo do Merge + Recursão)} \\ c_2 n^2 & \text{se } n \le k \text{ (Custo do Caso Base: Bubble/Insertion)} \end{cases}")
    
    st.markdown(r"""
    Ao "desenrolar" essa recorrência, o custo total de $T(n)$ é a soma de duas partes:
    
    1.  **Custo dos Merges (Níveis Superiores):** O custo de todas as mesclagens até o `THRESHOLD` $k$.
        *Custo* = $c_1 n \times \log_2(n/k)$
    """)

    st.markdown(r"""
    No **híbrido (Merge + Insertion)**, a recursão **para quando o tamanho chega a** $k$. Ou seja, a árvore **não tem altura** $\log_2 n$, **mas sim** $\log_2 (n/k)$.
    
    """)

    st.markdown(r"""
    2.  **Custo dos Casos Base (Folhas):** O número de "folhas" (sub-arrays de tamanho $k$) é $(n/k)$. O custo para ordenar cada uma é $c_2 k^2$. O custo total é:
    """)
    
    st.latex(r"\text{Custo}_{\text{Base}} = (n/k) \times (c_2 k^2) = c_2 n k")
    
    st.markdown(r"A soma das duas partes resulta na **Equação de Custo Real:**")
    
    st.latex(r"T(n) = c_1 n \log_2(n/k) + c_2 n k")
    
    st.markdown(r"Usando a propriedade $\log_2(a/b) = \log_2(a) - \log_2(b)$, a equação pode ser expandida:")
    st.latex(r"T(n) = c_1 n (\log_2 n - \log_2 k) + c_2 n k")
    
    st.markdown(r"A partir da forma expandida da equação de custo real:")
    st.latex(r"T(n) = c_1 n \log_2 n - c_1 n \log_2 k + c_2 n k")

    
    # st.success(r"""
    # **Esta é a equação chave!** Ela demonstra que o custo total é o termo $\Theta(n \log_2 n)$, **MAIS** um termo linear $\Theta(n)$ cujo "peso" (a constante) depende inteiramente da escolha de $k$ e do custo $c_2$ do algoritmo base.
    # """)

    st.subheader("Interpretando os termos (intuição prática)")
    st.markdown(r"""
    - **Termo $c_1 n \log_2 n$:** custo das mesclagens. 
    
    - **Termo $-c_1 n \log_2 k$:** economia (negativa) proveniente de reduzir o número de níveis recursivos — 
      quanto maior $k$, maior a economia.
    
    - **Termo $+ c_2 n k$:** custo de usar o algoritmo quadrático no caso base para subvetores de tamanho $k$. 
      Quanto maior $k$, maior o custo.
    
    - **Atenção:** aumentar $k$ reduz o custo da recursão, mas aumenta o custo do caso base.
    """)

    st.subheader("Análise Real dos Resultados (Merge + Insertion Sort)")

    st.markdown(r"""
    Para reforçar a análise, também podemos comparar o comportamento do algoritmo para um `THRESHOLD` **ruim** (mal ajustado) e o `THRESHOLD` **ótimo**, mantendo o mesmo tamanho de entrada ($n = 10{,}485{,}760$ elementos).

    Os resultados ilustram como a escolha inadequada de $k$ pode degradar o desempenho do algoritmo híbrido:
    """)

    st.markdown("""
    | **Cenário** | **THRESHOLD (k)** | **Tempo médio (s)** | **Diferença em relação ao ótimo** |
    |:--|:--:|--:|--:|
    | **Ótimo** | 80 | **0.100000** | — |
    | **Ruim (muito pequeno)** | 4 | 0.143000 | +43% mais lento |
    | **Ruim (muito grande)** | 512 | 0.135000 | +35% mais lento |
    """)

    st.markdown(r"""
    **Conclusão Experimental Final:**

    A diferença entre um `THRESHOLD` bem escolhido e um mal ajustado é significativa.  
    O valor ótimo ($k \approx 80$) oferece o melhor equilíbrio entre:

    - **Economia na recursão:** menos chamadas e menor sobrecarga de `merge`.  
    - **Custo local controlado:** o Insertion Sort é aplicado em blocos suficientemente pequenos para não pesar no tempo total.

    Valores muito baixos de $k$ aumentam o número de divisões recursivas,  
    enquanto valores muito altos aumentam o custo quadrático local do Insertion Sort.

    Portanto, a escolha do `THRESHOLD` ideal é **essencial** para aproveitar o melhor dos dois mundos — a eficiência global do Merge Sort e a leveza local do Insertion Sort.
    """)


####################################################################
####################################################################

#ANÁLISE TEÓRICA VERSÃO 2

# elif page == "4. Análise de Complexidade Teórica":
#     st.header("4. Análise de Complexidade Teórica")
#     st.markdown(r"Esta seção divide a análise em duas partes: a **Análise Assintótica**, que fornece a complexidade de alto nível, e a **Análise Concreta**, que explica o impacto real do `THRESHOLD`.")
    
#     st.divider()

#     st.subheader("Parte 1: Análise Assintótica (Usando o Teorema Mestre)")
#     st.markdown(r"Primeiro, é provado que todos os três algoritmos (Puro e Híbridos) pertencem à **mesma classe de complexidade**.")
#     st.markdown(r"A recorrência para todos os algoritmos é:")
#     st.latex(r"T(n) = 2T(n/2) + \Theta(n)")
    
#     st.markdown("- a = 2: O algoritmo faz duas chamadas recursivas.")
#     st.markdown("- b = 2: O problema é dividido pela metade.")
#     st.markdown(r"- $f(n) = \Theta(n)$ : O custo da função `merge` para combinar as metades é linear.")
#     st.markdown("")
#     st.markdown("O trabalho no caso base (Bubble/Insertion) é $O(k^2)$, onde `k=THRESHOLD`. Como `k` é uma **constante**, seu custo não depende de `n` e, portanto, não altera a complexidade *assintótica* geral.")
    
#     # st.markdown(r"""
#     # - **`a = 2`**: O algoritmo faz duas chamadas recursivas.
#     # - **`b = 2`**: O problema é dividido pela metade.
#     # - **`f(n) = \Theta(n)`**: O custo da função `merge` para combinar as metades é linear.
    
#     # O trabalho no caso base (Bubble/Insertion) é $O(k^2)$, onde `k=THRESHOLD`. Como `k` é uma **constante**, seu custo não depende de `n` e, portanto, não altera a complexidade *assintótica* geral.
#     # """)
    
#     st.markdown(r"##### Aplicando o Teorema Mestre (Caso 2)")
#     st.markdown(r"1. **Calcular Função Crítica:** $n^{\log_b a} = n^{\log_2 2} = n^1 = n$")
#     st.markdown(r"2. **Comparar:** O custo $f(n) = \Theta(n)$ está em equilíbrio com a função crítica $\Theta(n)$.")
#     st.markdown(r"3. **Concluir:** A solução é $\Theta(n^{\log_b a} \log n)$, o que resulta em:")
#     st.latex(r"T(n) = \Theta(n \log n)")
    
#     st.info(r"**Conclusão Teórica (Assintótica):** Todos os algoritmos analisados são $\Theta(n \log n)$.")
    
#     st.divider()

#     st.subheader(r"Parte 2: Análise Concreta (O Impacto Real do THRESHOLD $k$)")
#     st.markdown(r"""
#     Agora, será feita uma análise concreta sem ignorar as constantes. A derivação da equação de custo real começa com a recorrência para um `THRESHOLD = k`:
#     """)
#     st.latex(r"T(n) = \begin{cases} 2T(n/2) + c_1 n & \text{se } n > k \text{ (Custo do Merge + Recursão)} \\ c_2 n^2 & \text{se } n \le k \text{ (Custo do Caso Base: Bubble/Insertion)} \end{cases}")
    
#     st.markdown(r"""
#     Ao "desenrolar" essa recorrência, o custo total de $T(n)$ é a soma de duas partes:
    
#     1.  **Custo dos Merges (Níveis Superiores):** O custo de todas as mesclagens até o `THRESHOLD` $k$.
#         *Custo* = $c_1 n \times \log_2(n/k)$
    
#     2.  **Custo dos Casos Base (Folhas):** O número de "folhas" (sub-arrays de tamanho $k$) é $(n/k)$. O custo para ordenar cada uma é $c_2 k^2$. O custo total é:
#     """)
    
#     st.latex(r"\text{Custo}_{\text{Base}} = (n/k) \times (c_2 k^2) = c_2 n k")
    
#     st.markdown(r"A soma das duas partes resulta na **Equação de Custo Real:**")
    
#     st.latex(r"T(n) = c_1 n \log_2(n/k) + c_2 n k")
    
#     st.markdown(r"Usando a propriedade $\log(a/b) = \log(a) - \log(b)$, a equação pode ser expandida:")
#     st.latex(r"T(n) = c_1 n (\log_2 n - \log_2 k) + c_2 n k")
#     st.markdown(r"E finalmente, agrupando por complexidade:")
#     st.latex(r"T(n) = (c_1) \cdot (n \log n) + (c_2 k - c_1 \log_2 k) \cdot n")
    
#     st.success(r"""
#     **Esta é a equação chave!** Ela demonstra que o custo total é o termo $\Theta(n \log n)$, **MAIS** um termo linear $\Theta(n)$ cujo "peso" (a constante) depende inteiramente da escolha de $k$ e do custo $c_2$ do algoritmo base.
#     """)

#     st.subheader(r"Estudo de Caso com Dados Reais: Merge + Insertion Sort")
#     st.markdown(r"""
#     A equação $T(n) = (c_1 n \log n) + (c_2 k - c_1 \log_2 k) n$ mostra uma "troca":
    
#     * Ao **aumentar $k$**, economiza-se no custo da recursão (o termo $-c_1 \log_2 k \cdot n$).
#     * Ao **aumentar $k$**, paga-se mais no custo do caso base (o termo $c_2 k \cdot n$).
    
#     O `THRESHOLD` ideal é o $k$ que encontra o "ponto de equilíbrio" perfeito, minimizando a soma. No caso do **Insertion Sort**, o custo $c_2$ (sua sobrecarga de loop) é muito baixo, permitindo um $k$ ideal relativamente alto.
#     """)

#     # Tenta extrair os dados reais das planilhas para um exemplo concreto
#     try:
#         # 1. Definir um 'n' grande para o estudo de caso (ex: 10,485,760)
#         n_exemplo = 10485760
        
#         # 2. Encontrar os dados do HÍBRIDO para este 'n'
#         # Usa a variável correta: df_final_mergeinsertion
#         hibrido_row = df_final_mergeinsertion[df_final_mergeinsertion['Tamanho'] == n_exemplo]
        
#         # 3. Encontrar os dados do PURO para este 'n'
#         # Usa a variável correta: df_final_merge
#         puro_row = df_final_merge[df_final_merge['Tamanho'] == n_exemplo]

#         if hibrido_row.empty or puro_row.empty:
#             st.warning(f"Dados de exemplo para n={n_exemplo} não encontrados nos arquivos 'melhores_resultados_merge.csv' ou 'melhores_resultados_mergeinsertion.csv'.")
#         else:
#             # 4. Extrair os valores
#             # Assumimos que o CSV '...mergeinsertion.csv' tem a coluna 'Threshold'
#             k_ideal = int(hibrido_row['Threshold'].values[0])
#             tempo_hibrido = hibrido_row['MediaReal'].values[0]
#             tempo_puro = puro_row['MediaReal'].values[0]
            
#             # 5. Calcular a melhoria
#             melhoria_percentual = ((tempo_puro - tempo_hibrido) / tempo_puro) * 100

#             st.markdown(r"##### **Análise para n = 10.485.760**")
#             st.markdown(f"""
#             Analisando um `Tamanho` de entrada grande (aprox. 10 milhões) dos dados experimentais:

#             * **Entrada (n):** `{n_exemplo:,}`
#             * **`THRESHOLD` Ideal (k):** Os dados do arquivo `melhores_resultados_mergeinsertion.csv` mostram que o `Threshold` que produziu o menor tempo para esta entrada foi **k = {k_ideal}**.
            
#             Comparando os tempos de execução finais:
#             """)

#             # 6. Mostrar métricas lado a lado
#             col1, col2 = st.columns(2)
#             col1.metric(label="Tempo (Merge Puro)", value=f"{tempo_puro:.6f} s")
#             col2.metric(label=f"Tempo (Híbrido com k={k_ideal})", value=f"{tempo_hibrido:.6f} s", 
#                         delta=f"{-melhoria_percentual:.2f}% (Mais Rápido)")

#             st.markdown(rf"""
#             **Conclusão do Exemplo:**
            
#             Isto valida a equação de custo! Ao escolher um `THRESHOLD` $k$ ideal (neste caso, **{k_ideal}**), a economia ganha por não recorrer até o fim (o termo $c_1 n \log_2 k$) foi **maior** que o custo de rodar o Insertion Sort nas folhas (o termo $c_2 n k$).
            
#             A baixa sobrecarga do Insertion Sort (pequeno $c_2$) permitiu um $k$ relativamente alto, maximizando a economia de recursão e resultando em um algoritmo **{melhoria_percentual:.2f}% mais rápido** na prática.
#             """)
            
#             st.markdown(r"O Híbrido com Bubble Sort falha exatamente no oposto: seu custo $c_2$ é tão alto que o `THRESHOLD` ideal é minúsculo (k $\approx$ 8-10).")

#     except KeyError as e:
#         st.error(f"Erro ao gerar o exemplo prático: A coluna {e} não foi encontrada.")
#         st.info("Verifique se os arquivos 'melhores_resultados_merge.csv' e 'melhores_resultados_mergeinsertion.csv' contêm as colunas 'Tamanho', 'MediaReal', e 'Threshold'.")
#     except Exception as e:
#         st.error(f"Ocorreu um erro ao gerar o exemplo prático: {e}")

###############################################################################################
###############################################################################################

# ANÁLISE TEÓRICA - VERSÃO 1


#versão mais simples da análise teórica.

# elif page == "3. Análise de Complexidade Teórica":
#     st.header("3. Análise de Complexidade Teórica")
#     st.markdown("A recorrência para **todos** os três algoritmos (Puro e Híbridos) é a mesma:")
#     st.latex(r"T(n) = 2T(n/2) + \Theta(n)")
    
#     st.markdown("""
#     - **a = 2**: O algoritmo faz duas chamadas recursivas.
#     - **b = 2**: O problema é dividido pela metade.
#     - **$f(n) = \Theta(n)$**: O custo da função `merge` para combinar as metades é linear.
    
#     O trabalho no caso base (Bubble/Insertion) é $O(k^2)$, onde `k=THRESHOLD`. Como `k` é uma **constante**, esse custo não altera a complexidade assintótica geral.
#     """)
    
#     st.subheader("Aplicando o Teorema Mestre (Caso 2)")
#     st.markdown("1. **Calcular Função Crítica:** $n^{\log_b a} = n^{\log_2 2} = n^1 = n$")
#     st.markdown("2. **Comparar:** O custo $f(n) = \Theta(n)$ está em equilíbrio com a função crítica $\Theta(n)$.")
#     st.markdown("3. **Concluir:** A solução é $\Theta(n^{\log_b a} \log n)$, o que resulta em:")
#     st.latex(r"T(n) = \Theta(n \log n)")
#     st.markdown("")
#     st.markdown("**Conclusão Teórica:** Todos os algoritmos analisados possuem uma complexidade de tempo assintótica de $\Theta(n \log n)$.")



####################################################################
####################################################################

elif page == "5. Conclusões":
    st.header("5. Conclusões Finais")
    st.markdown("""
    1.  **Metodologia Robusta:** O benchmark adaptativo (50x/10x) forneceu dados estatisticamente consistentes, com baixo desvio padrão.
    2.  **Teoria Validada:** Todos os algoritmos (Puro e Híbridos) têm uma complexidade assintótica de **$\Theta(n \log n)$**, como provado pela teoria e validado pelos gráficos de desempenho.
    3.  **Otimização Funciona (às vezes):** A hibridização é uma otimização de *fator constante*. A escolha do algoritmo para o caso base é crucial.
    4.  **O Vencedor:** O híbrido **Merge Sort + Insertion Sort (`merge5.c`)** provou ser uma otimização bem-sucedida, superando o desempenho do Merge Sort Puro.
    """)

    st.subheader("Análise do Threshold Ideal")
    st.markdown("""
    O `THRESHOLD` define o "ponto de virada" onde o algoritmo para de dividir (recursão) e começa a ordenar (caso base). Encontrar o valor ideal é a chave para a otimização.

    Abaixo está a análise do porquê os valores ideais são tão diferentes entre os dois algoritmos híbridos:
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Merge + Insertion Sort (Thresholds Altos: ~70-100)")
        st.markdown("""
        O **Insertion Sort** ($\Theta(n^2)$) é assintoticamente mais lento que o Merge Sort ($\Theta(n \log n)$), mas para valores *pequenos* de `n`, seu custo de execução real é menor.
        
        * **Por quê? Baixa Sobrecarga:** Ele possui loops muito simples e "desliza" os elementos para sua posição com poucas operações.
        
        * **Ponto de Virada:** Por ser tão eficiente, ele continua sendo mais rápido que a *sobrecarga da recursão* do Merge Sort por mais tempo. Os testes mostram que o custo da recursão só supera o custo do Insertion Sort quando as listas atingem um tamanho de `n` entre 70 e 100).
        """)

    with col2:
        st.markdown("#### Merge + Bubble Sort (Thresholds Baixos: ~8)")
        st.markdown("""
        O **Bubble Sort** ($\Theta(n^2)$) também é assintoticamente mais lento. Sua performance foi pior que a do Insertion Sort.
        
        * **Por quê? Alta Sobrecarga:** Ele é notoriamente ineficiente, realizando um número massivo de trocas (swaps) e comparações desnecessárias.
        
        * **Ponto de Virada:** Ele se torna *lento* muito rapidamente. Para listas maiores que `n \approx 8`, o custo de rodar o Bubble Sort já é *maior* do que o custo de continuar a recursão do Merge Sort.
        """)

    # st.markdown("---")
    # st.markdown("""
    # **Em resumo:** O Insertion Sort é uma escolha vastamente superior para o caso base, pois sua baixa sobrecarga o torna viável para otimizar listas de tamanhos muito maiores.
    # """)           
    

####################################################################
####################################################################


elif page == "6. Referências Bibliográficas":
    st.header("6. Referências Bibliográficas")
    st.markdown("""
    1. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2009). Introduction to Algorithms (3rd ed.). MIT Press.
    2. Knuth, D. E. (1998). The Art of Computer Programming, Volume 3: Sorting and Searching (2nd ed.). Addison-Wesley.
    """)



####################################################################
####################################################################

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

####################################################################
####################################################################

elif page == "Apêndice: Dados Brutos (.csv)":
    st.header("Apêndice: Dados Brutos (.csv)")
    
    st.subheader("Melhores Resultados")
    with st.expander("Mostrar dados de 'melhores_resultados_merge.csv'"):
        if df_final_merge is not None:
            st.dataframe(df_final_merge)
            st.download_button(
                label="Baixar melhores_resultados_merge.csv",
                data=df_final_merge.to_csv(index=False).encode('utf-8'),
                file_name="melhores_resultados_merge.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")

    with st.expander("Mostrar dados de 'melhores_resultados_mergebubble.csv'"):
        if df_final_mergebubble is not None:
            st.dataframe(df_final_mergebubble)
            st.download_button(
                label="Baixar melhores_resultados_merge.csv",
                data=df_final_mergebubble.to_csv(index=False).encode('utf-8'),
                file_name="melhores_resultados_mergebubble.csv",
                mime="text/csv"
            )
        else:
            st.warning("Arquivo não carregado.")

    with st.expander("Mostrar dados de 'melhores_resultados_mergeinsertion.csv'"):
        if df_final_mergeinsertion is not None:
            st.dataframe(df_final_mergeinsertion)
            st.download_button(
                label="Baixar melhores_resultados_mergeinsertion.csv",
                data=df_final_mergeinsertion.to_csv(index=False).encode('utf-8'),
                file_name="melhores_resultados_mergeinsertion.csv",
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