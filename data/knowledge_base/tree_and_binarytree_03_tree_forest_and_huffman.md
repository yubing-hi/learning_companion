---
title: 树、森林与哈夫曼树
topic: tree_and_binarytree
subtopics: [tree_storage, forest, tree_binary_tree_conversion, forest_binary_tree_conversion, huffman_tree, huffman_coding]
aliases: [树, 森林, 哈夫曼树, 哈夫曼编码, 霍夫曼树, 霍夫曼编码, 孩子兄弟表示法, WPL]
language: zh-CN
related_files: [tree_and_binarytree_01_tree_and_binary_tree_basics.md, tree_and_binarytree_04_complexity_teaching_and_examples.md]
---

# 树、森林与哈夫曼树

## 五、树和森林

### 5.1 树的存储结构

#### 5.1.1 双亲表示法（顺序存储）
**结构定义**：
```c
#define MAX_TREE_SIZE 100
typedef struct PTNode {
    ElemType data;
    int parent;  // 双亲位置
} PTNode;

typedef struct {
    PTNode nodes[MAX_TREE_SIZE];
    int r;       // 根节点位置
    int n;       // 节点数
} PTree;
```

**特点**：
- 查找双亲方便（O(1)）
- 查找孩子需要遍历整个数组（O(n)）
- 适合以查双亲为主的场景

#### 5.1.2 孩子表示法（链式存储）
**结构定义**：
```c
typedef struct CTNode {
    int child;              // 孩子节点位置
    struct CTNode *next;    // 指向下一个孩子
} CTNode;

typedef struct {
    ElemType data;
    CTNode *firstchild;     // 第一个孩子指针
} CTBox;

typedef struct {
    CTBox nodes[MAX_TREE_SIZE];
    int n;                  // 节点数
    int r;                  // 根节点位置
} CTree;
```

**特点**：
- 查找孩子方便
- 查找双亲需要遍历（可增加parent域优化）
- 适合以查孩子为主的场景

#### 5.1.3 孩子兄弟表示法（二叉树表示法）
**结构定义**：
```c
typedef struct CSNode {
    ElemType data;
    struct CSNode *firstchild;  // 第一个孩子
    struct CSNode *nextsibling; // 下一个兄弟
} CSNode, *CSTree;
```

**特点**：
- 将树转换为二叉树
- 查找第一个孩子和下一个兄弟方便
- 适合树与二叉树的转换

### 5.2 树与二叉树的转换

#### 5.2.1 树转换为二叉树
**转换规则**（孩子兄弟表示法）：
1. 加线：在兄弟节点之间加一条连线
2. 去线：对每个节点，除了保留与其第一个孩子的连线外，去掉与其他孩子的连线
3. 旋转：以树的根节点为轴心，将整棵树顺时针旋转45度

**转换步骤**：
1. 将树中每个节点的第一个孩子作为二叉树节点的左孩子
2. 将树中每个节点的下一个兄弟作为二叉树节点的右孩子

#### 5.2.2 二叉树转换为树
**转换规则**：
1. 加线：若某节点的左孩子存在，则将该左孩子的右孩子、右孩子的右孩子...都作为该节点的孩子
2. 去线：删除原二叉树中所有节点与其右孩子的连线
3. 整理：将层次调整合适

### 5.3 森林与二叉树的转换

#### 5.3.1 森林转换为二叉树
**转换规则**：
1. 将森林中的每棵树转换为二叉树
2. 将第一棵树的根作为二叉树的根
3. 将第一棵树的根的右孩子指向第二棵树的根
4. 将第二棵树的根的右孩子指向第三棵树的根
5. 依此类推

**转换步骤**：
1. 将森林中各棵树的根节点视为兄弟
2. 按照树转二叉树的规则进行转换

#### 5.3.2 二叉树转换为森林
**转换规则**：
1. 若二叉树非空，则二叉树的根及其左子树为第一棵树
2. 二叉树根的右子树转换为森林
3. 递归进行

**转换步骤**：
1. 从二叉树的根开始，沿右指针将二叉树分解为多棵树
2. 将每棵树按二叉树转树的规则转换

### 5.4 树和森林的遍历

#### 5.4.1 树的遍历
- **先根遍历**：访问根节点，然后依次先根遍历每棵子树
- **后根遍历**：依次后根遍历每棵子树，然后访问根节点
- **层次遍历**：按层次从上到下，每层从左到右

**对应关系**：
- 树的先根遍历对应二叉树的先序遍历
- 树的后根遍历对应二叉树的中序遍历

#### 5.4.2 森林的遍历
- **先序遍历**：访问第一棵树的根，先序遍历第一棵树的子树森林，先序遍历剩余树构成的森林
- **中序遍历**：中序遍历第一棵树的子树森林，访问第一棵树的根，中序遍历剩余树构成的森林

**对应关系**：
- 森林的先序遍历对应二叉树的先序遍历
- 森林的中序遍历对应二叉树的中序遍历

## 六、哈夫曼树及其应用

### 6.1 基本概念

#### 6.1.1 路径和路径长度
- **路径**：从树中一个节点到另一个节点之间的分支构成的路径
- **路径长度**：路径上的分支数目

#### 6.1.2 节点的带权路径长度
节点的带权路径长度 = 节点的权值 × 该节点到根的路径长度

#### 6.1.3 树的带权路径长度（WPL）
树的带权路径长度 = 树中所有叶子节点的带权路径长度之和
WPL = Σ(wi × li)，其中wi为叶子节点的权值，li为该叶子节点到根的路径长度

### 6.2 哈夫曼树（最优二叉树）

#### 6.2.1 定义
在具有相同叶子节点数和相同权值集合的所有二叉树中，带权路径长度最小的二叉树称为哈夫曼树（Huffman Tree）或最优二叉树。

#### 6.2.2 哈夫曼树的性质
1. 哈夫曼树中没有度为1的节点（只有度为0和2的节点）
2. 权值越大的叶子节点离根越近
3. 哈夫曼树不唯一，但WPL唯一
4. 具有n个叶子节点的哈夫曼树共有2n-1个节点

### 6.3 构造哈夫曼树

#### 6.3.1 哈夫曼算法
**步骤**：
1. 根据给定的n个权值{w1, w2, ..., wn}，构造n棵只有一个根节点的二叉树，构成森林F
2. 在F中选取两棵根节点权值最小的树作为左右子树，构造一棵新的二叉树，新二叉树的根节点权值为左右子树根节点权值之和
3. 从F中删除这两棵树，将新树加入F
4. 重复步骤2和3，直到F中只剩下一棵树为止

#### 6.3.2 算法实现
```c
typedef struct {
    int weight;      // 权值
    int parent;      // 双亲位置
    int lchild;      // 左孩子位置
    int rchild;      // 右孩子位置
} HTNode, *HuffmanTree;

void CreateHuffmanTree(HuffmanTree HT, int *w, int n) {
    if (n <= 1) return;
    
    int m = 2 * n - 1;  // 哈夫曼树的节点总数
    HT = (HuffmanTree)malloc((m + 1) * sizeof(HTNode));  // 0号单元不用
    
    // 初始化叶子节点
    for (int i = 1; i <= n; i++) {
        HT[i].weight = w[i - 1];
        HT[i].parent = 0;
        HT[i].lchild = 0;
        HT[i].rchild = 0;
    }
    
    // 初始化非叶子节点
    for (int i = n + 1; i <= m; i++) {
        HT[i].weight = 0;
        HT[i].parent = 0;
        HT[i].lchild = 0;
        HT[i].rchild = 0;
    }
    
    // 构造哈夫曼树
    for (int i = n + 1; i <= m; i++) {
        int s1, s2;
        Select(HT, i - 1, s1, s2);  // 选择权值最小的两棵树
        
        HT[s1].parent = i;
        HT[s2].parent = i;
        HT[i].lchild = s1;
        HT[i].rchild = s2;
        HT[i].weight = HT[s1].weight + HT[s2].weight;
    }
}

// 选择权值最小的两棵树
void Select(HuffmanTree HT, int n, int &s1, int &s2) {
    int min1 = INT_MAX, min2 = INT_MAX;
    
    for (int i = 1; i <= n; i++) {
        if (HT[i].parent == 0) {  // 选择未被选中的节点
            if (HT[i].weight < min1) {
                min2 = min1;
                s2 = s1;
                min1 = HT[i].weight;
                s1 = i;
            } else if (HT[i].weight < min2) {
                min2 = HT[i].weight;
                s2 = i;
            }
        }
    }
}
```

### 6.4 哈夫曼编码

#### 6.4.1 问题的产生
在数据通信中，需要将字符编码为二进制序列。固定长度编码（如ASCII）效率不高，可变长度编码可以提高效率，但需要解决前缀码问题。

#### 6.4.2 前缀码
**定义**：任何字符的编码都不是另一个字符编码的前缀。

**优点**：
- 译码唯一
- 无需分隔符

#### 6.4.3 哈夫曼编码
**构造方法**：
1. 以字符出现的频率作为权值，构造哈夫曼树
2. 规定左分支为0，右分支为1
3. 从根到叶子节点的路径上的分支代码构成该叶子节点的编码

**特点**：
- 是最优前缀码
- 频率高的字符编码短，频率低的字符编码长
- 平均码长最短

#### 6.4.4 编码实现
```c
typedef char **HuffmanCode;

void HuffmanCoding(HuffmanTree HT, HuffmanCode &HC, int n) {
    HC = (HuffmanCode)malloc((n + 1) * sizeof(char *));
    char *cd = (char *)malloc(n * sizeof(char));
    cd[n - 1] = '\0';
    
    for (int i = 1; i <= n; i++) {
        int start = n - 1;
        int c = i;
        int f = HT[i].parent;
        
        // 从叶子到根逆向求编码
        while (f != 0) {
            --start;
            if (HT[f].lchild == c) {
                cd[start] = '0';
            } else {
                cd[start] = '1';
            }
            c = f;
            f = HT[f].parent;
        }
        
        HC[i] = (char *)malloc((n - start) * sizeof(char));
        strcpy(HC[i], &cd[start]);
    }
    
    free(cd);
}
```

#### 6.4.5 译码实现
```c
void HuffmanDecoding(HuffmanTree HT, char *code, char *text, int n) {
    int p = 2 * n - 1;  // 从根节点开始
    int i = 0, j = 0;
    
    while (code[i] != '\0') {
        if (code[i] == '0') {
            p = HT[p].lchild;
        } else {
            p = HT[p].rchild;
        }
        
        if (HT[p].lchild == 0 && HT[p].rchild == 0) {  // 到达叶子节点
            text[j++] = HT[p].weight;  // 假设weight存储字符
            p = 2 * n - 1;  // 回到根节点
        }
        
        i++;
    }
    
    text[j] = '\0';
}
```

### 6.5 哈夫曼树的应用

#### 6.5.1 数据压缩
- 文件压缩（如ZIP、GZIP）
- 图像压缩（如JPEG）
- 音频压缩（如MP3）

#### 6.5.2 优化判定过程
- 最优判定树
- 最优搜索树

#### 6.5.3 其他应用
- 网络路由
- 数据加密
- 机器学习中的决策树
