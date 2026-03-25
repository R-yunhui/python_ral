# Java 基础高频面试题（语法 · 集合 · 并发 · 新特性）

> 面向 **JDK 8～21** 常见考点；**API 细节以当前 JDK 文档为准**。含**场景题**与自测表。

---

## 目录

1. [语言基础与面向对象](#一语言基础与面向对象)
2. [集合框架](#二集合框架)
3. [异常与泛型](#三异常与泛型)
4. [IO / NIO](#四io--nio)
5. [并发基础](#五并发基础)
6. [Java 8～21 新特性速记](#六java-821-新特性速记)
7. [场景题](#七场景题)
8. [进阶补充](#八进阶补充)
9. [自测清单](#九自测清单)

---

## 一、语言基础与面向对象

### 1. `==` 与 `equals` 区别？String 比较注意什么？

**答：** **`==`** 基本类型比 **值**，引用类型比 **地址**。**`equals`** 默认同 `==`，**String** 等重写为 **内容相等**。**常量池** 与 **`new String`** 导致 `==` 结果不同是高频考点。

---

### 2. `hashCode` 与 `equals` 约定？

**答：** **相等对象必须有相同 `hashCode`**；**重写 `equals` 必须重写 `hashCode`**。用于 **HashMap/HashSet** 桶定位与去重。

---

### 3. 抽象类与接口区别？Java 8+ 之后呢？

**答：** **单继承多实现**；接口 **Java8 `default/static`**、**Java9 `private` 方法**；**函数式接口**（单抽象方法）支撑 **Lambda**。抽象类可有 **状态**，接口多 **契约**。

---

### 4. `final` 修饰类、方法、变量？

**答：** **类**不可继承；**方法**不可重写；**变量**引用不可变（对象内容可变若类型允许）。

---

### 5. 字符串拼接 `+` 与 `StringBuilder`？

**答：** **编译期常量** 可能折叠；**循环中 `+`** 常编译为 **StringBuilder**（或应手写 **StringBuilder** 避免多次创建）。**JDK9+** `String` 内部实现有调整，**面试答思路**。

---

### 6. 序列化 `serialVersionUID` 有什么用？

**答：** **版本兼容**；不显式声明可能因字段变化导致 **InvalidClassException**。

---

## 二、集合框架

### 7. `ArrayList` 与 `LinkedList`？

**答：** **ArrayList** 动态数组，**随机访问 O(1)**，尾部扩容；**LinkedList** 双向链表，**头尾插入** 友好，**随机访问慢**。**内存局部性** 常使 ArrayList 更常用。

---

### 8. `HashMap` 底层？JDK8 链表过长怎么办？

**答：** **数组 + 链表**；**JDK8+** 链表过长 **转红黑树**（与容量、哈希分布有关）。**扩容** **2 倍**、**rehash**。

---

### 9. `HashMap` 线程安全吗？`ConcurrentHashMap` 呢？

**答：** **HashMap** 非线程安全；**JDK7 CHM 分段锁**，**JDK8+ CAS + synchronized 桶头**（实现细节以源码为准）。**`Collections.synchronizedMap`** 与 **Hashtable** 性能/语义不同。

---

### 10. `HashMap` 的 `key` 为什么常建议不可变对象？

**答：** **`hashCode/equals` 若参与后变更**，定位错乱，**找不到或重复**。**String、Integer** 常用作 key。

---

### 11. `fail-fast` 与 `fail-safe`？

**答：** **迭代时结构修改** 抛 **ConcurrentModificationException**（**fail-fast**）；**CopyOnWriteArrayList** 等 **迭代副本**（**fail-safe**，弱一致）。

---

## 三、异常与泛型

### 12. `Error` 与 `Exception`？受检与非受检？

**答：** **`Error`** 严重系统问题；**`Exception`** 分 **RuntimeException（非受检）** 与 **受检异常**（需声明/捕获）。**业务异常设计** 常考。

---

### 13. 泛型擦除是什么？带来什么问题？

**答：** **编译期** 泛型信息擦为 **原始类型** + **桥方法**；**运行时** `List<String>` 与 `List<Integer>` **同一 Class**。**反射**、**instanceof**、**数组** 有坑。

---

## 四、IO / NIO

### 14. BIO、NIO、AIO 区别？（口头）

**答：** **BIO** 一连接一线程阻塞；**NIO** **多路复用**（`Selector`）非阻塞；**AIO** **异步回调**（Linux 上实际使用与实现有关）。**Netty** 常基于 **NIO/epoll**。

---

### 15. `try-with-resources` 要求？

**答：** 实现 **`AutoCloseable`**；**编译器生成 close**，**抑制异常** 有 **addSuppressed**。

---

## 五、并发基础

### 16. 创建线程几种方式？`start` 与 `run`？

**答：** **Thread**、**Runnable**、**Callable+Future**、**线程池**。**`start`** 新线程执行；**`run`** 普通方法调用。

---

### 17. 线程池参数？`ThreadPoolExecutor` 拒绝策略？

**答：** **corePoolSize、maximumPoolSize、keepAlive、queue、threadFactory、handler**。**Abort/CallerRuns/Discard/OldestDiscard**。**队列选型**（有界 vs 无界）与 **OOM** 场景常考。

---

### 18. `synchronized` 与 `ReentrantLock`？

**答：** **JVM 关键字** vs **API**；**Lock** 可 **尝试锁、超时、可中断**；**公平锁**；**需手动 unlock**（`finally`）。

---

### 19. `ThreadLocal` 内存泄漏？

**答：** **Entry 弱引用 key、强引用 value**；**线程池** 线程复用时 **未 remove** 可能 **泄漏**；**用完 remove**。

---

## 六、Java 8～21 新特性速记

### 20. Java 8：Lambda、Stream、`Optional`？

**答：** **函数式接口** + **Lambda**；**Stream** 惰性、**中间/终端**操作；**`Optional`** 避免裸 **null**（不滥用）。

---

### 21. Java 9～11 常考点？

**答：** **模块系统 JPMS**（`module-info.java`）；**`var` 局部类型推断**（10）；**HTTP Client**（11）；**单文件源码运行**（11）；**String API** 增强等。

---

### 22. Java 17 LTS：密封类、`record`、模式匹配？

**答：** **`sealed`** 限制继承；**`record`** 不可变数据载体（自动生成 **equals/hashCode/toString**）；**`switch` 模式匹配** 逐步增强。

---

### 23. Java 21 LTS：虚拟线程（Virtual Threads）？

**答：** **轻量级线程**，**海量阻塞 IO** 场景减少 **平台线程** 消耗；**不要与 CPU 密集** 混用错误预期；**同步原语** 与 **载体线程** 调度关系是面试延伸点。

---

### 24. `record` 与 Lombok `@Data` 区别（口头）？

**答：** **`record`** 语言级、语义固定（不可继承常规类）；**Lombok** 编译期生成代码，需依赖插件。

---

## 七、场景题

### 25. 场景：高并发计数用 `volatile long` 行吗？

**答：** **`i++` 非原子**；用 **`AtomicLong`**、**LongAdder**（高竞争更优）或 **`synchronized`**。

---

### 26. 场景：`HashMap` 多线程 `put` 死循环（JDK7）？

**答：** **JDK7 并发扩容** 可能 **环形链表**；**JDK8+ 修复**，但仍 **数据错乱**，应 **ConcurrentHashMap**。

---

### 27. 场景：线程池用 `Executors.newFixedThreadPool` 有什么问题？

**答：** **无界队列 `LinkedBlockingQueue`**，任务堆积可能导致 **内存暴涨**；生产常用 **有界队列 + 明确拒绝策略 + 自定义 `ThreadPoolExecutor`**。

---

### 28. 场景：`SimpleDateFormat` 并发问题？

**答：** **非线程安全**；用 **`ThreadLocal`**、**`DateTimeFormatter`（Java8）** 或 **每次 new**。

---

### 29. 场景：大列表去重统计？

**答：** **`Stream.distinct`**、**`HashSet`**；**超大数据** 考虑 **布隆过滤器**、**外部排序**、**分布式**（超出基础题可延伸）。

---

### 30. 场景：接口要兼容老客户端，新增字段？

**答：** **JSON** 忽略未知字段、**`default`** 方法、**版本号**；**序列化** 向前兼容设计。

---

### 31. 场景：虚拟线程适合什么业务？

**答：** **大量阻塞等待**（RPC、DB、HTTP）；**不适合** 把 **CPU 密集** 任务无限放大在少量核心上期待线性提速（需 **并行流/结构** 另行设计）。

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

**答：** **非线程安全**，可能 **丢数据/异常**；用 **`collect(Collectors.toConcurrentMap`)** 或 **`reduce` 合并** 等 **线程安全** 归约。

---

### 42. 场景：双重检查锁定单例为何要 `volatile`？

**答：** **指令重排序** 可能导致 **未初始化对象** 被引用；**`volatile`** 禁止 **实例构造** 与 **引用赋值** 重排（**happens-before**）。

---

### 43. 场景：`List.of` / `Arrays.asList` 能 `add` 吗？

**答：** **`List.of`** **不可变**；**`Arrays.asList`** **固定大小** 视图，**增删** 抛异常或 **意外修改原数组**；需 **`new ArrayList<>(...)`**。

---

## 九、自测清单

| 考点 | 一句话 |
|------|--------|
| equals/hashCode | **一致**、**HashMap key** |
| 集合 | **HashMap 树化**、**CHM 并发** |
| 并发 | **线程池 7 参**、**拒绝策略** |
| ThreadLocal | **线程池 + remove** |
| 新特性 | **record**、**sealed**、**虚拟线程** |
| 场景 | **LongAdder**、**线程池无界队列**、**SimpleDateFormat** |
| 进阶 | **DCL+volatile**、**CompletableFuture 线程池**、**并行流线程安全** |

---

*路径：`interview/java-basics/java-basics-interview.md`*
