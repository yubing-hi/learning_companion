---
title: 二叉树遍历与线索二叉树
topic: tree_and_binarytree
subtopics: [binary_tree_traversal, preorder, inorder, postorder, level_order, threaded_binary_tree]
aliases: [二叉树遍历, 先序遍历, 前序遍历, 中序遍历, 后序遍历, 层序遍历, 线索二叉树, threaded binary tree]
language: zh-CN
related_files: [tree_and_binarytree_01_tree_and_binary_tree_basics.md, tree_and_binarytree_04_complexity_teaching_and_examples.md, queue.md]
---

# 二叉树遍历与线索二叉树

## 三、二叉树的遍历

### 3.1 遍历的定义
遍历（Traversal）是指按照某种搜索路径访问二叉树中的每个节点，且每个节点仅被访问一次。

### 3.2 遍历方式

#### 3.2.1 先序遍历（Preorder Traversal）
**访问顺序**：根节点 → 左子树 → 右子树

**递归实现**：
```c
void PreOrderTraverse(BiTree T) {
    if (T) {
        Visit(T->data);              // 访问根节点
        PreOrderTraverse(T->lchild); // 遍历左子树
        PreOrderTraverse(T->rchild); // 遍历右子树
    }
}
```

**迭代实现**：
```c
void PreOrderTraverse_Iterative(BiTree T) {
    if (!T) return;
    
    Stack S;
    InitStack(S);
    Push(S, T);
    
    while (!IsEmpty(S)) {
        BiTree p = Pop(S);
        Visit(p->data);
        
        if (p->rchild) Push(S, p->rchild); // 右子树先入栈
        if (p->lchild) Push(S, p->lchild); // 左子树后入栈
    }
}
```

**应用场景**：
- 树的复制
- 表达式的前缀表示
- 目录结构的遍历

#### 3.2.2 中序遍历（Inorder Traversal）
**访问顺序**：左子树 → 根节点 → 右子树

**递归实现**：
```c
void InOrderTraverse(BiTree T) {
    if (T) {
        InOrderTraverse(T->lchild); // 遍历左子树
        Visit(T->data);              // 访问根节点
        InOrderTraverse(T->rchild); // 遍历右子树
    }
}
```

**迭代实现**：
```c
void InOrderTraverse_Iterative(BiTree T) {
    Stack S;
    InitStack(S);
    BiTree p = T;
    
    while (p || !IsEmpty(S)) {
        if (p) {
            Push(S, p);
            p = p->lchild;  // 一直向左走
        } else {
            p = Pop(S);
            Visit(p->data);  // 访问节点
            p = p->rchild;   // 转向右子树
        }
    }
}
```

**应用场景**：
- 二叉排序树的有序遍历
- 表达式的中缀表示
- 求后继节点

#### 3.2.3 后序遍历（Postorder Traversal）
**访问顺序**：左子树 → 右子树 → 根节点

**递归实现**：
```c
void PostOrderTraverse(BiTree T) {
    if (T) {
        PostOrderTraverse(T->lchild); // 遍历左子树
        PostOrderTraverse(T->rchild); // 遍历右子树
        Visit(T->data);                // 访问根节点
    }
}
```

**迭代实现**：
```c
void PostOrderTraverse_Iterative(BiTree T) {
    if (!T) return;
    
    Stack S;
    InitStack(S);
    BiTree p = T, r = NULL;
    
    while (p || !IsEmpty(S)) {
        if (p) {
            Push(S, p);
            p = p->lchild;
        } else {
            GetTop(S, p);  // 取栈顶但不弹出
            
            if (p->rchild && p->rchild != r) {
                p = p->rchild;  // 转向右子树
            } else {
                p = Pop(S);
                Visit(p->data);
                r = p;  // 记录最近访问的节点
                p = NULL;
            }
        }
    }
}
```

**应用场景**：
- 树的销毁（后序释放内存）
- 表达式的后缀表示
- 求树的高度

#### 3.2.4 层次遍历（Level Order Traversal）
**访问顺序**：按层次从上到下，每层从左到右

**实现**：
```c
void LevelOrderTraverse(BiTree T) {
    if (!T) return;
    
    Queue Q;
    InitQueue(Q);
    EnQueue(Q, T);
    
    while (!IsEmpty(Q)) {
        BiTree p = DeQueue(Q);
        Visit(p->data);
        
        if (p->lchild) EnQueue(Q, p->lchild);
        if (p->rchild) EnQueue(Q, p->rchild);
    }
}
```

**应用场景**：
- 求树的宽度
- 判断完全二叉树
- 最短路径问题

### 3.3 遍历的性质

#### 3.3.1 遍历序列的唯一性
- 已知先序和中序遍历序列，可以唯一确定一棵二叉树
- 已知后序和中序遍历序列，可以唯一确定一棵二叉树
- 已知先序和后序遍历序列，不能唯一确定一棵二叉树（除非是满二叉树）

#### 3.3.2 遍历序列的关系
- 先序序列的第一个元素是根节点
- 后序序列的最后一个元素是根节点
- 中序序列中，根节点左边是左子树，右边是右子树

#### 3.3.3 由遍历序列构造二叉树

**由先序和中序构造**：
```c
BiTree BuildTree_PreIn(ElemType pre[], ElemType in[], int preStart, int preEnd, int inStart, int inEnd) {
    if (preStart > preEnd) return NULL;
    
    BiTree T = (BiTree)malloc(sizeof(BiTNode));
    T->data = pre[preStart];
    
    // 在中序序列中找到根节点位置
    int rootIndex = inStart;
    while (in[rootIndex] != pre[preStart]) rootIndex++;
    
    int leftSize = rootIndex - inStart;
    
    T->lchild = BuildTree_PreIn(pre, in, preStart + 1, preStart + leftSize, inStart, rootIndex - 1);
    T->rchild = BuildTree_PreIn(pre, in, preStart + leftSize + 1, preEnd, rootIndex + 1, inEnd);
    
    return T;
}
```

**由后序和中序构造**：
```c
BiTree BuildTree_PostIn(ElemType post[], ElemType in[], int postStart, int postEnd, int inStart, int inEnd) {
    if (postStart > postEnd) return NULL;
    
    BiTree T = (BiTree)malloc(sizeof(BiTNode));
    T->data = post[postEnd];
    
    // 在中序序列中找到根节点位置
    int rootIndex = inStart;
    while (in[rootIndex] != post[postEnd]) rootIndex++;
    
    int leftSize = rootIndex - inStart;
    
    T->lchild = BuildTree_PostIn(post, in, postStart, postStart + leftSize - 1, inStart, rootIndex - 1);
    T->rchild = BuildTree_PostIn(post, in, postStart + leftSize, postEnd - 1, rootIndex + 1, inEnd);
    
    return T;
}
```

### 3.4 遍历算法的应用

#### 3.4.1 求二叉树的深度
```c
int GetDepth(BiTree T) {
    if (!T) return 0;
    
    int leftDepth = GetDepth(T->lchild);
    int rightDepth = GetDepth(T->rchild);
    
    return (leftDepth > rightDepth ? leftDepth : rightDepth) + 1;
}
```

#### 3.4.2 求二叉树的节点数
```c
int CountNodes(BiTree T) {
    if (!T) return 0;
    return CountNodes(T->lchild) + CountNodes(T->rchild) + 1;
}
```

#### 3.4.3 求二叉树的叶子节点数
```c
int CountLeaves(BiTree T) {
    if (!T) return 0;
    if (!T->lchild && !T->rchild) return 1;
    return CountLeaves(T->lchild) + CountLeaves(T->rchild);
}
```

#### 3.4.4 复制二叉树
```c
BiTree CopyTree(BiTree T) {
    if (!T) return NULL;
    
    BiTree newT = (BiTree)malloc(sizeof(BiTNode));
    newT->data = T->data;
    newT->lchild = CopyTree(T->lchild);
    newT->rchild = CopyTree(T->rchild);
    
    return newT;
}
```

#### 3.4.5 判断两棵二叉树是否相等
```c
bool IsEqual(BiTree T1, BiTree T2) {
    if (!T1 && !T2) return true;
    if (!T1 || !T2) return false;
    return (T1->data == T2->data) &&
           IsEqual(T1->lchild, T2->lchild) &&
           IsEqual(T1->rchild, T2->rchild);
}
```

## 四、线索二叉树

### 4.1 引入线索二叉树的原因
在二叉链表中，有n个节点就有n+1个空指针域。这些空指针域可以用来存放指向节点在某种遍历次序下的前驱和后继节点的指针，这种指针称为线索（Thread）。

**优点**：
- 充分利用空指针域
- 提高遍历效率（无需递归或栈）
- 便于查找前驱和后继节点

### 4.2 线索二叉树的基本概念

#### 4.2.1 线索的定义
- **前驱线索**：指向节点在遍历序列中前驱节点的指针
- **后继线索**：指向节点在遍历序列中后继节点的指针

#### 4.2.2 线索化
将二叉树中的空指针改为指向前驱或后继的线索的过程称为线索化。

#### 4.2.3 线索二叉树的类型
- **先序线索二叉树**：按先序遍历线索化
- **中序线索二叉树**：按中序遍历线索化（最常用）
- **后序线索二叉树**：按后序遍历线索化

### 4.3 线索二叉树的存储结构

#### 4.3.1 结构定义
```c
typedef enum { Link, Thread } PointerTag;  // Link=0表示孩子指针，Thread=1表示线索

typedef struct ThreadNode {
    ElemType data;                    // 数据域
    struct ThreadNode *lchild;        // 左指针
    struct ThreadNode *rchild;        // 右指针
    PointerTag LTag;                  // 左标志
    PointerTag RTag;                  // 右标志
} ThreadNode, *ThreadTree;
```

**标志位含义**：
- LTag = 0：lchild指向左孩子
- LTag = 1：lchild指向前驱节点
- RTag = 0：rchild指向右孩子
- RTag = 1：rchild指向后继节点

### 4.4 二叉树的线索化

#### 4.4.1 中序线索化
```c
ThreadTree pre = NULL;  // 全局变量，指向前驱节点

void InThread(ThreadTree T) {
    if (T) {
        InThread(T->lchild);  // 线索化左子树
        
        // 建立当前节点的前驱线索
        if (!T->lchild) {
            T->LTag = Thread;
            T->lchild = pre;
        }
        
        // 建立前驱节点的后继线索
        if (pre && !pre->rchild) {
            pre->RTag = Thread;
            pre->rchild = T;
        }
        
        pre = T;  // 保持前驱
        
        InThread(T->rchild);  // 线索化右子树
    }
}

// 中序线索化二叉树
void InOrderThreading(ThreadTree *Thrt, ThreadTree T) {
    *Thrt = (ThreadTree)malloc(sizeof(ThreadNode));
    (*Thrt)->LTag = Link;
    (*Thrt)->RTag = Thread;
    (*Thrt)->rchild = *Thrt;  // 右指针回指
    
    if (!T) {
        (*Thrt)->lchild = *Thrt;  // 空树，左指针回指
    } else {
        (*Thrt)->lchild = T;
        pre = *Thrt;
        InThread(T);  // 线索化
        pre->rchild = *Thrt;  // 最后一个节点的后继指向头节点
        pre->RTag = Thread;
        (*Thrt)->rchild = pre;  // 头节点的右指针指向最后一个节点
    }
}
```

#### 4.4.2 先序线索化
```c
void PreThread(ThreadTree T) {
    if (T) {
        // 建立当前节点的前驱线索
        if (!T->lchild) {
            T->LTag = Thread;
            T->lchild = pre;
        }
        
        // 建立前驱节点的后继线索
        if (pre && !pre->rchild) {
            pre->RTag = Thread;
            pre->rchild = T;
        }
        
        pre = T;
        
        if (T->LTag == Link) PreThread(T->lchild);  // 只线索化左孩子
        if (T->RTag == Link) PreThread(T->rchild);  // 只线索化右孩子
    }
}
```

#### 4.4.3 后序线索化
后序线索化相对复杂，因为需要处理父节点的线索。

### 4.5 线索二叉树的遍历

#### 4.5.1 中序线索二叉树的遍历
```c
void InOrderTraverse_Thr(ThreadTree T) {
    ThreadTree p = T->lchild;  // p指向根节点
    
    while (p != T) {  // 空树或遍历结束时，p==T
        while (p->LTag == Link) {
            p = p->lchild;  // 找到最左下节点
        }
        
        Visit(p->data);  // 访问左下节点
        
        while (p->RTag == Thread && p->rchild != T) {
            p = p->rchild;  // 沿后继线索访问
            Visit(p->data);
        }
        
        p = p->rchild;  // 转向右子树
    }
}
```

#### 4.5.2 先序线索二叉树的遍历
```c
void PreOrderTraverse_Thr(ThreadTree T) {
    ThreadTree p = T->lchild;
    
    while (p != T) {
        Visit(p->data);
        
        if (p->LTag == Link) {
            p = p->lchild;  // 有左孩子，访问左孩子
        } else {
            p = p->rchild;  // 无左孩子，沿线索访问
        }
    }
}
```

### 4.6 线索二叉树的优缺点

**优点**：
- 遍历效率高，时间复杂度O(n)，空间复杂度O(1)
- 便于查找前驱和后继节点
- 充分利用空指针域

**缺点**：
- 插入和删除操作复杂
- 需要额外的标志位
- 构造线索二叉树需要额外的时间
