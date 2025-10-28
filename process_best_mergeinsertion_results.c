#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h> // Para DBL_MAX (o maior double possível)

#define MAX_LINE_LEN 1024  // Comprimento máximo de uma linha do CSV
#define INITIAL_CAPACITY 30 // Já sabemos que são 30 tamanhos

// Estrutura para armazenar os dados de uma linha do CSV
typedef struct {
    long tamanho;
    int threshold;
    double mediaCPU;
    double desvioCPU;
    double mediaReal;
    double desvioReal;
} ResultData;

// Estrutura para rastrear o melhor resultado para um 'Tamanho'
typedef struct {
    long tamanho;
    ResultData best_row;
} TamanhoTracker;

// Função de comparação para o qsort, para ordenar por 'Tamanho'
int compareTrackers(const void *a, const void *b) {
    TamanhoTracker *trackerA = (TamanhoTracker *)a;
    TamanhoTracker *trackerB = (TamanhoTracker *)b;
    
    // Compara valores long
    if (trackerA->tamanho < trackerB->tamanho) return -1;
    if (trackerA->tamanho > trackerB->tamanho) return 1;
    return 0;
}

int main() {
    const char *input_filename = "resultados_parciais/merge-insertion-summary_results.csv";
    const char *output_filename = "resultados_parciais/best_insertion_results.csv";

    FILE *in_file = fopen(input_filename, "r");
    if (in_file == NULL) {
        perror("Erro ao abrir o arquivo de entrada");
        return EXIT_FAILURE;
    }

    // Aloca memória para nossos rastreadores
    // Usamos calloc para inicializar tudo com zero/NULL
    TamanhoTracker *trackers = calloc(INITIAL_CAPACITY, sizeof(TamanhoTracker));
    if (trackers == NULL) {
        fprintf(stderr, "Erro ao alocar memória\n");
        fclose(in_file);
        return EXIT_FAILURE;
    }
    int tracker_count = 0;

    char line_buffer[MAX_LINE_LEN];

    // 1. Ler e pular a linha do cabeçalho
    if (fgets(line_buffer, MAX_LINE_LEN, in_file) == NULL) {
        fprintf(stderr, "Arquivo de entrada vazio ou erro de leitura\n");
        fclose(in_file);
        free(trackers);
        return EXIT_FAILURE;
    }

    // 2. Processar cada linha de dados
    while (fgets(line_buffer, MAX_LINE_LEN, in_file)) {
        ResultData current_row;
        
        // Copia a linha para não modificar o original com strtok
        char line_copy[MAX_LINE_LEN];
        strcpy(line_copy, line_buffer);

        // Parse (análise) da linha do CSV
        char *token;
        token = strtok(line_copy, ","); current_row.tamanho = atol(token);
        token = strtok(NULL, ",");     current_row.threshold = atoi(token);
        
        // LÓGICA PRINCIPAL: Ignora se for o merge puro
        if (current_row.threshold == -1) {
            continue;
        }

        token = strtok(NULL, ",");     current_row.mediaCPU = atof(token);
        token = strtok(NULL, ",");     current_row.desvioCPU = atof(token);
        token = strtok(NULL, ",");     current_row.mediaReal = atof(token);
        token = strtok(NULL, ",");     current_row.desvioReal = atof(token);

        // 3. Encontrar o rastreador para este 'Tamanho'
        int found_index = -1;
        for (int i = 0; i < tracker_count; i++) {
            if (trackers[i].tamanho == current_row.tamanho) {
                found_index = i;
                break;
            }
        }

        if (found_index != -1) {
            // Já vimos esse 'Tamanho' antes. Verificar se este é melhor.
            if (current_row.mediaCPU < trackers[found_index].best_row.mediaCPU) {
                trackers[found_index].best_row = current_row; // Atualiza
            }
        } else {
            // Primeira vez que vemos este 'Tamanho'.
            if (tracker_count < INITIAL_CAPACITY) {
                trackers[tracker_count].tamanho = current_row.tamanho;
                trackers[tracker_count].best_row = current_row;
                // Inicializa o 'melhor' com DBL_MAX na primeira vez que o vemos
                // (Embora o primeiro encontrado seja o melhor por padrão)
                trackers[tracker_count].best_row.mediaCPU = current_row.mediaCPU;
                tracker_count++;
            } else {
                // Isso não deve acontecer se INITIAL_CAPACITY for 30
                fprintf(stderr, "Aviso: Excedeu a capacidade do rastreador.\n");
            }
        }
    }

    fclose(in_file);
    printf("Processamento do arquivo de entrada concluído.\n");

    // 4. Ordenar os resultados finais por 'Tamanho'
    qsort(trackers, tracker_count, sizeof(TamanhoTracker), compareTrackers);
    printf("Resultados ordenados por tamanho.\n");

    // 5. Escrever os resultados no arquivo de saída
    FILE *out_file = fopen(output_filename, "w");
    if (out_file == NULL) {
        perror("Erro ao criar o arquivo de saída");
        free(trackers);
        return EXIT_FAILURE;
    }

    // Escreve o cabeçalho
    fprintf(out_file, "Tamanho,Threshold,MediaCPU,DesvioCPU,MediaReal,DesvioReal,Algoritmo\n");

    // Escreve os dados
    for (int i = 0; i < tracker_count; i++) {
        ResultData row = trackers[i].best_row;
        fprintf(out_file, "%ld,%d,%.8f,%.8f,%.8f,%.8f,Merge+Insertion\n",
                row.tamanho,
                row.threshold,
                row.mediaCPU,
                row.desvioCPU,
                row.mediaReal,
                row.desvioReal);
    }

    fclose(out_file);
    free(trackers); // Libera a memória alocada

    printf("Arquivo '%s' gerado com sucesso!\n", output_filename);

    return EXIT_SUCCESS;
}
