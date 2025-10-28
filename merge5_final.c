#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

#define NUM_THRESHOLDS 23
int thresholds[NUM_THRESHOLDS] = {-1, 100, 90, 80, 70, 60, 50, 40, 30, 28,
                                  26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2};

#define NUM_SIZES 30
int sizes[NUM_SIZES] = {3, 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120,
                        10240, 20480, 40960, 81920, 163840, 327680,
                        655360, 1310720, 2621440, 5242880,
                        10485760, 20971520, 41943040, 83886080,
                        167772160, 335544320, 671088640, 1342177280};

#define NUM_RUNS 50

// --- Funções auxiliares ---
void merge(int *array, int *temp, int left, int mid, int right);
void hybridSort(int *array, int *temp, int left, int right, int threshold);
void insertionSort(int *array, int left, int right);
void mergeSort(int *array, int *temp, int left, int right);

// --- Estrutura para retorno de tempos ---
typedef struct
{
    double cpu_time;
    double wall_time;
} TimeResult;

// Insertion Sort para subvetores pequenos
void insertionSort(int *array, int left, int right)
{
    for (int i = left + 1; i <= right; i++)
    {
        int key = array[i];
        int j = i - 1;
        while (j >= left && array[j] > key)
        {
            array[j + 1] = array[j];
            j--;
        }
        array[j + 1] = key;
    }
}

// --- Merge Sort ---
void merge(int *array, int *temp, int left, int mid, int right)
{
    int i = left, j = mid + 1, k = left;
    for (int l = left; l <= right; l++)
        temp[l] = array[l];

    while (i <= mid && j <= right)
    {
        if (temp[i] <= temp[j])
            array[k++] = temp[i++];
        else
            array[k++] = temp[j++];
    }

    while (i <= mid)
        array[k++] = temp[i++];
    while (j <= right)
        array[k++] = temp[j++];
}

void mergeSort(int *array, int *temp, int left, int right)
{
    if (left < right)
    {
        int mid = left + (right - left) / 2;
        mergeSort(array, temp, left, mid);
        mergeSort(array, temp, mid + 1, right);
        merge(array, temp, left, mid, right);
    }
}

// --- Merge Sort híbrido ---
void hybridSort(int *array, int *temp, int left, int right, int threshold)
{
    if (right - left + 1 <= threshold)
    {
        insertionSort(array, left, right);
    }
    else
    {
        int mid = left + (right - left) / 2;
        hybridSort(array, temp, left, mid, threshold);
        hybridSort(array, temp, mid + 1, right, threshold);
        merge(array, temp, left, mid, right);
    }
}

// --- Função de teste de uma execução ---
TimeResult test_sort(int *original, int n, int threshold)
{
    int *array = malloc(n * sizeof(int));
    int *temp = malloc(n * sizeof(int));
    if (!array || !temp)
    {
        printf("Erro ao alocar memória\n");
        exit(1);
    }

    memcpy(array, original, n * sizeof(int));

    struct timespec start_wall, end_wall;
    clock_t start_cpu, end_cpu;

    clock_gettime(CLOCK_MONOTONIC, &start_wall);
    start_cpu = clock();

    if (threshold == -1)
        mergeSort(array, temp, 0, n - 1);
    else
        hybridSort(array, temp, 0, n - 1, threshold);

    end_cpu = clock();
    clock_gettime(CLOCK_MONOTONIC, &end_wall);

    double cpu_time = (double)(end_cpu - start_cpu) / CLOCKS_PER_SEC;
    double wall_time = (end_wall.tv_sec - start_wall.tv_sec) +
                       (end_wall.tv_nsec - start_wall.tv_nsec) / 1e9;

    free(array);
    free(temp);

    TimeResult result = {cpu_time, wall_time};
    return result;
}

int main()
{
    srand(42);

    FILE *raw_file = fopen("merge-insertion-raw_times.csv", "w");
    FILE *summary_file = fopen("merge-insertion-summary_results.csv", "w");

    if (!raw_file || !summary_file)
    {
        printf("Erro ao abrir arquivos de saída.\n");
        return 1;
    }

    fprintf(raw_file, "Tamanho,Threshold,Execucao,TempoCPU,TempoReal\n");
    fprintf(summary_file, "Tamanho,Threshold,MediaCPU,DesvioCPU,MediaReal,DesvioReal\n");

    printf("Tamanho\\Threshold");
    for (int i = 0; i < NUM_THRESHOLDS; i++)
    {
        if (thresholds[i] == -1)
            printf("\tMerge");
        else
            printf("\tHybrid(%d)", thresholds[i]);
    }
    printf("\n");

    for (int s = 0; s < NUM_SIZES; s++)
    {
        int n = sizes[s];
        printf("%d", n);

        int *original = malloc(n * sizeof(int));
        if (!original)
        {
            printf("Erro ao alocar vetor original\n");
            return 1;
        }

        for (int i = 0; i < n; i++)
            original[i] = rand();

        for (int t = 0; t < NUM_THRESHOLDS; t++)
        {
            int current_threshold = thresholds[t];
            double times_cpu[NUM_RUNS], times_wall[NUM_RUNS];
            double sum_cpu = 0.0, sum_wall = 0.0;

            for (int run = 0; run < NUM_RUNS; run++)
            {
                TimeResult result = test_sort(original, n, current_threshold);
                times_cpu[run] = result.cpu_time;
                times_wall[run] = result.wall_time;
                sum_cpu += result.cpu_time;
                sum_wall += result.wall_time;

                fprintf(raw_file, "%d,%d,%d,%.6f,%.6f\n", n, current_threshold, run + 1, result.cpu_time, result.wall_time);
            }

            double mean_cpu = sum_cpu / NUM_RUNS;
            double mean_wall = sum_wall / NUM_RUNS;

            double sum_sq_cpu = 0.0, sum_sq_wall = 0.0;
            for (int run = 0; run < NUM_RUNS; run++)
            {
                sum_sq_cpu += pow(times_cpu[run] - mean_cpu, 2);
                sum_sq_wall += pow(times_wall[run] - mean_wall, 2);
            }

            double std_cpu = sqrt(sum_sq_cpu / NUM_RUNS);
            double std_wall = sqrt(sum_sq_wall / NUM_RUNS);

            printf("\t%.4f/%.4f", mean_cpu, mean_wall);
            fprintf(summary_file, "%d,%d,%.6f,%.6f,%.6f,%.6f\n",
                    n, current_threshold, mean_cpu, std_cpu, mean_wall, std_wall);
        }

        printf("\n");
        free(original);
    }

    fclose(raw_file);
    fclose(summary_file);

    printf("\nResultados salvos em 'merge-insertion-raw_times.csv' e 'merge-insertion-summary_results.csv'.\n");
    return 0;
}

// Compilar:
// gcc -O2 -o execmerge5 merge5_final.c -lm
