---
title: 排序算法基础
topic: sorting_algorithms
subtopics: [basic_concepts, insertion_sort, selection_sort, exchange_sort, merge_sort, other_sorting_algorithms]
aliases: [排序, 排序算法, 内部排序, 外部排序, 稳定性, 时间复杂度, 空间复杂度]
language: zh-CN
related_files: [sort_02_algorithm_comparision.md]
---

# 排序算法基础

## 一、排序的基本概念

### 1.1 定义
排序是将一组记录按照某个或某些关键字的大小，递增或递减排列的过程。排序是数据处理中经常使用的一种重要运算。

### 1.2 基本术语
- **关键字**：数据元素中某个可以标识该元素的数据项
- **主关键字**：可以唯一标识一个记录的关键字
- **次关键字**：可以标识多个记录的关键字
- **内部排序**：整个排序过程在内存中进行
- **外部排序**：排序过程中需要访问外存
- **稳定性**：如果待排序记录中有两个记录Ri和Rj，它们的关键字相等，且在排序前Ri在Rj之前，排序后它们的相对次序保持不变，则称该排序算法是稳定的

### 1.3 排序算法评价指标
- **时间复杂度**：比较次数和移动次数
- **空间复杂度**：算法所需的额外存储空间
- **稳定性**：排序后相同关键字记录的相对次序是否改变
- **适用性**：数据规模、数据分布、是否频繁更新等

## 二、插入排序

### 2.1 直接插入排序

#### 2.1.1 算法思想
将待排序的记录插入到已排序的有序表中，从而得到一个新的、记录数增1的有序表。

#### 2.1.2 算法实现
```c
void InsertSort(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}
```

#### 2.1.3 性能分析
- 时间复杂度：平均O(n²)，最好O(n)，最坏O(n²)
- 空间复杂度：O(1)
- 稳定性：稳定
- 适用场景：小规模数据，基本有序的数据

### 2.2 希尔排序

#### 2.2.1 算法思想
先将整个待排序记录序列分割成若干子序列分别进行直接插入排序，待整个序列中的记录"基本有序"时，再对全体记录进行一次直接插入排序。

#### 2.2.2 算法实现
```c
void ShellSort(int arr[], int n) {
    for (int gap = n / 2; gap > 0; gap /= 2) {
        for (int i = gap; i < n; i++) {
            int key = arr[i];
            int j = i - gap;
            while (j >= 0 && arr[j] > key) {
                arr[j + gap] = arr[j];
                j -= gap;
            }
            arr[j + gap] = key;
        }
    }
}
```

#### 2.2.3 性能分析
- 时间复杂度：依赖于增量序列，平均约为O(n^1.3)
- 空间复杂度：O(1)
- 稳定性：不稳定
- 适用场景：中等规模数据

## 三、选择排序

### 3.1 直接选择排序

#### 3.1.1 算法思想
每一趟在待排序的记录中选出关键字最小的记录，顺序放在已排序的记录序列的最后。

#### 3.1.2 算法实现
```c
void SelectSort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int min_idx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[min_idx]) {
                min_idx = j;
            }
        }
        if (min_idx != i) {
            int temp = arr[i];
            arr[i] = arr[min_idx];
            arr[min_idx] = temp;
        }
    }
}
```

#### 3.1.3 性能分析
- 时间复杂度：O(n²)
- 空间复杂度：O(1)
- 稳定性：不稳定
- 适用场景：记录较少，对稳定性无要求

### 3.2 堆排序

#### 3.2.1 算法思想
利用堆这种数据结构所设计的排序算法。堆是一个近似完全二叉树的结构，并同时满足堆的性质：子结点的键值或索引总是小于（或大于）它的父结点。

#### 3.2.2 算法实现
```c
void Heapify(int arr[], int n, int i) {
    int largest = i;
    int left = 2 * i + 1;
    int right = 2 * i + 2;
    
    if (left < n && arr[left] > arr[largest]) {
        largest = left;
    }
    if (right < n && arr[right] > arr[largest]) {
        largest = right;
    }
    if (largest != i) {
        int temp = arr[i];
        arr[i] = arr[largest];
        arr[largest] = temp;
        Heapify(arr, n, largest);
    }
}

void HeapSort(int arr[], int n) {
    // 建立大顶堆
    for (int i = n / 2 - 1; i >= 0; i--) {
        Heapify(arr, n, i);
    }
    
    // 逐个取出堆顶元素
    for (int i = n - 1; i > 0; i--) {
        int temp = arr[0];
        arr[0] = arr[i];
        arr[i] = temp;
        Heapify(arr, i, 0);
    }
}
```

#### 3.2.3 性能分析
- 时间复杂度：O(n log n)
- 空间复杂度：O(1)
- 稳定性：不稳定
- 适用场景：大规模数据，对稳定性无要求

## 四、交换排序

### 4.1 冒泡排序

#### 4.1.1 算法思想
重复地走访要排序的数列，一次比较两个元素，如果它们的顺序错误就把它们交换过来。

#### 4.1.2 算法实现
```c
void BubbleSort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        bool swapped = false;
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
                swapped = true;
            }
        }
        if (!swapped) break;
    }
}
```

#### 4.1.3 性能分析
- 时间复杂度：平均O(n²)，最好O(n)，最坏O(n²)
- 空间复杂度：O(1)
- 稳定性：稳定
- 适用场景：小规模数据，基本有序的数据

### 4.2 快速排序

#### 4.2.1 算法思想
通过一趟排序将待排记录分割成独立的两部分，其中一部分记录的关键字均比另一部分记录的关键字小，然后分别对这两部分记录继续进行排序。

#### 4.2.2 算法实现（Hoare版本）
```c
int Partition(int arr[], int low, int high) {
    int pivot = arr[low];
    while (low < high) {
        while (low < high && arr[high] >= pivot) high--;
        arr[low] = arr[high];
        while (low < high && arr[low] <= pivot) low++;
        arr[high] = arr[low];
    }
    arr[low] = pivot;
    return low;
}

void QuickSort(int arr[], int low, int high) {
    if (low < high) {
        int pivotpos = Partition(arr, low, high);
        QuickSort(arr, low, pivotpos - 1);
        QuickSort(arr, pivotpos + 1, high);
    }
}
```

#### 4.2.3 性能分析
- 时间复杂度：平均O(n log n)，最好O(n log n)，最坏O(n²)
- 空间复杂度：平均O(log n)，最坏O(n)
- 稳定性：不稳定
- 适用场景：大规模数据，对稳定性无要求

## 五、归并排序

### 5.1 算法思想
将已有序的子序列合并，得到完全有序的序列；即先使每个子序列有序，再使子序列段间有序。

### 5.2 算法实现
```c
void Merge(int arr[], int low, int mid, int high) {
    int *temp = (int*)malloc((high - low + 1) * sizeof(int));
    int i = low, j = mid + 1, k = 0;
    
    while (i <= mid && j <= high) {
        if (arr[i] <= arr[j]) {
            temp[k++] = arr[i++];
        } else {
            temp[k++] = arr[j++];
        }
    }
    
    while (i <= mid) temp[k++] = arr[i++];
    while (j <= high) temp[k++] = arr[j++];
    
    for (i = low, k = 0; i <= high; i++, k++) {
        arr[i] = temp[k];
    }
    
    free(temp);
}

void MergeSort(int arr[], int low, int high) {
    if (low < high) {
        int mid = (low + high) / 2;
        MergeSort(arr, low, mid);
        MergeSort(arr, mid + 1, high);
        Merge(arr, low, mid, high);
    }
}
```

### 5.3 性能分析
- 时间复杂度：O(n log n)
- 空间复杂度：O(n)
- 稳定性：稳定
- 适用场景：大规模数据，要求稳定性

## 六、其他排序算法

### 6.1 基数排序
- 按照低位先排序，然后收集；再按照高位排序，然后再收集
- 时间复杂度：O(d(n+r))，d为位数，r为基数
- 空间复杂度：O(n+r)
- 稳定性：稳定
- 适用场景：整数排序，位数较少

### 6.2 计数排序
- 适用于一定范围内的整数排序
- 时间复杂度：O(n+k)，k为整数范围
- 空间复杂度：O(n+k)
- 稳定性：稳定
- 适用场景：整数范围较小

