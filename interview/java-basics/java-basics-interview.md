# Java 基础高频面试题（语法 · 集合 · 并发 · 新特性）

> 面向 **JDK 8～25** 常见考点（**21 / 25** 均为 **LTS**；**预览特性与 API 以所用 JDK 与项目为准**）。含**分层答法**、**（基础补充）**、**场景题**、**面经补充**与 **自测表**。与 **JVM**、**Spring** 文档可交叉复习。

---

## 目录

### 快速锚点（`#sec-*` 可点击跳转）

| 锚点 | 内容 |
|------|------|
| [CHM / HashMap（JDK7·8）](#sec2-chm) | 分段锁 vs CAS + 桶头 `synchronized` |
| [synchronized（JDK8 锁）](#sec5-sync) | Mark Word、锁升级与膨胀 |
| [ReentrantLock · AQS · Condition](#sec5-lock) | 公平、可中断、`state`、`Condition` |
| [AQS · CLH 同步队列](#sec5-aqs-clh) | `Node`、FIFO、`park` / `unpark` |
| [Latch · Semaphore · Barrier](#sec5-aqs-juc) | 共享 AQS、协调工具 |
| [读写锁 · `StampedLock`](#sec5-rw) | `RRW`、`Stamp`、乐观读 |
| [volatile · CAS · 原子类](#sec5-jmm-atomic) | happens-before、`LongAdder` |
| [BlockingQueue / COW List](#sec5-queue) | `ArrayBlockingQueue`、`LinkedBlockingQueue`、`CopyOnWriteArrayList` |
| [ThreadPoolExecutor](#sec5-tpe) | 预热、超时回收、`shutdown*`、观测钩子等 |

### 分章

1. [一、语言基础与面向对象](#一语言基础与面向对象)  
2. [二、集合框架](#二集合框架) — 含 [CHM 深挖](#sec2-chm)  
3. [三、异常与泛型](#三异常与泛型)  
4. [四、IO / NIO](#四io--nio)  
5. [五、并发基础](#五并发基础) — [sync](#sec5-sync) · [Lock/AQS](#sec5-lock) · [CLH](#sec5-aqs-clh) · [JUC](#sec5-aqs-juc) · [RW / Stamped](#sec5-rw) · [队列](#sec5-queue) · [池](#sec5-tpe) · [JMM](#sec5-jmm-atomic)  
6. [六、Java 8～25 新特性](#六java-825-新特性速记)  
7. [七、场景题](#七场景题) — [近年场景补充](#sec7-scenes)  
8. [八、进阶补充](#八进阶补充)  
9. [九、面经补充](#sec9-mianjing) — 题 **44～66**  
10. [十、自测清单](#十自测清单)

> **复习主线：** **`==/equals` → 集合（HashMap/CHM）→ 线程池 → `volatile`/原子类 → AQS/JUC → Stream/虚拟线程**。**官文：** <https://docs.oracle.com/en/java/> 、 <https://openjdk.org/>  
> **面经口径** 与 OpenJDK / 常见面经对齐；**链路以文内 HTML 锚点为准**（预览器需支持行内 `<a id="…">`）。

---

## 一、语言基础与面向对象

### Java 平台与字节码是什么？（开胃）

**答：** **`.java` 经 `javac` 编译为 `.class`（字节码）**，由 **JVM** **加载 → 验证 → 准备 → 解析 → 初始化**（初始化阶段见 JVM 文档），再 **解释执行** 或由 **JIT** 编译为本地代码。**JDK = 语言 + 工具 + 标准库**；**JRE 侧重运行环境**（现代语境多直接说 JDK）。**规范**：**JLS** 定义语言；**JVMS** 定义字节码与 class 文件——面试深挖时区分 **「语言保证」与「HotSpot 实现/调优」**。

---

### 1. `==` 与 `equals` 区别？String 比较注意什么？

**答（分层）：**

1. **`==`**：**基本类型** 比较 **值**；**引用类型** 比较 **是否同一对象**（引用相等）。
2. **`equals`**：Object 默认 **等同于 `==`**；**String、包装类型** 等重写为 **逻辑相等**。
3. **String：** **字面量** 入 **字符串常量池**（编译期能确定的常量折叠等），故 **同字面量 `==` 常 true**；**`new String("x")`** 堆上新建，**`==` 字面量多为 false`**。**`intern()`** 可将堆实例与池中引用对齐。
4. **工程：** **`Objects.equals(a, b)`** 防空指针；**业务比较勿依赖 `==`**（除枚举单例等明确场景）。

---

### 2. `hashCode` 与 `equals` 约定？

**答：** **契约（覆写必背）：**

- **`equals` 为 true ⇒ `hashCode` 必须相同**（否则 HashMap/HashSet 破坏桶）。
- **`hashCode` 相同 ⇒ `equals` 不必为 true**（冲突正常）。

**实现提示：** `Objects.hash(...)` 或 **31 多项式** 组合字段；**参与 `equals` 的字段应参与 `hashCode`**。**可变对象** 改字段后 **hash 变化** → **Map 中「丢失」**，故 **key 宜不可变**（与 **题 10** 呼应）。

---

### 3. 抽象类与接口区别？Java 8+ 之后呢？

**答：**

| 维度 | 抽象类 | 接口（Java 8+） |
|------|--------|-----------------|
| 继承 | **单继承** | **多实现** |
| 状态 | 可有 **字段、构造器** | 多为常量 **public static final**；**实例字段** 在 **Java 8+ 前无** |
| 方法 | 抽象 + 具体 | **`default` / `static`（8）**、**`private` 实例方法（9）** 丰富 |
| 设计 | **is-a 强抽象**、模板方法 | **能力组合**、`@FunctionalInterface` 支撑 **Lambda** |

**追问：** **函数式接口** = 仅 **一个抽象方法**（可多个 default）。

---

### 4. `final` 修饰类、方法、变量？

**答：** **类**：**不可被继承**（如 `String`、常见工具类）。**方法**：**子类不可重写**（可与 **早期绑定** 优化一并记）。**变量**：**引用不可变**——**不能再指向别的对象**；**若指向可变对象**（如 `StringBuilder`），**对象内容仍可改**。**`final` 与 可见性**：常被与 **安全发布**、`volatile` 对比考。

---

### 5. 字符串拼接 `+` 与 `StringBuilder`？

**答：** **编译器**：**常量表达式** 可能 **编译期折叠** 为一个字面量。**运行时循环里 `+=`**：通常等价于多次 `StringBuilder.append`（字节码可反编译验证）；**手写单个 `StringBuilder`** 可少建临时对象。**JDK 9+**：`String.concat` / 编译策略有演进，**面试答「编译器优化 + 大循环用 Builder」** 即可。**线程安全**：`**StringBuffer**` 带同步，**单线程拼禁用** 一般选 **StringBuilder**。

---

### 6. 序列化 `serialVersionUID` 有什么用？

**答：** **反序列化** 时用 **`serialVersionUID`** 校验 **类版本兼容**：**不一致** 抛 **InvalidClassException**。**不显式声明**：依赖编译器根据类细节生成，**改字段名/签名** 易导致 **UID 漂移**、线上反序列化失败。**实践：** `private static final long serialVersionUID = ...L` **显式固定**；**`transient`** 字段不落盘；**兼容性策略** 与 **API 版本** 一起设计。

---

### （基础补充）`Object` 还有哪些常考方法？

**答：** **`toString`、`equals`、`hashCode`、`clone`（`Cloneable`）、`finalize`（已过时）、`getClass`、`notify/notifyAll`、`wait`**。面试常追问 **`clone` 浅拷贝** 与 **`Cloneable` 标记接口** 的设计争议；**优先 copy 构造器或拷贝工厂**。

---

### （基础补充）重载（Overload）与重写（Override）？

**答：** **重载**：**同签名方法名**、**参数列表不同**（类型/个数/顺序）；**返回类型单独变不构成重载**；**编译期绑定**。**重写**：**子类** 与父类 **方法签名一致**、**返回类型协变**；**访问权限不可更窄**；抛异常 **不能更宽**；**`@Override` 建议必写**。

---

### （基础补充）包装类型、`==` 与缓存？

**答：** **整型包装** 使用 **`Integer.valueOf`** 时，默认缓存 **-128～127**（上限可通过 JVM 参数 `java.lang.Integer.IntegerCache.high` 调整），故 **自动装箱** 落在缓存内时 **`==` 可能为 true**；**`new Integer(1)`** 恒为新对象、**勿用 `==`**。**`Float`、`Double`** **无** 整型那种固定缓存，**比较必须用 `equals` 或 `Float.compare`**。与 **题 1、46** 合并记忆。

---

### （基础补充）强 / 软 / 弱 / 虚引用？（近年常问）

**答：** **`StrongReference`**：默认，**只要可达 GC 不回收**。**`SoftReference`**：**内存紧张才回收**，适合 **敏感缓存**（图片缓存等，仍可能 OOM）。**`WeakReference`**：**下一次 GC 就可能清**，典型 **`WeakHashMap`**（key 弱）、**`ThreadLocal`** 的 Entry key。**`PhantomReference`**：**无法通过引用取对象**，用于 **回收跟踪 / 事前清理**（配合 `ReferenceQueue`）。面经：**不要** 指望引用类型当「精确析构」；**资源释放** 仍靠 **try-with-resources / `Cleaner`（JDK9+）** 等显式策略。

---

## 二、集合框架

### 7. `ArrayList` 与 `LinkedList`？

**答：** **ArrayList**：**动态数组**，扩容 **约 1.5 倍**（以 JDK 源码为准），**随机访问 O(1)**，尾部插入 **均摊 O(1)**，**中间插入** 搬移 **O(n)**。**LinkedList**：**双向链表**，头尾 **O(1)**，按索引 **O(n)**。**CPU 缓存**：数组 **局部性好**，多数业务 **默认 ArrayList**；**LinkedList** 适合 **双端队列**、频繁头尾删插（亦可选 **`ArrayDeque`** 对比）。

---

### 8. `HashMap` 底层？JDK8 链表过长怎么办？

**答：** **数组 + 链表/红黑树**。**hash 扰动后取桶**；冲突挂链。**树化**：链表长 **≥ 8** 且 **容量 ≥ 64** 转 **红黑树**；**元素过少（≤ 6）** 可 **退链**。**负载因子 0.75**、容量 **2 的幂**。**JDK7 并发扩容头插成环** → **`get` 死循环**；**JDK8 尾插** 缓解但 **仍非线程安全**。**`put` 主线**：**hash & (n-1)** 定位桶 → **空则新建节点** → **否则链表/树里找 key**（有则覆盖 value）→ **尾插 + 计数** → **超阈值则树化或扩容**（**CHM 才大量用 CAS**，勿混）。

---

### 9. `HashMap` 线程安全吗？`ConcurrentHashMap` 呢？

**答：** **`HashMap`**：**否**。**`ConcurrentHashMap`**：**JDK7 `Segment` 分段**；**JDK8+** **`Node` 数组 + CAS + synchronized（必要时锁首节点）`**，**读路径多无锁 volatile**。**`Collections.synchronizedMap`**：**互斥锁包一层**。**`Hashtable`**：过时。**详见题 44**。**实现深挖见下节 [CHM / HashMap](#sec2-chm)**。

---

<a id="sec2-chm"></a>

### （基础补充）`HashMap` 与 `ConcurrentHashMap`：JDK 7 / JDK 8 与面经

#### A. `HashMap`（非线程安全）

| 维度 | JDK 7 | JDK 8 |
|------|--------|--------|
| 结构 | 数组 + 链表 | 数组 + 链表/红黑树 |
| 冲突插入 | 头插 | 尾插 |
| 并发扩容 | 可能 **成环** → `get` 死循环 | 尾插避免该死循环；**仍不能多线程写** |
| 树化 | 无 | 链表 **≥8** 且容量 **≥64**；**≤6** 退链 |

#### B. `ConcurrentHashMap` JDK 7：`Segment` + `ReentrantLock`

- **分段锁**：每段一把锁，**并发度 ≈ Segment 数**（默认 16）。**`get`** 常尽量不持段锁；**`put`** 锁段。

#### C. `ConcurrentHashMap` JDK 8+：`Node[]` + CAS + 桶头 `synchronized`

- **空桶**：**CAS** 放首结点。  
- **扩容**：`ForwardingNode`，**多线程协助迁移**。  
- **冲突**：对 **桶头** `synchronized`，链表/树内操作。  
- **`get`**：多 **无锁 volatile 读**；与 **`put`/`size`** **弱一致**。  
- **禁止 `null` key/value**（`HashMap` 允许一个 `null` key）。

#### D. 面经追问

| 问 | 要点 |
|----|------|
| `size()` | **非全局原子快照**；实现为近似/重试等。 |
| 迭代 | **弱一致**，**无 `ConcurrentModificationException`**。 |
| `computeIfAbsent` | **原子计算 + 插入**；回调勿阻塞。 |
| `putIfAbsent` vs `computeIfAbsent` | **`putIfAbsent`**：已有则**不覆盖**，**无**计算；**`computeIfAbsent`**：无则**跑一次 mapping**，需防**重计算/阻塞**。 |

---

### 10. `HashMap` 的 `key` 为什么常建议不可变对象？

**答：** **`hashCode`/`equals` 依赖字段** 在 **插入后变更** → **错桶/找不到**。**宜：** `String`、枚举、**不可变值对象**。

---

### 11. `fail-fast` 与 `fail-safe`？

**答：** **fail-fast**：**`modCount`** 与迭代器 **`expectedModCount`** 不一致 → **`ConcurrentModificationException`**（**`Iterator.remove` 合法**）。**fail-safe**（如 **COW**）：**迭代副本**，**可能看不到最新写**。

---

### （基础补充）`Map` / `Collections` 怎么选？

**答：** **`LinkedHashMap`**：按 **插入或访问序**（`accessOrder`），可做 **LRU**（覆写 **`removeEldestEntry`**）。**`TreeMap`**：**红黑树**、`NavigableMap`。**`EnumMap`**：**枚举为键** 省内存。**`Collections.unmodifiableXxx`**：**视图**，底层变仍可见；**`emptyList` 等** 不可变单例。**勿** 误以为 **unmodifiable = 深拷贝**。

---

## 三、异常与泛型

### 12. `Error` 与 `Exception`？受检与非受检？

**答：** **`Throwable`** 分 **`Error`**（如 **`OutOfMemoryError`、`StackOverflowError`**）—— **一般不捕获**、属 **JVM/不可恢复**；与 **`Exception`**。**受检异常**（`IOException`）：编译器要求 **`throws` 或 try/catch**。**非受检 `RuntimeException`**：可 **不显式声明**。**业务**：自定义 **运行时异常 + 错误码**；避免 **API 全 throws Exception**。

---

### 13. 泛型擦除是什么？带来什么问题？

**答：** **编译期** 做 **类型检查**；**字节码** 中多擦为 **原始类型**（`List<String>` → `List`），必要时 **合成桥方法** 保持多态。**运行时**：`list.getClass()` **无 `<String>`**。**坑：** **`new T[]` 非法**；**`instanceof` / 原始类型 catch**；**反射** 要 `ParameterizedType` 才拿泛型信息。**PECS**：`Producer Extends, Consumer Super`。

---

### （基础补充）`try-catch-finally` 与 `return`？

**答：** **`finally`** 常执行（**`System.exit`、线程死亡等除外**）；**`finally` 里 return** 会 **覆盖 try 返回值**（笔试题）。**`try-with-resources`**：关闭顺序 **逆序**，**抑制异常** **`addSuppressed`**。**try-with-resources** 优于手写 `finally` 关流。

---

## 四、IO / NIO

### 14. BIO、NIO、AIO 区别？（口头）

**答：** **BIO**：**一连接一线程**，**accept/read** 阻塞，**C10K** 压力大。**NIO（New I/O / NIO2 部分）**：**Channel + Buffer + Selector**，**单线程多路复用** 监听多 Channel **就绪事件**（Linux **epoll**），**Netty** 默认基于此模型。**AIO（NIO2 AsynchronousChannel）**：**异步回调/ Future**；**Linux** 上实现可能仍用 **线程池模拟**，**与平台相关**。**面试：** **高并发网关：NIO/epoll**。

---

### 15. `try-with-resources` 要求？

**答：** 资源类实现 **`AutoCloseable`**（`Closeable` 是其子接口）；**编译器脱糖** 为 **try-finally 安全关闭**。**多资源**：**分号分隔**，**逆序关闭**。**异常**：**首要异常抛出**，关闭异常 **`Throwable.addSuppressed`**。

---

### （基础补充）NIO `Buffer` 简要？

**答：** **`capacity/limit/position/mark`**；**`flip()`** 读模式准备；**`clear()`** 写模式重置。**`DirectByteBuffer`**：堆外内存，**零拷贝** 路径相关，**分配昂贵**，见 JVM **直接内存 OOM**。

---

## 五、并发基础

### 16. 创建线程几种方式？`start` 与 `run`？

**答：** **实质**：**底层都是 `Thread` 与 `Runnable.run`**。**常见形态**：继承 `Thread`（少用）、**`new Thread(runnable)`**、**`FutureTask` + Callable**、**线程池 `Executor.execute/submit`**。**`start()`**：**新栈**、**JVM 调度**；**`run()`**：**当前线程普通调用**。**`Callable`**：**有返回值、可抛受检异常**，经 **`Future.get`** 获取。

---

### 17. 线程池参数？`ThreadPoolExecutor` 拒绝策略？

**答：** **核心线程数**、**最大线程数**、**存活时间**、**工作队列**、**线程工厂**（命名、守护、优先级）、**拒绝策略**。队列满且线程达 **`maximumPoolSize`** 触发 **拒绝**：

| 策略 | 行为 |
|------|------|
| **AbortPolicy**（默认） | 抛 **`RejectedExecutionException`** |
| **CallerRuns** | **调用者线程**执行，**背压** |
| **Discard** | **静默丢** |
| **DiscardOldest** | **丢队列头** 再试提交 |

**有界队列 + CallerRuns/降级** 防 **`Executors` 无界队列 OOM**。

**执行顺序（易错）：** **核心未满 → 建核心线程执行**；**核心满 → 入队**；**队列满 → 扩到 `maximumPoolSize`**；**再满 → 拒绝**。**不是**先满最大线程再入队。**`LinkedBlockingQueue` 默认近似无界时** `maximumPoolSize`** 往往用不上**。详见 [ThreadPoolExecutor](#sec5-tpe)。

**`Executors` 坑：** **`newFixedThreadPool`/`newSingleThreadExecutor`** 用无界 **`LinkedBlockingQueue`** → 堆积 **OOM**；**`newCachedThreadPool`** 线程上限极大 → 突发 **线程爆炸**。**生产用 `ThreadPoolExecutor` 显式构造**。

---

### 18. `synchronized` 与 `ReentrantLock`？

**答：** **`synchronized`**：JVM **监视器**，**自动释放**。**`ReentrantLock`**：**可中断、超时、`tryLock`、公平/非公平**、**Condition**；**须在 `finally unlock`**。深挖见 [JDK8 锁升级](#sec5-sync)、[ReentrantLock / AQS](#sec5-lock)、[读写锁 / StampedLock](#sec5-rw)。**虚拟线程** 长时间持锁慎用 **`synchronized`**（**pinning**），可换 **`ReentrantLock`**。

<a id="sec5-sync"></a>

### （基础补充）`synchronized`：JDK 8 HotSpot 锁升级（面经）

| 状态 | 含义 | lock bits（常考） |
|------|------|------------------|
| 无锁 | hash/年龄等 | `01`，偏向位 0 |
| 偏向锁 | 偏向一线程 | `01`，偏向位 1 |
| 轻量级 | 栈 Lock Record + CAS | `00` |
| 重量级 | `ObjectMonitor` | `10` |

**链路：** 无锁 → 偏向 → 轻量 → 重量（竞争加剧）。**锁膨胀**：轻量失败等 → **重量级 monitor**。**JDK 15+** 偏向默认关并逐步移除；**JDK 21+** 有 **fast-locking** 等——深挖答「以所用 JDK 为准」。

---

<a id="sec5-lock"></a>

### （基础补充）`ReentrantLock`、AQS、`Condition`

|  | `synchronized` | `ReentrantLock` |
|--|----------------|-----------------|
| 释放 | 自动 | `finally` 中 **`unlock`** |
| 可中断等锁 | 否 | **`lockInterruptibly`** |
| 超时/尝试 | 否 | **`tryLock`** |
| 公平 | 非公平可选语义 | **构造参数 `fair`** |
| 条件 | 一个 wait 集 | **多个 `Condition`** |

**AQS（独占）：** **`state`** = 重入计数；**FIFO 同步队列** + CAS；**公平** = 禁止插队抢 **`state`**。自定义同步器：子类实现 **`tryAcquire` / `tryRelease`（独占）** 或 **`tryAcquireShared` / `tryReleaseShared`（共享）**；**不要** 直接绕开 AQS 队列 API **错误唤醒**。

<a id="sec5-aqs-clh"></a>

#### CLH 变体同步队列（口述）

- **CLH**：队列锁思想，竞争关注 **前驱**。  
- **AQS**：**变体** — **`Node` 双向链表**、**`park`/`unpark`**、独占/共享、取消；**≠ 纯自旋论文实现**。  
- **`Condition`** 是 **另一队列**，勿与 sync queue 混。  
- **三句：** `state` + CLH 风格 FIFO + `park`；共享 **`releaseShared`** 可连续唤醒。

#### `Condition` 铁律

持锁下 **`await`/`signal`**；**`await` 用 `while`** 防虚假唤醒。

---

<a id="sec5-aqs-juc"></a>

### （基础补充）`CountDownLatch`、`Semaphore`、`CyclicBarrier`

同步队列结构见 [CLH 小节](#sec5-aqs-clh)。

|  | AQS | `state` 含义 | 重用 |
|--|-----|--------------|------|
| `ReentrantLock` | 独占 | 重入次数 | 是 |
| `CountDownLatch` | 共享 | 剩余计数 | **一次性** |
| `Semaphore` | 共享 | 剩余许可 | 是 |
| `CyclicBarrier` | **非 AQS** | Lock + Condition | **多轮** |

- **Latch：`await` / `countDown`**；到 0 **放行所有等待者**。  
- **Semaphore：`acquire`/`release`；`release` 不必同线程**（防多释/漏释）。  
- **Barrier：各线程 `await`；齐了就下一轮**；中断等 → **`BrokenBarrierException`**。  
- **`Phaser`**：**动态注册**参与者、**多阶段** barrier，游戏/多阶段流水线面经可带一句。

---

<a id="sec5-rw"></a>

### （基础补充）`ReentrantReadWriteLock` 与 `StampedLock`

| | 读锁 | 写锁 |
|--|------|------|
| **`ReentrantReadWriteLock`** | **共享**（多线程可同时读） | **独占**（与读互斥） |
| **升降级** | **不支持读→写**（易死锁）；**写→读降级** 合法（先持写再拿读再释放写） | 见 [面经 57](#sec9-mianjing) |

**`StampedLock`：** **非 AQS**；**乐观读 `tryOptimisticRead` + `validate`** 失败再转悲观锁；**stamp 配对释放**；**不可重入**、**无 `Condition`**。与 **题 36、面经 62** 合并复习。

---

<a id="sec5-jmm-atomic"></a>

### （基础补充）`volatile`、CAS、原子类

- **`volatile`：** **可见性 + 有序约束**（**happens-before**）；**不保证** `i++` 原子。  
- **happens-before（常背）：** **`volatile` 写 → 同 volatile 晚读**；**`unlock` → 后续同监视器 `lock`**；**`Thread.start` → 新线程动作**；**`join` 结束 → 调用线程读该线程结果**。  
- **CAS / ABA：** 无版本号时 **地址值从 A→B→A** 仍会认为未变；用 **`AtomicStampedReference` / `AtomicMarkableReference`**。  
- **`LongAdder` vs `AtomicLong`：** 高竞争 **累加** 用 **`LongAdder`**（多 Cell，`sum` 近似）；要 **随时可读的全局 CAS 语义** 或 **低竞争** 用 **`AtomicLong`**。  
- **字段级原子更新：** **`AtomicIntegerFieldUpdater`** 等对 **已有类已有字段** 做 CAS（**可见性约束**、**不要用 private 乱反射**）。  
- **假共享（false sharing）：** 多核上相邻 **高频计数器** 同缓存行互相 **失效** → 剧降；JDK 有 **`@jdk.internal.vm.annotation.Contended`**（框架/面试点到为止）；**`LongAdder`** 本身也缓解竞争。  
- **`VarHandle`（9+）：** 标准 API 做 **volatile 读/写、有序、CAS**；替代部分 **Unsafe** 用法（面经：**规范代码优先 VarHandle**）。

---

<a id="sec5-queue"></a>

### （基础补充）`BlockingQueue` 与 `CopyOnWriteArrayList`

> **`CopyOnWriteArrayList`** 是 **`List`**（**非** `BlockingQueue`），同属 **`java.util.concurrent`**，面试常和阻塞队列 **放一起对比「读多写少」方案**，故放在本节。

#### API 四族（必背）

|  | 抛异常 | 特殊值 | 阻塞 | 限时 |
|--|--------|--------|------|------|
| 入 | `add` | `offer` | `put` | `offer(…, time)` |
| 出 | `remove` | `poll` | `take` | `poll(…, time)` |

---

#### `ArrayBlockingQueue` vs `LinkedBlockingQueue`（超高频）

| 维度 | **`ArrayBlockingQueue`** | **`LinkedBlockingQueue`** |
|------|--------------------------|---------------------------|
| **底层** | **定长循环数组** | **单向链表节点**（含 `count`） |
| **有界** | **必须**指定 `capacity` | **构造可指定**；**无参构造** 容量约为 **`Integer.MAX_VALUE`** ≈ **无界**（面经雷区） |
| **锁** | 典型 **`ReentrantLock` + 一两个 `Condition`**，**入/出常共用同一把锁**（实现以 JDK 源码为准） | **两把锁**：**`putLock` + `takeLock`**，**头尾分离**，高并发下 **入队与出队更易并行** |
| **内存** | **预分配数组**，无 per-element 节点对象 | **每个元素一个 Node**，GC 压力更大 |
| **局部性** | 数组 **CPU 缓存友好** | 链表 **跳跃访问** |
| **公平** | 构造可选 **`fair`**（吞吐略降、防饥饿） | 同（以构造器为准） |
| **线程池** | **显式 `ThreadPoolExecutor` + 有界 `ArrayBlockingQueue`** 很常见 | **`Executors.newFixedThreadPool` 内部用默认 `LinkedBlockingQueue`** → **无界 OOM**（**题 27**） |

**口述口诀：** **要背压、生产必限长** → 优先 **有界**；**`LinkedBlockingQueue()` 空参 ≈ 无界**；**ABQ 一员一把锁、LBQ 双锁头尾**。

**其它 `BlockingQueue`：** **`SynchronousQueue`**：不存元素，**一对一直传**；配合 **较大的 `maximumPoolSize`**。**`PriorityBlockingQueue`**：**无界** 堆，**`put` 不阻塞**（满的概念弱），堆积仍 **OOM**。**`DelayQueue`**：**元素到期** 才能被 **`take`**。**`LinkedTransferQueue`**：带 **`transfer`（等到消费者拿走）** 等，吞吐量调优面经偶问。

---

<a id="sec5-cow"></a>

#### `CopyOnWriteArrayList`（并发 **List**，写时复制）

| 点 | 说明 |
|----|------|
| **适用** | **读极多、写极少**（监听器列表、配置快照、白名单） |
| **写语义** | **`add/set/remove`** 时 **拷贝整份底层数组** 再替换引用，写 **`O(n)`**、**占两份数组瞬时内存** |
| **迭代** | **`iterator` 基于某次快照**，**弱一致**，**不抛 `ConcurrentModificationException`**；**可能看不到刚写入** |
| **不要用** | **写频繁**、**大列表**（**复制爆炸**） |

**和 `Vector` / `Collections.synchronizedList`：** 后两者 **读也要同步**；**COW** **读无锁**（仅读引用后遍历数组）。**和 `ConcurrentLinkedQueue`：** 后者 **无界非阻塞队列**，**不是 List**。

---

<a id="sec5-tpe"></a>

### （基础补充）`ThreadPoolExecutor` 深挖

- **`submit` vs `execute`：** 非 `Runnable` 包装异常多在 **`Future.get`** 才冒泡；勿吞 **`ExecutionException`**。  
- **`shutdown`**：停接新任务、已提交继续跑；**`shutdownNow`**：**中断** worker + 返回队列中任务；**`awaitTermination`**：**限时等跑完**。  
- **`allowCoreThreadTimeOut(true)`**：闲时核心也可回收（默认核心不因超时销毁）。**`prestartAllCoreThreads`**：启动即预热核心线程。  
- **观测/扩展：** **`getPoolSize`、`getActiveCount`、`getQueue().size()`**；可覆写 **`beforeExecute` / `afterExecute`** 打点。  
- **`discardOldest`**：丢 **队头** 再提交，**须确认业务允许丢最老任务**。  
- **`ScheduledThreadPoolExecutor`：** 替代 **`Timer`**（单线程、任务异常拖死调度）。  
- **`ForkJoinPool`：** 工作窃取；**勿把阻塞 IO 铺满 `commonPool`**（`parallelStream` 默认池）。

---

### 19. `ThreadLocal` 内存泄漏？

**答：** **`ThreadLocalMap`** 的 **Entry 以 ThreadLocal 为 key（弱引用）**、**value 强引用**；**线程池** 线程长期存活 → **value 不释放**。**规范：** **`try { ... } finally { tl.remove(); }`**。**`InheritableThreadLocal`**：子线程**继承**父值；**虚拟线程/线程池** 注意 **传播语义**。

---

### （基础补充）线程状态与 `InterruptedException`？

**答：** **`NEW/RUNNABLE/BLOCKED/WAITING/TIMED_WAITING/TERMINATED`**（以枚举为准）。**`interrupt()`**：**打中断标志**；**阻塞在 `wait/join/sleep/IO` 等** 会 **抛 `InterruptedException` 并清标志**，**应恢复中断 `Thread.currentThread().interrupt()`** 或 **在高层处理**。**不要** 吞掉中断异常。

---

## 六、Java 8～25 新特性速记

### 20. Java 8：Lambda、Stream、`Optional`？

**答：** **函数式接口**（`@FunctionalInterface`，**仅一个抽象方法**，可有 default）+ **Lambda/方法引用**。**Stream**：**中间操作**（`map/filter/sorted`）**惰性**，**终端操作**（`collect/forEach/reduce`）**触发流水线**。**`Optional`**：**显式可空**，避免 **NPE**；**不要** 作字段、**不要** 滥用 `get()`。

---

### 21. Java 9～11 常考点？

**答：** **JPMS**（**`module-info.java`、`exports/opens`**，迁移痛点多）。**10：`var`**。**11：`HttpClient`**、**`Files.readString`**、**单文件 `java Hello.java` 运行**、**ZGC 实验入口**（版本有关）。**面试：** **模块化 vs classpath**。

---

### 22. Java 17 LTS：密封类、`record`、模式匹配？

**答：** **`sealed` + permits**：限制 **可继承子集**，与 **`switch` 穷尽性** 配合。**`record`**：**不可变载体**、**自动生成访问器/equals/hashCode/toString**、**可嵌套与接口实现**。**模式匹配**：`instanceof` 绑定、`switch` **`case String s`** 等，减少样板代码。

---

### 23. Java 21 LTS：虚拟线程（Virtual Threads）？

**答：** **`Thread.ofVirtual().start(...)` / `Executors.newVirtualThreadPerTaskExecutor()`**：**海量任务** 映射到 **少量载体平台线程**；**阻塞**（IO、`park`）时 **卸載**，**别在 synchronized 里长时间阻塞**（**pinning**）削弱收益 → **用 `ReentrantLock`** 等。**CPU 密集** 仍靠 **并行度控制 + 算法**。追问 **「结构化并发 / 子任务取消」** → **`StructuredTaskScope`**（**面经 64**）；**请求上下文传播** → **`ScopedValue` vs `ThreadLocal`**（**面经 65**）。

---

### 24. `record` 与 Lombok `@Data` 区别（口头）？

**答：** **`record`**：**语言语义**、**继承受限**、**序列化/反射** 行为 **标准**。**Lombok**：**编译期注解处理器** 生成样板码，**IDE/增量编译** 要配置。**选型：** 公共 API DTO 倾向 **record**（JDK 17+）。

---

### （版本补充）JDK 25 与 JDK 21，面经怎么答？

**答：** **JDK 21** 仍是 **虚拟线程、模式匹配等能力** 的「主力 LTS 参考」；**JDK 25** 为 **2025 年起的新 LTS**（具体与支持周期以 [Oracle / OpenJDK 发布公告](https://openjdk.org/projects/jdk/25/) 为准）。面试若问「为何升 25」→ **长期安全更新、运行时与 GC 演进、基准测试收益**，并强调 **依赖与框架兼容性验证**、**勿死记 JEP 清单**。业务代码仍优先保证 **在团队统一 JDK 上跑通测试**。

---

## 七、场景题

### 25. 场景：高并发计数用 `volatile long` 行吗？

**答：** **不行（用于 `count++` 这类复合操作）**。`volatile` 只保证 **可见性**，不保证 **read-modify-write** 原子性；多线程 **`i++`** 仍会 **丢更新**。

**正确做法：** **`AtomicLong.addAndGet`** 或 **`LongAdder`**（**高竞争** 下多 Cell 分散竞争，吞吐更好）；必须 **与业务状态强绑定** 时用 **`synchronized`** 包住临界区。  
**面试收束：** **volatile ≠ 原子计数**。**详见 [volatile / CAS / 原子类](#sec5-jmm-atomic)**。

---

### 26. 场景：`HashMap` 多线程 `put` 死循环（JDK7）？

**答：** **JDK7** 扩容时 **头插法** 迁移链表，并发下可能 **形成环**，`get` **死循环**。**JDK8** 改为 **尾插** + 树化，**避免该死循环**，但 **多线程 put 仍不保证正确性**（**丢数据、覆盖异常**）。

**生产环境** 并发写 **必须用 `ConcurrentHashMap`** 或 **外部锁**。  
**收束：** **HashMap 非线程安全**，问题不止 JDK7 死循环。

---

### 27. 场景：线程池用 `Executors.newFixedThreadPool` 有什么问题？

**答：** 工厂方法 **`newFixedThreadPool(n)`** 内部使用 **`LinkedBlockingQueue` 无界队列**：任务提交速度 **持续大于** 处理速度时，**队列无限涨**，**最终 OOM**。

**推荐：** 显式 **`ThreadPoolExecutor`**，**有界队列**（`ArrayBlockingQueue` 等）+ **`CallerRunsPolicy` / 自定义拒绝** + **明确命名线程** + **监控队列长度**。  
**收束：** **无界队列是生产事故常见来源**。

---

### 28. 场景：`SimpleDateFormat` 并发问题？

**答：** **`SimpleDateFormat` 非线程安全**（内部可变状态），多线程共用 **会错乱或抛异常**。

**做法：** **`ThreadLocal<SimpleDateFormat>`**（注意 **线程池** 中 **remove** 防泄漏）；或 **Java 8+ `DateTimeFormatter` 不可变**，可安全共享；或 **每次 `new SimpleDateFormat`**（开销可接受时）。

---

### 29. 场景：大列表去重统计？

**答：** **内存放得下**：**`new HashSet<>(list)`** 或 **`stream().distinct()`** 得到 **去重后集合/流**。**只要个数**：**`Set` 大小**。

**内存放不下或近似即可**：**布隆过滤器** 判重；**超大规模** **外部排序** 或 **MapReduce/分布式**。**面试** 先说 **Set/distinct**，再问 **数据规模** 再延伸。

---

### 30. 场景：接口要兼容老客户端，新增字段？

**答：** **API 契约** 上：**老客户端** 应 **忽略未知 JSON 字段**（多数库默认如此）；**新字段** 给 **默认值** 或 **可选**。服务端 **接口版本号**（`/v2`）或 **请求头** 区分行为。

**Java 服务端：** **`default` 接口方法**、**DTO 新增字段用包装类型** 便于判空。**序列化**（Protobuf/Avro）用 **向后兼容 schema 演进** 规则。

---

### 31. 场景：虚拟线程适合什么业务？

**答：** **虚拟线程（Project Loom）** 适合 **大量阻塞式 IO**（HTTP 客户端、JDBC、锁等待），用 **同步写法** 获得 **高并发连接** 而 **不必为每个请求开一个平台线程**。

**不适合：** 把 **CPU 密集计算** 铺到海量虚拟线程上——**仍会占满 CPU**，应 **并行流、专用线程池、分片**。  
**收束：** **阻塞换吞吐，不替代算法复杂度**。

<a id="sec7-scenes"></a>

### （近年场景补充 · 面经口径）

以下与 **近年 Java 后端面经整理帖**（如掘金等 **2025～2026「八股 + 场景」** 汇总）、**Spring/JavaLab 等并发面试向文章**、以及 **OpenJDK 21+ 文档中的虚拟线程 / 结构化并发 / `ScopedValue`** 的常见追问 **大致对齐**；**编者未逐条复核真伪**，请你以 **官方文档 + 自己项目 JDK 版本** 为准。**死记参数不如说「压测 + 监控 + 有界背压」**。

#### 场景 A：`corePoolSize` / `maximumPoolSize` / 队列长度怎么定？

**答：** **CPU 密集**：`core` ≈ **`Runtime.getRuntime().availableProcessors()`**（或 **+1**），`max` 不必远大于 `core`，队列可偏小，避免过度线程切换。**IO 密集**：线程常在等 IO，**池可更大**，经典 **粗估** `N * (1 + 等待时间/计算时间)`（**Little定律**思想）；**仍以压测与指标为准**。**队列**：生产 **`有界`** + **`CallerRuns`/拒绝策略** 做背压；**忌** 无界堆积（**题 27**）。**隔离**：不同业务 **独立线程池**，防 **慢调用拖死全局**。

#### 场景 B：网关调下游 RT 飙高，本服务线程池「看似有线程」却不消费？

**答：** **先排**：队列长度、**活跃线程**、任务是否 **全阻塞在下游**（HTTP/JDBC **未设超时** 会占满 worker）、**死锁**、**pinned 虚拟线程**。**手段**：**超时 + 熔断/舱壁**（框架层）、**池隔离**、**限流**；**虚拟线程** 场景查 **载体池是否被 pinning/synchronized 拖住**（**题 23**、**面经 63**）。

#### 场景 C：用 `HashMap` 做多线程「缓存」偶发错乱？

**答：** **`HashMap`** **非线程安全**：可见性、**无限死循环（JDK7 扩容）**、`size` 不准、**丢失更新** 都有可能。**正确**：**`ConcurrentHashMap`**，或 **Caffeine / Guava Cache** 等；读多写极少可考虑 **不变快照** + 定期替换。

#### 场景 D：接口要 **幂等**，Java 服务侧怎么收口？

**答：** **业务唯一键**（订单号、`Idempotency-Key` 头）+ **DB 唯一索引** / **状态机** 防重复落账；短时 **去重表**。**与分布式事务/消息** 可交叉看框架文档；**本地**：`ConcurrentHashMap.putIfAbsent` 只适合 **进程内、可丢** 的简易 gate。**答场景题先讲「唯一约束 + 能扛重试 + 可观测」**。

#### 场景 E：金额用 `double`，线上对账差一分钱？

**答：** **金融/金额** 用 **`BigDecimal`**，**`String` 构造** 或 **`valueOf` 注意二进制浮点陷阱**。**比较大小** 用 **`compareTo`**；**`equals` 还看 `scale`**，**2.0 与 2.00 可能不相等**。除法指定 **`RoundingMode`**。面经：**double 只适合科学计算/近似**。

#### 场景 F：`Stream.collect` / `parallelStream` 结果偶尔错？

**答：** **`Collectors.toMap` 键冲突** 未合并函数会 **`IllegalStateException`**，要 **`toMap(k,v, merge)`**。**并行** 流：**可变累加**（`ArrayList::add`）**必错**；用 **`collect` 的线程安全收集器** 或 **规约**（**题 41**、**题 37**）。

#### 场景 G：异步链（`CompletableFuture` / 虚拟线程）里 **MDC 日志上下文丢了**？

**答：** **线程边界** 不自动拷贝 **ThreadLocal 风格上下文**。**做法**：在 **切换线程时封装 Runnable**（MDC `copy`/`run`）、或用框架自带 **context 传播**；**JDK 21+** 可关注 **`ScopedValue`**（**不可变、按作用域绑定、可跨子线程快照式传播**），与 **`ThreadLocal` 可变可泄漏** 对比常考点（**面经 65**）。

#### 场景 H：大促前 **全链路压测**，Java 侧你最关心哪几项指标？

**答：** **延迟分位（P95/P99）**、**错误率**、**线程池队列长度与拒绝次数**、**GC pause / 分配速率**、**直接内存**（若 Netty）、**Metaspace**。与 **JVM 文档** 交叉：**先瓶颈定位再调参**。

---

## 八、进阶补充

### 32. `Comparable` 与 `Comparator`？

**答：** **自然排序** vs **外部比较器**；**TreeMap/TreeSet** 依赖 **Comparable** 或构造传入 **Comparator**；**优先级队列** 同。

---

### 33. 子类重写 `equals` 的里氏替换注意？

**答：** **对称性、传递性**；**`getClass` vs `instanceof`** 风格争论；**继承体系** 中 **父类 equals 与子类** 混用易错，常建议 **组合优于继承** 或 **不可继承的类 + 工厂**。

---

### 34. `Optional` 反模式？

**答：** **不要** `Optional` 字段/序列化默认值滥用；**不要** `get()` 裸用；**链式** `map/filter/orElse`；**返回类型** 表达可空比 **null** 更清晰。

---

### 35. `CompletableFuture` 与线程池？

**答：** **默认 `ForkJoinPool.commonPool()`**；**IO 密集** 应 **自定义 Executor**，避免 **抢占公共池**；**异常** `exceptionally/handle`；**组合** `thenCompose` 防嵌套。

**深挖：** **`runAsync`** 无返回值，**`supplyAsync`** 有；**`thenApplyAsync`** 可指定 **Executor**；**`get`** 受检 **`ExecutionException`**，**`join`** 包装为非受检；**`allOf`/`anyOf`** 组合多任务。回调里 **长时间阻塞** 会占满池。

---

### 36. `StampedLock` 适用场景？

**答：** **读多写少**；**乐观读** `tryOptimisticRead` → **`validate` 失败再悲观读/写**；**stamp 必须配对释放**，**不可重入**、**无 `Condition`**。**一般先用 `ReentrantReadWriteLock` 评审通过再上**。规范对照见 **[读写锁与 StampedLock](#sec5-rw)**。

---

### 37. `Stream` 并行流 `parallelStream()` 注意？

**答：** 默认 **`ForkJoinPool.commonPool()`**，与 **CPU 核数** 相关。**数据源** 必须 **可高效拆分**（`ArrayList`、数组等优于 **有序链表**）。**`reduce`/合并** 需 **结合律**；**共用可变集合** 必错。**forEachOrdered** 保序有开销。**不要在并行流里阻塞 IO**。顺序/吞吐以 **JMH 或压测** 为准。深问见 **[ForkJoin / commonPool](#sec5-tpe)**、[面经 61](#sec9-mianjing)。

---

### 38. 文本块（Text Blocks）与 `formatted`？

**答：** **Java15+** 三引号字符串；**缩进** 规则；**Java21** `STR.` 模板处理器（预览特性以版本为准）。

---

### 39. `switch` 模式匹配（Pattern Matching for switch）？

**答：** **Java17+** 逐步稳定；**类型模式 + null 处理**；减少 **if-else/instanceof** 链；**穷尽性** 与 **`sealed`** 配合常考。

---

### 40. `record` 能否继承？能否加字段？

**答：** **隐式 final**；**不可继承常规类**（除 `java.lang.Record`）；**状态** 全在 **构造参数**；可加 **静态字段**、**紧凑构造器** 校验。

---

### 41. 场景：`parallelStream` 修改共享 `ArrayList`？

**答：** **`parallelStream`** 使用 **公共 ForkJoinPool**，**多线程** 同时 **`add` 普通 `ArrayList`** → **数据竞争**，结果 **丢元素、`ArrayIndexOutOfBoundsException`**。

**正确做法：** **`collect`** 到 **线程安全容器**（如 **`toConcurrentMap`**），或 **`reduce`/`collect` 合并结果**；或 **不用并行流**，单线程 **`for`**。  
**收束：** **并行流 ≠ 自动线程安全**。

---

### 42. 场景：双重检查锁定单例为何要 `volatile`？

**答：** 无 **`volatile`** 时，**构造实例** 与 **把引用写入静态变量** 可能被 **重排序**，其他线程可能看到 **非空引用但字段未初始化完成** 的 **半初始化对象**。

**`volatile` 写** 建立 **happens-before**，保证 **对象发布前构造完成**（与 **内存模型** 考点绑定）。**枚举单例**、**静态 holder** 可 **避免 DCL 复杂度**。

---

### 43. 场景：`List.of` / `Arrays.asList` 能 `add` 吗？

**答：** **`List.of(...)`** 返回 **不可变列表**，**`add`/`remove` 抛 `UnsupportedOperationException`**。  
**`Arrays.asList(array)`** 返回 **固定大小** 的 **列表视图**：**不能增删**，**`set` 会写回底层数组**；若需要 **独立可变列表**，**`new ArrayList<>(Arrays.asList(...))`**。

**面试陷阱：** **`Arrays.asList` 包装基本类型数组** 时得到 **单元素列表**（整个数组当一个对象），需注意 **重载**。

---

## 九、面经普通题补充（近年）

<a id="sec9-mianjing"></a>

### 44. `ConcurrentHashMap` 的 `get` 要加锁吗？

**答：** **JDK8** 实现下 **`get` 一般无锁**（**volatile 读** tab + **桶首 CAS/普通读**），**与 `put` 并发** 时 **弱一致迭代**；**`size` 可能近似**。面经：**读多写少** 友好，**不要** 误以为 **所有方法都无锁**。

### 45. `String` 不可变有什么好处？

**答：** **可哈希缓存**（`hashCode`）、**常量池复用**、**线程安全**、**安全参数**（如文件路径不被改）。**JDK9+** **byte[] 存储** 优化内存，**语义仍不可变**。

### 46. `==` 与 `equals` 再补一刀（Integer 缓存）？

**答：** **`Integer.valueOf(127)==127`** 可能 **true**（缓存），**大数** 可能 **false**；**应用比较** 用 **`equals`**。**与题 1** 合并复习。

### 47. Stream 是惰性求值吗？

**答：** **中间操作** 惰性，**终止操作** 才 **触发流水线**；因此 **无终止操作** 的 stream **什么也不做**。面经：**peek 调试用**，**不要在 peek 里改外部状态**。

### 48. `synchronized` 锁的是什么？

**答：** **实例方法** 锁 **this**；**静态方法** 锁 **`Class` 对象**；**同步块** 锁 **括号里对象**。**对象头 Mark Word** 与 **锁升级**（偏向→轻量→重量）常被追问。

### 49. SPI 与双亲委派「破坏」？

**答：** **`ServiceLoader`** 常配合 **`Thread.currentThread().getContextClassLoader()`** 加载 **实现类**（父加载器加载的 **接口** + 应用 classpath 的 **实现**）。属 **委派模型的补充**；深问见 **JVM「双亲委派 / `loadClass`」** 专题。

### 50. `ReentrantLock` 公平锁与非公平锁？默认是哪种？

**答：** **默认非公平**（吞吐更好，可减少换线程）。**公平锁** 按 **队列顺序** 获取，避免饥饿，代价是 **更多上下文切换**。实现见 **[ReentrantLock / AQS](#sec5-lock)**。

### 51. 生产环境 `BlockingQueue` 为什么倾向有界？

**答：** **无界队列**（或默认极大容量）会在 **生产快于消费** 时 **堆满任务对象** → **OOM**；**有界 + 拒绝/背压**（如 **CallerRuns**）把压力 **退回上游**。见 **[BlockingQueue](#sec5-queue)**、**[线程池](#sec5-tpe)**。

### 52. `CountDownLatch` 与 `CyclicBarrier` 区别？

**答：** **Latch：一到零放行一批**；**不可重用**。**Barrier：等齐再一起走**；**可循环多轮**；**`BrokenBarrierException`**。见 **[Latch / Semaphore / Barrier](#sec5-aqs-juc)**。

### 53. `Semaphore` 的 `release` 要注意什么？

**答：** **`release` 不必与 `acquire` 同线程**，易 **多释/漏释** 破坏不变量；务必 **配对**、**业务层防错**。共享 **AQS 的 `state`**。

### 54. `volatile` 能保证 `i++` 原子吗？

**答：** **不能**。`i++` 是 **读-改-写**，需 **原子类** 或 **锁**。**`volatile`** 管 **可见/有序**，不管 **复合操作原子性**。见 **[volatile / CAS](#sec5-jmm-atomic)**。

### 55. CAS 的 ABA 怎么破？

**答：** **版本号 / 戳**：如 **`AtomicStampedReference`**、**`AtomicMarkableReference`**；或 **只关心最终一致** 的场景用业务层防误用。

### 56. `LongAdder` 与 `AtomicLong` 何时选谁？

**答：** **高竞争累加** 选 **`LongAdder`**（分段、最后 **`sum`**）；要 **强一致全局 CAS 语义** 或 **简单场景** 用 **`AtomicLong`**。见 **[同节](#sec5-jmm-atomic)**。

### 57. `ReadWriteLock` 能「读锁升写锁」吗？

**答：** **`ReentrantReadWriteLock`：不支持读升写**（会 **死锁风险**）；**可先解读后抢写**。**写锁可降级为读**（在持有写时先取读再释放写），用于 **一写多读发布**。面经：背 **API 能力边界**，别臆测。

### 58. `CompletableFuture` 默认在哪个线程池跑？

**答：** **默认 `ForkJoinPool.commonPool()`**（`supplyAsync`/`runAsync` 无指定 Executor 时）。**IO 密集** 应 **传自定义 Executor**，避免 **占满公共池**（与 **题 35** 一致）。

### 59. AQS 的队列是不是「教科书 CLH」？

**答：** **变体**：**`Node` 双向链表** + **`park`/`unpark`** + 独占/共享/取消；**思想来自 CLH/MCS**，**不是** 原论文自旋实现一字不差。三句：**`state` + FIFO 同步队列 + `park`**。见 **[CLH 小节](#sec5-aqs-clh)**。

### 60. `Condition.await` 要注意什么？

**答：** **必须先持锁**（与监视器 **`wait` 同理）；**`await` 放在 `while` 条件** 防虚假唤醒；**`signal`/`signalAll` 仍在锁内**。

### 61. 为什么不能把大量阻塞 IO 任务丢进 `ForkJoinPool.commonPool()`？

**答：** **工作窃取** 假设任务 **CPU 短**；**阻塞** 会 **占住 worker**，**饿死** 其他任务。**并行流** 默认 **commonPool**，易踩坑；应 **专用线程池** 做 IO。

### 62. `StampedLock` 乐观读怎么用？

**答：** **`tryOptimisticRead` → 读后 `validate`**；失败则 **升级为悲观 `readLock`/`writeLock`**。**stamp 必须配对 `unlock`**；**不可重入**。与 **题 36** 合并。

### 63. 虚拟线程里长时间持 `synchronized` 会怎样？

**答：** 可能 **pinning（钉在载体线程）**，**占用平台线程载体**，**吞吐下降**。**长时间/阻塞临界区** 可换 **`ReentrantLock`** 等（以所用 JDK 文档为准）。

### 64. 结构化并发（`StructuredTaskScope`）相对 `CompletableFuture` 有什么好处？

**答：** **Java 21+** **`StructuredTaskScope`**（或同类 API）：子任务 **同属一作用域**，**任一失败可取消兄弟**、**超时整体退出**，**生命周期清晰**；对比 **CF 链** 易出现 **「泄露的异步」**、**错误与取消需手写传递**。面经：**结构化 = 把 fork 的任务绑在同一控制流里**，与 **虚拟线程** 同属 **Loom** 叙事。

### 65. `ScopedValue` 与 `ThreadLocal` 场景怎么选？

**答：** **`ScopedValue`（JDK 21+）**：**不可变**、**按作用域绑定**（如 **一次请求处理**），**子线程可继承绑定快照**，**无 `remove` 泄漏焦虑**（作用域结束即失效）。**`ThreadLocal`**：**可变**、**线程存续期长** 时易 **泄漏**（尤其 **池化线程**）。**追问：** 上下文传播与 **MDC/追踪 ID** 可对比 **手动包装 Runnable** vs 框架支持。

### 66. `BigDecimal` 用 `equals` 比较 0.1 + 0.2 行吗？

**答：** **判等金额/数值大小** 用 **`compareTo`**。**`equals`** 还比较 **`scale`**，**`new BigDecimal("0.3")` 与 `new BigDecimal("0.30")` 可能 `equals` 为 false**。运算指定 **`scale` + `RoundingMode`**。与 **[场景 E](#sec7-scenes)** 合并。

---

## 十、自测清单

| 域 | 一句话 |
|----|--------|
| 平台 | **javac → class → JVM/JIT**；**JLS vs HotSpot** |
| equals/`==` | **引用/值**；**常量池与 `intern`** |
| hashCode | **与 equals 一致**；**不可变 key** |
| OO | **接口 default/private**；**重载 vs 重写** |
| String | **`StringBuilder`**；**Buffer 线程安全** |
| 序列化 | **`serialVersionUID`、`transient`** |
| 包装 | **Integer 缓存**；**勿 `==` 比 Double** |
| 引用 | **强/软/弱/虚**；**WeakHashMap、PhantomReference** |
| ArrayList | **扩容**、**LinkedList vs Deque** |
| HashMap | **树化 8/64**、**尾插**、**非线程安全** |
| CHM | **JDK8 CAS + 锁桶**、**弱一致迭代** |
| 迭代 | **fail-fast modCount**、**COW** |
| Map 选型 | **LinkedHashMap LRU**、**TreeMap** |
| 异常 | **受检 vs 非受检**、**Error 不抓** |
| 泛型 | **擦除、桥方法、PECS** |
| IO | **BIO/NIO(epoll)/AIO**、**DirectBuffer** |
| 线程池 | **七参数、顺序、拒绝、`shutdown`；忌 `Executors` 无界**；[深挖](#sec5-tpe) |
| 锁 / AQS | **`synchronized` 升级**、[Lock / `Condition`](#sec5-lock)、[CLH](#sec5-aqs-clh)、[JUC 工具](#sec5-aqs-juc)、[RRW / Stamped](#sec5-rw) |
| JMM / 原子 | **HB 规则**、[volatile/CAS/ABA/LongAdder/`VarHandle`](#sec5-jmm-atomic) |
| 队列 / COW | **[BlockingQueue + COW List](#sec5-queue)** |
| ThreadLocal | **弱 key 强 value**、**remove** |
| 中断 | **`InterruptedException` 恢复标志** |
| 新特性 | **Stream 惰性**、**record/sealed**、**虚拟线程 pinning**、**StructuredTaskScope / ScopedValue（21+）** |
| LTS | **21 / 25 口径 + OpenJDK** |
| 场景 | **LongAdder**、**无界队列 OOM**、**DateTimeFormatter**、[近年场景 A～H](#sec7-scenes) |
| 进阶 | **DCL volatile**、**CompletableFuture 自定义池**、**并行流** |
| 面经 | **题 44～66**（[九](#sec9-mianjing)） |

---

*路径：`interview/java-basics/java-basics-interview.md`（含 **九、面经 44～66**、**`sec7-scenes` 场景补充**、**sec-\* 并发锚点**）*
