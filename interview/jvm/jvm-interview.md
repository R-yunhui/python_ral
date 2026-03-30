# JVM 高频面试题（HotSpot + 近年考点）

> 面向 **JDK 8+～25 LTS**（**具体收集器与默认值以版本为准**）。含**分层答法**、**（基础补充）**、**场景题**、**面经补充**与 **自测表**。与 **Java 基础**、**并发** 文档对照复习。

---

## 目录

1. [运行时数据区与对象](#一运行时数据区与对象)
2. [垃圾回收](#二垃圾回收)
3. [类加载与字节码](#三类加载与字节码)
4. [JIT 编译与性能](#四jit-编译与性能)
5. [内存模型与并发（JMM）](#五内存模型与并发jmm)
6. [监控、诊断与参数](#六监控诊断与参数)
7. [场景题](#七场景题)
8. [进阶补充](#八进阶补充)
9. [面经普通题补充](#九面经普通题补充)
10. [高频补充（GC 细节·收集器·版本演进）](#十高频补充gc-细节收集器版本演进)
11. [自测清单](#十一自测清单)

> **复习主线：** **数据区（栈/堆/元空间）→ 对象头与指针压缩 → 分代与 GC Roots → 收集器（G1/ZGC）→ 类加载双亲委派 → JMM happens-before → 调参（堆/元空间/日志）**。文档：<https://docs.oracle.com/en/java/> ；GC：[Garbage Collection Tuning Guide](https://docs.oracle.com/en/java/javase/21/gctuning/)。

---

## 一、运行时数据区与对象

### JVM 与 HotSpot 是什么？（开胃）

**答：** **JVM** 是 **运行字节码的抽象机器**（**JVMS**）；**HotSpot** 是 Oracle/OpenJDK 的 **参考实现**，含 **C1/C2 JIT**、**GC**、**压缩指针** 等。**面试**：区分 **规范行为**、**JVM 实现默认**、**项目显式 `-XX` 参数**。

---

### 1. JVM 内存区域怎么划分？线程私有与共享各是什么？

**答：**

| 区域 | 线程 | 内容 |
|------|------|------|
| **程序计数器** | 私有 | 当前 **字节码指令地址**（Native 方法可能未定义值） |
| **虚拟机栈** | 私有 | **栈帧**：局部变量表、操作数栈、动态链接、返回地址 |
| **本地方法栈** | 私有 | **JNI Native** 栈 |
| **堆** | 共享 | **对象实例、数组**（**GC 主战场**） |
| **元空间** | 共享 | **类元数据**（**JDK8+ 本地内存**，替代 PermGen） |
| **直接内存** | 共享 | **NIO、`DirectByteBuffer`**，受 **`MaxDirectMemorySize`** |

**口诀：** **一计数两栈堆外元**；**栈帧 OutOfMemoryError**（极少见）与 **StackOverflowError** 区分。

**注意：** **局部变量槽** 里是 **引用或基本类型**；**对象实例在堆**（除非 **逃逸分析** 优化掉可感知分配）。

---

### 2. 对象在堆里如何布局？（Mark Word、指针压缩）

**答：** **64 位 HotSpot**（布局以实现为准）：**对象头** = **Mark Word**（**哈希、分代年龄、锁标记/偏向线程 ID** 等 **复用同一域**）+ **Klass 指针**（指向类元数据）；**数组** 另有 **长度字**。**压缩指针 `-XX:+UseCompressedOops`**：引用 **32 位**，**对象对齐 8 字节**，省堆；**超过 ~32GB 堆** 等场景可能 **关闭**。**追问：** **指针与对象实际地址** 的映射由 JVM 管理。

---

### 3. 栈上分配、标量替换是什么？

**答：** **逃逸分析** 若判断对象未逃逸出方法，可能 **栈上分配** 或拆成标量 **标量替换**，减少堆分配与 GC 压力。**是否发生依赖 JIT 与逃逸分析结果**，不能当语言保证。

---

### 4. OOM 常见有哪几种？分别什么原因？

**答（高频）：**

| 类型 | 典型原因 |
|------|----------|
| **Java heap space** | 堆对象过多、泄漏、`-Xmx` 过小 |
| **Metaspace** | 类/类加载器过多、动态生成类未回收 |
| **Direct buffer memory** | 直接内存泄漏或未限制 |
| **unable to create new native thread** | 线程数过多、栈或系统限制 |
| **GC overhead limit exceeded**（若开启） | GC 时间占比过高（多为堆太小或分配过快） |
| **StackOverflowError** | **栈帧过深**（递归无出口、极深调用链）、**`-Xss` 过小** |

**追问：** **`Requested array size exceeds VM limit`** 等为较少见边界；**`OutOfMemoryError: Metaspace`** 与 **类加载器** 强相关（见场景 **题 28**）。

---

### 5. `String.intern()` 在 JDK6 与 JDK7+ 区别常被问什么？

**答：** **JDK6**：`intern` 的字符串在 **永久代**。**JDK7+**：字符串常量池在 **堆**，与 **GC、内存** 行为不同；滥用 `intern` 仍可能导致 **堆压力** 或 **去重开销**。

---

### （基础补充）堆内分代（经典 HotSpot）？

**答：** **新生代**：**Eden + Survivor（S0/S1）**；**Minor GC** 复制存活对象 **Survivor 间往返**，**年龄++**，超阈值进 **老年代**。**老年代**：**长寿命对象**、**大对象**（可能直接进老年代，依策略）。**Metaspace**：**类元数据**，**满** 触发 **Full GC 元数据回收**。**G1/ZGC** 用 **Region/分区** 心智，但 **「年轻/老」逻辑** 仍便于口述。

---

## 二、垃圾回收

### 6. 如何判断对象已死？可达性分析里哪些可作为 GC Roots？

**答：** HotSpot 主要用 **可达性分析**（从根集合出发做图遍历，与根无关的对象可回收；**非**引用计数，不处理循环引用靠 RC）。**GC Roots** 是实现定义的根集合入口，常见类别与**举例**如下（口述能覆盖 4～5 类即可）：

| 根类型 | 含义 | 例子（口述） |
|--------|------|----------------|
| **栈上引用** | 线程栈帧局部变量、参数里的引用 | `main` 里 `Object o = new Object()`，`o` 指向的对象从栈可达 |
| **静态字段** | 已加载类的 `static` 引用 | `Holder.staticCache = new HashMap<>()`，`cache` 指向的 Map |
| **运行时常量** | 常量池解析出的引用（如字符串相关） | 字面量、`String.intern()` 进入池后的引用（JDK7+ 池在堆） |
| **JNI 引用** | Native 全局/局部强引用 | `NewGlobalRef` 未 `DeleteGlobalRef` 的 Java 对象 |
| **同步监视器** | 正在执行且已持有 `synchronized(obj)` 的锁对象 | `synchronized(lock) { ... }` 执行期间 `lock` |
| **活动线程等 JVM 内部** | 线程对象、部分 ClassLoader/Class、内部数据结构 | 存活 `Thread`、bootstrap 加载的核心类 |
| **JVMTI 等** | 调试/Agent 固定引用 | 实现相关，面经提一句即可 |

**追问：** **Remembered Set / 卡表** 不是 GC Root，是 **加速跨代扫描** 的辅助结构。

---

### 7. 分代收集为什么有效？Minor GC / Major GC / Full GC 口头怎么区分？

**答：** **弱分代假设**：大多对象朝生夕死；老年代对象存活久。  
**口头区分**（非严格规范）：**Young GC** 清理新生代；**Old GC** 清理老年代；**Full GC** 常指 **整堆 + 元空间** 等一次较大停顿的收集（具体与收集器有关）。

---

### 8. CMS、G1、ZGC、Shenandoah 各自特点？（近年高频）

**答（简表）：**

| 收集器 | 特点 |
|--------|------|
| **CMS** | 老年代并发标记清除；**碎片**、**浮动垃圾**；JDK9 标记 deprecated，**14 移除** |
| **G1** | 分区 Region、**可预期停顿**、Mixed GC；**JDK9+ 服务端默认** 常见 |
| **ZGC** | **超低延迟**目标、染色指针、并发整理；**JDK15+** 逐步生产可用；高版本有 **分代 ZGC** 等演进（**以当前 JDK Release Notes 为准**） |
| **Shenandoah** | 并发压缩、低停顿；**OpenJDK** 特性，与发行版是否包含有关；**JDK 25** 等版本继续迭代 **分代 Shenandoah** |
| **Parallel（Throughput）** | 多线程 **STW** 回收，**吞吐优先**；小内存或批处理常见 |
| **Serial** | **单线程** STW，客户端或极小堆、低端设备 |
| **Epsilon** | **No-Op GC**（几乎不回收），**压测分配性能/短命任务** 或 **明确知晓无泄漏** 的场景 |

面试答：**选型看延迟/吞吐/堆大小/版本**，并提 **STW** 与 **并发阶段**；**JDK 21 起** 服务端默认常见仍为 **G1**，**ZGC/Shenandoah** 多用于 **延迟敏感 / 大堆** 且 **验证过** 的环境。

---

### 9. G1 的 Mixed GC、Remembered Set、SATB 常被问什么？

**答：**

- **RSet**：记录 **谁引用了本 Region**，避免全堆扫描 **跨区引用**。  
- **Mixed GC**：不仅 Young，还回收部分 **老年代 Region**（回收价值、停顿目标）。  
- **SATB**：并发标记阶段 **快照**，处理并发修改带来的 **漏标** 问题（与写屏障配合）。

**（高频补充）IHOP、Humongous：**  
**IHOP**（Initiating Heap Occupancy Percent，如默认约 **45%**，且可**自适应**）表示当 **非年轻代占用** 达到阈值时触发 **并发标记**，为后续 **Mixed GC** 做准备（不是「堆总占用 45%」的朴素理解，以官方 GC 文档为准）。**Humongous 对象**：大小超过 Region 一半的对象占 **连续 Humongous Region**，常 **直接进老年代区**，大量短寿命大对象可能干扰 IHOP 与并发标记节奏；**JDK 11+** 等对 IHOP 与 Humongous 回收有持续修补，线上问题需 **对照具体小版本 Release Notes**。

**（面经）`MaxGCPauseMillis`：** 目标而非硬保证；过小可能导致 **回收更频繁、吞吐下降**，需压测权衡。

---

### 10. `finalize()` 为什么不再推荐使用？

**答：** 不确定性大、执行顺序与线程模型复杂、影响 GC；**`Cleaner`、try-with-resources** 等更可控。**Java 9+** 已 **deprecated**，后续版本移除方向。

---

### 11. 安全点、安全区域是什么？

**答：** GC 等需 **停顿线程** 的操作不能在任意指令点发生，需在 **安全点**（如方法调用、循环回边等）；线程阻塞在 **安全区域** 内可视为安全，避免长时间不进入安全点。

---

### （基础补充）并发标记「三色标记」与漏标？

**答：** **黑**：已完成扫描且子引用已处理。**灰**：已扫描自身，**子引用未扫完**。**白**：未访问。**并发标记** 时 **用户线程改引用** 可能 **漏标存活对象** → **误回收**。**缓解**：**写屏障** + **SATB（G1）** 或 **增量更新** 等，把变动 **记进集合** 或 **保守处理**。**面试：** 能说出 **「并发 = 要处理浮动垃圾/漏标」** 即可深化。

---

## 三、类加载与字节码

### 12. 类加载过程大致几步？

**答：** **加载**（得 Class）→ **验证** → **准备**（静态变量零值）→ **解析**（符号引用转直接）→ **初始化**（`<clinit>`）。**使用**、**卸载**（条件苛刻）。

---

### 13. 双亲委派模型是什么？为什么要破坏？（SPI 场景）

**答：** **`ClassLoader.loadClass` 默认**：**先父后子**；父 **Bootstrap**（`JAVA_HOME/lib`）、**Extension/Platform**、**Application**。**好处**：**`java.lang` 等核心类** 只能由 **Bootstrap** 定义，**防伪造**。**破坏/跳过**：**SPI**（接口在 **Bootstrap**，实现在 **应用路径**）→ **`Thread.getContextClassLoader()`**；**OSGi、Tomcat 多 WebApp** **隔离** 依赖。**`Class.forName`** 与 **`loadClass`** **是否触发初始化** 区别见 **进阶题 34**。

---

### 14. 哪些情况会触发初始化？

**答：** **new**、**反射**、**子类触发父类**、**主类**、**静态方法/字段** 首次访问等（**被动引用**不触发子类初始化等细节常考）。

---

## 四、JIT 编译与性能

### 15. 解释执行、C1、C2 是什么关系？

**答：** 热点代码经 **JIT** 编译成本地码。**分层编译**：**C1** 较快、优化少；**C2** 激进优化。**阈值**与 **热点计数** 由 `-XX:CompileThreshold` 等控制（版本差异大，答思路即可）。

---

### 16. 逃逸分析、内联、锁消除、标量替换与 JIT 的关系？

**答：** 均为 **JIT 优化**：**内联** 减少调用开销；**逃逸分析** 支撑 **锁消除/栈上分配/标量替换**；**需达到编译热点** 才可能触发。

---

## 五、内存模型与并发（JMM）

### 17. `volatile` 语义？

**答：** **可见性**：写刷到主内存，读从主内存取。**有序性**：**禁止特定重排序**（happens-before）。**不保证原子性**（`i++` 仍需原子类或锁）。

---

### 18. happens-before 规则列举几条？

**答：** **单线程** 顺序；**volatile** 写→读；**锁** 解锁→后续加锁；**线程 start/join**；**传递性** 等。用于判断 **可见性** 与 **禁止重排序** 边界。

---

### 19. `synchronized` 底层与锁升级（偏向→轻量→重量）？

**答：** **monitor** 与 **对象头 Mark Word**；历史上 JDK6+ **偏向锁**（无竞争同线程）、**轻量级锁**（CAS 自旋）、**重量级锁**（操作系统 mutex）。**版本演进（面试常追问）：** **JEP 374**，**JDK15** 起 **默认禁用偏向锁**（仍可用 `-XX:+UseBiasedLocking` 临时开启）；**JDK18 起偏向锁被移除**，不再有「偏向→撤销」路径，口述时应**按当前 JDK** 说明。**无锁/轻量/重量** 与 **竞争程度、自旋、膨胀** 仍常考；**具体路径以版本与竞争为准**。

---

### 20. `java.util.concurrent` 里 `AQS` 是什么？

**答：** **AbstractQueuedSynchronizer**，**CLH 变体队列** + **state**，支撑 **ReentrantLock、Semaphore、CountDownLatch** 等；面试常问 **公平/非公平**、**可重入**。

---

## 六、监控、诊断与参数

### 21. 常用诊断工具？

**答：** **`jcmd`**、**`jstack`**（线程）、**`jmap`**（堆 dump，生产慎用）、**`jstat`**（GC 统计）、**`jhsdb`**、**Arthas**、**async-profiler**、**MAT** / **JProfiler** 分析 dump。

---

### 22. 如何看 GC 日志？（JDK9+ unified logging）

**答：** **`-Xlog:gc*`**（unified logging）；关注 **pause**、**heap before/after**、**promotion**、**Full GC 原因**。老参数与 **G1/ZGC** 日志格式不同，**以当前 JDK 文档为准**。

---

### 23. 常用堆栈参数（概念题）

**答：** **`-Xms/-Xmx`**、**`-Xss`**、**`-XX:MetaspaceSize/MaxMetaspaceSize`**、**G1**：**`-XX:MaxGCPauseMillis`**、**`-XX:+UseG1GC`** 等；**具体默认值随版本变**。

---

## 七、场景题

### 24. 场景：线上 Full GC 频繁，如何排查？

**答：** **Full GC 频繁** 往往伴随 **长停顿** 与 **吞吐下降**，排查要 **日志 + 指标 + 堆分析** 三线并行。

**（1）先拿证据**  
开启或收集 **GC 日志**（JDK9+ **统一日志** `Xlog:gc*`），看 **Full GC 触发原因**（**Metadata GC Threshold**、**Allocation Failure**、**System.gc**、**CMS / G1 的 concurrent mode failure** 等）、**停顿时间**、**堆前后占用**。配合 **Prometheus + Grafana** 或云平台 **JVM 指标**。

**（2）堆与泄漏**  
**堆 dump**（`jcmd PID GC.heap_dump`、OOM 时 **HeapDumpOnOutOfMemoryError**）用 **MAT、JProfiler** 看 **Dominators**：是否 **大集合只增不减**、**缓存无上限**、**静态 Map 持有请求对象**。**老年代涨满** 要区分 **内存泄漏** vs **堆太小**。

**（3）非堆**  
**Metaspace** 满 → **类加载泄漏**（见 **题 28**）；**Direct Memory** → **题 25**。**`-Xmx` 过小** 导致 **频繁 Full GC**，需 **压测调堆**。

**（4）代码侧典型坑**  
**无界队列缓存**、**ThreadLocal 未 remove（线程池场景）**、**未关闭流/连接**、**动态字节码** 生成过多类。

**（5）调优方向**  
**增大堆**（在确认不是泄漏后）、换 **G1/ZGC**、**减少 Full GC 触发**（如 **`-XX:InitiatingHeapOccupancyPercent`** 仅对部分收集器）；**根本** 常是 **代码与容量** 而非 **魔参**。

---

### 25. 场景：`DirectByteBuffer` OOM，堆却不大？

**答：** 直接内存 **不在 Java 堆**，受 **`MaxDirectMemorySize`**（或默认与堆相关）与 **显式释放**（Cleaner）影响；**未释放** 或 **分配过快** 会 **Direct buffer memory OOM**。

---

### 26. 场景：接口 RT 毛刺，CPU 不高，怀疑 JVM？

**答：** **CPU 不高** 但 **延迟尖刺**，常见是 **STW**、**锁等待**、**IO 与 JVM 无关**，不要先怪业务算法。

**（1）GC**  
**Young GC / Mixed GC** 的 **停顿** 落在请求时间线上：**JFR**、**GC log** 与 **APM  trace** 对齐时间戳。

**（2）JIT**  
**去优化（deoptimization）**、**C2 编译** 可能造成 **短暂变慢**（**题 35**）；**冷路径** 首次慢。

**（3）锁**  
**`jstack`** 或 **async-profiler** 看 **线程阻塞在 `synchronized`、`ReentrantLock`**；**池化资源** 耗尽表现为 **等待** 而非 CPU 高。

**（4）分配**  
**分配速率突增** → **GC 频率升**，毛刺增多；**逃逸分析** 与 **对象分配** 可优化。

**（5）排查顺序**  
**JFR 一次** 往往能看到 **GC、锁、IO** 占比；再决定 **调堆** 还是 **改代码**。

---

### 27. 场景：容器里 Java 进程被 OOM Killer？

**答：** **容器 memory limit** 含 **堆 + 元空间 + 线程栈 + 直接内存 + 本地库**；**`-Xmx`** 未预留 **非堆** 会被 ** cgroup OOM**；用 **`-XX:MaxRAMPercentage`** 等让 JVM **感知 cgroup**（版本有关）。

---

### 28. 场景：Metaspace 持续增长？

**答：** **类加载器泄漏**（OSGi、动态代理、Groovy 等）、**大量反射/字节码增强**；**MAT** 看 **ClassLoader**；**解决**：修复生命周期、**卸载** 条件或 **减少动态类**。

---

### 29. 场景：如何选择 G1 还是 ZGC？

**答：** 没有 **绝对优劣**，看 **延迟 SLA、堆规模、JDK 版本、团队熟悉度**。

**（1）G1**  
**JDK 8u40+** 起广泛用于 **服务端大堆**；**可预期停顿**（**`-XX:MaxGCPauseMillis`**），**Region** 化、**Mixed GC**。**适合** 大多数 **堆 4G～数十 G**、**吞吐与延迟折中** 的业务。

**（2）ZGC**  
**JDK 11+ 实验，15+ 生产可用**（以官方为准），**亚毫秒级停顿** 目标，**大堆** 场景更有优势；**CPU 与内存** 开销需评估，**架构**（染色指针等）与 **平台** 有关。

**（3）决策**  
**P99/P999 延迟** 极敏感、**堆很大** → **倾向 ZGC（在版本与 OS 支持前提下）**；**通用业务、求稳** → **G1** 更常见。**必须压测**：同样 **QPS** 下对比 **吞吐、停顿、资源**。

**（4）面试收束**  
**先 JDK 版本**，再 **指标驱动**，**勿跟风**。

---

### 30. 场景：`System.gc()` 能手动 GC 吗？

**答：** **建议**：生产少依赖；默认 **Full GC 语义** 可能很重（**`-XX:+DisableExplicitGC`** 常见）。**DirectByteBuffer** 场景历史上有 **显式触发 Cleaner** 的误用，**现代代码应规范释放**。

---

## 八、进阶补充

### 31. TLAB 是什么？

**答：** **Thread Local Allocation Buffer**，线程在 **Eden** 内优先 **本地分配**，减少 **分配竞争**；**仍** 在堆上，**GC 仍管**。

---

### 32. Card Table / 记忆集在分代 GC 里干什么？

**答：** 把老年代划 **卡页**，Young GC 时 **只扫跨代引用** 的卡，避免 **全老年代扫描**（与 **RSet** 概念相关，不同收集器实现不同）。

---

### 33. 强引用、软引用、弱引用、虚引用？

**答：** **Strong** 默认；**Soft** 内存不足可回收，适合 **缓存**；**Weak** 下次 GC 回收；**Phantom** 跟踪 **对象回收时机**、配合 **ReferenceQueue**。**`WeakHashMap`** 键弱引用常考。

---

### 34. `Class.forName` 与 `ClassLoader.loadClass` 区别？

**答：** **`forName`** 常 **触发初始化**；**`loadClass`** 双亲委派下 **只加载不初始化**（用途：**懒加载**、SPI）。**具体重载** 看方法签名。

---

### 35. JIT 的「去优化」是什么？

**答：** **假设不成立**（如 **类层次变化**、**未捕获分支**）时 **回退解释执行** 或 **重新编译**；可能导致 **短暂性能抖动**。

---

### 36. `VarHandle` / `Unsafe` 面试怎么提？

**答：** **底层并发与内存访问**；**`Unsafe` 私有 API** 逐步封装；**`VarHandle`**（Java9+）为 **标准** 替代方向之一。**生产慎用反射破封**。

---

### 37. JDK 模块系统（JPMS）与 Classpath？

**答：** **Java9+** **模块路径** 强封装 **`exports/opens`**；**类加载** 与 **反射访问** 受限；**迁移** 老项目常见 **拆包/开放** 问题。

---

## 九、面经普通题补充（近年）

### 38. `volatile` 除了可见性还有什么？（面经）

**答：** **禁止** 某些 **指令重排序**（**happens-before** 规则），对 **DCL、状态标志** 很关键；**不保证** **`i++` 原子性**。常与 **MESI、主内存** 一起被追问，答 **JMM 规范** 而非 **仅 CPU 缓存**。

### 39. happens-before 常见几条？

**答：** **程序次序**；**volatile 写 → 读**；**锁释放 → 同锁获取**；**线程 start**；**线程 join**；**传递性**。面试能 **举 2～3 条 + 例子** 即可。

### 40. AQS 在面经里怎么一句话？

**答：** **AbstractQueuedSynchronizer**，**state + CLH 变体队列**；**`ReentrantLock`、`Semaphore`、`CountDownLatch`** 等基于 AQS **实现同步语义**。深问再说 **独占/共享、acquire/release**。

### 41. 线程池线程数「经验公式」？

**答：** **CPU 密集**：约 **`Ncpu` 或 `Ncpu+1`**。**IO 密集**：**`Ncpu × (1 + IO等待/计算时间比)`** 或面经 **2×Ncpu** 起步；**最终以压测为准**。与 **题 27（线程池无界队列）** 一起考。

### 42. SafePoint / Stop-The-World 口头关系？

**答：** JVM 在 **安全点** 暂停线程做 **GC 根枚举、偏向锁撤销** 等；**STW** 阶段所有线程需 **跑到安全点**。**过多安全点** 或 **长时间不到达** 影响 **延迟**（与 **题 26 毛刺** 相关）。**JDK18+** 无偏向锁后，安全点相关表述仍以 **GC、去优化** 等为主。

---

## 十、高频补充（GC 细节·收集器·版本演进）

> 本节补充 **老年代/Humongous、浮动垃圾、跨代、类卸载、诊断、面经追问**；参数与行为以 **当前 JDK 官方 GC Tuning Guide** 为准。

### 43. 什么情况会导致「老年代空间不足」或晋升失败？

**答：** 本质是 **晋升 + 长期存活 + 大对象** 进入老年代的速率 **长期大于** 老年代 **回收 + 可用连续空间**。常见：**存活率过高**导致 Minor GC 后大量对象进老年代；**堆/老年代偏小**或 **年轻代过大**；**内存泄漏**（静态集合、缓存、监听器、线程池 **ThreadLocal** 未清理）；**Humongous/大数组** 挤占；**CMS 时代碎片**导致「总空闲够但没有连续块」；**并发 GC 跟不上分配**（如 CMS **Concurrent Mode Failure** 类问题，以历史版本为参考）。与 **题 24、9（Humongous）** 联动复习。

### 44. 「浮动垃圾」（Floating Garbage）是什么？

**答：** **并发标记** 期间用户线程仍在运行，**已死对象在标记时仍被当作存活**（或来不及处理），本轮回收 **暂不释放**，留给下次 GC。是 **用空间换停顿** 的代价，不是泄漏。**追问：** 与 **漏标** 区分——漏标是 **误回收存活**，浮动垃圾是 **延迟回收死亡**。

### 45. 卡表（Card Table）与 G1 的 RSet 口头怎么区分？

**答：** 二者都是 **记录跨区引用、避免全堆扫描** 的思路。**分代经典**：老年代切 **Card**，Young GC **Dirty Card** 里找指向新生代的引用。**G1**：**每个 Region 有 RSet**，记录 **哪些 Region 有引用指向本 Region**；实现上以 **Per-Region Table** 为主，**概念题**说清「** Granularity 与扫谁 **」即可。

### 46. 类什么时候可能「卸载」？为什么很难？

**答：** 需 **加载该类的 ClassLoader 可回收**（无引用）、**该类所有实例已死**、**无反射/ JNI 等强引用** 等条件同时满足；**Bootstrap/系统类** 基本不卸载。**OSGi、动态脚本、大量临时 ClassLoader** 若泄漏会导致 **Metaspace 涨**（见 **题 28**）。

### 47. `invokedynamic` 与 Lambda 和 JVM 有什么关系？

**答：** **字节码指令**；**Lambda** 与 **方法引用** 在实现上依赖 **` invokedynamic`** 绑定 **CallSite**（**Bootstrap Method**），**首次链接** 有一次性开销，热点后可 **JIT 内联**。**面经：** 与 **匿名内部类**（常多一个类文件）对比 **实现机制** 不同。

### 48. Native Memory Tracking（NMT）是什么？

**答：** **`-XX:NativeMemoryTracking=summary|detail`**，配合 **`jcmd VM.native_memory`** 看 **堆外**（元空间、线程栈、代码缓存、GC 等）占用；**容器 OOM** 排查常与 **题 27**、**Direct Memory** 一起看。

### 49. JFR（Java Flight Recorder）面试怎么说？

**答：** **低开销** 的事件采集，分析 **GC 停顿、分配、锁、IO、方法热点**；**JDK 商业协议与 OpenJDK 使用条款** 以当前版本为准。**与场景题 24、26** 对齐：**先 JFR/日志拿证据再调参**。

### 50. GC 日志里常见触发原因口头解释？

**答（示例名，以实际前缀与收集器为准）：** **Allocation Failure**（分配失败触发一次收集）；**Metadata GC Threshold**（元数据 GC）；**G1 Evacuation Pause**；**System.gc()**（显式）；**Ergonomics**（自适应触发）等。**面试：** 能说出 **「看日志第一行原因 + pause + 前后堆占用」**。

### 51. 伪共享（False Sharing）与 JVM？

**答：** **多核缓存行** 上不同变量被不同 CPU 修改导致 **缓存失效**；**`@Contended`**（JDK8）、**`@jdk.internal.vm.annotation.Contended`** 或 **padding** 缓解（**面经与并发文档** 联动）。**JIT** 可能对无关字段做布局优化，但 **缓存行** 仍是性能考点。

### 52. `StrongReference / SoftReference / WeakReference / PhantomReference` 与 ReferenceQueue？

**答：** **见题 33**；补充 **面经：** **Soft** 适合 **内存敏感缓存**；**Phantom** **get 总为 null**，用于 **回收后业务清理**（比 `finalize` 可控），需 **ReferenceQueue 轮询/线程消费**。**Cleaner**（DirectByteBuffer）类似思路。

### 53. ZGC / Shenandoah 口头对比（加分项）？

**答：** 均主打 **低停顿**、**并发整理**；**ZGC** 在 Oracle/OpenJDK 主线演进快（**分代 ZGC** 等以 Release Notes 为准）；**Shenandoah** 在 **Red Hat / 部分发行版** 场景常见。**共同追问：** **STW** 根枚举是否需 **停顿**、**读/写屏障** 成本、**平台与 JDK 版本**。

### 54. 容器（Docker/K8s）里 JVM 内存还要注意什么？

**答：** **`-Xmx` + 元空间 + 直接内存 + 栈 × 线程数 + CodeCache** 应 **小于 cgroup 限额**；使用 **`-XX:MaxRAMPercentage`**、**`-XX:InitialRAMPercentage`** 等让 JVM **读 cgroup**（版本差异查文档）；**题 27**。**误配：** 堆顶满 limit → **Killed**；堆过小 → **Heap OOM**。

### 55. `append` 字符串与 `StringBuilder`？

**答：** **编译器** 对 **纯常量** 拼接常 **编译期折叠**；**循环内** `+` 可能生成 **`StringBuilder`** 或次优代码，**热点** 应显式 **`StringBuilder`**；**字符串不可变性**、**常量池** 与 **题 5** 联动。

---

### （面经续）56～60 快问快答

**56. `StackOverflowError` vs `OutOfMemoryError`（栈）？** 前者 **栈深度/递归**；后者 **线程过多创建栈失败**（如 `unable to create new native thread` 周边症状）。

**57. 为什么需 happens-before 不能只信「最后一次写」？** **重排序** 与 **可见性** 无保证；需 **volatile/锁** 建立 **顺序与可见**。

**58. DCL 单例为何要用 `volatile`？** 防止 **构造与引用发布** 被重排序导致 **读到未构造完成的对象**。

**59. `synchronized` 可重入如何实现？** **同线程** 重复 **获取 monitor**，计数 **recursion/重入计数**（概念）；**object header** 与 **重量级** 结构相关。

**60. `wait/notify` 为何要在同步块里？** 需 **持有同一 monitor** 才能 **释放/唤醒** 语义正确，否则 **`IllegalMonitorStateException`**。

---

## 十一、自测清单

| 域 | 一句话 |
|----|--------|
| 规范 | **JVM vs HotSpot**、**JVMS** |
| 数据区 | **栈帧、堆、元空间、直接内存** |
| 对象 | **Mark Word、Klass、数组长、压缩指针** |
| 分代 | **Eden/S0/S1、晋升、Region 心智** |
| OOM | **heap/meta/direct/thread、StackOverflow** |
| Roots | **栈、JNI、静态、常量、同步持有、JVM 内部** |
| 收集器 | **G1 默认、ZGC 延迟、CMS 已移除** |
| G1 | **Mixed、RSet、SATB** |
| 并发标记 | **三色、漏标、写屏障** |
| 类加载 | **加载链接初始化、双亲委派、TCCL** |
| JIT | **C1/C2、逃逸、内联、去优化** |
| JMM | **happens-before、volatile、synchronized** |
| AQS | **state + CLH 变体** |
| 工具 | **jcmd、jstat、Arthas、MAT** |
| 参数 | **-Xmx、Metaspace、MaxGCPause、Xlog** |
| 场景 | **Full GC、Direct、容器、cgroup** |
| 进阶 | **TLAB、引用、Card Table、JPMS** |
| 面经 | **题 38～42** |
| GC 深入 | **GC Roots 表、老年代不足、浮动垃圾、卡表 vs RSet** |
| G1 | **IHOP、Humongous、`MaxGCPauseMillis` 语义** |
| 版本 | **偏向锁 JDK15/18、Epsilon、Parallel/Serial** |
| 诊断 | **NMT、JFR、GC 日志触发原因** |
| 其他 | **类卸载、`invokedynamic`/Lambda、容器内存、伪共享** |
| 快问 | **题 56～60** |

---

*路径：`interview/jvm/jvm-interview.md`（含 **九、十、（面经续）**；持续对照 [Oracle GC Tuning](https://docs.oracle.com/en/java/javase/21/gctuning/) 与当前 JDK Release Notes。）*
