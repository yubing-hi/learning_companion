---
title: 平衡二叉树（AVL树）
topic: avl_tree
subtopics: [avl_concept, balance_factor, rotation_operations, insertion_deletion, performance_analysis]
aliases: [AVL树, 平衡二叉树, 平衡因子, 旋转操作, LL旋转, RR旋转, LR旋转, RL旋转]
language: zh-CN
related_files: [avl_tree_02_implementation_details_and_examples.md, avl_tree_03_comparison_with_other_balanced_trees.md]
---

# 平衡二叉树（AVL树）

## 1. 基本概念与定义
平衡二叉树（AVL树）是一种特殊的二叉排序树，由Adelson-Velsky和Landis于1962年提出。其定义如下：
- 空树是平衡二叉树
- 非空树满足以下条件：
  1. 左右子树都是平衡二叉树
  2. 左右子树的高度差的绝对值不超过1（即平衡因子的绝对值≤1）

**平衡因子（Balance Factor）**：结点的左子树高度减去右子树高度，记为BF。
- BF = 0：左右子树等高
- BF = 1：左子树比右子树高1
- BF = -1：右子树比左子树高1

## 2. 结点结构定义
```c
typedef struct AVLNode {
    int data;           // 结点数据
    int height;         // 结点高度
    struct AVLNode *left, *right;  // 左右孩子指针
} AVLNode, *AVLTree;
```

## 3. 基本操作函数

### 3.1 获取结点高度
```c
int getHeight(AVLNode* node) {
    if (node == NULL) return 0;
    return node->height;
}
```

### 3.2 更新结点高度
```c
void updateHeight(AVLNode* node) {
    if (node != NULL) {
        node->height = fmax(getHeight(node->left), getHeight(node->right)) + 1;
    }
}
```

### 3.3 计算平衡因子
```c
int getBalanceFactor(AVLNode* node) {
    if (node == NULL) return 0;
    return getHeight(node->left) - getHeight(node->right);
}
```

## 4. 平衡调整（旋转操作）
当插入或删除结点导致树失去平衡时，需要通过旋转操作恢复平衡。根据失衡情况分为四种类型：

### 4.1 LL型（右旋）
**情况**：在结点A的左孩子的左子树上插入结点导致失衡
**调整方法**：以A为轴心进行右旋

```c
AVLNode* rotateRight(AVLNode* y) {
    AVLNode* x = y->left;
    AVLNode* T2 = x->right;
    
    // 执行旋转
    x->right = y;
    y->left = T2;
    
    // 更新高度
    updateHeight(y);
    updateHeight(x);
    
    return x;  // 新的根结点
}
```

### 4.2 RR型（左旋）
**情况**：在结点A的右孩子的右子树上插入结点导致失衡
**调整方法**：以A为轴心进行左旋

```c
AVLNode* rotateLeft(AVLNode* x) {
    AVLNode* y = x->right;
    AVLNode* T2 = y->left;
    
    // 执行旋转
    y->left = x;
    x->right = T2;
    
    // 更新高度
    updateHeight(x);
    updateHeight(y);
    
    return y;  // 新的根结点
}
```

### 4.3 LR型（先左旋后右旋）
**情况**：在结点A的左孩子的右子树上插入结点导致失衡
**调整方法**：先对A的左孩子进行左旋，再对A进行右旋

```c
AVLNode* rotateLR(AVLNode* z) {
    z->left = rotateLeft(z->left);
    return rotateRight(z);
}
```

### 4.4 RL型（先右旋后左旋）
**情况**：在结点A的右孩子的左子树上插入结点导致失衡
**调整方法**：先对A的右孩子进行右旋，再对A进行左旋

```c
AVLNode* rotateRL(AVLNode* z) {
    z->right = rotateRight(z->right);
    return rotateLeft(z);
}
```

## 5. 插入操作
插入操作在二叉排序树插入的基础上，增加了平衡检查和调整：

```c
AVLNode* insert(AVLNode* node, int key) {
    // 1. 执行标准BST插入
    if (node == NULL) {
        AVLNode* newNode = (AVLNode*)malloc(sizeof(AVLNode));
        newNode->data = key;
        newNode->left = newNode->right = NULL;
        newNode->height = 1;
        return newNode;
    }
    
    if (key < node->data) {
        node->left = insert(node->left, key);
    } else if (key > node->data) {
        node->right = insert(node->right, key);
    } else {
        // 相等的键值，不插入
        return node;
    }
    
    // 2. 更新当前结点的高度
    updateHeight(node);
    
    // 3. 获取平衡因子
    int balance = getBalanceFactor(node);
    
    // 4. 如果当前结点失衡，进行相应的旋转
    // Left Left Case
    if (balance > 1 && key < node->left->data) {
        return rotateRight(node);
    }
    
    // Right Right Case
    if (balance < -1 && key > node->right->data) {
        return rotateLeft(node);
    }
    
    // Left Right Case
    if (balance > 1 && key > node->left->data) {
        return rotateLR(node);
    }
    
    // Right Left Case
    if (balance < -1 && key < node->right->data) {
        return rotateRL(node);
    }
    
    // 返回未改变的结点指针
    return node;
}
```

## 6. 删除操作
删除操作比插入更复杂，因为删除可能导致多个祖先结点失衡：

```c
AVLNode* deleteNode(AVLNode* root, int key) {
    // 1. 执行标准BST删除
    if (root == NULL) return root;
    
    if (key < root->data) {
        root->left = deleteNode(root->left, key);
    } else if (key > root->data) {
        root->right = deleteNode(root->right, key);
    } else {
        // 找到要删除的结点
        if ((root->left == NULL) || (root->right == NULL)) {
            AVLNode* temp = root->left ? root->left : root->right;
            if (temp == NULL) {
                temp = root;
                root = NULL;
            } else {
                *root = *temp;
            }
            free(temp);
        } else {
            // 有两个子结点，找到中序后继
            AVLNode* temp = minValueNode(root->right);
            root->data = temp->data;
            root->right = deleteNode(root->right, temp->data);
        }
    }
    
    if (root == NULL) return root;
    
    // 2. 更新高度
    updateHeight(root);
    
    // 3. 获取平衡因子
    int balance = getBalanceFactor(root);
    
    // 4. 如果失衡，进行旋转调整
    // Left Left Case
    if (balance > 1 && getBalanceFactor(root->left) >= 0) {
        return rotateRight(root);
    }
    
    // Left Right Case
    if (balance > 1 && getBalanceFactor(root->left) < 0) {
        return rotateLR(root);
    }
    
    // Right Right Case
    if (balance < -1 && getBalanceFactor(root->right) <= 0) {
        return rotateLeft(root);
    }
    
    // Right Left Case
    if (balance < -1 && getBalanceFactor(root->right) > 0) {
        return rotateRL(root);
    }
    
    return root;
}

// 辅助函数：找到最小值结点
AVLNode* minValueNode(AVLNode* node) {
    AVLNode* current = node;
    while (current->left != NULL) {
        current = current->left;
    }
    return current;
}
```

## 7. 性能分析
- **时间复杂度**：
  - 查找：O(log n)
  - 插入：O(log n)
  - 删除：O(log n)
- **空间复杂度**：O(n)
- **优点**：
  - 保证树的高度始终保持在O(log n)
  - 查找、插入、删除操作的时间复杂度稳定
  - 适用于频繁查找且数据动态变化的场景
- **缺点**：
  - 实现复杂，需要维护高度信息
  - 插入和删除时可能需要多次旋转操作
  - 对于小规模数据，额外的维护开销可能超过收益

## 8. 与其他平衡树的比较
| 特性 | AVL树 | 红黑树 |
|------|-------|--------|
| 平衡程度 | 严格平衡（高度差≤1） | 近似平衡 |
| 查找性能 | 更优（树更矮） | 稍差 |
| 插入/删除 | 可能需要多次旋转 | 最多两次旋转 |
| 实现复杂度 | 较高 | 中等 |
| 适用场景 | 查找密集型应用 | 插入/删除密集型应用 |

## 9. 教学要点
- **理解平衡因子的概念**：BF = left_height - right_height
- **掌握四种旋转类型的判断条件**：
  - LL型：BF > 1 且 插入在左子树的左侧
  - RR型：BF < -1 且 插入在右子树的右侧
  - LR型：BF > 1 且 插入在左子树的右侧
  - RL型：BF < -1 且 插入在右子树的左侧
- **理解旋转操作的本质**：保持二叉排序树性质的同时恢复平衡
- **注意高度更新的时机**：每次插入/删除后都要更新路径上所有结点的高度