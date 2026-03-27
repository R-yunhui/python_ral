# Java 基础高频面试题（语法 · 集合 · 并发 · 新特性）

> 面向 **JDK 8～21** 常见考点；**API 细节以当前 JDK 文档为准**。含**场景题**、**面经普通题补充**与自测表。

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
9. [面经普通题补充](#九面经普通题补充)
10. [自测清单](#十自测清单)

---

## 一、语言基础与面向对象

### 1. `==` 与 `equals` 区别？String 比较注意什么？

**答：** **`==`**：基本类型比较 **数值**；引用类型比较 **引用地址是否同一对象**。**`equals`**：Object 默认 **等价于 `==`**；**String、Integer** 等重写为 **值相等** 语义。  
**String：** **字面量** 可能进 **常量池** 使 `==` 为 true；**`new String("a")`** 与字面量 **通常 `==` false**、**`equals` true**。业务比较 **统一用 `equals`**，注意 **NPE** 时用 **`Objects.equals`**。

---

### 2. `hashCode` 与 `equals` 约定？

**答：** **约定：** **`equals` 相等 → `hashCode` 必须相同**；**`hashCode` 相同不要求 `equals` 相等**（哈希冲突）。**重写 `equals` 必须重写 `hashCode`**，否则 **HashMap/HashSet** 行为错误。  
**实现：** 常用 **31 多项式** 组合字段；**可变对象** 作 key 会导致 **插入后修改字段 → 找不到**，故 **key 宜不可变**（与 **题 10** 呼应）。

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

**答：** **数组（桶）+ 链表** 解决冲突；**JDK8+** 当 **链表长度超过阈值**（默认 8）且 **桶数达到最小树化容量** 时 **链表 → 红黑树**，将 **最坏查找** 从 O(n) 降到 **O(log n)**。**扩容** 时 **容量翻倍**，**重新分布**（rehash）。  
**负载因子** 默认 0.75，**空间与时间** 折中。面经：**并发不要用 HashMap**。

---

### 9. `HashMap` 线程安全吗？`ConcurrentHashMap` 呢？

**答：** **`HashMap`** **非线程安全**，多线程 **扩容死循环（JDK7）**、**数据错乱（JDK8+）**。**`ConcurrentHashMap`**：**JDK7** **分段锁**；**JDK8+** **CAS + synchronized（锁桶头）**，**读多写少** 性能较好。**`Collections.synchronizedMap`** 全局锁、**Hashtable** 老旧，**少用**。详见 **题 44**。

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

**答：** **ServiceLoader** 用 **线程上下文类加载器** 加载 **实现类**，解决 **父加载器** 无法加载 **子 classpath** 的问题；属 **委派模型灵活应用**，面经常和 **题 34 `loadClass`** 一起出现。

---

## 十、自测清单

| 考点 | 一句话 |
|------|--------|
| equals/hashCode | **一致**、**HashMap key** |
| 集合 | **HashMap 树化**、**CHM 并发** |
| 并发 | **线程池 7 参**、**拒绝策略** |
| ThreadLocal | **线程池 + remove** |
| 新特性 | **record**、**sealed**、**虚拟线程** |
| 场景 | **LongAdder**、**线程池无界队列**、**SimpleDateFormat** |
| 进阶 | **DCL+volatile**、**CompletableFuture 线程池**、**并行流线程安全** |
| 面经补充 | **CHM get**、**String 不可变**、**Integer 缓存**、**Stream 惰性**、**synchronized 锁对象**、**SPI**（**题 44～49**） |

---

*路径：`interview/java-basics/java-basics-interview.md`（含 **九、面经普通题补充**）*
