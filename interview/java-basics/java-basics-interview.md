# Java 基础高频面试题（语法 · 集合 · 并发 · 新特性）

> 面向 **JDK 8～25** 常见考点（**21 / 25** 均为 **LTS**；**预览特性与 API 以所用 JDK 与项目为准**）。含**分层答法**、**（基础补充）**、**场景题**、**面经补充**与 **自测表**。与 **JVM**、**Spring** 文档可交叉复习。

---

## 目录

1. [语言基础与面向对象](#一语言基础与面向对象)
2. [集合框架](#二集合框架)
3. [异常与泛型](#三异常与泛型)
4. [IO / NIO](#四io--nio)
5. [并发基础](#五并发基础)
6. [Java 8～25 新特性速记](#六java-825-新特性速记)
7. [场景题](#七场景题)
8. [进阶补充](#八进阶补充)
9. [面经普通题补充](#九面经普通题补充)
10. [自测清单](#十自测清单)

> **复习主线：** **`==/equals` → 集合（HashMap 树化/CHM）→ 线程池七参数 → `volatile` 与原子类 → Stream/Optional → 虚拟线程与 record**。**官文：** <https://docs.oracle.com/en/java/> 、 <https://openjdk.org/>

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

## 二、集合框架

### 7. `ArrayList` 与 `LinkedList`？

**答：** **ArrayList**：**动态数组**，扩容 **约 1.5 倍**（以 JDK 源码为准），**随机访问 O(1)**，尾部插入 **均摊 O(1)**，**中间插入** 搬移 **O(n)**。**LinkedList**：**双向链表**，头尾 **O(1)**，按索引 **O(n)**。**CPU 缓存**：数组 **局部性好**，多数业务 **默认 ArrayList**；**LinkedList** 适合 **双端队列**、频繁头尾删插（亦可选 **`ArrayDeque`** 对比）。

---

### 8. `HashMap` 底层？JDK8 链表过长怎么办？

**答：** **数组 + 链表/红黑树**。**hash 扰动后取桶**；冲突挂链。**树化**：链表长 **≥ 8** 且 **容量 ≥ 64** 转 **红黑树**；**元素过少（≤ 6）** 可 **退链**。**负载因子 0.75**、容量 **2 的幂**。**JDK7 并发扩容头插成环** → **`get` 死循环**；**JDK8 尾插** 缓解但 **仍非线程安全**。**`put` 主线**：**hash & (n-1)** 定位桶 → **空则新建节点** → **否则链表/树里找 key**（有则覆盖 value）→ **尾插 + 计数** → **超阈值则树化或扩容**（**CHM 才大量用 CAS**，勿混）。

---

### 9. `HashMap` 线程安全吗？`ConcurrentHashMap` 呢？

**答：** **`HashMap`**：**否**。**`ConcurrentHashMap`**：**JDK7 `Segment` 分段**；**JDK8+** **`Node` 数组 + CAS + synchronized（必要时锁首节点）`**，**读路径多无锁 volatile**。**`Collections.synchronizedMap`**：**互斥锁包一层**。**`Hashtable`**：过时。**详见题 44**（`get` 是否加锁）。

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

---

### 18. `synchronized` 与 `ReentrantLock`？

**答：** **`synchronized`**：JVM **监视器**，**自动释放**；**锁升级** 路径由 JVM 实现。**`ReentrantLock`**：**可中断、超时、`tryLock`、公平/非公平**、**Condition**；**须在 `finally unlock`**。**性能**：竞争不激烈时接近；**高阶并发结构**（读写锁、信号量）基于 **AQS**。

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

**答：** **`Thread.ofVirtual().start(...)` / `Executors.newVirtualThreadPerTaskExecutor()`**：**海量任务** 映射到 **少量载体平台线程**；**阻塞**（IO、`park`）时 **卸載**，**别在 synchronized 里长时间阻塞**（**pinning**）削弱收益 → **用 `ReentrantLock`** 等。**CPU 密集** 仍靠 **并行度控制 + 算法**。

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
**面试收束：** **volatile ≠ 原子计数**。

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

---

### 36. `StampedLock` 适用场景？

**答：** **读多写少** 优化 **读写锁**；**乐观读** `tryOptimisticRead` 后 **validate**；**不** 可重入、**使用复杂**，用错易挂。

---

### 37. `Stream` 并行流 `parallelStream()` 注意？

**答：** **ForkJoinPool**；**线程安全** 的 **reduce/收集器**；**错误** 用并行处理 **IO 阻塞**；**顺序** 与 **性能** 需实测。

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
| ArrayList | **扩容**、**LinkedList vs Deque** |
| HashMap | **树化 8/64**、**尾插**、**非线程安全** |
| CHM | **JDK8 CAS + 锁桶**、**弱一致迭代** |
| 迭代 | **fail-fast modCount**、**COW** |
| Map 选型 | **LinkedHashMap LRU**、**TreeMap** |
| 异常 | **受检 vs 非受检**、**Error 不抓** |
| 泛型 | **擦除、桥方法、PECS** |
| IO | **BIO/NIO(epoll)/AIO**、**DirectBuffer** |
| 线程池 | **七参数、拒绝策略、有界队列** |
| 锁 | **`synchronized` vs ReentrantLock** |
| ThreadLocal | **弱 key 强 value**、**remove** |
| 中断 | **`InterruptedException` 恢复标志** |
| 新特性 | **Stream 惰性**、**record/sealed**、**虚拟线程 pinning** |
| LTS | **21 / 25 口径 + OpenJDK** |
| 场景 | **LongAdder**、**无界队列 OOM**、**DateTimeFormatter** |
| 进阶 | **DCL volatile**、**CompletableFuture 自定义池**、**并行流** |
| 面经 | **题 44～49** |

---

*路径：`interview/java-basics/java-basics-interview.md`（含 **九、面经普通题补充**）*
